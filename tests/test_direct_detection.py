"""Offline direct-mode protocol, evaluation, CLI, and GUI tests."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pydantic import ValidationError
from context_audit.catalog import FragmentCatalog
from context_audit.direct import DirectResponse, run_function, aggregate, messages
from context_audit.datasets.dappscan import DAppSCAN
from context_audit.direct_evaluation import evaluate


class DirectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog = FragmentCatalog(self.root)
        self.catalog.fragments = {'b': {'id': 'b', 'source': 'helper'}}
        self.payload = {'target': {'id': 'x.sol:function:0:20', 'signature': 'f()', 'contract': 'C', 'source': 'function f() public {}', 'lines': [1]}, 'available_context': [{'id': 'b'}]}

    def run_response(self, response, rounds=2):
        return run_function(self.payload, self.catalog, self.root/'r.json', rounds,
                            lambda *_: {'assessment': response, 'usage': {'total_tokens': 10}})

    def finding(self, kind='reentrancy'):
        return {'vulnerability_type': kind, 'swc_id': 'SWC-107', 'severity': 'high', 'explanation': 'Evidence', 'evidence_ids': [self.payload['target']['id']]}

    def test_final_states(self):
        for state in ('no_vulnerability_found', 'inconclusive'):
            r = self.run_response({'action': 'final', 'verdict': state, 'findings': []})
            self.assertEqual(r['assessment']['verdict'], state)
        with self.assertRaises(ValidationError):
            DirectResponse(action='final', verdict='vulnerable')

    def test_multiple_and_deduplication(self):
        findings = [self.finding(), self.finding(), self.finding('unchecked call')]
        r = self.run_response({'action': 'final', 'verdict': 'vulnerable', 'findings': findings})
        report = aggregate([r])[0]
        self.assertEqual(len(r['assessment']['findings']), 3)
        self.assertEqual(len(report['findings']), 2)
        self.assertEqual(report['usage']['total_tokens'], 10)

    def test_invalid_request(self):
        r = self.run_response({'action': 'request_context', 'requested_ids': ['missing']})
        self.assertTrue(r['errors'])
        self.assertEqual(r['assessment']['verdict'], 'inconclusive')

    def test_max_rounds(self):
        r = self.run_response({'action': 'request_context', 'requested_ids': ['b']}, 1)
        self.assertEqual(r['requested_fragments'], 1)
        self.assertEqual(r['assessment']['verdict'], 'inconclusive')

    def test_unseen_evidence(self):
        f = self.finding(); f['evidence_ids'] = ['missing']
        self.assertTrue(self.run_response({'action': 'final', 'verdict': 'vulnerable', 'findings': [f]})['errors'])

    def test_dataset_and_isolation(self):
        folder = self.root/'DAppSCAN-source'
        (folder/'contracts'/'project').mkdir(parents=True)
        (folder/'contracts'/'project'/'C.sol').write_text('contract C {}')
        (folder/'SWC_source').mkdir()
        label = {'file': 'C.sol', 'swc_id': 'SWC-107', 'description': 'SECRET_AUDIT', 'expected_verdict': 'SECRET_EXPECTED', 'lines': [98765]}
        (folder/'SWC_source'/'project.json').write_text(json.dumps([label]))
        dataset = DAppSCAN(self.root)
        self.assertEqual(dataset.files('project'), ['project/C.sol'])
        labels = dataset.labels('project/C.sol')
        self.assertEqual(labels[0]['lines'], [98765])
        r = self.run_response({'action': 'request_context', 'requested_ids': ['b']}, 1)
        serialized = json.dumps(r['prompt_journal'])
        for hidden in ('SWC-107', 'Reentrancy', 'SECRET_AUDIT', 'SECRET_EXPECTED', '98765'):
            self.assertNotIn(hidden, serialized)
        with self.assertRaises(ValueError):
            dataset.source_path('../escape.sol')

    def test_location_mismatch(self):
        r = self.run_response({'action': 'final', 'verdict': 'vulnerable', 'findings': [self.finding()]})
        r['dataset_file'] = 'project/C.sol'
        report = evaluate([{'file': 'project/C.sol', 'labels': [{'swc_id': 'SWC-107', 'function': 'other()', 'lines': []}]}], [r])
        self.assertEqual(report['labels'][0]['status'], 'UNEVALUABLE')
        self.assertEqual(len(report['additional_findings']), 1)

    def test_gui_rows(self):
        from context_audit.app.direct_page import result_rows
        r = self.run_response({'action': 'final', 'verdict': 'no_vulnerability_found'})
        self.assertEqual(result_rows([r])[0]['Function'], 'f()')

    def test_paste_index(self):
        from context_audit.app.direct_page import index_paste
        with patch('context_audit.app.direct_page.prepare', return_value=([], self.catalog)) as mocked:
            index_paste('../C.sol', 'contract C {}', self.root/'paste')
            self.assertEqual(mocked.call_args.args[0], self.root/'paste'/'C.sol')

    def test_real_paste_index(self):
        from context_audit.app.direct_page import index_paste
        payloads, catalog = index_paste('Demo.sol', 'pragma solidity ^0.4.25; contract Demo { uint x; function set(uint v) public { x=v; } function get() public view returns(uint) { return x; } }', self.root/'real')
        self.assertEqual(len(payloads), 2)
        self.assertTrue(payloads[0]['target']['state_writes'])
        self.assertNotIn('finding', json.dumps(payloads))

    def test_dry_run(self):
        spec = importlib.util.spec_from_file_location('runner', 'scripts/run_dappscan_direct_detection.py')
        runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
        folder = self.root/'contracts'/'project'; folder.mkdir(parents=True)
        (folder/'C.sol').write_text('contract C {}')
        with patch.object(runner, 'prepare', return_value=([self.payload], self.catalog)), patch.object(runner, 'run_function', side_effect=AssertionError('API forbidden')):
            runner.main(['--dataset-root', str(self.root), '--project', 'project', '--output', str(self.root/'out')])
        self.assertTrue((self.root/'out'/'prepared_targets.json').exists())

    def test_upstream_metadata(self):
        folder = self.root/'contracts'/'project'; folder.mkdir(parents=True)
        (folder/'C.sol').write_text('contract C {}')
        reports = self.root/'SWCsource'/'project'; reports.mkdir(parents=True)
        (reports/'C.json').write_text(json.dumps({'filePath': 'DAppSCAN-source/contracts/project/C.sol', 'SWCs': [{'category': 'SWC-107-Reentrancy', 'function': 'N/A', 'lineNumber': 'L12-L14'}]}))
        labels = DAppSCAN(self.root).labels('project/C.sol')
        self.assertEqual(labels[0]['lines'], [12,13,14])
        self.assertIsNone(labels[0]['function'])

    def test_request_then_final_and_prompt_isolation(self):
        responses = iter([
            {'action': 'request_context', 'requested_ids': ['b'], 'reason': 'Need helper'},
            {'action': 'final', 'verdict': 'no_vulnerability_found', 'explanation': 'No supported issue'}])
        self.payload['evaluation'] = {'swc_id': 'SECRET_SWC', 'description': 'SECRET_AUDIT'}
        r = run_function(self.payload, self.catalog, self.root/'r.json', analyze_fn=lambda *_: {'assessment': next(responses)})
        self.assertEqual(r['round_count'], 2)
        self.assertEqual(r['assessment']['verdict'], 'no_vulnerability_found')
        self.assertIn('helper', json.dumps(r['prompt_journal'][1]))
        self.assertNotIn('SECRET_', json.dumps(r['prompt_journal']))

    def test_multiple_contracts(self):
        import copy
        a = self.run_response({'action': 'final', 'verdict': 'no_vulnerability_found'})
        b = copy.deepcopy(a); b['target']['contract'] = 'Other'
        self.assertEqual(len(aggregate([a,b])), 2)

    def test_normalized_detection_and_missed(self):
        r = self.run_response({'action': 'final', 'verdict': 'vulnerable', 'findings': [self.finding()]})
        r['dataset_file'] = 'C.sol'
        cases = [{'file': 'C.sol', 'labels': [{'swc_id': 'SWC-107', 'function': 'f()', 'lines': [1]}, {'swc_id': 'SWC-104', 'function': 'f()', 'lines': [1]}]}]
        report = evaluate(cases, [r])
        self.assertEqual([x['status'] for x in report['labels']], ['DETECTED', 'MISSED'])
        self.assertEqual(report['metrics']['recall'], 0.5)

    def test_old_import(self):
        from context_audit.verifier import verify_prepared_finding
        self.assertTrue(callable(verify_prepared_finding))

    def test_summarize_without_api(self):
        spec = importlib.util.spec_from_file_location('runner', 'scripts/run_dappscan_direct_detection.py')
        runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
        (self.root/'prepared_targets.json').write_text('{"cases": []}')
        with patch('context_audit.direct.analyze', side_effect=AssertionError('API forbidden')):
            result = runner.main(['--summarize', '--output', str(self.root)])
        self.assertEqual(result['metrics']['total_api_calls'], 0)

    def test_streamlit_modes(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path('streamlit_app.py').resolve()), default_timeout=30).run()
        self.assertFalse(app.exception)
        app.radio(key='analysis_mode').set_value('Direct LLM Detection').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('This mode does not use Slither' in x.value for x in app.info))
        app.radio(key='analysis_mode').set_value('Slither Verification').run()
        self.assertFalse(app.exception)

"""Interactive scanner integration: real Solidity tools, mocked model responses."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from context_audit.app.config import ApplicationError
from context_audit.app.scanner import ScannerSettings, prepare_upload, scan_direct, scan_static, direct_report, report_html
from context_audit.app.scanner_worker import run_job
from context_audit.app.services import create_upload

ROOT = Path(__file__).resolve().parents[1]


class ScannerTests(unittest.TestCase):
    def upload(self, name='VulnerableVault.sol'):
        upload = create_upload(name, (ROOT / 'examples/scanner' / name).read_bytes())
        self.addCleanup(upload.close)
        return upload

    def request(self, upload, action='prepare'):
        return {'action': action, 'source': str(upload.source_path), 'source_sha256': upload.digest}

    def test_real_static_scan_finds_vulnerable_ordering(self):
        upload = self.upload()
        with patch('openai.OpenAI.__init__', side_effect=AssertionError('No API')):
            r = scan_static(upload, '0.8.24')
        self.assertTrue(any(f['type'] == 'reentrancy-eth' and f['severity'] == 'high' for f in r['findings']))
        self.assertEqual(r['usage']['api_calls'], 0)
        self.assertEqual(r['source_sha256'], upload.digest)

    def test_real_guarded_scan_removes_reentrancy_warning(self):
        with patch('openai.OpenAI.__init__', side_effect=AssertionError('No API')):
            r = scan_static(self.upload('GuardedVault.sol'), '0.8.24')
        self.assertFalse(any(f['type'].startswith('reentrancy') for f in r['findings']))
        self.assertTrue(any(f['type'] == 'low-level-calls' for f in r['findings']))

    def test_real_prepare_is_source_only_and_offline(self):
        upload = self.upload()
        with patch('openai.OpenAI.__init__', side_effect=AssertionError('No API')):
            p = prepare_upload(upload)
        self.assertEqual(p['compiler'], '0.8.24')
        self.assertEqual(p['analyzable_functions'], 2)
        self.assertEqual(p['batch_count'], 1)
        self.assertEqual(hashlib.sha256(upload.source_path.read_bytes()).hexdigest(), upload.digest)

    def test_live_scan_requires_credentials_before_worker(self):
        upload = self.upload()
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}), patch('context_audit.app.scanner._worker') as worker:
            with self.assertRaisesRegex(ApplicationError, 'API_KEY'):
                scan_direct(upload, {}, ScannerSettings('model'))
        worker.assert_not_called()

    def test_limits_are_checked_before_model_calls(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}):
            for s in (ScannerSettings(''), ScannerSettings('test', max_candidates=999), ScannerSettings('test', max_rounds=0)):
                with self.assertRaises(ApplicationError):
                    s.validate()

    def test_changed_prepared_source_is_rejected_before_worker(self):
        upload = self.upload()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}), patch('context_audit.app.scanner._worker') as worker:
            with self.assertRaisesRegex(ApplicationError, 'source changed'):
                scan_direct(upload, {'source_sha256': 'old'}, ScannerSettings('test'))
        worker.assert_not_called()

    def test_changed_source_bytes_are_rejected_before_preparation(self):
        upload = self.upload()
        request = self.request(upload)
        upload.source_path.write_text('modified')
        with self.assertRaisesRegex(ValueError, 'SOURCE_CHANGED'):
            run_job(request)

    def exercise_direct(self, verdict='confirmed', filename='VulnerableVault.sol', contradict=False):
        upload = self.upload(filename)
        preparation = run_job(self.request(upload))
        request = self.request(upload, 'scan')
        settings = ScannerSettings('test-fixture', max_rounds=3, max_candidates=1)
        request.update(settings=asdict(settings), prepared_identity=preparation['source_identity'],
            output=str(upload.source_path.parent / 'direct-run'))
        seen = []
        def discover(batch):
            row = next(f for f in batch['functions'] if f['signature'] == 'withdraw()')
            return {'assessment': {'examined_functions': [{'fragment_id': f['fragment_id'], 'reason': 'Reviewed structure'} for f in batch['functions']],
                'candidates': [{'candidate_id': 'one', 'contract': batch['contract'], 'primary_function': row['signature'],
                    'primary_fragment_id': row['fragment_id'], 'suspected_type': 'State update ordering',
                    'reason': 'The transfer and accounting relationship needs source verification.',
                    'related_fragment_ids': [], 'requested_context_ids': [], 'uncertainty': 'Ordering unknown from metadata.'}]},
                'usage': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}}
        def verify(payload, supplied, **kwargs):
            allowed = {payload['target']['id'], *(f['id'] for f in supplied)}
            seen.append(allowed)
            if not supplied:
                wanted = next(f['id'] for f in payload['available_context'] if f['kind'] == ('modifier' if verdict == 'rejected' else 'state_variable'))
                a = dict(action='request_context', requested_ids=[wanted], verdict=None, severity=None,
                    explanation='Need the related implementation.', evidence_ids=[], execution_flow=[], incomplete_evidence=[], verdict_basis=None)
            else:
                explanation = ('The supplied guard prevents the suspected path.' if verdict == 'rejected' else
                    'The transfer allows an attacker to reenter before the stored balance is cleared.')
                if contradict:
                    explanation = 'The supplied guard prevents the suspected path.'
                ids = [payload['target']['id'], supplied[0]['id']]
                a = dict(action='final', requested_ids=[], verdict=verdict, severity='high' if verdict == 'confirmed' else None,
                    explanation=explanation, evidence_ids=ids, execution_flow=['Read the balance, then follow the supplied function.'], incomplete_evidence=[],
                    verdict_basis=dict(mechanism_status='supported' if verdict == 'confirmed' else 'contradicted',
                        core_conditions='established' if verdict == 'confirmed' else 'not_established',
                        mitigation_status='none_identified' if verdict == 'confirmed' else 'effective',
                        mechanism='Transfer and state-update ordering relative to the caller.',
                        mitigation_reason='' if verdict == 'confirmed' else 'The supplied guard blocks reentry.',
                        unresolved_conditions=[], evidence_claims=[dict(fragment_id=f['id'], source_quote=f['source'],
                            role='dangerous_behavior' if verdict == 'confirmed' else 'protection') for f in [payload['target'], supplied[0]]]))
            return {'assessment': a, 'status': 'completed', 'usage': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only', 'OPENAI_MODEL': settings.model}), \
                patch('openai.OpenAI.__init__', side_effect=AssertionError('Model transport must be mocked')):
            response = run_job(request, discover_fn=discover, verify_fn=verify)
        return direct_report(upload, response, settings), seen

    def test_direct_discovery_selective_retrieval_and_confirmation(self):
        report, seen = self.exercise_direct()
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['findings'][0]['verdict'], 'confirmed')
        self.assertEqual(report['counts']['examined'], 2)
        self.assertEqual(len(seen[0]), 1)
        self.assertEqual(len(seen[1]), 2)
        self.assertEqual(report['usage']['api_calls'], 3)
        self.assertEqual(report['usage']['total_tokens'], 450)
        self.assertEqual(report['findings'][0]['retrieved_fragments'], 1)

    def test_direct_rejection_cites_supplied_modifier(self):
        report, _ = self.exercise_direct('rejected', 'GuardedVault.sol')
        self.assertEqual(report['findings'][0]['verdict'], 'rejected')
        self.assertTrue(any(f['kind'] == 'modifier' for f in report['findings'][0]['evidence']))

    def test_contradiction_becomes_partial_scan_without_accepted_verdict(self):
        report, _ = self.exercise_direct(contradict=True)
        self.assertEqual(report['status'], 'partial')
        self.assertIsNone(report['findings'][0]['verdict'])
        self.assertEqual(report['findings'][0]['original_model_verdict'], 'confirmed')
        self.assertIn('SEMANTIC_CONSISTENCY_FAILED', report['findings'][0]['errors'])

    def test_readable_report_escapes_source_and_model_text(self):
        report = scan_static(self.upload(), '0.8.24')
        report['source'] = '<script>alert(1)</script>'
        report['findings'][0]['explanation'] = '<img src=x onerror=alert(1)>'
        document = report_html(report)
        self.assertNotIn('<script>', document)
        self.assertIn('&lt;script&gt;', document)
        self.assertIn('&lt;img', document)

    def test_cli_default_is_local_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'scan'
            command = [sys.executable, 'scripts/scanner.py', 'scan', '--example', 'vulnerable', '--output', str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = (output / 'report.json').read_bytes()
            report = json.loads(before)
            self.assertEqual(report['usage']['api_calls'], 0)
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual((output / 'report.json').read_bytes(), before)

    def test_cli_direct_requires_explicit_live_flag(self):
        p = subprocess.run([sys.executable, 'scripts/scanner.py', 'scan', '--example', 'vulnerable', '--method', 'direct'], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('requires --live', p.stderr)

    def test_compile_error_is_actionable_without_traceback(self):
        upload = create_upload('invalid.sol', b'pragma solidity 0.8.24; contract Broken { nonsense }')
        self.addCleanup(upload.close)
        with self.assertRaisesRegex(ApplicationError, 'COMPILATION_FAILED'):
            prepare_upload(upload)


class SessionCredentialTests(unittest.TestCase):
    def test_session_credential_only_enters_child_environment(self):
        from types import SimpleNamespace
        from context_audit.app.scanner import _worker
        upload=create_upload('one.sol',b'pragma solidity 0.8.24; contract One { function act() external {} }')
        self.addCleanup(upload.close)
        settings=ScannerSettings('test-fixture')
        before=dict(os.environ)
        with patch('context_audit.app.scanner.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{}')) as run:
            settings.validate(api_key='synthetic-session-key')
            _worker(upload,'scan',settings=settings,preparation={'source_identity':{}},api_key='synthetic-session-key')
        self.assertEqual(run.call_args.kwargs['env']['OPENAI_API_KEY'],'synthetic-session-key')
        self.assertNotIn('synthetic-session-key',run.call_args.kwargs['input'])
        self.assertEqual(dict(os.environ),before)
        self.assertNotIn('api_key',asdict(settings))

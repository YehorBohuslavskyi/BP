"""Bounded investigation profiles: offline behavior, accounting and no auto-run."""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from context_audit import direct_discovery as d, direct_verification as v
from context_audit.app.scanner import ScannerSettings
from context_audit.app.scanner_worker import run_job
from context_audit.app.config import ApplicationError
from context_audit.app.services import create_upload
from context_audit.verification_profiles import limits_for
from context_audit.v2_pipeline import run_verification
from scripts import run_subscription_evaluation as runner
from test_direct_discovery import response
from test_direct_verification import request, final


class VerificationProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'Calls.sol'
        self.source.write_text('pragma solidity 0.4.25; contract C { uint value; ' +
            ' '.join('function f'+str(i)+'() public { value = '+str(i)+'; }' for i in range(11)) + ' }')
        self.contracts, self.catalog = d.prepare(self.source)
        row = self.contracts[0]['functions'][0]
        self.candidate = dict(candidate_id='test', contract='C', primary_function=row['signature'],
            primary_fragment_id=row['fragment_id'], suspected_type='Accounting hypothesis',
            reason='Check source and caller state constraints.', related_fragment_ids=[],
            requested_context_ids=[], uncertainty='External assumptions remain unresolved.')

    def test_single_factor_profiles_and_expanded_values(self):
        baseline = limits_for('baseline').model_dump()
        for name, field, value in [('rounds','max_rounds',5), ('context','max_fragments',12), ('coverage','max_candidates',6)]:
            changed = limits_for(name).model_dump()
            self.assertEqual({k for k in baseline if baseline[k] != changed[k]}, {field})
            self.assertEqual(changed[field], value)
        expanded = limits_for('expanded')
        self.assertEqual((expanded.max_candidates, expanded.max_rounds, expanded.max_fragments), (6,5,12))
        self.assertEqual(expanded.max_total_tokens, 400000)
        self.assertEqual(expanded.max_source_tokens, baseline['max_source_tokens'])
        with self.assertRaisesRegex(ValueError,'UNKNOWN_LIMIT_PROFILE'):
            limits_for('arbitrary')

    def test_more_rounds_really_deliver_additional_context_without_auto_promotion(self):
        results = {}
        for profile in ('baseline','rounds'):
            calls = []
            def verify(payload, supplied, **kwargs):
                wire = json.loads(v.messages(payload, supplied)[1]['content'])
                calls.append(wire)
                if wire['available_context'] and len(supplied) < 4:
                    return request([wire['available_context'][0]['id']])
                return final(payload, supplied, 'inconclusive')
            results[profile] = v.verify_candidate(self.candidate,self.contracts,self.catalog,
                limits=limits_for(profile),analyze_fn=verify)
            self.assertEqual(results[profile]['verdict'],'inconclusive')
        self.assertEqual(results['baseline']['round_count'],3)
        self.assertEqual(results['rounds']['round_count'],5)
        self.assertEqual(results['baseline']['retrieved_fragments'],2)
        self.assertEqual(results['rounds']['retrieved_fragments'],4)

    def test_more_context_really_allows_ten_fragments_with_same_round_count(self):
        results = {}
        for profile in ('baseline','context'):
            def verify(payload, supplied, **kwargs):
                if not supplied:
                    menu = v.requestable_context(payload,supplied)
                    count = min(10,payload['retrieval_budget']['max_new_fragments'])
                    return request([e['id'] for e in menu[:count]])
                return final(payload,supplied,'inconclusive')
            results[profile] = v.verify_candidate(self.candidate,self.contracts,self.catalog,
                limits=limits_for(profile),analyze_fn=verify)
        self.assertEqual(results['baseline']['retrieved_fragments'],8)
        self.assertEqual(results['context']['retrieved_fragments'],10)
        self.assertEqual(results['baseline']['round_count'],results['context']['round_count'])

    def test_more_candidates_reduces_budget_skips_without_changing_discovery(self):
        def discover(batch):
            candidates = [{**self.candidate,'candidate_id':'test-'+str(i),
                'primary_function':row['signature'],'primary_fragment_id':row['fragment_id']}
                for i,row in enumerate(batch['functions'][:6])]
            return response(batch,candidates)
        found = d.run_discovery(self.contracts,self.catalog,execute=True,analyze_fn=discover)
        before = copy.deepcopy(found)
        counts = {}
        for profile in ('baseline','coverage'):
            report = run_verification(found,self.contracts,self.catalog,self.root/profile,
                limits=limits_for(profile),analyze_fn=lambda p,s,**kw:final(p,s,'inconclusive'))
            counts[profile] = report['coverage_counts']
        self.assertEqual(found,before)
        self.assertEqual(counts['baseline']['skipped_candidates'],4)
        self.assertEqual(counts['coverage']['skipped_candidates'],0)
        self.assertEqual(counts['coverage']['inconclusive_candidates'],6)
        self.assertEqual(counts['coverage']['confirmed_candidates'],0)

    def test_source_and_token_guards_still_stop_expanded_profile(self):
        for limits in (limits_for('expanded').model_copy(update={'max_source_tokens':1}),
                       limits_for('expanded').model_copy(update={'max_total_tokens':1})):
            client = Mock(side_effect=AssertionError('must stop before model'))
            result = v.verify_candidate(self.candidate,self.contracts,self.catalog,limits=limits,analyze_fn=client)
            client.assert_not_called()
            self.assertIsNone(result['verdict'])

    def test_scanner_profile_and_worker_pass_all_caps_to_pipeline(self):
        settings = ScannerSettings.for_profile('offline','expanded',provider='codex')
        settings.validate()
        upload = create_upload('Calls.sol',self.source.read_bytes())
        self.addCleanup(upload.close)
        req = dict(action='prepare',source=str(upload.source_path),source_sha256=upload.digest)
        prepared = run_job(req)
        req.update(action='scan',settings=asdict(settings),prepared_identity=prepared['source_identity'],output=str(self.root/'scan'))
        transport = Mock()
        transport.state = {}
        with patch('context_audit.codex_transport.CodexTransport',return_value=transport) as factory, \
             patch('context_audit.app.scanner_worker.discovery.run_discovery',return_value={'coverage':[]}), \
             patch('context_audit.app.scanner_worker.run_verification',return_value={}) as pipeline:
            run_job(req)
        actual = pipeline.call_args.kwargs['limits']
        self.assertEqual(actual.model_dump(),limits_for('expanded').model_dump())
        self.assertEqual(factory.call_args.kwargs['max_calls'],prepared['batch_count']+30)
        self.assertEqual(factory.call_args.kwargs['max_tokens'],settings.observed_token_cap(prepared['batch_count']))
        self.assertGreater(factory.call_args.kwargs['max_tokens'],400000)

    def test_invalid_custom_fragment_cap_rejected_before_worker(self):
        settings = ScannerSettings('offline',provider='codex',max_fragments=-1)
        with self.assertRaises(ApplicationError):
            settings.validate()

    def test_fresh_development_profile_records_caps_and_preserves_parent(self):
        proposal = self.root/'proposal'
        proposal.mkdir()
        case = dict(id='development',source_identity={'source_sha256':'a'*64},project='p',split='development',
            budget={'max_reserved_tokens':60000},limits=limits_for('baseline').model_dump())
        original = {'cases':[case]}
        (proposal/'manifest.json').write_text(json.dumps(original))
        before = (proposal/'manifest.json').read_bytes()
        with patch.object(runner,'known_source_hashes',return_value=set()), \
             patch.object(runner,'catalog_for',return_value=(self.contracts,self.catalog)), \
             patch.object(runner,'identity',return_value={}):
            runner.prepare(proposal,self.root/'new-plan',1,'expanded')
        plan = json.loads((self.root/'new-plan/plan.json').read_text())
        self.assertEqual(plan['limit_profile'],'expanded')
        self.assertEqual(plan['cases'][0]['limits'],limits_for('expanded').model_dump())
        self.assertEqual(plan['limits']['max_model_turns'],plan['cases'][0]['budget']['max_codex_turns'])
        self.assertEqual(plan['limits']['max_observed_tokens'],plan['cases'][0]['budget']['max_observed_tokens'])
        self.assertEqual(plan['cases'][0]['budget']['max_verification_tokens'],400000)
        self.assertEqual((proposal/'manifest.json').read_bytes(),before)
        self.assertFalse((self.root/'new-plan/cases').exists())

    def test_nonbaseline_cannot_silently_change_validation_or_heldout_study(self):
        with self.assertRaisesRegex(ValueError,'DEVELOPMENT_PILOT'):
            runner.prepare(self.root/'missing',self.root/'unused',None,'expanded')
        self.assertFalse((self.root/'unused').exists())

    def test_cli_profile_reaches_scanner_without_real_transport(self):
        module = runpy.run_path('scripts/scanner.py')
        fake = Mock(return_value={})
        argv = ['scanner.py','scan','--example','vulnerable','--method','direct','--live',
                '--provider','codex','--limit-profile','expanded','--output',str(self.root/'cli')]
        globals_ = module['main'].__globals__
        with patch.object(sys,'argv',argv), patch.dict(globals_,{
            'prepare_upload':lambda _: {},'scan_direct':fake,
            'direct_report':lambda *a:dict(status='completed',counts={},usage={}),
            'report_html':lambda _: '<html></html>'}):
            self.assertEqual(module['main'](),0)
        settings = fake.call_args.args[2]
        self.assertEqual(settings.max_rounds,5)
        self.assertEqual(settings.max_candidates,6)
        self.assertEqual(settings.max_fragments,12)


    def test_case_observed_cap_is_enforced_even_when_plan_cap_is_larger(self):
        from context_audit.v2_artifacts import digest,file_hash
        proposal=self.root/'cap-proposal'
        proposal.mkdir()
        (proposal/'manifest.json').write_text('{}')
        output=self.root/'cap-run'
        output.mkdir()
        batches,_=d.make_batches(self.contracts)
        limits=limits_for('baseline')
        case=dict(id='one',source=str(self.source),source_identity=self.catalog.source_identity,split='development',
            limits=limits.model_dump(),budget=dict(max_discovery_turns=len(batches),
                max_codex_turns=len(batches)+6,max_verification_tokens=200000,max_observed_tokens=250000))
        plan=dict(configuration=runner.identity(),proposal=str(proposal),model='offline',cases=[case],
            proposal_manifest_sha256=file_hash(proposal/'manifest.json'),
            limits=dict(max_model_turns=20,max_observed_tokens=750000,max_case_observed_tokens=400000))
        (output/'plan.json').write_text(json.dumps(plan))
        transport=Mock()
        transport.state=dict(calls=0,observed_tokens=0,stopped=False)
        found=dict(coverage=[],errors=[])
        report=dict(coverage_counts=dict(processing_failures=0,skipped_candidates=0,pending_candidates=0,confirmed_candidates=0))
        with patch.dict('os.environ',{},clear=True), patch.object(runner,'catalog_for',return_value=(self.contracts,self.catalog)), \
             patch.object(runner,'CodexTransport',return_value=transport) as factory, \
             patch.object(d,'run_discovery',return_value=found),patch.object(runner,'run_verification',return_value=report):
            runner.execute(output,digest(plan))
        self.assertEqual(factory.call_args.kwargs['max_tokens'],250000)

    def test_inconsistent_case_call_budget_stops_before_transport(self):
        from context_audit.v2_artifacts import digest,file_hash
        proposal=self.root/'invalid-proposal'
        proposal.mkdir()
        (proposal/'manifest.json').write_text('{}')
        output=self.root/'invalid-run'
        output.mkdir()
        case=dict(id='one',limits=limits_for('expanded').model_dump(),
            budget=dict(max_discovery_turns=0,max_codex_turns=1,max_verification_tokens=400000))
        plan=dict(configuration=runner.identity(),proposal=str(proposal),model='offline',cases=[case],
            proposal_manifest_sha256=file_hash(proposal/'manifest.json'))
        (output/'plan.json').write_text(json.dumps(plan))
        with patch.dict('os.environ',{},clear=True), patch.object(runner,'catalog_for',return_value=(self.contracts,self.catalog)), \
             patch.object(runner,'CodexTransport') as factory, self.assertRaisesRegex(ValueError,'BUDGET_MISMATCH'):
            runner.execute(output,digest(plan))
        factory.assert_not_called()
        self.assertFalse((output/'cases').exists())


if __name__ == '__main__':
    unittest.main()

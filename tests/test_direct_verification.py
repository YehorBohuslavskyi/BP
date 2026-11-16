"""Mode B v2 integration and adversarial protocol tests. All inference is mocked."""
import copy
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

from slither.core.declarations import Function
from context_audit import direct_discovery as discovery
from context_audit import direct_verification as verifier
from context_audit import v2_pipeline as pipeline
from context_audit.v2_artifacts import digest, discovery_manifest
from test_direct_discovery import prepared, response
from consistency_fixtures import with_basis


def final(payload, supplied, verdict='confirmed'):
    return {'assessment': with_basis({'action': 'final', 'requested_ids': [], 'verdict': verdict,
            'severity': 'high' if verdict == 'confirmed' else None,
            'explanation': {'confirmed': 'The supplied source allows an attacker to reach the dangerous operation.',
                'rejected': 'The supplied protection prevents the suspected path.',
                'inconclusive': 'Required external behavior remains unknown.'}[verdict],
            'evidence_ids': [payload['target']['id'], *(f['id'] for f in supplied)],
            'execution_flow': ['Mocked caller path through supplied function.'],
            'incomplete_evidence': ['Missing external behavior'] if verdict == 'inconclusive' else []}, [payload['target'], *supplied]),
            'usage': {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}}


def request(ids):
    return {'assessment': {'action': 'request_context', 'requested_ids': ids, 'verdict': None,
            'severity': None, 'verdict_basis': None, 'explanation': 'Need the relevant implementation', 'evidence_ids': [],
            'execution_flow': [], 'incomplete_evidence': []},
            'usage': {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}}


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.contracts, self.catalog = prepared(self.root)
        self.discovery = self.discover()
        self.candidate = self.discovery['candidates'][0]

    def discover(self):
        def mock(batch):
            candidates = []
            row = next((r for r in batch['functions'] if r['signature'] == 'withdraw(uint256)'), None)
            if row:
                candidates = [dict(candidate_id='one', contract=batch['contract'], primary_function=row['signature'],
                    primary_fragment_id=row['fragment_id'], suspected_type='Reentrancy', reason='External call interacts with shared state',
                    related_fragment_ids=[r['fragment_id'] for r in batch['functions'] if r['signature'] == 'deposit()'],
                    requested_context_ids=[m['fragment_id'] for m in row['modifiers']], uncertainty='Check guards and ordering')]
            return response(batch, candidates)
        return discovery.run_discovery(self.contracts, self.catalog, execute=True, analyze_fn=mock)

    def reseal(self):
        self.discovery['manifest'] = discovery_manifest(self.discovery, self.catalog, 24000, True)

    def run_candidate(self, fn=None, **kwargs):
        return verifier.verify_candidate(self.candidate, self.contracts, self.catalog,
                analyze_fn=fn or (lambda p, s, **kw: final(p, s)), **kwargs)

    def run_pipeline(self, fn=None, **kwargs):
        return pipeline.run_verification(self.discovery, self.contracts, self.catalog, self.root / 'out',
            analyze_fn=fn or (lambda p, s, **kw: final(p, s)), **kwargs)

    def test_confirmed_end_to_end_and_locations(self):
        report = self.run_pipeline()
        self.assertEqual(report['coverage_counts']['confirmed_candidates'], 1)
        self.assertEqual(report['coverage_counts']['candidates_verified'], 1)
        self.assertEqual(report['coverage_counts']['not_selected'], 2)
        result = report['issues'][0]['result']
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['preparation_mode'], 'FULL_INDEX')
        self.assertTrue(result['source_locations'][result['evidence_ids'][0]]['lines'])
        self.assertEqual(report['efficiency']['total']['total_tokens'], 45)
        self.assertEqual(report['efficiency']['total']['api_calls'], 3)
        self.assertTrue((self.root / 'out/report.md').is_file())

    def test_rejected(self):
        result = self.run_candidate(lambda p, s, **kw: final(p, s, 'rejected'))
        self.assertEqual(result['verdict'], 'rejected')
        self.assertIsNone(result['severity'])

    def test_inconclusive(self):
        result = self.run_candidate(lambda p, s, **kw: final(p, s, 'inconclusive'))
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertTrue(result['incomplete_evidence'])

    def test_multiple_requests_and_accounting(self):
        modifier = self.candidate['requested_context_ids'][0]
        deposit = self.candidate['related_fragment_ids'][0]
        def mock(p, s, **kw):
            return request([modifier if not s else deposit]) if len(s) < 2 else final(p, s)
        result = self.run_candidate(mock)
        self.assertEqual(result['round_count'], 3)
        self.assertEqual(result['usage']['total_tokens'], 45)
        self.assertEqual(result['retrieved_fragments'], 2)
        self.assertEqual([r['supplied_ids'] for r in result['requests']], [[modifier], [deposit]])
        self.assertEqual(set(result['evidence_ids']), {self.candidate['primary_fragment_id'], modifier, deposit})
        self.assertEqual(len(result['source_locations']), 3)

    def test_invalid_primary_and_contract(self):
        for field, value in [('primary_fragment_id', 'fragment-fake'), ('primary_function', 'missing()'), ('contract', 'Missing')]:
            with self.subTest(field=field):
                raw = {**self.candidate, field: value}
                result = verifier.verify_candidate(raw, self.contracts, self.catalog,
                    analyze_fn=lambda *a, **k: self.fail('Must not call model'))
                self.assertEqual(result['status'], 'processing_failed')
                self.assertIsNone(result['verdict'])
                self.assertEqual(result['round_count'], 0)

    def test_missing_source(self):
        self.catalog.fragments[self.candidate['primary_fragment_id']]['source'] = ''
        result = self.run_candidate()
        self.assertEqual(result['status'], 'processing_failed')
        self.assertIsNone(result['verdict'])

    def test_fabricated_and_unseen_evidence(self):
        for fid in ['fragment-fake', self.candidate['related_fragment_ids'][0]]:
            def mock(p, s, **kw):
                r = final(p, s); r['assessment']['evidence_ids'] = [fid]; return r
            result = self.run_candidate(mock)
            self.assertEqual(result['errors'][0]['code'], 'UNSEEN_EVIDENCE_ID')
            self.assertIsNone(result['verdict'])

    def test_bad_protocol_variants(self):
        for mutation in [lambda r: r.update(action='bad'), lambda r: r.update(evidence_ids=[]),
                         lambda r: r.update(requested_ids=['fragment-fake']),
                         lambda r: r.update(verdict='rejected', severity='high'),
                         lambda r: r.update(incomplete_evidence=['Required guard missing'])]:
            def mock(p, s, **kw):
                r = final(p, s); mutation(r['assessment']); return r
            result = self.run_candidate(mock)
            self.assertEqual(result['status'], 'processing_failed')
            self.assertIsNone(result['verdict'])

    def test_malformed_json_and_incomplete_response(self):
        for raw in [{'assessment': '{'}, {'assessment': {}, 'status': 'incomplete'}]:
            result = self.run_candidate(lambda *a, **k: raw)
            self.assertEqual(result['status'], 'processing_failed')
            self.assertIsNone(result['verdict'])

    def test_invalid_and_repeated_context_requests(self):
        for fid, code in [('fragment-fake', 'INVALID_CONTEXT_ID'), (self.candidate['primary_fragment_id'], 'REPEATED_CONTEXT_ID')]:
            result = self.run_candidate(lambda *a, **k: request([fid]))
            self.assertEqual(result['errors'][0]['code'], code)
            self.assertFalse(result['provided_context'])

    def test_round_limit_is_not_security_verdict(self):
        result = self.run_candidate(lambda *a, **k: request(self.candidate['requested_context_ids']), limits=verifier.Limits(max_rounds=1))
        self.assertEqual(result['status'], 'budget_exhausted')
        self.assertIsNone(result['verdict'])
        self.assertEqual(result['requests'][0]['supplied_ids'], [])

    def test_fragment_and_source_limits(self):
        result = self.run_candidate(lambda *a, **k: request(self.candidate['requested_context_ids']), limits=verifier.Limits(max_fragments=0))
        self.assertEqual(result['errors'][0]['code'], 'CONTEXT_BUDGET')
        result = self.run_candidate(limits=verifier.Limits(max_source_tokens=1))
        self.assertEqual(result['round_count'], 0)
        self.assertEqual(result['errors'][0]['code'], 'PRIMARY_SOURCE_BUDGET')

    def test_input_and_total_token_limits(self):
        for limits in [verifier.Limits(max_input_tokens=1), verifier.Limits(max_total_tokens=1)]:
            result = self.run_candidate(limits=limits)
            self.assertEqual(result['errors'][0]['code'], 'TOKEN_BUDGET')
            self.assertEqual(result['usage']['api_calls'], 0)

    def test_candidate_limit(self):
        report = self.run_pipeline(limits=verifier.Limits(max_candidates=0))
        self.assertEqual(report['coverage_counts']['skipped_candidates'], 1)
        self.assertEqual(report['coverage_counts']['rejected_candidates'], 0)
        self.assertEqual(report['efficiency']['verification']['api_calls'], 0)

    def test_exact_dedup_preserves_ids_and_usage(self):
        self.discovery['candidates'].append({**self.candidate, 'candidate_id': 'duplicate'})
        self.reseal()
        report = self.run_pipeline()
        self.assertEqual(report['coverage_counts']['candidates_generated'], 2)
        self.assertEqual(report['coverage_counts']['unique_candidates'], 1)
        self.assertEqual(len(report['issues'][0]['original_candidate_ids']), 2)
        self.assertEqual(report['efficiency']['verification']['total_tokens'], 15)

    def test_overlapping_distinct_claims_not_merged(self):
        self.discovery['candidates'].append({**self.candidate, 'candidate_id': 'different', 'reason': 'Distinct reachable path'})
        self.reseal()
        calls = []
        def mock(p, s, **kw):
            calls.append(1); return final(p, s, 'confirmed' if len(calls) == 1 else 'rejected')
        report = self.run_pipeline(mock)
        self.assertEqual(report['coverage_counts']['unique_candidates'], 2)
        self.assertEqual(report['coverage_counts']['confirmed_candidates'], 1)
        self.assertEqual(report['coverage_counts']['rejected_candidates'], 1)
        self.assertFalse(report['possible_overlaps'][0]['merged'])

    def test_duplicate_candidate_ids_rejected_before_calls(self):
        self.discovery['candidates'].append(copy.deepcopy(self.candidate)); self.reseal()
        with self.assertRaises(ValueError): self.run_pipeline()

    def test_resume_reuses_without_calls_or_double_counting(self):
        before = self.run_pipeline()
        after = self.run_pipeline(lambda *a, **k: self.fail('No duplicate API calls'), resume=True)
        self.assertEqual(before['efficiency']['total'], after['efficiency']['total'])
        self.assertEqual(after['efficiency']['verification_this_invocation']['api_calls'], 0)
        self.assertTrue(after['issues'][0]['reused'])

    def test_source_version_mismatch(self):
        self.run_pipeline()
        self.source.write_text(self.source.read_text() + '\n')
        self.contracts, self.catalog = discovery.prepare(self.source)
        with self.assertRaisesRegex(ValueError, 'mismatch'): self.run_pipeline(resume=True)

    def test_model_prompt_and_limit_mismatch(self):
        self.run_pipeline()
        with patch.dict(os.environ, {'OPENAI_MODEL': 'different'}):
            with self.assertRaises(ValueError): self.run_pipeline(resume=True)
        with patch.object(verifier, 'SYSTEM_PROMPT', 'changed'):
            with self.assertRaises(ValueError): self.run_pipeline(resume=True)
        with self.assertRaises(ValueError): self.run_pipeline(resume=True, limits=verifier.Limits(max_rounds=5))

    def test_catalog_sanitizer_manifest_mismatch(self):
        for field in ('catalog_sha256', 'sanitizer_sha256', 'sanitized_project_sha256'):
            identity = copy.deepcopy(self.catalog.source_identity)
            self.catalog.source_identity[field] = 'changed'
            with self.assertRaises(ValueError): self.run_pipeline()
            self.catalog.source_identity = identity

    def test_modified_discovery_and_checkpoint_rejected(self):
        self.run_pipeline()
        self.discovery['candidates'][0]['reason'] = 'tampered'
        with self.assertRaisesRegex(ValueError, 'checksum'): self.run_pipeline(resume=True)
        self.discovery = self.discover()
        checkpoint = next((self.root / 'out/sessions').glob('*.json'))
        data = json.loads(checkpoint.read_text()); data['result']['verdict'] = 'rejected'
        checkpoint.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'checksum'): self.run_pipeline(resume=True)

    def test_interrupted_partial_report_and_resume_no_replay(self):
        self.discovery['candidates'].append({**self.candidate, 'candidate_id': 'later', 'reason': 'Other claim'})
        self.reseal()
        def interrupt(*a, **k): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.run_pipeline(interrupt)
        partial = json.loads((self.root / 'out/report.json').read_text())
        self.assertEqual(partial['coverage_counts']['processing_failures'], 1)
        self.assertEqual(partial['coverage_counts']['pending_candidates'], 1)
        report = self.run_pipeline(resume=True)
        self.assertEqual(report['coverage_counts']['candidates_verified'], 1)
        self.assertEqual(report['coverage_counts']['processing_failures'], 1)
        self.assertEqual(report['efficiency']['verification_this_invocation']['api_calls'], 1)

    def test_api_error_secrets_not_logged(self):
        def mock(*a, **k): raise RuntimeError('Authorization sk-SECRET password SECRET')
        result = self.run_candidate(mock)
        self.assertEqual(result['status'], 'processing_failed')
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertIsNone(result['verdict'])

    def test_gt_isolation_and_untrusted_metadata(self):
        result = self.run_candidate()
        transport = json.dumps(result['rounds'][0]['messages'])
        self.assertNotIn('SWC-107', transport)
        self.assertNotIn('DAppSCAN', transport)
        self.assertNotIn('ground truth', transport)
        self.catalog.fragments[self.candidate['primary_fragment_id']]['source'] += '\n// SWC-107 DAppSCAN ground truth'
        result = self.run_candidate()
        self.assertEqual(result['status'], 'processing_failed')
        self.assertEqual(result['round_count'], 0)

    def test_source_fallback_can_request_and_abstain(self):
        original = Function.generate_slithir_and_analyze
        def fail(f):
            if f.name == 'withdraw': raise ValueError('IR failure')
            return original(f)
        with patch.object(Function, 'generate_slithir_and_analyze', fail):
            self.contracts, self.catalog = discovery.prepare(self.source)
        self.discovery = self.discover(); self.candidate = self.discovery['candidates'][0]
        def mock(p, s, **kw):
            self.assertEqual(p['preparation_mode'], 'SOURCE_FALLBACK')
            self.assertIn('state_dependencies', p['metadata_unavailable'])
            return request(self.candidate['requested_context_ids']) if not s else final(p, s, 'inconclusive')
        result = self.run_candidate(mock)
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertEqual(result['round_count'], 2)

    def test_cli_combined_and_verification_only_resume(self):
        with patch.dict(os.environ, {'OPENAI_MODEL': 'mock'}):
            saved_discovery = self.discover()
            argv = ['run_direct_discovery.py', str(self.source), '--stage', 'all', '--run', '--output', str(self.root / 'cli')]
            with patch.object(sys, 'argv', argv), patch('context_audit.direct_discovery.analyze', side_effect=lambda b: response(b)), patch.object(verifier, 'analyze', side_effect=lambda p, s, **kw: final(p, s)):
                # Return prepared candidates through the normal run_discovery interface.
                with patch('context_audit.direct_discovery.run_discovery', return_value=saved_discovery):
                    runpy.run_path('scripts/run_direct_discovery.py', run_name='__main__')
            saved = self.root / 'cli/discovery.json'
            argv = ['run_direct_discovery.py', str(self.source), '--stage', 'verify', '--run', '--candidates', str(saved), '--output', str(self.root / 'verify')]
            with patch.object(sys, 'argv', argv), patch.object(verifier, 'analyze', side_effect=lambda p, s, **kw: final(p, s)):
                runpy.run_path('scripts/run_direct_discovery.py', run_name='__main__')
            with patch.object(sys, 'argv', argv + ['--resume']), patch.object(verifier, 'analyze', side_effect=AssertionError('No API calls on resume')):
                runpy.run_path('scripts/run_direct_discovery.py', run_name='__main__')

    def test_transport_configuration(self):
        from types import SimpleNamespace
        candidate, row = verifier.validate_candidate(self.candidate, self.contracts, self.catalog)
        payload = verifier.payload_for(candidate, row, self.catalog)
        parsed = verifier.VerificationResponse.model_validate(final(payload, [])['assessment'])
        with patch.dict(os.environ, {'OPENAI_MODEL': 'mock'}), patch.object(verifier, 'OpenAI') as client:
            from openai.types.responses import Response, ResponseOutputMessage, ResponseOutputText, ResponseUsage
            client.return_value.responses.create.return_value = Response.model_construct(status='completed', model='mock', id='id',
                usage=ResponseUsage.model_construct(input_tokens=10, output_tokens=5, total_tokens=15),
                output=[ResponseOutputMessage.model_construct(type='message', id='m', role='assistant', status='completed',
                    content=[ResponseOutputText.model_construct(type='output_text', text=parsed.model_dump_json(), annotations=[])])])
            result = verifier.analyze(payload, [], max_output_tokens=1234)
            kwargs = client.return_value.responses.create.call_args.kwargs
            self.assertEqual(kwargs['max_output_tokens'], 1234)
            self.assertFalse(kwargs['store'])
            self.assertTrue(kwargs['text']['format']['strict'])
            self.assertEqual(kwargs['text']['format']['name'], 'VerificationResponse')
            self.assertEqual(result['usage']['total_tokens'], 15)


    def test_empty_discovery_has_no_verification_calls(self):
        self.discovery = discovery.run_discovery(self.contracts, self.catalog, execute=True, analyze_fn=response)
        report = self.run_pipeline(lambda *a, **k: self.fail('No candidates'))
        self.assertEqual(report['coverage_counts']['unique_candidates'], 0)
        self.assertEqual(report['efficiency']['verification']['api_calls'], 0)
        self.assertIsNone(report['efficiency']['verification_context_reduction'])

    def test_later_candidate_survives_processing_failure(self):
        self.discovery['candidates'].append({**self.candidate, 'candidate_id': 'later', 'reason': 'Other claim'})
        self.reseal()
        calls = []
        def mock(p, s, **kw):
            calls.append(1)
            if len(calls) == 1: return {'assessment': 'bad JSON'}
            return final(p, s, 'rejected')
        report = self.run_pipeline(mock)
        self.assertEqual(report['coverage_counts']['processing_failures'], 1)
        self.assertEqual(report['coverage_counts']['rejected_candidates'], 1)

    def test_completed_checkpoint_protocol_revalidated(self):
        self.run_pipeline()
        path = next((self.root / 'out/sessions').glob('*.json'))
        saved = json.loads(path.read_text())
        saved['result']['evidence_ids'] = ['fragment-fake']
        saved['result_sha256'] = digest(saved['result'])
        path.write_text(json.dumps(saved))
        with self.assertRaises(ValueError): self.run_pipeline(resume=True)

    def test_hard_interruption_pending_call_is_not_replayed(self):
        self.run_pipeline()
        path = next((self.root / 'out/sessions').glob('*.json'))
        saved = json.loads(path.read_text())
        result = saved['result']
        result.update(status='running', verdict=None, severity=None)
        result['rounds'][0].pop('response')
        result['rounds'][0]['status'] = 'pending_call'
        result['usage'] = {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'api_calls': 1}
        saved['result_sha256'] = digest(result)
        path.write_text(json.dumps(saved))
        report = self.run_pipeline(lambda *a, **k: self.fail('Unknown call outcome must not replay'), resume=True)
        self.assertEqual(report['coverage_counts']['processing_failures'], 1)
        self.assertIsNone(report['issues'][0]['result']['verdict'])

    def test_unsanitized_retrieval_never_reaches_model(self):
        modifier = self.candidate['requested_context_ids'][0]
        self.catalog.fragments[modifier]['source'] += '\n// SWC-107 ground truth'
        result = self.run_candidate(lambda *a, **k: request([modifier]))
        self.assertEqual(result['errors'][0]['code'], 'CONTEXT_SOURCE_ERROR')
        self.assertEqual(result['round_count'], 1)
        self.assertEqual(result['provided_context'], [])

    def test_source_token_budget_for_added_context(self):
        from context_audit.cgt_inference import estimated_tokens
        primary_size = estimated_tokens(self.catalog.get(self.candidate['primary_fragment_id'])['source'])
        result = self.run_candidate(lambda *a, **k: request(self.candidate['requested_context_ids']),
            limits=verifier.Limits(max_source_tokens=primary_size))
        self.assertEqual(result['errors'][0]['code'], 'CONTEXT_BUDGET')
        self.assertFalse(result['provided_context'])

    def test_invalid_limits_and_offline_cli_live_guard(self):
        with self.assertRaises(ValueError): verifier.Limits(max_rounds=0)
        argv = ['run_direct_discovery.py', str(self.source), '--stage', 'all', '--output', str(self.root / 'no-api')]
        with patch.object(sys, 'argv', argv), self.assertRaises(SystemExit):
            runpy.run_path('scripts/run_direct_discovery.py', run_name='__main__')
        self.assertFalse((self.root / 'no-api').exists())

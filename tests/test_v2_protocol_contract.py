"""Exercise examples emitted by the real prompt through the wire schema/SDK/parser."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import jsonschema
from context_audit import direct_verification as v
from context_audit import direct_discovery as d
from context_audit.v2_response import response_format, parse_result
from context_audit.v2_pipeline import run_verification
from context_audit.v2_smoke import CountedTransport, RETRY_BUDGET
from test_direct_discovery import prepared, response
from test_v2_verification_failures import envelope
from test_direct_verification import final


class ProtocolContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.contracts, self.catalog = prepared(self.root)
        contract = next(c for c in self.contracts if c['contract'] == 'Vault')
        row = next(f for f in contract['functions'] if f['signature'] == 'withdraw(uint256)')
        self.candidate = dict(candidate_id='test-candidate', contract='Vault', primary_function=row['signature'],
            primary_fragment_id=row['fragment_id'], suspected_type='Mock type', reason='Mock reason',
            related_fragment_ids=[], requested_context_ids=[], uncertainty='Mock unknown')
        self.payload = v.payload_for(self.candidate, row, self.catalog)
        self.prompt = v.messages(self.payload, [])
        self.protocol = json.loads(self.prompt[1]['content'])['response_protocol']
        self.examples = self.protocol['examples']
        self.schema = response_format(v.VerificationResponse)['format']['schema']

    def parse(self, data):
        return parse_result(envelope(json.dumps(data)), v.VerificationResponse, candidate_id=self.candidate['candidate_id'])

    def run_candidate(self, data, **kwargs):
        return v.verify_candidate(self.candidate, self.contracts, self.catalog,
            analyze_fn=lambda p, s, **kw: self.parse(data), **kwargs)

    def assert_invalid(self, data):
        result = self.run_candidate(data)
        self.assertEqual(result['status'], 'processing_failed')
        self.assertIsNone(result['verdict'])
        self.assertEqual(result['usage']['total_tokens'], 120)
        diag = result['errors'][0]['diagnostic']
        self.assertEqual(diag['candidate_id'], self.candidate['candidate_id'])
        self.assertTrue(diag['validation_errors'])
        self.assertEqual(diag['processing_stage'], 'response_parsing')
        return diag

    def test_prompt_fields_are_exact_wire_schema_contract(self):
        self.assertEqual(self.protocol['required_fields'], self.schema['required'])
        self.assertEqual(self.protocol['fields'], self.schema['properties'])
        self.assertFalse(self.protocol['extra_fields_allowed'])
        self.assertFalse(self.schema['additionalProperties'])
        self.assertEqual(len(self.schema['required']), 9)
        self.assertIn('verdict_basis', self.schema['required'])
        self.assertIn('VerdictBasis', self.protocol['definitions'])
        self.assertTrue(response_format(v.VerificationResponse)['format']['strict'])
        self.assertIn('confirmed MUST have incomplete_evidence=[]', v.SYSTEM_PROMPT)
        self.assertIn('severity MUST be null for rejected and inconclusive', v.SYSTEM_PROMPT)
        self.assertIn('without Markdown fences', v.SYSTEM_PROMPT)

    def test_all_emitted_examples_pass_schema_and_installed_sdk_parser(self):
        self.assertEqual(set(self.examples), {'request_context', 'confirmed', 'rejected', 'inconclusive'})
        for name, example in self.examples.items():
            with self.subTest(name=name):
                self.assertEqual(set(example), set(self.schema['required']))
                jsonschema.validate(example, self.schema)
                result = self.parse(example)
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(result['assessment'], example)
                self.assertEqual(result['usage']['total_tokens'], 120)

    def test_request_example_drives_real_selective_context_round(self):
        def mock(payload, supplied, **kwargs):
            contract = json.loads(v.messages(payload, supplied)[1]['content'])['response_protocol']
            example = contract['examples']['request_context'] if not supplied else final(payload, supplied, 'rejected')['assessment']
            return self.parse(example)
        result = v.verify_candidate(self.candidate, self.contracts, self.catalog, analyze_fn=mock)
        self.assertEqual(result['round_count'], 2)
        self.assertEqual(result['verdict'], 'rejected')
        self.assertEqual(result['retrieved_fragments'], 1)
        self.assertEqual(result['usage']['total_tokens'], 240)

    def test_syntax_examples_cannot_be_copied_as_security_assessments(self):
        for verdict in ('confirmed', 'rejected', 'inconclusive'):
            with self.subTest(verdict=verdict):
                result = self.run_candidate(self.examples[verdict])
                self.assertIsNone(result['verdict'])
                self.assertEqual(result['status'], 'processing_failed')
                self.assertEqual(result['errors'][0]['code'], 'SEMANTIC_CONSISTENCY_FAILED')

    def test_examples_never_request_already_supplied_ids(self):
        supplied = [v.safe_fragment(self.catalog.get(f['id'])) for f in self.payload['available_context']]
        contract = json.loads(v.messages(self.payload, supplied)[1]['content'])['response_protocol']
        self.assertNotIn('request_context', contract['examples'])

    def test_each_missing_required_field_is_rejected(self):
        for field in self.schema['required']:
            with self.subTest(field=field):
                bad = copy.deepcopy(self.examples['confirmed']); del bad[field]
                diag = self.assert_invalid(bad)
                self.assertIn([field], [e['location'] for e in diag['validation_errors']])

    def test_incorrect_enums_not_coerced(self):
        for field, value in [('action', 'FINAL'), ('verdict', 'vulnerable'), ('verdict', ' confirmed '), ('severity', 'HIGH')]:
            with self.subTest(field=field, value=value):
                self.assert_invalid({**self.examples['confirmed'], field: value})

    def test_wrong_types_for_every_field_are_rejected(self):
        for field, value in [('action', 1), ('requested_ids', 'fragment-1'), ('verdict', True), ('severity', 3),
                             ('explanation', []), ('evidence_ids', {}), ('execution_flow', 'a -> b'), ('incomplete_evidence', None)]:
            with self.subTest(field=field): self.assert_invalid({**self.examples['confirmed'], field: value})

    def test_extra_field_rejected_without_logging_name_or_value(self):
        diag = self.assert_invalid({**self.examples['confirmed'], 'SECRET_FIELD': 'SECRET_VALUE'})
        self.assertNotIn('SECRET', json.dumps(diag))

    def test_malformed_json_and_markdown_are_not_repaired(self):
        for text in ('{', '```json\n' + json.dumps(self.examples['confirmed']) + '\n```'):
            result = parse_result(envelope(text), v.VerificationResponse, candidate_id='test-candidate')
            self.assertEqual(result['status'], 'response_parse_failed')
            self.assertIsNone(result['assessment'])
            self.assertEqual(result['usage']['total_tokens'], 120)
            self.assertEqual(result['diagnostic']['validation_errors'][0]['type'], 'json_invalid')

    def test_fabricated_context_ids_fail_catalog_validation(self):
        result = self.run_candidate({**self.examples['request_context'], 'requested_ids': ['fragment-fabricated']})
        self.assertIsNone(result['verdict'])
        self.assertEqual(result['errors'][0]['code'], 'INVALID_CONTEXT_ID')
        self.assertFalse(result['provided_context'])

    def test_unseen_and_fabricated_evidence_rejected(self):
        for fid in ('fragment-fabricated', self.payload['available_context'][0]['id']):
            result = self.run_candidate({**self.examples['confirmed'], 'evidence_ids': [fid]})
            self.assertEqual(result['errors'][0]['code'], 'UNSEEN_EVIDENCE_ID')
            self.assertIsNone(result['verdict'])

    def test_confirmation_without_evidence_rejected(self):
        diag = self.assert_invalid({**self.examples['confirmed'], 'evidence_ids': []})
        self.assertEqual(diag['validation_errors'][0]['rule'], 'decisive_verdict_without_evidence')

    def test_confirmation_with_unresolved_conditions_rejected(self):
        diag = self.assert_invalid({**self.examples['confirmed'], 'incomplete_evidence': ['Required source missing']})
        self.assertEqual(diag['validation_errors'][0]['rule'], 'confirmation_with_missing_evidence')

    def test_empty_discovery_is_coverage_not_security_verdict(self):
        with patch.dict(os.environ, {'OPENAI_MODEL': 'mock'}):
            discovery = d.run_discovery(self.contracts, self.catalog, execute=True, analyze_fn=response)
            report = run_verification(discovery, self.contracts, self.catalog, self.root / 'out',
                analyze_fn=lambda *a, **k: self.fail('Empty candidate result must not call model'))
        self.assertEqual(report['coverage_counts']['unique_candidates'], 0)
        self.assertEqual(report['efficiency']['verification']['api_calls'], 0)
        self.assertEqual(report['issues'], [])
        self.assertEqual(report['coverage_counts']['not_selected'], report['coverage_counts']['total_functions'])

    def test_source_context_budget_exhaustion_has_no_verdict(self):
        from context_audit.cgt_inference import estimated_tokens
        primary_tokens = estimated_tokens(self.payload['target']['source'])
        result = self.run_candidate(self.examples['request_context'], limits=v.Limits(max_source_tokens=primary_tokens))
        self.assertEqual(result['status'], 'budget_exhausted')
        self.assertIsNone(result['verdict'])
        self.assertEqual(result['errors'][0]['code'], 'CONTEXT_BUDGET')
        self.assertFalse(result['provided_context'])

    def test_ordinary_client_preserves_usage_and_safe_validation_details(self):
        bad = {**self.examples['confirmed'], 'incomplete_evidence': ['SECRET']}
        with patch.dict(os.environ, {'OPENAI_MODEL': 'mock'}), patch.object(v, 'OpenAI') as client:
            client.return_value.responses.create.return_value = envelope(json.dumps(bad))
            result = v.verify_candidate(self.candidate, self.contracts, self.catalog)
            call = client.return_value.responses.create.call_args.kwargs
            self.assertEqual(call['text'], response_format(v.VerificationResponse))
            expected_payload={**self.payload,'retrieval_budget':{
                'rounds_after_this':v.Limits().max_rounds-1,
                'max_new_fragments':v.Limits().max_fragments,
                'max_new_source_tokens':v.Limits().max_source_tokens-v.estimated_tokens(self.payload['target']['source']),
                'verification_tokens_remaining':v.Limits().max_total_tokens}}
            self.assertEqual(call['input'], v.messages(expected_payload, []))
        self.assertIsNone(result['verdict'])
        self.assertEqual(result['usage']['total_tokens'], 120)
        diag = result['errors'][0]['diagnostic']
        self.assertEqual(diag['validation_errors'][0]['rule'], 'confirmation_with_missing_evidence')
        self.assertNotIn('SECRET', json.dumps(result))

    def test_counted_runner_uses_same_prompt_schema_and_parser(self):
        client = MagicMock()
        client.responses.input_tokens.count.return_value = type('Count', (), {'input_tokens': 100})()
        client.responses.create.return_value = envelope(json.dumps(final(self.payload, [], 'inconclusive')['assessment']))
        transport = CountedTransport(client, 'mock', self.root / 'counted', dict(RETRY_BUDGET))
        result = v.verify_candidate(self.candidate, self.contracts, self.catalog, analyze_fn=transport.verify)
        counted = client.responses.input_tokens.count.call_args.kwargs
        generated = client.responses.create.call_args.kwargs
        self.assertEqual(counted['text'], generated['text'])
        self.assertEqual(generated['text'], response_format(v.VerificationResponse))
        self.assertEqual(counted['input'], generated['input'])
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertEqual(result['usage']['total_tokens'], 120)

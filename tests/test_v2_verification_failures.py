"""Mock-only failures, SDK parser reproduction, and provenance-checked retry plans."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import httpx2
import jsonschema
from openai import APITimeoutError, APIConnectionError, BadRequestError, AuthenticationError, RateLimitError, InternalServerError
from openai.lib._parsing._responses import type_to_text_format_param, parse_response
from openai.types.responses import Response, ResponseOutputMessage, ResponseOutputText, ResponseUsage
from pydantic import ValidationError
from context_audit import direct_discovery as d
from context_audit import direct_verification as v
from context_audit.v2_artifacts import atomic_json
from context_audit.v2_smoke import CountedTransport, RETRY_BUDGET, prepare_verification_plan, execute_plan, SmokeStopped
from test_direct_discovery import prepared, response


def envelope(text, status='completed'):
    return Response.model_construct(id='mock-response', model='mock', status=status,
        output=[ResponseOutputMessage.model_construct(id='msg', type='message', role='assistant', status='completed',
            content=[ResponseOutputText.model_construct(type='output_text', text=text, annotations=[])])],
        usage=ResponseUsage.model_construct(input_tokens=100, output_tokens=20, total_tokens=120))


class VerificationFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.contracts, self.catalog = prepared(self.root)
        def discover(batch):
            row = next((f for f in batch['functions'] if f['signature'] == 'withdraw(uint256)'), None)
            candidates = [dict(candidate_id='candidate', contract=batch['contract'], primary_function=row['signature'],
                primary_fragment_id=row['fragment_id'], suspected_type='Accounting', reason='Mock hypothesis',
                related_fragment_ids=[], requested_context_ids=[], uncertainty='Mock unknown')] if row else []
            return response(batch, candidates)
        with patch.dict(os.environ, {'OPENAI_MODEL': 'mock'}):
            self.discovery = d.run_discovery(self.contracts, self.catalog, execute=True, analyze_fn=discover)
        self.candidate = self.discovery['candidates'][0]
        self.saved = self.root / 'saved-discovery.json'
        atomic_json(self.saved, self.discovery)
        self.client = MagicMock()
        self.client.responses.input_tokens.count.return_value = SimpleNamespace(input_tokens=100)
        self.transport = CountedTransport(self.client, 'mock', self.root / 'transport', dict(RETRY_BUDGET))
        self.request = httpx2.Request('POST', 'https://api.openai.com/v1/responses', headers={'Authorization': 'Bearer SECRET'})

    def run_failure(self, error):
        self.client.responses.create.side_effect = error
        return v.verify_candidate(self.candidate, self.contracts, self.catalog, analyze_fn=self.transport.verify)

    def assert_failure(self, result, category, status=None):
        self.assertEqual(result['status'], 'processing_failed')
        self.assertIsNone(result['verdict'])
        self.assertFalse(result['evidence_ids'])
        diag = result['errors'][0]['diagnostic']
        self.assertEqual(diag['category'], category)
        self.assertEqual(diag['candidate_id'], self.candidate['candidate_id'])
        self.assertEqual(diag['round'], 1)
        self.assertEqual(diag['processing_stage'], 'generation_request')
        if status is not None: self.assertEqual(diag['http_status'], status)
        self.assertTrue(self.transport.state['stopped'])
        self.assertEqual(self.client.responses.create.call_count, 1)
        # No raw exception text, authorization or response body in diagnostics.
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('SECRET', json.dumps(self.transport.state))
        self.assertNotIn('request', self.transport.state['events'][0])

    def test_timeout(self):
        self.assert_failure(self.run_failure(APITimeoutError(self.request)), 'timeout')

    def test_connection_failure(self):
        self.assert_failure(self.run_failure(APIConnectionError(message='SECRET', request=self.request)), 'connection_failure')

    def http_failure(self, cls, status, category, body=None):
        error = cls('SECRET', response=httpx2.Response(status, request=self.request), body=body or {'message': 'SECRET'})
        self.assert_failure(self.run_failure(error), category, status)

    def test_http_400(self): self.http_failure(BadRequestError, 400, 'invalid_request')
    def test_http_401(self): self.http_failure(AuthenticationError, 401, 'authentication_failure')
    def test_http_429(self): self.http_failure(RateLimitError, 429, 'rate_limit')
    def test_http_500(self): self.http_failure(InternalServerError, 500, 'provider_server_error')
    def test_unsupported_model_parameter(self):
        self.http_failure(BadRequestError, 400, 'unsupported_model_parameter', {'code': 'unsupported_parameter', 'message': 'SECRET'})

    def test_malformed_response_json_preserves_received_usage(self):
        self.client.responses.create.return_value = envelope('{"action": SECRET')
        result = v.verify_candidate(self.candidate, self.contracts, self.catalog, analyze_fn=self.transport.verify)
        self.assertEqual(result['status'], 'processing_failed')
        self.assertIsNone(result['verdict'])
        self.assertEqual(result['usage']['total_tokens'], 120)
        self.assertEqual(result['unknown_usage_calls'], 0)
        self.assertEqual(result['rounds'][0]['response']['response_id'], 'mock-response')
        diag = result['errors'][0]['diagnostic']
        self.assertEqual(diag['processing_stage'], 'response_parsing')
        self.assertEqual(diag['exception_type'], 'ValidationError')
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('SECRET', json.dumps(self.transport.state))

    def test_malformed_api_envelope_does_not_escape_gate(self):
        self.client.responses.create.return_value = object()
        result = v.verify_candidate(self.candidate, self.contracts, self.catalog, analyze_fn=self.transport.verify)
        self.assertIsNone(result['verdict'])
        self.assertEqual(result['status'], 'processing_failed')
        self.assertTrue(self.transport.state['stopped'])
        self.assertEqual(result['unknown_usage_calls'], 1)

    def final(self):
        from consistency_fixtures import with_basis
        return with_basis(dict(action='final', requested_ids=[], verdict='confirmed', severity='high',
            explanation='The supplied operation allows an attacker to bypass the intended invariant.',
            evidence_ids=[self.candidate['primary_fragment_id']], execution_flow=['Mock flow'], incomplete_evidence=[]),
            [self.catalog.get(self.candidate['primary_fragment_id'])])

    def test_schema_valid_protocol_invalid_reproduces_old_parser_failure(self):
        data = self.final(); data['incomplete_evidence'] = ['Missing required authorization source SECRET']
        schema = type_to_text_format_param(v.VerificationResponse)['schema']
        jsonschema.validate(data, schema)  # Wire JSON schema allows this combination.
        with self.assertRaises(ValidationError):
            parse_response(text_format=v.VerificationResponse, input_tools=None, response=envelope(json.dumps(data)))
        self.client.responses.create.return_value = envelope(json.dumps(data))
        result = v.verify_candidate(self.candidate, self.contracts, self.catalog, analyze_fn=self.transport.verify)
        self.assertIsNone(result['verdict'])
        self.assertEqual(result['status'], 'processing_failed')
        self.assertEqual(result['usage']['total_tokens'], 120)
        self.assertNotIn('SECRET', json.dumps(result))

    def test_incomplete_output_keeps_usage_without_parsing(self):
        self.client.responses.create.return_value = envelope('{', status='incomplete')
        result = v.verify_candidate(self.candidate, self.contracts, self.catalog, analyze_fn=self.transport.verify)
        self.assertIsNone(result['verdict'])
        self.assertEqual(result['usage']['total_tokens'], 120)
        self.assertEqual(self.transport.state['stop_reason'], 'INCOMPLETE_STRUCTURED_RESPONSE')

    def test_context_request_and_final_remain_compatible(self):
        modifier = next(fid for fid, f in self.catalog.fragments.items() if f['kind'] == 'modifier')
        ask = dict(action='request_context', requested_ids=[modifier], verdict=None, severity=None,
            explanation='Need guard source', evidence_ids=[], execution_flow=[], incomplete_evidence=[], verdict_basis=None)
        done = self.final(); done['evidence_ids'].append(modifier)
        self.client.responses.create.side_effect = [envelope(json.dumps(ask)), envelope(json.dumps(done))]
        result = v.verify_candidate(self.candidate, self.contracts, self.catalog, analyze_fn=self.transport.verify)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['verdict'], 'confirmed')
        self.assertEqual(result['retrieved_fragments'], 1)
        self.assertEqual(result['usage']['total_tokens'], 240)

    def test_offline_retry_plan_reuses_discovery_and_no_old_session(self):
        before = self.saved.read_bytes()
        with patch('openai.OpenAI.__init__', side_effect=AssertionError('No real API')):
            plan = prepare_verification_plan(self.source, 'mock', self.root / 'retry', self.saved)
        self.assertEqual(plan['budget']['max_discovery_calls'], 0)
        self.assertEqual(plan['budget']['max_generation_calls'], 3)
        self.assertEqual(plan['original_candidate_ids'], [self.candidate['candidate_id']])
        self.client.responses.create.return_value = envelope(json.dumps(self.final()))
        with patch.dict(os.environ, {'OPENAI_MODEL': 'mock', 'OPENAI_API_KEY': 'offline-test', 'OPENAI_BASE_URL': 'https://api.openai.com/v1'}), \
             patch.object(d, 'run_discovery', side_effect=AssertionError('Must not rediscover')):
            report = execute_plan(plan, client_factory=lambda **kw: self.client)
            with self.assertRaises(ValueError): execute_plan(plan, client_factory=lambda **kw: self.fail('No replay'))
        self.assertEqual(report['smoke_transport']['discovery_calls'], 0)
        self.assertEqual(report['smoke_transport']['generation_calls'], 1)
        self.assertTrue(report['discovery_reused'])
        self.assertEqual(report['efficiency']['verification_this_invocation']['api_calls'], 1)
        self.assertEqual(self.saved.read_bytes(), before)

    def test_retry_rejects_model_and_candidate_mutation(self):
        with self.assertRaises(ValueError):
            prepare_verification_plan(self.source, 'other-model', self.root / 'retry', self.saved)
        plan = prepare_verification_plan(self.source, 'mock', self.root / 'retry', self.saved)
        changed = copy.deepcopy(self.discovery); changed['candidates'][0]['reason'] = 'changed'
        atomic_json(self.saved, changed)
        with patch.dict(os.environ, {'OPENAI_MODEL': 'mock', 'OPENAI_API_KEY': 'offline-test'}):
            with self.assertRaises(ValueError): execute_plan(plan, client_factory=lambda **kw: self.fail('No API'))
        self.assertFalse((self.root / 'retry').exists())

    def test_normal_verifier_retains_safe_diagnostics(self):
        def fail(*a, **kw): raise APITimeoutError(self.request)
        result = v.verify_candidate(self.candidate, self.contracts, self.catalog, analyze_fn=fail)
        self.assertEqual(result['errors'][0]['diagnostic']['exception_type'], 'APITimeoutError')
        self.assertEqual(result['errors'][0]['diagnostic']['verifier_stage'], 'API_CALL')
        self.assertEqual(result['errors'][0]['diagnostic']['candidate_id'], self.candidate['candidate_id'])
        self.assertIsNone(result['verdict'])


    def test_interrupt_retains_explicit_processing_status(self):
        result = self.run_failure(KeyboardInterrupt())
        self.assertEqual(result['status'], 'interrupted')
        self.assertIsNone(result['verdict'])
        self.assertTrue(result['errors'][0]['diagnostic']['interrupted'])
        with self.assertRaises(SmokeStopped):
            self.transport.call('verification', [], v.VerificationResponse, 2500, candidate_id=self.candidate['candidate_id'])

    def test_retry_rejects_source_edit_before_client_creation(self):
        plan = prepare_verification_plan(self.source, 'mock', self.root / 'retry', self.saved)
        self.source.write_text(self.source.read_text() + '\n')
        with patch.dict(os.environ, {'OPENAI_MODEL': 'mock', 'OPENAI_API_KEY': 'offline-test'}):
            with self.assertRaises(ValueError): execute_plan(plan, client_factory=lambda **kw: self.fail('No API'))
        self.assertFalse((self.root / 'retry').exists())


    def test_safe_diagnostics_identify_each_protocol_rule(self):
        from context_audit.v2_errors import exception_metadata
        cases = [
            ({'requested_ids': ['x', 'x']}, 'duplicate_context_ids'),
            ({'action': 'request_context', 'requested_ids': ['x']}, 'invalid_context_request'),
            ({'requested_ids': ['x']}, 'invalid_final_response'),
            ({'evidence_ids': []}, 'decisive_verdict_without_evidence'),
            ({'verdict': 'inconclusive'}, 'severity_without_confirmation'),
            ({'incomplete_evidence': ['SECRET']}, 'confirmation_with_missing_evidence'),
        ]
        for change, rule in cases:
            with self.subTest(rule=rule):
                with self.assertRaises(ValidationError) as caught:
                    v.VerificationResponse.model_validate({**self.final(), **change})
                diagnostic = exception_metadata(caught.exception)
                self.assertEqual(diagnostic['validation_errors'][0]['rule'], rule)
                self.assertNotIn('SECRET', json.dumps(diagnostic))

    def test_safe_diagnostics_identify_field_without_exposing_input(self):
        from context_audit.v2_errors import exception_metadata
        with self.assertRaises(ValidationError) as caught:
            v.VerificationResponse.model_validate({**self.final(), 'severity': 'SECRET', 'SECRET_FIELD': 'SECRET'})
        diagnostic = exception_metadata(caught.exception)
        self.assertIn(['severity'], [e['location'] for e in diagnostic['validation_errors']])
        self.assertIn(['<field>'], [e['location'] for e in diagnostic['validation_errors']])
        self.assertNotIn('SECRET', json.dumps(diagnostic))

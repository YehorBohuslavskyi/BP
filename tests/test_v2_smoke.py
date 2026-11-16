"""Offline tests for hard smoke-call caps and counted token reservations."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from openai.lib._parsing._responses import type_to_text_format_param
from context_audit import direct_discovery as d
from context_audit import direct_verification as v
from context_audit.v2_smoke import BUDGET, CountedTransport, SmokeStopped, prepare_plan, execute_plan


class SmokeBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client = MagicMock()
        self.client.responses.input_tokens.count.return_value = SimpleNamespace(input_tokens=100)
        self.client.responses.create.return_value = self.response(d.DiscoveryResponse(examined_functions=[], candidates=[]))

    def response(self, parsed, count=100, output=20):
        from openai.types.responses import Response, ResponseOutputMessage, ResponseOutputText, ResponseUsage
        return Response.model_construct(status='completed', id='mock', model='mock',
            output=[ResponseOutputMessage.model_construct(id='msg', type='message', role='assistant', status='completed',
                content=[ResponseOutputText.model_construct(type='output_text', text=parsed.model_dump_json(), annotations=[])])],
            usage=ResponseUsage.model_construct(input_tokens=count, output_tokens=output, total_tokens=count + output))

    def transport(self, **limits):
        return CountedTransport(self.client, 'mock', self.root, {**BUDGET, **limits})

    def call(self, transport, stage='verification', maximum=100):
        return transport.call(stage, [{'role': 'user', 'content': 'test'}], d.DiscoveryResponse, maximum)

    def test_generation_limit_includes_both_stages(self):
        t = self.transport(max_generation_calls=2)
        self.call(t, 'discovery'); self.call(t)
        with self.assertRaises(SmokeStopped): self.call(t)
        self.assertEqual(self.client.responses.create.call_count, 2)
        self.assertEqual(self.client.responses.input_tokens.count.call_count, 2)

    def test_discovery_limit(self):
        t = self.transport()
        self.call(t, 'discovery')
        with self.assertRaises(SmokeStopped): self.call(t, 'discovery')
        self.assertEqual(t.state['discovery_calls'], 1)
        self.assertEqual(t.state['count_calls'], 1)

    def test_count_call_limit(self):
        t = self.transport(max_count_calls=1)
        self.call(t)
        with self.assertRaises(SmokeStopped): self.call(t)
        self.assertEqual(t.state['count_calls'], 1)

    def test_token_reservations_are_not_refunded(self):
        t = self.transport(max_reserved_tokens=200)
        self.call(t)
        self.assertEqual(t.state['reserved_tokens'], 200)
        with self.assertRaises(SmokeStopped): self.call(t)
        self.assertEqual(self.client.responses.create.call_count, 1)

    def test_input_limit_blocks_generation(self):
        t = self.transport(max_input_tokens_per_call=99)
        with self.assertRaises(SmokeStopped): self.call(t)
        self.assertEqual(t.state['count_calls'], 1)
        self.assertEqual(t.state['generation_calls'], 0)
        self.client.responses.create.assert_not_called()

    def test_counted_total_limit_blocks_generation(self):
        t = self.transport(max_reserved_tokens=199)
        with self.assertRaises(SmokeStopped): self.call(t)
        self.assertEqual(t.state['generation_calls'], 0)

    def test_count_failure_is_not_retried_or_logged_with_secrets(self):
        t = self.transport()
        self.client.responses.input_tokens.count.side_effect = RuntimeError('sk-SECRET')
        with self.assertRaises(SmokeStopped): self.call(t)
        with self.assertRaises(SmokeStopped): self.call(t)
        self.client.responses.create.assert_not_called()
        self.assertEqual(t.state['count_calls'], 1)
        self.assertNotIn('SECRET', (self.root / 'budget_ledger.json').read_text())

    def test_uncertain_generation_retains_reservation(self):
        t = self.transport()
        self.client.responses.create.side_effect = KeyboardInterrupt()
        with self.assertRaises(SmokeStopped): self.call(t)
        self.assertEqual(t.state['reserved_tokens'], 200)
        self.assertEqual(t.state['events'][0]['status'], 'generation_outcome_unknown')
        with self.assertRaises(SmokeStopped): self.call(t)
        self.assertEqual(t.state['generation_calls'], 1)

    def test_usage_count_mismatch_stops_subsequent_calls(self):
        t = self.transport()
        self.client.responses.create.return_value = self.response(d.DiscoveryResponse(examined_functions=[], candidates=[]), count=101)
        result = self.call(t)
        self.assertEqual(result['usage']['input_tokens'], 101)
        self.assertTrue(t.state['stopped'])
        with self.assertRaises(SmokeStopped): self.call(t)

    def test_missing_usage_and_incomplete_response_stop(self):
        t = self.transport()
        self.client.responses.create.return_value.usage = None
        self.call(t)
        self.assertEqual(t.state['stop_reason'], 'USAGE_OR_COUNT_MISMATCH')
        with self.assertRaises(SmokeStopped): self.call(t)

    def test_schema_in_count_matches_generation_and_no_retries(self):
        t = self.transport(); self.call(t)
        count = self.client.responses.input_tokens.count.call_args.kwargs
        generated = self.client.responses.create.call_args.kwargs
        self.assertEqual(count['input'], generated['input'])
        self.assertEqual(count['text']['format'], generated['text']['format'])
        self.assertEqual(generated['service_tier'], 'default')
        self.assertEqual(generated['truncation'], 'disabled')
        self.assertFalse(generated['store'])

    def prepare(self):
        source = self.root / 'C.sol'
        source.write_text(Path('examples/AccessDemoUnrestricted.sol').read_text())
        with patch('openai.OpenAI.__init__', side_effect=AssertionError('Offline')):
            return prepare_plan(source, 'mock', self.root / 'live')

    def test_offline_plan_and_configuration_gate(self):
        plan = self.prepare()
        self.assertEqual(plan['discovery_batches'], 1)
        self.assertEqual(len(plan['coverage']), 4)
        self.assertEqual(plan['compiler_readiness']['FULL_INDEX'], 4)
        with patch.dict(os.environ, {'OPENAI_API_KEY': '', 'OPENAI_MODEL': 'mock'}):
            with self.assertRaises(ValueError): execute_plan(plan, client_factory=lambda **kw: self.fail('No client'))
        self.assertFalse((self.root / 'live').exists())

    def test_changed_plan_and_source_block_execution(self):
        plan = self.prepare()
        changed = copy.deepcopy(plan); changed['budget']['max_generation_calls'] = 100
        with self.assertRaises(ValueError): execute_plan(changed)
        Path(plan['source']).write_text(Path(plan['source']).read_text() + '\n')
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-fake', 'OPENAI_MODEL': 'mock'}):
            with self.assertRaises(ValueError): execute_plan(plan, client_factory=lambda **kw: self.fail('No client'))

    def test_end_to_end_uses_shared_gate_and_existing_context(self):
        plan = self.prepare()
        def parse(**kwargs):
            payload = json.loads(kwargs['input'][1]['content'])
            if kwargs['text']['format']['name'] == 'DiscoveryResponse':
                f = payload['functions'][0]
                parsed = d.DiscoveryResponse.model_validate({'examined_functions': [dict(fragment_id=r['fragment_id'], reason='Mock') for r in payload['functions']],
                    'candidates': [dict(candidate_id='mock', contract=payload['contract'], primary_function=f['signature'], primary_fragment_id=f['fragment_id'],
                        suspected_type='Authorization', reason='Mock hypothesis', related_fragment_ids=[], requested_context_ids=[], uncertainty='Mock missing source')]})
            elif not payload['provided_context']:
                modifier = next(f for f in payload['available_context'] if f['kind'] == 'modifier')
                parsed = v.VerificationResponse(action='request_context', requested_ids=[modifier['id']], verdict=None, severity=None,
                    explanation='Mock request', evidence_ids=[], execution_flow=[], incomplete_evidence=[], verdict_basis=None)
            else:
                from consistency_fixtures import with_basis
                parsed = v.VerificationResponse.model_validate(with_basis(dict(action='final', requested_ids=[], verdict='inconclusive', severity=None,
                    explanation='Required external behavior remains unknown.', evidence_ids=[payload['target']['id']], execution_flow=[], incomplete_evidence=['Mock uncertainty']),[payload['target']]))
            return self.response(parsed)
        self.client.responses.create.side_effect = parse
        factory = MagicMock(return_value=self.client)
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-fake', 'OPENAI_MODEL': 'mock', 'OPENAI_BASE_URL': 'https://api.openai.com/v1'}):
            report = execute_plan(plan, client_factory=factory)
            with self.assertRaises(ValueError): execute_plan(plan, client_factory=factory)
        factory.assert_called_once_with(timeout=60, max_retries=0, base_url='https://api.openai.com/v1')
        self.assertEqual(report['smoke_transport']['generation_calls'], 3)
        self.assertEqual(report['smoke_transport']['count_calls'], 3)
        self.assertEqual(report['coverage_counts']['inconclusive_candidates'], 1)
        self.assertEqual(report['efficiency']['retrieved_fragments'], 1)
        self.assertEqual(report['efficiency']['total']['total_tokens'], 360)
        self.assertTrue((self.root / 'live/analysis/report.md').is_file())


    def test_safe_exception_diagnostics(self):
        class ProviderFailure(Exception):
            status_code = 400
        t = self.transport()
        self.client.responses.create.side_effect = ProviderFailure('Bearer sk-SECRET request body SECRET')
        with self.assertRaises(SmokeStopped): self.call(t)
        self.assertEqual(t.state['events'][0]['error'],
            {'exception_type': 'ProviderFailure', 'interrupted': False, 'http_status': 400,
             'category': 'invalid_request', 'processing_stage': 'generation_request', 'candidate_id': None, 'attempt': 1})
        self.assertNotIn('SECRET', (self.root / 'budget_ledger.json').read_text())

    def test_validation_diagnostics_omit_input(self):
        from pydantic import ValidationError
        from context_audit.v2_smoke import exception_metadata
        try:
            v.VerificationResponse.model_validate({'secret': 'sk-SECRET'})
        except ValidationError as exc:
            details = exception_metadata(exc)
        self.assertEqual(details['exception_type'], 'ValidationError')
        self.assertGreater(details['validation_error_count'], 0)
        self.assertNotIn('SECRET', json.dumps(details))

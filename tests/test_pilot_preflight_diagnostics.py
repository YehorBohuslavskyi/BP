"""Pre-transport failures must not masquerade as failed model responses."""
import json
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from context_audit import v2_dataset as runner
from context_audit.v2_errors import exception_metadata
from context_audit.v2_artifacts import file_hash

MODEL = 'gpt-5.4-mini-2026-03-17'


class PilotPreflightDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = {'id': 'case-offline', 'cohort': 'development', 'model': MODEL,
                     'output': str(self.root / 'case'),
                     'limits': runner.LIMITS.model_dump(),
                     'budget': {'max_generation_calls': 10, 'max_count_calls': 10,
                                'max_reserved_tokens': 60000}}

    def run_failure(self, env, expected):
        factory = Mock(side_effect=AssertionError('Client forbidden'))
        manifest = {'configuration': runner.identity(), 'output': str(self.root),
                    'cases': [self.case, {**self.case, 'id': 'never-start', 'output': str(self.root / 'next')}],
                    'cohort_budgets': {'development': {k: 2*v for k,v in self.case['budget'].items()}}}
        with patch.dict(os.environ, env, clear=True), patch.object(runner, 'preflight_case'), \
                patch.object(runner, 'JournalTransport') as transport:
            result = runner.execute_cohort(manifest, 'development', client_factory=factory)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'interrupted_or_failed')
        diagnostic = result[0]['diagnostic']
        self.assertEqual(diagnostic['error_code'], expected)
        self.assertEqual(diagnostic['processing_stage'], 'case_preflight')
        self.assertEqual(diagnostic['case_id'], self.case['id'])
        self.assertNotEqual(diagnostic['category'], 'malformed_response_or_protocol')
        self.assertNotIn('verdict', result[0])
        factory.assert_not_called()
        transport.assert_not_called()
        self.assertFalse(Path(self.case['output']).exists())
        self.assertFalse((self.root / 'next').exists())
        self.assertEqual(json.loads((self.root / 'development-execution.json').read_text())['cases'], result)
        return diagnostic

    def test_missing_credential_with_pinned_model_stops_before_transport(self):
        self.run_failure({'OPENAI_MODEL': MODEL}, 'CREDENTIAL_MISSING')

    def test_wrong_model_stops_before_transport(self):
        diagnostic = self.run_failure({'OPENAI_MODEL': 'secret-model', 'OPENAI_API_KEY': 'secret-key'}, 'MODEL_MISMATCH')
        self.assertNotIn('secret', json.dumps(diagnostic))

    def test_missing_model_stops_before_transport(self):
        self.run_failure({'OPENAI_API_KEY': 'offline-only'}, 'MODEL_MISMATCH')

    def test_endpoint_mismatch_stops_before_transport(self):
        self.run_failure({'OPENAI_MODEL': MODEL, 'OPENAI_API_KEY': 'offline-only',
                          'OPENAI_BASE_URL': 'https://secret.invalid'}, 'OFFICIAL_ENDPOINT_REQUIRED')

    def test_implementation_mismatch_precedes_environment_and_client(self):
        factory = Mock()
        with self.assertRaisesRegex(ValueError, 'IMPLEMENTATION_CHANGED'):
            runner.execute_case(self.case, {}, client_factory=factory)
        factory.assert_not_called()
        self.assertFalse(Path(self.case['output']).exists())

    def test_original_ambiguous_constant_is_classified_as_local_preflight(self):
        diagnostic = exception_metadata(ValueError('MODEL_OR_CREDENTIAL_MISSING'))
        self.assertEqual(diagnostic['operation'], 'validate_model_and_credential')
        self.assertEqual(diagnostic['category'], 'configuration_missing_or_mismatch')

    def test_arbitrary_valueerror_text_remains_private(self):
        diagnostic = exception_metadata(ValueError('CREDENTIAL_MISSING secret request contents'))
        self.assertEqual(diagnostic['category'], 'malformed_response_or_protocol')
        self.assertNotIn('secret', json.dumps(diagnostic))
        self.assertNotIn('error_code', diagnostic)

    def test_source_identity_failure_is_provenance_not_security_verdict(self):
        diagnostic = exception_metadata(ValueError('SOURCE_COMPILER_CATALOG_MISMATCH'))
        self.assertEqual(diagnostic['category'], 'provenance_mismatch')
        self.assertEqual(diagnostic['processing_stage'], 'source_preflight')

    def test_historical_failure_has_no_case_artifacts_to_recover(self):
        root = Path('runs/mode-b-v2-development-pilot-2026-11-10')
        record = json.loads((root/'development-execution.json').read_text())
        self.assertEqual(record['cases'][0]['case'], 'case-c8c6063234efc85a1847')
        self.assertEqual(record['cases'][0]['status'], 'interrupted_or_failed')
        self.assertFalse((root/record['cases'][0]['case']).exists())

    def test_exact_frozen_first_case_without_credential_fails_before_any_work(self):
        plan = json.loads(Path('experiments/mode-b-v2-development-pilot-2026-11-10/plan.json').read_text())
        case = plan['execution']['cases'][0]
        self.assertEqual(case['id'], 'case-c8c6063234efc85a1847')
        factory = Mock(side_effect=AssertionError('Client forbidden'))
        with patch.dict(os.environ, {'OPENAI_MODEL': case['model']}, clear=True), \
                patch.object(runner, 'preflight_case') as prepare, \
                patch.object(runner, 'JournalTransport') as transport, \
                self.assertRaisesRegex(ValueError, '^CREDENTIAL_MISSING$'):
            runner.execute_case(case, runner.identity(), client_factory=factory)
        prepare.assert_not_called()
        transport.assert_not_called()
        factory.assert_not_called()
        self.assertFalse(Path(case['output']).exists())

    def test_single_case_continuation_rejects_changed_compiler_before_preparation(self):
        module = runpy.run_path('scripts/run_v2_single_case.py')
        binary = self.root/'compiler'; binary.write_text('changed binary')
        case = {**self.case, 'model': MODEL}
        parent = {'cases': [case], 'scoring_protocol': module['SCORING_PROTOCOL'],
                  'compiler_proofs': [{'case_id': case['id'], 'compiler_binary': str(binary),
                                       'compiler_binary_sha256': 'wrong'}]}
        path = self.root/'parent.json'; path.write_text(json.dumps(parent))
        with patch.dict(module['prepare'].__globals__, {'preflight_case': Mock(side_effect=AssertionError('No preparation'))}), \
                self.assertRaisesRegex(ValueError, 'COMPILER_BINARY_CHANGED'):
            module['prepare'](path, case['id'])

    def test_single_case_continuation_accepts_exact_compiler_proof(self):
        module = runpy.run_path('scripts/run_v2_single_case.py')
        binary = self.root/'compiler'; binary.write_text('offline fixture binary')
        case = {**self.case, 'model': MODEL}
        parent = {'cases': [case], 'scoring_protocol': module['SCORING_PROTOCOL'],
                  'compiler_proofs': [{'case_id': case['id'], 'compiler_binary': str(binary),
                                       'compiler_binary_sha256': file_hash(binary)}]}
        path = self.root/'parent.json'; path.write_text(json.dumps(parent))
        prepare = Mock()
        with patch.dict(module['prepare'].__globals__, {'preflight_case': prepare}):
            result = module['prepare'](path, case['id'])
        prepare.assert_called_once_with(case)
        self.assertEqual(result['case'], case)

    def test_single_case_continuation_rejects_missing_compiler_proof(self):
        module = runpy.run_path('scripts/run_v2_single_case.py')
        parent = {'cases': [self.case], 'scoring_protocol': module['SCORING_PROTOCOL'], 'compiler_proofs': []}
        path = self.root/'parent.json'; path.write_text(json.dumps(parent))
        with self.assertRaisesRegex(ValueError, 'COMPILER_BINARY_CHANGED'):
            module['prepare'](path, self.case['id'])


if __name__ == '__main__':
    unittest.main()

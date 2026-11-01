"""Offline application tests; all model responses are injected or mocked."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

from context_audit.app.compilers import compatible_compilers, detect_pragmas, satisfies
from context_audit.app.config import ApplicationError, VerificationSettings
from context_audit.app.services import Analysis, analyze_upload, create_upload, export_analysis, verify_selected
from context_audit.app.session import AuditSession
from context_audit.app.slither_runner import process_environment, run_slither
from context_audit.app.worker import verify_request
from context_audit.findings import Finding

SOURCE = b'pragma solidity ^0.4.25; contract Demo { function kill() public { selfdestruct(msg.sender); } }'


def finding() -> Finding:
    """Create a synthetic warning for transport tests, not research evidence."""
    return Finding('test', 'suicidal', 'High', 'High', 'Unprotected destruction',
                   'Demo', 'kill()', 'source.sol', [1], 39, 51)


class CompilerTests(unittest.TestCase):
    def test_directives_ignore_comments_and_strings(self):
        source = '// pragma solidity 0.1.0;\npragma solidity >=0.4.25 <0.5.0; string s = "pragma solidity 1.0.0;";'
        self.assertEqual(detect_pragmas(source), ['>=0.4.25 <0.5.0'])
        self.assertEqual(compatible_compilers(source, ['0.4.24', '0.4.25', '0.8.24']), ['0.4.25'])

    def test_supported_ranges_and_intersections(self):
        for version, constraint, expected in [
            ('0.4.25', '^0.4.24', True), ('0.5.0', '^0.4.24', False),
            ('0.0.2', '^0.0.1', False), ('1.4.0', '^1.2.3', True),
            ('0.4.25', '~0.4.24', True), ('0.4.25', '0.4.24 || =0.4.25', True),
            ('0.4.25', '>0.4.25', False), ('0.4.25', '<=0.4.25', True),
        ]:
            with self.subTest(version=version, constraint=constraint):
                self.assertEqual(satisfies(version, constraint), expected)
        self.assertEqual(compatible_compilers('pragma solidity ^0.4.24; pragma solidity <=0.4.24;',
                                             ['0.4.24', '0.4.25']), ['0.4.24'])

    def test_unknown_range_fails_instead_of_guessing(self):
        for constraint in ('*', '0.4.x', '>=0.4', '0.4.0 - 0.5.0', '||'):
            with self.assertRaises(ApplicationError):
                satisfies('0.4.25', constraint)

    def test_child_environment_does_not_mutate_parent(self):
        before = dict(os.environ)
        child = process_environment('0.4.25', 'test-model')
        self.assertEqual(child['SOLC_VERSION'], '0.4.25')
        self.assertEqual(child['OPENAI_MODEL'], 'test-model')
        self.assertEqual(dict(os.environ), before)


class UploadTests(unittest.TestCase):
    def test_filename_cannot_escape_owned_directory(self):
        upload = create_upload('../../datasets/cgt/overwrite.sol', SOURCE)
        path = upload.source_path
        self.assertEqual(path.name, 'source.sol')
        self.assertNotIn('datasets', path.parts)
        self.assertEqual(path.read_bytes(), SOURCE)
        upload.close()
        self.assertFalse(path.exists())

    def test_invalid_uploads_and_imports(self):
        for name, content in [('bad.txt', SOURCE), ('bad.sol', b''), ('bad.sol', b'\xff'),
                              ('bad.sol', b'\x00'), ('bad.sol', b'a' * (1024 * 1024 + 1)),
                              ('bad.sol', b'import "/etc/passwd";'),
                              ('bad.sol', b'import { X } from "x.sol";')]:
            with self.subTest(name=name, content_size=len(content)), self.assertRaises(ApplicationError):
                create_upload(name, content)
        upload = create_upload('ok.sol', SOURCE + b' // import "not-real";')
        upload.close()

    def test_new_upload_invalidates_analysis_and_releases_old_files(self):
        session = AuditSession()
        session.set_upload('demo.sol', SOURCE)
        previous = session.upload.source_path
        session.analysis = Analysis('0.4.25', session.upload.digest, [finding()], {})
        session.history.append({'synthetic': True})
        with self.assertRaises(ApplicationError):
            session.set_upload('bad.sol', b'')
        self.assertIsNone(session.analysis)
        self.assertFalse(previous.exists())
        self.assertEqual(session.history, [])


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.upload = create_upload('demo.sol', SOURCE)
        self.addCleanup(self.upload.close)
        self.analysis = Analysis('0.4.25', self.upload.digest, [finding()], {})

    def test_missing_credentials_prevent_worker_start(self):
        with patch.dict(os.environ, {}, clear=True), patch('context_audit.app.services.subprocess.run') as run:
            with self.assertRaisesRegex(ApplicationError, 'OPENAI_API_KEY'):
                verify_selected(self.upload, self.analysis, 0, VerificationSettings('test'))
            run.assert_not_called()

    def test_configuration_and_function_resolution_errors(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}):
            for settings in (VerificationSettings(''), VerificationSettings('test', 0), VerificationSettings('test', 11)):
                with self.assertRaises(ApplicationError):
                    settings.validate()
            self.analysis.findings[0].function_signature = None
            with self.assertRaisesRegex(ApplicationError, 'no resolvable'):
                verify_selected(self.upload, self.analysis, 0, VerificationSettings('test'))

    def test_interactive_round_limit_preserves_recommended_default(self):
        self.assertEqual(VerificationSettings('test').max_rounds, 4)
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}):
            for rounds in (1, 4, 5, 10):
                VerificationSettings('test', rounds).validate()
            with self.assertRaises(ApplicationError):
                VerificationSettings('test', 11).validate()

    def test_worker_payload_contains_no_credentials_or_labels(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-secret'}), \
             patch('context_audit.app.services.subprocess.run', return_value=Mock(returncode=0, stdout='{"ok": true}')) as run:
            self.assertEqual(verify_selected(self.upload, self.analysis, 0, VerificationSettings('test')), {'ok': True})
            args, kwargs = run.call_args
            self.assertIsInstance(args[0], list)
            self.assertNotIn('shell', kwargs)
            self.assertNotIn('test-secret', kwargs['input'])
            self.assertNotIn('label', kwargs['input'])
            self.assertEqual(kwargs['env']['SOLC_VERSION'], '0.4.25')
            self.assertEqual(kwargs['env']['OPENAI_MODEL'], 'test')

    def test_changed_source_cannot_reuse_or_export_analysis(self):
        self.upload.source_path.write_text('changed')
        with self.assertRaisesRegex(ApplicationError, 'changed'):
            export_analysis(self.upload, self.analysis, [])

    def test_export_preserves_abstention_and_reported_usage(self):
        verification = {'result': {'assessment': {'verdict': 'inconclusive'}},
                        'summary': {'input_tokens': 12, 'output_tokens': 3, 'total_tokens': 15}}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'do-not-export'}):
            exported = export_analysis(self.upload, self.analysis, [verification])
        result = json.loads(exported)
        self.assertNotIn('do-not-export', exported)
        self.assertEqual(result['usage']['total_tokens'], 15)
        self.assertEqual(result['verification'][0]['verification']['verdict'], 'inconclusive')

    def test_slither_failures_and_timeout_are_actionable(self):
        compiler_ok = Mock(returncode=0)
        with patch('context_audit.app.slither_runner.executable', side_effect=lambda name: name):
            for failure in (Mock(returncode=1), Mock(returncode=0, stdout='not json')):
                with patch('context_audit.app.slither_runner.subprocess.run', side_effect=[compiler_ok, failure]), \
                     self.assertRaises(ApplicationError):
                    run_slither(self.upload.source_path, '0.4.25')
            with patch('context_audit.app.slither_runner.subprocess.run', side_effect=subprocess.TimeoutExpired('solc', 30)), \
                 self.assertRaisesRegex(ApplicationError, 'time limit'):
                run_slither(self.upload.source_path, '0.4.25')

    def test_api_error_is_visible_without_provider_details(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only'}), \
             patch('context_audit.app.services.subprocess.run', return_value=Mock(returncode=1, stdout='{"error": "OpenAI request failed"}')):
            with self.assertRaisesRegex(ApplicationError, 'OpenAI request failed'):
                verify_selected(self.upload, self.analysis, 0, VerificationSettings('test'))

    def test_real_slither_and_context_with_mock_inference(self):
        """Compile a real local source and verify its parsed warning without an API."""
        analysis = analyze_upload(self.upload, '0.4.25')
        target = next(item for item in analysis.findings if item.detector == 'suicidal')
        before = os.getcwd()
        try:
            # The production worker similarly resolves relative mappings in this directory.
            os.chdir(self.upload.source_path.parent)
            def fake_analyze(payload, provided):
                return {'assessment': {'action': 'final', 'verdict': 'confirmed',
                        'requested_ids': [], 'evidence_ids': [payload['target']['id']],
                        'explanation': 'Synthetic API response for service integration test'},
                        'usage': {'input_tokens': 100, 'output_tokens': 10, 'total_tokens': 110}}
            from dataclasses import asdict
            with patch.dict(os.environ, {'SOLC_VERSION': '0.4.25'}), \
                 patch('context_audit.verifier.analyze', side_effect=fake_analyze):
                report = verify_request({'source': str(self.upload.source_path), 'finding': asdict(target), 'max_rounds': 4})
            self.assertEqual(report['summary']['rounds'], 1)
            self.assertEqual(report['summary']['total_tokens'], 110)
            self.assertIn('selfdestruct', report['initial_payload']['target']['source'])
            exported = json.loads(export_analysis(self.upload, analysis, [report]))
            self.assertEqual(exported['usage']['total_tokens'], 110)
        finally:
            os.chdir(before)


class WorkerContextTests(unittest.TestCase):
    def test_selective_request_rounds_and_token_aggregation(self):
        upload = create_upload('demo.sol', SOURCE)
        self.addCleanup(upload.close)
        payload = {'target': {'id': 'target', 'source': 'kill() {}'},
                   'available_context': [{'id': 'guard', 'kind': 'modifier', 'name': 'onlyOwner'}]}
        catalog = Mock()
        catalog.get.return_value = {'id': 'guard', 'kind': 'modifier', 'name': 'onlyOwner',
                                    'source': 'modifier onlyOwner() { require(msg.sender == owner); _; }'}
        calls = []
        def fake_analyze(initial, provided):
            calls.append(list(provided))
            assessment = ({'action': 'request_context', 'verdict': 'pending', 'requested_ids': ['guard'],
                           'evidence_ids': [], 'explanation': 'Need guard'} if not provided else
                          {'action': 'final', 'verdict': 'false_positive', 'requested_ids': [],
                           'evidence_ids': ['guard'], 'explanation': 'Guard checks owner'})
            return {'assessment': assessment, 'usage': {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}}
        from dataclasses import asdict
        with patch('context_audit.app.worker.prepare_finding', return_value=(payload, catalog)), \
             patch('context_audit.verifier.analyze', side_effect=fake_analyze):
            report = verify_request({'source': str(upload.source_path), 'finding': asdict(finding()), 'max_rounds': 4})
        self.assertEqual(calls[0], [])
        self.assertEqual(calls[1][0]['id'], 'guard')
        self.assertEqual(report['summary']['rounds'], 2)
        self.assertEqual(report['summary']['requested_fragments'], 1)
        self.assertEqual(report['summary']['total_tokens'], 30)
        self.assertEqual(report['result']['assessment']['verdict'], 'false_positive')

"""Isolated technical-evidence CLI tests; no real inference or research mutations."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('case_processor', Path(__file__).resolve().parents[1] / 'scripts/process_defihacklabs_case.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
REPORT = {'success': True, 'results': {'detectors': [{
    'id': 'finding-1', 'check': 'unchecked-transfer', 'impact': 'High', 'confidence': 'Medium',
    'description': 'Analyzer claim', 'elements': [{'type': 'function',
        'source_mapping': {'lines': [2], 'start': 1, 'length': 10, 'filename_relative': 'Victim.sol'},
        'type_specific_fields': {'signature': 'f()', 'parent': {'type': 'contract', 'name': 'Victim'}}}]}]}}


class ProcessCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'Victim.sol'
        self.source.write_text('pragma solidity ^0.6.0;\ncontract Victim {}\n')
        self.output = self.root / 'cases'
        self.patch = patch.object(module, 'CASE_ROOT', self.output)
        self.patch.start(); self.addCleanup(self.patch.stop)

    def run_case(self, results=None, **kwargs):
        if results is None:
            results = [(0, 'compiled bytecode', ''), (0, json.dumps(REPORT), '')]
        with patch.object(module, 'compiler_path', return_value=Path('/local/solc')), \
             patch.object(module.shutil, 'which', return_value='/local/slither'), \
             patch.object(module, 'execute', side_effect=results) as execution, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            status = module.process('demo', self.source, '0.6.12', **kwargs)
        return status, execution

    def test_hash_and_metadata(self):
        metadata = module.source_metadata(self.source)
        self.assertEqual(metadata['source_sha256'], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(metadata['source_bytes'], self.source.stat().st_size)
        self.assertEqual(metadata['source_lines'], 2)
        self.assertTrue(metadata['looks_flattened'])
        self.source.write_text('/* import "fake.sol"; */\npragma solidity ^0.6.0;\nimport "real.sol";')
        metadata = module.source_metadata(self.source)
        self.assertEqual(metadata['imports'], ['import "real.sol";'])
        self.assertFalse(metadata['looks_flattened'])

    def test_overwrite_protection_before_subprocess(self):
        directory = self.output / 'demo/evidence'; directory.mkdir(parents=True)
        evidence = directory / 'compilation.txt'; evidence.write_text('original')
        with self.assertRaisesRegex(ValueError, 'Evidence exists'):
            self.run_case()
        self.assertEqual(evidence.read_text(), 'original')
        self.assertFalse((directory / '.processing.lock').exists())

    def test_missing_compiler_no_install_or_evidence(self):
        with patch('solc_select.solc_select.ARTIFACTS_DIR', self.root / 'no-compilers'), \
             patch.object(module.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'solc-select install 0.6.12'):
                module.process('demo', self.source, '0.6.12')
        run.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_compile_failure_saved_and_slither_not_run(self):
        status, execution = self.run_case([(1, '', 'syntax error')])
        self.assertEqual(status, 1); self.assertEqual(execution.call_count, 1)
        directory = self.output / 'demo/evidence'
        self.assertIn('syntax error', (directory / 'compilation.txt').read_text())
        data = json.loads((directory / 'integration.json').read_text())
        self.assertEqual(data['compilation_status'], 'FAILURE')
        self.assertEqual(data['slither_status'], 'NOT_RUN')
        self.assertFalse((directory / 'slither.json').exists())

    def test_summary_parsing(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output): module.print_summary(REPORT)
        for value in ['Total findings: 1', 'High:', 'Victim.f()', 'lines=2', 'finding-1', 'Medium']:
            self.assertIn(value, output.getvalue())

    def test_success_integration_no_labels_or_llm(self):
        from context_audit import llm
        original = self.source.read_bytes()
        with patch.object(llm, 'analyze', side_effect=AssertionError('No inference allowed')) as inference:
            status, execution = self.run_case()
        inference.assert_not_called(); self.assertEqual(status, 0)
        self.assertEqual(execution.call_count, 2)
        data = json.loads((self.output / 'demo/evidence/integration.json').read_text())
        self.assertEqual(data['source_status'], 'SOURCE_READY')
        self.assertEqual(data['baseline_classification'], 'PENDING_MANUAL_ADJUDICATION')
        self.assertEqual(data['matched_slither_finding_ids'], [])
        self.assertFalse(data['llm_target_created'])
        self.assertEqual(data['slither_finding_count'], 1)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(set(p.name for p in (self.output / 'demo/evidence').iterdir()), set(module.MANAGED))

    def test_summary_only_no_writes_or_commands_or_compiler(self):
        directory = self.output / 'demo/evidence'; directory.mkdir(parents=True)
        file = directory / 'slither.json'; file.write_text(json.dumps(REPORT))
        original = file.read_bytes()
        with patch.object(module, 'execute') as execute, patch.object(module, 'compiler_path') as compiler, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(['--case', 'demo', '--summary-only']), 0)
        execute.assert_not_called(); compiler.assert_not_called()
        self.assertEqual(file.read_bytes(), original)
        self.assertEqual(list(directory.iterdir()), [file])

    def test_explicit_overwrite_clears_stale_slither_on_compile_failure(self):
        self.run_case()
        self.run_case([(1, '', 'failure')], overwrite=True)
        self.assertFalse((self.output / 'demo/evidence/slither.json').exists())

    def test_invalid_inputs(self):
        for case, source, compiler in [('../escape', self.source, '0.6.12'), ('demo', self.source, 'latest'),
                                      ('demo', self.root / 'missing.sol', '0.6.12')]:
            with self.assertRaises(ValueError): module.process(case, source, compiler)

    def test_slither_malformed_output_preserved(self):
        status, _ = self.run_case([(0, 'binary', ''), (1, 'not JSON', 'failed')])
        self.assertEqual(status, 1)
        data = json.loads((self.output / 'demo/evidence/integration.json').read_text())
        self.assertEqual(data['slither_status'], 'FAILURE')
        self.assertIn('not JSON', (self.output / 'demo/evidence/slither.txt').read_text())

    def test_lock_prevents_concurrent_writer(self):
        directory = self.output / 'demo/evidence'; directory.mkdir(parents=True)
        (directory / '.processing.lock').touch()
        with self.assertRaises(FileExistsError): self.run_case(overwrite=True)
        self.assertTrue((directory / '.processing.lock').exists())

    def test_symlink_escape_rejected(self):
        self.output.mkdir(); (self.output / 'demo').symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'escapes'): self.run_case()

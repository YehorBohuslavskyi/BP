"""CLI selection regression tests; preparation mocked, inference forbidden."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


class FileSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        folder = self.root/'contracts'/'project'; folder.mkdir(parents=True)
        self.cases = []
        for name in ('A.sol', 'B.sol', 'C.sol'):
            (folder/name).write_text('pragma solidity ^0.4.25; contract C {}')
            self.cases.append({'project': 'project', 'file': 'project/'+name, 'labels': []})
        self.manifest = self.root/'manifest.json'
        self.manifest.write_text(json.dumps({'cases': self.cases + [self.cases[0]]}))
        spec = importlib.util.spec_from_file_location('selection_runner', 'scripts/run_dappscan_direct_detection.py')
        self.runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.runner)

    def run_cli(self, extra, manifest=True):
        args = ['--dataset-root', str(self.root), '--prepare', '--output', str(self.root/'out')]
        args += ['--manifest', str(self.manifest)] if manifest else ['--project', 'project']
        payloads = [{'target': {'signature': signature, 'contract': 'C'}} for signature in ('f()', 'g(uint256)')]
        with patch.object(self.runner, 'prepare', return_value=(payloads, SimpleNamespace(preparation_metadata={}))), patch.object(self.runner, 'run_function', side_effect=AssertionError('API forbidden')), contextlib.redirect_stdout(io.StringIO()) as output:
            prepared = self.runner.main(args+extra)
        return prepared, output.getvalue()

    def test_repeated_files_deduplicated_in_manifest_order(self):
        selected, output = self.run_cli(['--file','project/C.sol','--file','project/A.sol','--file','project/B.sol','--file','project/A.sol'])
        self.assertEqual([c['file'] for c in selected], [c['file'] for c in self.cases])
        self.assertIn('Selected files: 3', output)
        self.assertIn('Function sessions: 6', output)

    def test_single_file_unchanged(self):
        selected, _ = self.run_cli(['--file','project/B.sol'])
        self.assertEqual([c['file'] for c in selected], ['project/B.sol'])

    def test_explicit_limit_respected(self):
        selected, _ = self.run_cli(['--file','project/A.sol','--file','project/B.sol','--limit','1'])
        self.assertEqual(len(selected), 1)

    def test_discovery_still_defaults_to_one(self):
        selected, _ = self.run_cli([])
        self.assertEqual(len(selected), 1)

    def test_function_filter_across_files(self):
        selected, output = self.run_cli(['--file','project/A.sol','--file','project/B.sol','--function','g'])
        self.assertEqual([c['session_count'] for c in selected], [1,1])
        self.assertIn('Function sessions: 2', output)

    def test_repeated_files_without_manifest(self):
        selected, _ = self.run_cli(['--file','project/A.sol','--file','project/B.sol','--file','project/C.sol'], manifest=False)
        self.assertEqual(len(selected), 3)

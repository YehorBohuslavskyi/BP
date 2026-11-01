"""Local compilation and mocked inference; no provider calls or evidence writes."""
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from slither.slither import Slither
from slither.utils.output import Output

from context_audit.catalog import FragmentCatalog
from context_audit.context import build_function_context, build_target_context
from context_audit.findings import parse_slither_findings, Finding
from context_audit.indexer import find_function, find_target
from context_audit.payload import build_initial_payload, resolve_context_request
from context_audit.verifier import prepare_finding, verify_prepared_finding, summarize_verification
from context_audit.app.presentation import (is_finding_verifiable, source_fragments,
                                             target_kind_label, verification_export)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tests/fixtures/ModifierTargetTest.sol'


class ModifierTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {'SOLC_VERSION': '0.8.24'}):
            cls.slither = Slither(str(SOURCE))
        cls.contract = cls.slither.contracts[0]
        cls.modifier = cls.contract.modifiers[0]
        output = Output([cls.modifier, ' uses a dangerous strict equality'])
        cls.raw = {'success': True, 'results': {'detectors': [{
            **output.data, 'check': 'incorrect-equality', 'impact': 'Medium',
            'confidence': 'High', 'id': 'modifier-test'}]}}
        cls.finding = parse_slither_findings(cls.raw)[0]

    def context_payload(self):
        catalog = FragmentCatalog(SOURCE.parent)
        context = build_target_context(self.modifier, catalog)
        return context, build_initial_payload(context, catalog, self.finding), catalog

    def test_function_resolution_and_legacy_entry_point(self):
        function = find_target(self.slither, self.contract.name, 'privilegedAction()')
        self.assertIs(function, find_function(self.slither, self.contract.name, 'privilegedAction()'))
        context = build_function_context(function, FragmentCatalog(SOURCE.parent))
        self.assertEqual(context['kind'], 'function')
        self.assertEqual(context['modifiers'][0]['name'], 'onlyManager')

    def test_only_manager_resolution(self):
        self.assertIsNone(find_function(self.slither, self.contract.name, 'onlyManager()'))
        self.assertIs(find_target(self.slither, self.contract.name, 'onlyManager()',
                                 self.finding.file, self.finding.function_start,
                                 self.finding.function_length), self.modifier)

    def test_modifier_fragment_and_selective_payload(self):
        context, payload, catalog = self.context_payload()
        self.assertEqual(context['kind'], 'modifier')
        self.assertEqual(payload['target']['kind'], 'modifier')
        self.assertEqual(payload['target']['signature'], 'onlyManager()')
        self.assertEqual(catalog.get(context['fragment_id'])['kind'], 'modifier')
        self.assertEqual(payload['target']['source'], self.modifier.source_mapping.content)
        self.assertNotIn('privilegedAction', payload['target']['source'])
        self.assertNotIn('false_positive', json.dumps(payload))
        self.assertTrue(all('source' not in item for item in payload['available_context']))

    def test_dependencies_and_writers_are_requestable(self):
        context, payload, catalog = self.context_payload()
        self.assertEqual(set(context['state_reads']), {'roles', 'owner'})
        dependencies = {item['name']: item for item in context['state_dependencies']}
        self.assertEqual(set(dependencies), {'roles', 'owner'})
        self.assertIn('setRole(address,ModifierTargetTest.Role)',
                      [writer['signature'] for writer in dependencies['roles']['direct_writers']])
        ids = [item['id'] for item in payload['available_context']]
        resolved = resolve_context_request(ids, payload, catalog)
        self.assertFalse(resolved['errors'])
        self.assertTrue(any('mapping' in f['source'] for f in resolved['fragments']))
        self.assertTrue(any('owner = msg.sender' in f['source'] for f in resolved['fragments']))

    def test_prepare_and_mocked_verification_export(self):
        with patch('context_audit.verifier.Slither', return_value=self.slither), \
             patch('context_audit.verifier.analyze') as provider:
            payload, catalog = prepare_finding(SOURCE, SOURCE.parent, self.finding)
            def infer(initial, supplied):
                self.assertEqual(initial['target']['kind'], 'modifier')
                return {'assessment': {'action': 'final', 'verdict': 'false_positive',
                        'explanation': 'Mock response: exact enum access-control check.',
                        'requested_ids': [], 'evidence_ids': [initial['target']['id']]}}
            result = verify_prepared_finding(self.finding, payload, catalog, analyze_fn=infer)
            provider.assert_not_called()
        exported = verification_export({'result': result, 'initial_payload': payload,
                                        'summary': summarize_verification(result),
                                        'finding': asdict(self.finding)})
        self.assertEqual(exported['finding']['function'], 'onlyManager()')
        self.assertEqual(exported['source_fragments'][0]['kind'], 'modifier')
        self.assertEqual(Finding(**json.loads(json.dumps(asdict(self.finding)))), self.finding)
        self.assertEqual(payload['finding']['function'], 'onlyManager()')

    def test_unresolvable_target_fails_before_inference(self):
        with patch('context_audit.verifier.Slither', return_value=self.slither), \
             patch('context_audit.verifier.analyze') as provider:
            for finding in (replace(self.finding, function_signature='missing()'),
                            replace(self.finding, function_signature=None),
                            replace(self.finding, function_start=999999),
                            replace(self.finding, file='wrong.sol')):
                with self.assertRaises(ValueError):
                    prepare_finding(SOURCE, SOURCE.parent, finding)
            provider.assert_not_called()

    def test_ambiguous_targets_use_range_or_fail(self):
        duplicate = SimpleNamespace(full_name=self.modifier.full_name,
                                    source_mapping=SimpleNamespace(start=999, length=1, lines=[99]))
        slither = SimpleNamespace(contracts=[SimpleNamespace(name=self.contract.name,
            functions=[], modifiers=[self.modifier, duplicate])])
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            find_target(slither, self.contract.name, 'onlyManager()')
        self.assertIs(find_target(slither, self.contract.name, 'onlyManager()', start=999), duplicate)
        self.assertIs(find_target(slither, self.contract.name, 'onlyManager()', lines=[99]), duplicate)

    def test_gui_eligibility_and_kind(self):
        self.assertTrue(is_finding_verifiable(self.finding, SOURCE))
        self.assertEqual(target_kind_label(SOURCE.read_text(), self.finding), 'Modifier')
        _, payload, _ = self.context_payload()
        self.assertEqual(source_fragments(payload, {})[0]['kind'], 'modifier')

    def test_explicit_modifier_json_tag_also_parses(self):
        raw = json.loads(json.dumps(self.raw))
        raw['results']['detectors'][0]['elements'][0]['type'] = 'modifier'
        self.assertEqual(parse_slither_findings(raw)[0], self.finding)

    def test_large_treasury_saved_finding_prepares_locally(self):
        source = ROOT / 'examples/scalability/LargeTreasury.sol'
        evidence = ROOT / 'results/large_treasury_slither.json'
        if not source.exists() or not evidence.exists():
            self.skipTest('Optional local scalability experiment is absent')
        findings = parse_slither_findings(json.loads(evidence.read_text()))
        finding, = [f for f in findings if f.detector == 'incorrect-equality'
                    and f.function_signature == 'onlyManager()']
        with patch.dict(os.environ, {'SOLC_VERSION': '0.8.24'}), \
             patch('context_audit.verifier.analyze') as provider:
            payload, catalog = prepare_finding(source, source.parent, finding)
            provider.assert_not_called()
        self.assertEqual(payload['target']['kind'], 'modifier')
        self.assertIn('members[msg.sender].role == Role.Manager', payload['target']['source'])
        declarations = [catalog.get(item['id'])['source'] for item in payload['available_context']
                        if item['kind'] == 'state_variable']
        self.assertTrue(any('members' in text for text in declarations))
        self.assertTrue(any('owner' in text for text in declarations))

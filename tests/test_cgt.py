import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from check_cgt import run
from context_audit.cgt_dataset import load_cgt
from context_audit.cgt_findings import load_reviewed_findings, sha256
from context_audit.cgt_inference import BlindAnalyzer, strip_comments
from context_audit.classification_metrics import classification_metrics, compare_verification, context_efficiency
from context_audit.findings import parse_slither_findings
from context_audit.verifier import verify_prepared_finding


class CGTTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'source').mkdir()
        self.source = self.root / 'source' / ('a' * 32 + '.sol')
        self.source.write_text('contract C { function f() public {} }')
        self.row = dict(dataset='Example', id='case', property='weakness', property_holds='t',
                        fp_sol='a' * 32, contractname='C', swc='115', dasp='2')

    def write(self, rows):
        with (self.root / 'consolidated.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.row), delimiter=';')
            writer.writeheader()
            writer.writerows(rows)
        return load_cgt(self.root)

    def test_positive_and_negative_labels_and_source(self):
        dataset = self.write([self.row, {**self.row, 'id': 'case2', 'property_holds': 'f'}])
        self.assertEqual([a.property_holds for a in dataset.assessments], [True, False])
        self.assertEqual(dataset.assessments[0].original_label, 't')
        self.assertEqual(dataset.assessments[0].source_path, self.source)
        self.assertEqual(dataset.issues, [])

    def test_tool_filter_does_not_confuse_dataset_with_tool(self):
        dataset = self.write([{**self.row, 'dataset': 'Slither'}])
        with self.assertRaisesRegex(ValueError, 'provenance'):
            dataset.filter_tool('slither')

    def test_invalid_label_is_reported_not_dropped_silently(self):
        dataset = self.write([{**self.row, 'property_holds': 'unknown'}])
        self.assertEqual(dataset.total_rows, 1)
        self.assertFalse(dataset.assessments)
        self.assertEqual(dataset.issues[0]['kind'], 'invalid_row')

    def test_duplicate_and_conflict_preserved(self):
        dataset = self.write([self.row, self.row, {**self.row, 'property_holds': 'f'}])
        self.assertEqual(len(dataset.assessments), 3)
        self.assertEqual([i['kind'] for i in dataset.issues], ['duplicate_key', 'conflicting_label'])

    def test_path_traversal_rejected(self):
        dataset = self.write([{**self.row, 'fp_sol': '../../secrets'}])
        self.assertEqual(dataset.issues[0]['kind'], 'invalid_row')

    def test_source_symlink_escape_rejected(self):
        self.source.unlink()
        self.source.symlink_to('/etc/passwd')
        dataset = self.write([self.row])
        self.assertEqual(dataset.issues[0]['kind'], 'invalid_row')

    def test_missing_source_is_explicit(self):
        dataset = self.write([{**self.row, 'fp_sol': ''}])
        self.assertIsNone(dataset.assessments[0].source_path)
        self.assertEqual(dataset.issues[0]['kind'], 'source_not_provided')

    def test_missing_header_rejected(self):
        (self.root / 'consolidated.csv').write_text('wrong;header\na;b\n')
        with self.assertRaises(ValueError):
            load_cgt(self.root)

    def test_missing_dataset_generates_blocked_evidence(self):
        summary = run(self.root, self.root / 'out')
        self.assertEqual(summary['status'], 'blocked')
        self.assertIsNone(summary['baseline'])
        self.assertIsNone(summary['reviewed_eligible_findings'])
        self.assertTrue((self.root / 'out/errors.json').exists())

    def test_inventory_does_not_invent_slither_labels(self):
        self.write([self.row])
        summary = run(self.root, self.root / 'out')
        self.assertEqual(summary['assessment_rows'], 1)
        self.assertEqual(summary['reviewed_eligible_findings'], 0)
        self.assertIsNone(summary['baseline'])

    def manifest(self):
        raw = {'success': True, 'results': {'detectors': [{'id': 'finding', 'check': 'tx-origin',
               'description': 'C.f uses tx.origin', 'elements': [{'type': 'function',
               'source_mapping': {'filename_relative': str(self.source), 'lines': [1], 'start': 13, 'length': 21},
               'type_specific_fields': {'signature': 'f()', 'parent': {'type': 'contract', 'name': 'C'}}}]}]}}
        artifact = self.root / 'slither.json'
        artifact.write_text(json.dumps(raw))
        row = {'review_id': 'r1', 'assessment_key': ['Example', 'case', 'weakness'],
               'review_status': 'accepted', 'reviewer': 'unit-test-fixture', 'rationale': 'synthetic fixture only',
               'property_is_weakness': True, 'label': True, 'leakage_reviewed': True,
               'source_sha256': sha256(self.source), 'slither_json': 'slither.json',
               'slither_json_sha256': sha256(artifact), 'finding_id': 'finding',
               'compiler_version': '0.4.24', 'slither_version': '0.11.6'}
        path = self.root / 'reviews.json'
        path.write_text(json.dumps([row]))
        return path, row

    def test_reviewed_link_binds_source_and_exact_finding(self):
        dataset = self.write([self.row])
        path, _ = self.manifest()
        accepted, errors = load_reviewed_findings(dataset, path)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(errors, [])
        self.source.write_text('changed')
        self.assertIn('SHA256', load_reviewed_findings(dataset, path)[1][0]['error'])

    def test_duplicate_candidates_rejected(self):
        dataset = self.write([self.row])
        path, row = self.manifest()
        path.write_text(json.dumps([row, row]))
        accepted, errors = load_reviewed_findings(dataset, path)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(errors), 1)

    def test_unreviewed_and_disagreeing_labels_rejected(self):
        dataset = self.write([self.row])
        path, row = self.manifest()
        for override in ({'review_status': 'pending'}, {'label': False}, {'leakage_reviewed': False}):
            path.write_text(json.dumps([{**row, **override}]))
            self.assertEqual(len(load_reviewed_findings(dataset, path)[1]), 1)

    def test_paid_pilot_pipeline_with_mock_api_is_explicitly_test_only(self):
        from context_audit.cgt_sample import run_pilot
        dataset = self.write([self.row])
        path, _ = self.manifest()
        candidates, _ = load_reviewed_findings(dataset, path)
        payload = InferenceTests().payload()
        fake = {'assessment': {'action': 'final', 'verdict': 'confirmed', 'requested_ids': [],
                               'evidence_ids': ['fragment_0000'], 'explanation': 'synthetic test'},
                'usage': {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120}}
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'unit-test-placeholder', 'OPENAI_MODEL': 'test-model'}), \
             patch('context_audit.verifier.prepare_finding', return_value=(payload, Mock())), \
             patch('context_audit.llm.analyze', return_value=fake) as api:
            result = run_pilot(candidates, self.root / 'pilot', 1)
            self.assertEqual(api.call_count, 1)
            self.assertEqual(result['actual_usage']['total_tokens'], 120)
            self.assertEqual(result['comparison']['llm_non_abstained']['TP'], 1)
            self.assertTrue((self.root / 'pilot/findings.csv').is_file())
            row = json.loads((self.root / 'pilot/findings.json').read_text())[0]
            self.assertEqual(row['explanation'], 'synthetic test')
            self.assertEqual(row['input_tokens'], 100)
            self.assertEqual(row['total_tokens'], 120)
            self.assertEqual(row['evidence_ids'], [payload['target']['id']])
            self.assertEqual(row['requested_fragment_ids'], [])
            self.assertEqual(result['average_rounds'], 1)
            self.assertEqual(result['source_function_resolution_failures'], 0)
            with (self.root / 'pilot/findings.csv').open() as stream:
                exported = next(csv.DictReader(stream))
            self.assertEqual(exported['explanation'], 'synthetic test')
            self.assertEqual(json.loads(exported['evidence_ids']), [payload['target']['id']])

            with self.assertRaisesRegex(ValueError, 'already exists'):
                run_pilot(candidates, self.root / 'pilot', 1)

    def test_large_pilot_rejected(self):
        from context_audit.cgt_sample import choose_sample
        with self.assertRaises(ValueError):
            choose_sample([], 21)


class MetricsTests(unittest.TestCase):
    def test_confusion_matrix(self):
        metrics = classification_metrics([True, True, False, False],
                                         ['confirmed', 'false_positive', 'confirmed', 'false_positive'])
        self.assertEqual([metrics[k] for k in ['TP', 'FP', 'TN', 'FN']], [1, 1, 1, 1])
        self.assertEqual(metrics['precision'], .5)
        self.assertEqual(metrics['recall'], .5)
        self.assertEqual(metrics['f1'], .5)
        self.assertEqual(metrics['false_positive_rate'], .5)

    def test_abstentions_do_not_count_as_fp_reduction(self):
        metrics = compare_verification([False, False, True], ['inconclusive', 'error', 'confirmed'])
        self.assertEqual(metrics['false_positive_reduction'], 0)
        self.assertEqual(metrics['conservative_retained_FP'], 2)
        self.assertAlmostEqual(metrics['llm_non_abstained']['coverage'], 1/3)

    def test_no_defined_denominator_is_null(self):
        self.assertIsNone(classification_metrics([], [])['precision'])
        self.assertIsNone(compare_verification([True], ['confirmed'])['false_positive_reduction'])

    def test_invalid_predictions_and_mismatched_lengths(self):
        for labels, verdicts in [([True], []), ([True], ['pending']), ([1], ['confirmed'])]:
            with self.assertRaises(ValueError):
                classification_metrics(labels, verdicts)

    def test_context_reduction_denominators(self):
        metrics = context_efficiency(100, 20, 50, 200)
        self.assertEqual(metrics['initial_source_reduction'], .8)
        self.assertEqual(metrics['initial_payload_reduction'], .5)
        self.assertEqual(metrics['cumulative_input_reduction'], -1)
        self.assertIsNone(context_efficiency(0, 0, 0, 0)['initial_source_reduction'])


class InferenceTests(unittest.TestCase):
    def payload(self):
        return {'task': 'verify_static_analysis_finding', 'finding': {
            'id': 'benchmark-true', 'tool': 'slither', 'detector': 'tx-origin', 'impact': 'High',
            'confidence': 'High', 'description': 'warning in expected_false.sol', 'contract': 'C',
            'function': 'f()', 'file': 'expected_false.sol', 'lines': [1], 'label': True},
            'target': {'id': 'expected_false.sol:function:1:10', 'source': 'f() { /* expected negative */ x(); }'},
            'available_context': [{'id': 'expected_false.sol:modifier:20:10', 'kind': 'modifier', 'name': 'm'}],
            'context_complete': False, 'label': False}

    def test_strip_comments_preserves_string_literals(self):
        self.assertEqual(strip_comments('"https://example" // label\nx();'), '"https://example"         \nx();')

    def test_no_label_or_filename_leak_and_ids_roundtrip(self):
        payload = self.payload()
        fake = Mock(return_value={'assessment': {'requested_ids': ['fragment_0001'], 'evidence_ids': ['fragment_0000']}})
        adapter = BlindAnalyzer(payload, fake)
        result = adapter(payload, [])
        sent = json.dumps(fake.call_args.args)
        for value in ['expected_false', 'benchmark-true', 'expected negative', '"label"']:
            self.assertNotIn(value, sent)
        self.assertEqual(result['assessment']['requested_ids'], [payload['available_context'][0]['id']])

    def test_existing_verifier_roundtrip_with_injected_inference(self):
        finding = parse_slither_findings({'success': True, 'results': {'detectors': [{'id': 'x'}]}})[0]
        result = verify_prepared_finding(finding, self.payload(), Mock(), 1,
                                        lambda *args: {'assessment': {'action': 'final', 'verdict': 'confirmed'}})
        self.assertEqual(result['assessment']['verdict'], 'confirmed')
        self.assertEqual(result['round_count'], 1)

    def test_round_limit_is_abstention(self):
        finding = parse_slither_findings({'success': True, 'results': {'detectors': [{'id': 'x'}]}})[0]
        payload = self.payload()
        fragment_id = payload['available_context'][0]['id']
        result = verify_prepared_finding(finding, payload, Mock(get=lambda key: {'id': key}), 1,
                                        lambda *args: {'assessment': {'action': 'request_context', 'verdict': 'pending',
                                                                    'requested_ids': [fragment_id]}})
        self.assertEqual(result['assessment']['verdict'], 'inconclusive')

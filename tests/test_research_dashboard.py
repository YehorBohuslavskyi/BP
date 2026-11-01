"""Saved research presentation checks; no inference or artifact mutation."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from context_audit.app.research import load_research, load_artifact, pilot_metrics, finding_rows, ROOT


class ResearchTests(unittest.TestCase):
    def test_artifact_loading_and_pilot_extraction(self):
        data = load_research()
        self.assertEqual(len(data['findings']), 10)
        metrics = pilot_metrics(data['pilot'])
        self.assertEqual(metrics['before']['FP'], 5)
        self.assertEqual(metrics['after']['FP'], 2)
        self.assertEqual(data['pilot']['actual_usage']['total_tokens'], 22424)

    def test_reduction_and_retention(self):
        metrics = pilot_metrics(load_research()['pilot'])
        self.assertEqual(metrics['fp_reduction'], .6)
        self.assertEqual(metrics['tp_retention'], 1)

    def test_zero_denominators(self):
        summary = copy.deepcopy(load_research()['pilot'])
        summary['comparison']['slither_candidate_baseline'].update(TP=0, FP=0)
        metrics = pilot_metrics(summary)
        self.assertIsNone(metrics['fp_reduction'])
        self.assertIsNone(metrics['tp_retention'])

    def test_missing_and_invalid_artifacts(self):
        with TemporaryDirectory() as directory:
            self.assertTrue(all(v is None for v in load_research(Path(directory)).values()))
            invalid = Path(directory) / 'bad.json'
            invalid.write_text('{broken')
            self.assertIsNone(load_artifact(invalid))

    def test_readable_table(self):
        rows = finding_rows(load_research()['findings'])
        self.assertEqual(sum(r['Ground truth'] == 'REAL' for r in rows), 5)
        self.assertEqual(sum(r['Correct?'] == 'CORRECT' for r in rows), 8)
        self.assertEqual(sum(r['Correct?'] == 'MISSED FP' for r in rows), 2)
        item = copy.deepcopy(load_research()['findings'][0])
        item['verdict'] = 'inconclusive'
        self.assertEqual(finding_rows([item])[0]['Correct?'], 'ABSTENTION')
        item['verdict'] = 'false_positive'
        self.assertEqual(finding_rows([item])[0]['Correct?'], 'WRONG REJECTION')

    def test_cohort_is_separate_from_pilot(self):
        data = load_research()
        self.assertEqual(data['cohort']['reviewed_eligible_findings'], 27)
        self.assertEqual(data['cohort']['baseline']['TP'], 22)
        self.assertAlmostEqual(data['cohort']['baseline']['precision'], 22 / 27)
        self.assertEqual(pilot_metrics(data['pilot'])['before']['precision'], .5)

    def test_smartbugs_is_detection_recall(self):
        summary = load_research()['smartbugs']['summary']
        self.assertEqual(summary['selected_contracts'], 18)
        self.assertEqual(summary['ground_truth_total'], 21)
        self.assertEqual(summary['detected'], 9)
        self.assertEqual(summary['missed'], 12)
        self.assertAlmostEqual(summary['recall'], 9 / 21)

    def test_dashboard_default_never_analyzes_or_calls_llm(self):
        from streamlit.testing.v1 import AppTest
        with patch('context_audit.app.session.analyze_upload') as analyze, \
             patch('context_audit.app.session.verify_selected') as verify:
            app = AppTest.from_file(str(ROOT / 'streamlit_app.py')).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.segmented_control(key='workspace_page').value, 'Evaluation Dashboard')
            self.assertTrue(any(m.value == '60%' for m in app.metric))
            app.run()
            analyze.assert_not_called()
            verify.assert_not_called()

    def test_missing_dashboard_artifacts_do_not_crash(self):
        from streamlit.testing.v1 import AppTest
        with patch('context_audit.app.dashboard.load_research', return_value=dict(pilot=None, findings=None, cohort=None, smartbugs=None)):
            app = AppTest.from_file(str(ROOT / 'streamlit_app.py')).run()
        self.assertFalse(app.exception)
        self.assertTrue(any(w.value == 'Research result artifact not available' for w in app.warning))

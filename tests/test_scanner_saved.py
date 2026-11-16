"""Saved evidence is authentic, clearly labeled, and usable without any scanner."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from context_audit.app.scanner_saved import EXAMPLES, SAVED_REPORT, load_saved_example


class SavedEvidenceTests(unittest.TestCase):
    def test_saved_original_verdicts_and_limited_review_are_preserved(self):
        with patch('openai.OpenAI.__init__', side_effect=AssertionError('No API')), patch('context_audit.direct_discovery.prepare', side_effect=AssertionError('No compiler')):
            for name, expected in zip(EXAMPLES, ('confirmed', 'rejected', 'inconclusive')):
                e = load_saved_example(name)
                self.assertEqual(e['original_verdict'], expected)
                self.assertFalse(e['new_scan'])
                self.assertTrue(e['consistency_review']['passed'])
                self.assertEqual(e['consistency_review']['mode'], 'historical_limited')

    def test_modified_saved_file_is_not_presented_as_preserved_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / SAVED_REPORT
            path.parent.mkdir(parents=True)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                load_saved_example(next(iter(EXAMPLES)), Path(directory))

    def test_saved_page_does_not_run_scans_or_inference(self):
        from streamlit.testing.v1 import AppTest
        root = Path(__file__).resolve().parents[1]
        with patch('openai.OpenAI.__init__', side_effect=AssertionError('No API')), patch('context_audit.direct_discovery.prepare', side_effect=AssertionError('No compiler')):
            app = AppTest.from_file(str(root / 'streamlit_app.py')).run()
            app.radio(key='analysis_mode').set_value('Saved LLM evidence').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.title[0].value, 'Saved LLM evidence')
            for label in EXAMPLES:
                app.selectbox(key='scanner_saved_example').set_value(label).run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)

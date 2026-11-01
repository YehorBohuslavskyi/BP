"""Demonstration sources load locally without starting analysis or inference."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from context_audit.app.config import ApplicationError
from context_audit.app.demos import DEMO_CONTRACTS, load_demo


class DemoTests(unittest.TestCase):
    def test_confirmed_demo_is_registered_and_readable(self):
        name, content = load_demo('simple_suicide')
        self.assertEqual(name, 'simple_suicide.sol')
        self.assertIn(b'selfdestruct', content)
        self.assertIn('Confirmed vulnerability example', DEMO_CONTRACTS['simple_suicide'].label)

    def test_missing_or_unknown_demo_is_a_safe_error(self):
        with self.assertRaises(ApplicationError):
            load_demo('unknown')
        with TemporaryDirectory() as directory:
            with self.assertRaises(ApplicationError):
                load_demo('simple_suicide', Path(directory))

    def test_demo_load_requires_no_slither_or_llm_call(self):
        from streamlit.testing.v1 import AppTest
        root = Path(__file__).resolve().parents[1]
        with patch('context_audit.app.session.analyze_upload') as analyze, \
             patch('context_audit.app.session.verify_selected') as verify:
            app = AppTest.from_file(str(root / 'streamlit_app.py')).run()
            app.segmented_control(key='workspace_page').set_value('Analyze Contract').run()
            app.segmented_control(key='source_mode').set_value('Demo').run()
            next(b for b in app.button if b.label == 'Load selected demo').click().run()
            self.assertFalse(app.exception)
            session = app.session_state['audit_session']
            self.addCleanup(session.clear)
            self.assertIn('selfdestruct', session.upload.source)
            self.assertIsNone(session.analysis)
            app.run()
            analyze.assert_not_called()
            verify.assert_not_called()

"""Streamlit runtime smoke tests, enabled when the optional GUI dependency is installed."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


@unittest.skipUnless(importlib.util.find_spec('streamlit'), 'Optional Streamlit dependency is not installed')
class StreamlitTests(unittest.TestCase):
    def test_initial_screen_does_not_run_analysis_or_inference(self):
        from streamlit.testing.v1 import AppTest
        root = Path(__file__).resolve().parents[1]
        with patch('context_audit.app.session.analyze_upload') as analysis, \
             patch('context_audit.app.session.verify_selected') as inference:
            app = AppTest.from_file(str(root / 'streamlit_app.py')).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.title[0].value, 'Smart contract vulnerability verifier')
        analysis.assert_not_called()
        inference.assert_not_called()

    def test_ten_round_selection_and_explicit_verification(self):
        import os
        from types import SimpleNamespace
        from streamlit.testing.v1 import AppTest
        from context_audit.app.services import Analysis
        from context_audit.findings import Finding

        content = b'pragma solidity ^0.4.25; contract Demo { function kill() public { selfdestruct(msg.sender); } }'
        uploaded = SimpleNamespace(name='demo.sol', getvalue=lambda: content)
        warning = Finding('gui-test', 'suicidal', 'High', 'High', 'Unprotected destruction',
                          'Demo', 'kill()', 'source.sol', [1], 39, 51)
        assessment = {'action': 'final', 'verdict': 'confirmed', 'explanation': 'Synthetic UI test response',
                      'requested_ids': [], 'evidence_ids': ['target']}
        report = {
            'result': {'assessment': assessment, 'provided_context': [],
                       'rounds': [{'round': 1, 'result': {'assessment': assessment}}]},
            'summary': {'rounds': 1, 'input_tokens': 100, 'output_tokens': 10,
                        'total_tokens': 110, 'requested_fragments': 0},
            'initial_payload': {'target': {'id': 'target', 'source': content.decode()}},
            'context_efficiency': {'full_source_tokens': 100, 'initial_source_tokens': 20,
                                  'initial_payload_tokens': 30, 'initial_payload_reduction': .7,
                                  'cumulative_input_reduction': 0},
            'source_bytes': len(content), 'model': 'test-only', 'compiler': '0.4.25',
        }
        root = Path(__file__).resolve().parents[1]
        with patch.dict(os.environ, {'OPENAI_MODEL': 'test-only', 'OPENAI_API_KEY': 'test-only',
                                     'OPENAI_MODELS': 'alternate-test-model'}), \
             patch('streamlit.file_uploader', return_value=uploaded), \
             patch('context_audit.app.gui.compatible_compilers', return_value=['0.4.25']), \
             patch('context_audit.app.session.analyze_upload',
                   side_effect=lambda upload, compiler: Analysis(compiler, upload.digest, [warning], {})) as analyze, \
             patch('context_audit.app.session.verify_selected', return_value=report) as verify:
            app = AppTest.from_file(str(root / 'streamlit_app.py')).run()
            self.addCleanup(app.session_state['audit_session'].clear)
            self.assertFalse(app.exception)
            self.assertEqual(app.slider[0].value, 4)
            self.assertEqual(app.slider[0].max, 10)
            app.slider[0].set_value(10).run()
            self.assertEqual(app.selectbox(key='verification_model').value, 'test-only')
            app.selectbox(key='verification_model').set_value('alternate-test-model').run()
            self.assertEqual(os.environ['OPENAI_MODEL'], 'test-only')
            analyze.assert_not_called()
            verify.assert_not_called()
            next(button for button in app.button if button.label == 'Run Slither').click().run()
            self.assertFalse(app.exception)
            analyze.assert_called_once()
            verify.assert_not_called()
            next(button for button in app.button if button.label == 'Verify selected finding').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(verify.call_args.args[3].max_rounds, 10)
            self.assertEqual(verify.call_args.args[3].model, 'alternate-test-model')
            self.assertTrue(any(metric.value == '110' for metric in app.metric))
            app.run()
            verify.assert_called_once()
            self.assertEqual(app.selectbox(key='verification_model').value, 'alternate-test-model')

    def test_model_can_be_entered_without_server_default(self):
        import os
        from streamlit.testing.v1 import AppTest
        root = Path(__file__).resolve().parents[1]
        with patch.dict(os.environ, {'OPENAI_MODEL': '', 'OPENAI_MODELS': ''}), \
             patch('context_audit.app.session.verify_selected') as verify:
            app = AppTest.from_file(str(root / 'streamlit_app.py')).run()
            self.assertEqual(app.selectbox(key='verification_model').value, '')
            app.text_input(key='custom_verification_model').set_value('custom-test-model').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input(key='custom_verification_model').value, 'custom-test-model')
            self.assertEqual(os.environ['OPENAI_MODEL'], '')
            verify.assert_not_called()

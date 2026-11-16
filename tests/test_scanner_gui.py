"""New scanner screen: explicit actions, state invalidation, and real local scans."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class ScannerGuiTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(ROOT / 'streamlit_app.py'), default_timeout=30).run()
        self.addCleanup(lambda: app.session_state['scanner_upload'].close() if 'scanner_upload' in app.session_state else None)
        return app

    def test_landing_page_is_offline_and_does_not_start_scan(self):
        with patch('context_audit.app.scanner_page.scan_static') as static, patch('context_audit.app.scanner_page.scan_direct') as live:
            app = self.app()
            self.assertFalse(app.exception)
            self.assertEqual(app.title[0].value, 'Smart Contract Scanner')
            app.run()
            static.assert_not_called()
            live.assert_not_called()

    def test_real_scan_then_rerender_keeps_report_and_source_change_clears(self):
        with patch('context_audit.app.scanner_page.scan_direct') as live:
            app = self.app()
            app.button(key='scanner_static_run').click().run()
            self.assertFalse(app.exception)
            report = app.session_state['scanner_report']
            self.assertTrue(any(f['type'] == 'reentrancy-eth' for f in report['findings']))
            app.run()
            self.assertEqual(app.session_state['scanner_report'], report)
            app.selectbox(key='scanner_example').set_value('Guarded vault').run()
            self.assertNotIn('scanner_report', app.session_state)
            self.assertFalse(app.exception)
            live.assert_not_called()

    def test_direct_preparation_without_key_disables_paid_scan(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': '', 'OPENAI_MODEL': ''}), patch('context_audit.app.scanner_page.scan_direct') as live:
            app = self.app()
            app.radio(key='scanner_method').set_value('Direct LLM scan (v2)').run()
            app.button(key='scanner_prepare').click().run()
            app.selectbox(key='scanner_provider').set_value('OpenAI API (separate billing)').run()
            self.assertFalse(app.exception)
            self.assertTrue(app.button(key='scanner_live_run').disabled)
            self.assertEqual(app.session_state['scanner_prepared']['analyzable_functions'], 2)
            app.run()
            live.assert_not_called()

    def test_paste_compile_error_does_not_crash_app(self):
        app = self.app()
        app.radio(key='scanner_source_method').set_value('Paste').run()
        app.text_area(key='scanner_paste').set_value('pragma solidity 0.8.24; contract Broken { oops }').run()
        app.button(key='scanner_static_run').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)


    def test_session_password_requires_consent_and_can_be_forgotten(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': '', 'OPENAI_MODEL': ''}), patch('context_audit.app.scanner_page.scan_direct') as live:
            app = self.app()
            app.radio(key='scanner_method').set_value('Direct LLM scan (v2)').run()
            app.button(key='scanner_prepare').click().run()
            app.selectbox(key='scanner_provider').set_value('OpenAI API (separate billing)').run()
            app.text_input(key='scanner_model').set_value('test-fixture').run()
            app.text_input(key='scanner_session_api_key').set_value('synthetic-session-key').run()
            self.assertTrue(app.button(key='scanner_live_run').disabled)
            app.checkbox(key='scanner_cost_ack').check().run()
            self.assertFalse(app.button(key='scanner_live_run').disabled)
            live.assert_not_called()
            app.button(key='scanner_forget_key').click().run()
            self.assertEqual(app.text_input(key='scanner_session_api_key').value, '')
            self.assertTrue(app.button(key='scanner_live_run').disabled)
            self.assertFalse(app.exception)

    def test_expanded_profile_updates_visible_limits_without_starting_model(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'','OPENAI_MODEL':''}), patch('context_audit.app.scanner_page.scan_direct') as live:
            app = self.app()
            app.radio(key='scanner_method').set_value('Direct LLM scan (v2)').run()
            app.button(key='scanner_prepare').click().run()
            app.selectbox(key='scanner_provider').set_value('OpenAI API (separate billing)').run()
            app.selectbox(key='scanner_limit_profile').set_value('Expanded review').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.number_input(key='scanner_candidate_limit').value,6)
            self.assertEqual(app.number_input(key='scanner_round_limit').value,5)
            self.assertEqual(app.number_input(key='scanner_fragment_limit').value,12)
            self.assertEqual(app.number_input(key='scanner_verification_tokens').value,400000)
            app.number_input(key='scanner_candidate_limit').set_value(7).run()
            self.assertEqual(app.number_input(key='scanner_candidate_limit').value,7)
            app.selectbox(key='scanner_limit_profile').set_value('Current settings').run()
            self.assertEqual(app.number_input(key='scanner_candidate_limit').value,3)
            self.assertEqual(app.number_input(key='scanner_fragment_limit').value,20)
            self.assertEqual(app.number_input(key='scanner_verification_tokens').value,60000)
            live.assert_not_called()

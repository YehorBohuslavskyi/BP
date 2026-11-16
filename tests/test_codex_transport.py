"""Subscription transport tests use fake CLI responses, never account quota."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from context_audit.codex_transport import (
    CodexTransport,CodexStopped,clean_environment,command_for,parse_events,cli_path,login_status,
)
from context_audit.direct_discovery import StrictModel
from context_audit.app.scanner import ScannerSettings


class Probe(StrictModel):
    ok: bool


class CodexTransportTests(unittest.TestCase):
    def test_api_keys_and_custom_endpoint_are_removed(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'fake-one','CODEX_API_KEY':'fake-two','OPENAI_BASE_URL':'https://invalid'}):
            env=clean_environment()
        self.assertNotIn('OPENAI_API_KEY',env)
        self.assertNotIn('CODEX_API_KEY',env)
        self.assertNotIn('OPENAI_BASE_URL',env)

    def test_command_forces_chatgpt_and_disables_tools(self):
        command=command_for(Path('/bin/codex'),Path('/tmp/one'),Path('/tmp/one/schema.json'),Path('/tmp/one/result.json'),'test')
        self.assertIn('forced_login_method="chatgpt"',command)
        self.assertIn('--ignore-user-config',command)
        self.assertIn('--ephemeral',command)
        self.assertIn('read-only',command)
        for feature in ('shell_tool','plugins','apps','multi_agent','browser_use','hooks'):
            self.assertIn(feature,command)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',command)

    def test_windows_paths_are_explicitly_mapped(self):
        self.assertEqual(cli_path('/mnt/c/Scan Folder/one.json',Path('/mnt/c/codex.exe')),'C:\\Scan Folder\\one.json')
        with self.assertRaises(CodexStopped):
            cli_path('/home/private/evaluation.json',Path('/mnt/c/codex.exe'))

    def test_api_key_login_cannot_pass_subscription_check(self):
        with patch('context_audit.codex_transport.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='Logged in using an API key',stderr='')):
            self.assertFalse(login_status(Path('/bin/codex')))

    def test_tools_invalidate_source_only_assessment(self):
        events=[{'type':'thread.started','thread_id':'id'},
            {'type':'item.completed','item':{'type':'command_execution'}},
            {'type':'turn.completed','usage':{'input_tokens':3,'output_tokens':1}}]
        with self.assertRaisesRegex(CodexStopped,'SOURCE_ISOLATION'):
            parse_events('\n'.join(map(json.dumps,events)))

    def test_incomplete_turn_is_not_accepted(self):
        with self.assertRaises(CodexStopped):
            parse_events(json.dumps({'type':'thread.started','thread_id':'id'}))

    def test_quota_error_is_not_silently_retried(self):
        with self.assertRaisesRegex(CodexStopped,'LIMIT_REACHED'):
            parse_events(json.dumps({'type':'turn.failed','error':{'message':'quota'}}))

    def test_usage_is_required(self):
        events=[{'type':'thread.started','thread_id':'id'},{'type':'turn.completed','usage':{'input_tokens':1}}]
        with self.assertRaisesRegex(CodexStopped,'USAGE_UNKNOWN'):
            parse_events('\n'.join(map(json.dumps,events)))

    def test_subscription_settings_do_not_require_api_key(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':''}):
            ScannerSettings('test',provider='codex').validate()

    def test_structured_response_usage_and_call_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def fake_run(command,**kwargs):
                if command[-2:]==['login','status']:
                    return SimpleNamespace(returncode=0,stdout='Logged in using ChatGPT',stderr='')
                result=Path(command[command.index('--output-last-message')+1])
                result.write_text('{"ok":true}')
                events=[{'type':'thread.started','thread_id':'unique'},
                    {'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}},
                    {'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':3,'cached_input_tokens':5}}]
                return SimpleNamespace(returncode=0,stdout='\n'.join(map(json.dumps,events)),stderr='')
            with patch('context_audit.codex_transport.resolve_paths',return_value=(root/'codex',root/'scratch')), \
                 patch('context_audit.codex_transport.subprocess.run',side_effect=fake_run) as run:
                t=CodexTransport(root/'output',max_calls=1)
                r=t.call('test',[],Probe,20)
                self.assertTrue(r['assessment']['ok'])
                self.assertEqual(r['usage']['total_tokens'],13)
                self.assertEqual(r['provider'],'codex_chatgpt')
                with self.assertRaisesRegex(CodexStopped,'SCAN_LIMIT'):
                    t.call('test',[],Probe,20)
                self.assertEqual(run.call_count,2)

    def test_cli_failure_stops_transport_with_no_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch('context_audit.codex_transport.resolve_paths',return_value=(root/'codex',root/'scratch')), \
                 patch('context_audit.codex_transport.login_status',return_value=True), \
                 patch('context_audit.codex_transport.subprocess.run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='')) as run:
                t=CodexTransport(root/'output')
                with self.assertRaises(CodexStopped):t.call('test',[],Probe,20)
                with self.assertRaises(CodexStopped):t.call('test',[],Probe,20)
                run.assert_called_once()


    def test_failed_turn_with_zero_exit_retains_only_redacted_public_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            events=[{'type':'item.completed','item':{'type':'reasoning','text':'PRIVATE_REASONING_SENTINEL'}},
                    {'type':'turn.failed','error':{'message':'Usage limit. Bearer secret-token sk-fakecredential123456'}}]
            with patch('context_audit.codex_transport.resolve_paths',return_value=(root/'codex',root/'scratch')), \
                 patch('context_audit.codex_transport.login_status',return_value=True), \
                 patch('context_audit.codex_transport.subprocess.run',return_value=SimpleNamespace(
                     returncode=0,stdout='\n'.join(map(json.dumps,events)),stderr='')) as run:
                transport=CodexTransport(root/'output')
                with self.assertRaisesRegex(CodexStopped,'LIMIT_REACHED'):
                    transport.call('test',[],Probe,20)
                with self.assertRaisesRegex(CodexStopped,'ALREADY_STOPPED'):
                    transport.call('test',[],Probe,20)
                run.assert_called_once()
            saved=(root/'output/subscription-transport.json').read_text()
            self.assertIn('Usage limit.',saved)
            self.assertIn('[REDACTED]',saved)
            self.assertNotIn('secret-token',saved)
            self.assertNotIn('sk-fakecredential123456',saved)
            self.assertNotIn('PRIVATE_REASONING_SENTINEL',saved)
            self.assertFalse(transport.state['api_fallback'])


class CodexScreenTests(unittest.TestCase):
    def test_subscription_screen_needs_no_key_and_does_not_run_on_render(self):
        from streamlit.testing.v1 import AppTest
        repo=Path(__file__).resolve().parents[1]
        with patch('context_audit.codex_transport.login_status',return_value=True), \
             patch('context_audit.app.scanner_page.scan_direct') as live:
            app=AppTest.from_file(str(repo/'streamlit_app.py'),default_timeout=30).run()
            self.addCleanup(lambda:app.session_state['scanner_upload'].close())
            app.radio(key='scanner_method').set_value('Direct LLM scan (v2)').run()
            app.button(key='scanner_prepare').click().run()
            self.assertEqual(app.selectbox(key='scanner_provider').value,'Codex subscription')
            self.assertNotIn('scanner_session_api_key',[field.key for field in app.text_input])
            app.checkbox(key='scanner_codex_ack').check().run()
            self.assertFalse(app.button(key='scanner_live_run').disabled)
            live.assert_not_called()
            self.assertFalse(app.exception)


class SubscriptionWorkerLayoutTests(unittest.TestCase):
    def test_telemetry_stays_outside_strict_verification_directory(self):
        from context_audit.app.scanner_worker import run_job
        from context_audit.app.services import create_upload
        from test_direct_verification import final
        repo=Path(__file__).resolve().parents[1]
        upload=create_upload('demo.sol',(repo/'examples/scanner/VulnerableVault.sol').read_bytes())
        self.addCleanup(upload.close)
        request={'action':'prepare','source':str(upload.source_path),'source_sha256':upload.digest}
        prepared=run_job(request)
        output=upload.source_path.parent/'analysis'
        class Fake:
            def __init__(self,path,*args,**kwargs):
                self.path=Path(path);self.path.mkdir();self.state={}
                (self.path/'subscription-transport.json').write_text('{}')
            def discover(self,batch):
                row=next(f for f in batch['functions'] if f['signature']=='withdraw()')
                return {'assessment':{'examined_functions':[{'fragment_id':f['fragment_id'],'reason':'Reviewed'} for f in batch['functions']],
                    'candidates':[dict(candidate_id='one',contract=batch['contract'],primary_function=row['signature'],primary_fragment_id=row['fragment_id'],
                        suspected_type='Ordering',reason='Review ordering',related_fragment_ids=[],requested_context_ids=[],uncertainty='Needs source')]},
                    'usage':{'input_tokens':10,'output_tokens':5,'total_tokens':15}}
            def verify(self,payload,supplied,**kwargs):
                return final(payload,supplied)
        request.update(action='scan',settings={'model':'fixture','provider':'codex'},
            output=str(output),prepared_identity=prepared['source_identity'])
        with patch.dict(os.environ,{'OPENAI_MODEL':'fixture'}),patch('context_audit.codex_transport.CodexTransport',Fake):
            response=run_job(request)
        self.assertEqual(response['report']['coverage_counts']['confirmed_candidates'],1)
        self.assertTrue((output.parent/'analysis-codex/subscription-transport.json').exists())
        self.assertFalse((output/'codex').exists())

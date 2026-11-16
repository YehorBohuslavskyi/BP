"""A local scanner workspace with explicit preparation and model execution."""
import hashlib
import os
from pathlib import Path

import streamlit as st

from context_audit.app.compilers import compatible_compilers
from context_audit.app.config import ApplicationError
from context_audit.app.services import create_upload
from context_audit.app.scanner import (
    ScannerSettings, prepare_upload, scan_direct, direct_report, scan_static, report_json, report_html,
)

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = {'Vulnerable vault': 'VulnerableVault.sol', 'Guarded vault': 'GuardedVault.sol'}


def load_example(name):
    filename = EXAMPLES[name]
    return filename, (ROOT / 'examples/scanner' / filename).read_bytes()


def clear_workspace():
    upload = st.session_state.pop('scanner_upload', None)
    if upload:
        upload.close()
    st.session_state.pop('scanner_prepared', None)
    st.session_state.pop('scanner_report', None)


def _current_upload(name, data):
    digest = hashlib.sha256(data.decode('utf-8-sig').encode('utf-8')).hexdigest()
    upload = st.session_state.get('scanner_upload')
    if not upload or upload.digest != digest:
        # Validate first so an invalid replacement does not delete an existing run.
        replacement = create_upload(name, data)
        clear_workspace()
        st.session_state.scanner_upload = replacement
    return st.session_state.scanner_upload


def render_report(report):
    st.divider()
    label = 'Local static analysis' if report['analysis_kind'] == 'local_static' else 'Direct LLM scanner · v2'
    st.subheader('Scan results')
    st.caption(f"{label} · Compiler {report['compiler']} · {report['status'].upper()}")
    if report.get('model'):
        st.caption('Model used for this report: ' + report['model'])
    if report['status'] == 'partial':
        st.warning('The scan is partial. Some candidates failed validation or reached a limit. Review coverage and errors below.')
    if report['analysis_kind'] == 'local_static':
        st.metric('Static warnings', len(report['findings']))
    else:
        columns = st.columns(4)
        for column, text, key in zip(columns, ('Confirmed', 'Rejected hypotheses', 'Inconclusive', 'Processing failures'),
            ('confirmed_candidates', 'rejected_candidates', 'inconclusive_candidates', 'processing_failures')):
            column.metric(text, report['counts'][key])
    if not report['findings']:
        st.info('No findings were reported. Review function coverage; this does not establish that the contract is secure.')
    else:
        st.dataframe([{'Function': f['function'], 'Type': f['type'],
            'Result': (f['verdict'] or f['status']).replace('_', ' '),
            'Severity': f['severity'] or '—'} for f in report['findings']], hide_index=True, width='stretch')
        for f in report['findings']:
            with st.expander(f"{f['function']} · {f['type']} · {(f['verdict'] or f['status']).replace('_', ' ')}"):
                st.write(f['explanation'] or f.get('hypothesis', 'No accepted assessment.'))
                if f['errors']:
                    st.error('Processing outcome: ' + ', '.join(f['errors']))
                if f.get('consistency') and not f['consistency']['passed']:
                    st.write('Validation rules: ' + ', '.join(f['consistency']['failed_rules']))
                    st.caption('The original model verdict was not accepted as a security finding.')
                if f.get('flow'):
                    st.write('Execution flow')
                    for step in f['flow']:
                        st.write('• ' + step)
                if f.get('incomplete_evidence'):
                    st.write('Unresolved evidence: ' + '; '.join(f['incomplete_evidence']))
                for e in f['evidence']:
                    st.caption(e['name'] + ' · cited source')
                    st.code(e['source'], language='solidity')
                if f['lines']:
                    first, last = min(f['lines']), max(f['lines'])
                    st.caption(f'Source lines {first}–{last}')
                    st.code('\n'.join(f'{i}: {line}' for i, line in enumerate(report['source'].splitlines(), 1)
                                      if first <= i <= last), language='solidity')
    if report.get('coverage'):
        with st.expander('Function coverage'):
            st.dataframe([{'Contract': r['contract'], 'Function': r['signature'], 'Status': r['status'],
                           'Reason': r['reason']} for r in report['coverage']], hide_index=True, width='stretch')
            st.caption('Not selected is a discovery decision, not a safe verdict.')
    if report.get('discovery_errors'):
        st.warning('Discovery errors were recorded; affected functions were not fully evaluated.')
        st.json(report['discovery_errors'])
    usage = report['usage']
    if report.get('provider') == 'codex':
        st.caption(f"Codex turns: {usage['model_turns']} · API-key requests: 0 · Reported tokens: {usage['total_tokens']:,}")
        st.caption(report['billing_note'])
    else:
        st.caption(f"API requests: {usage['api_calls']} · Reported tokens: {usage['total_tokens']:,}")
    if usage['unknown_usage_calls']:
        st.warning('Some requests have unknown usage. Reported tokens are a lower bound.')
    if report.get('efficiency'):
        e = report['efficiency']
        st.caption(f"Verification rounds: {e['rounds']} · Additional source fragments: {e['retrieved_fragments']}")
        if e['verification_context_reduction'] is not None:
            st.caption(f"Estimated source-context reduction: {e['verification_context_reduction']:.1%}. This is not billing savings or detection accuracy.")
    st.caption('Findings require review. This scanner does not execute exploits or prove that a contract is secure.')
    columns = st.columns(2)
    columns[0].download_button('Download JSON report', report_json(report), file_name='scan-report.json',
        mime='application/json', on_click='ignore')
    columns[1].download_button('Download readable report', report_html(report), file_name='scan-report.html',
        mime='text/html', on_click='ignore')


def forget_session_key():
    st.session_state.pop('scanner_session_api_key', None)


def render_scanner():
    st.title('Smart Contract Scanner')
    st.write('Inspect Solidity source, review findings, and export the evidence.')
    kind = st.radio('Scan method', ['Local static scan (no API)', 'Direct LLM scan (v2)'], key='scanner_method', horizontal=True)
    st.caption('Local scanning uses Slither. Direct LLM scanning discovers hypotheses from contract structure and verifies them against selected source.')
    method = st.radio('Source', ['Example', 'Upload', 'Paste'], key='scanner_source_method', horizontal=True)
    name, data = 'source.sol', b''
    if method == 'Example':
        example = st.selectbox('Example contract', list(EXAMPLES), key='scanner_example')
        name, data = load_example(example)
    elif method == 'Upload':
        uploaded = st.file_uploader('Solidity file', type=['sol'], key='scanner_file',
            help='One self-contained UTF-8 file, up to 1 MiB. Use the advanced CLI for projects with imports.')
        if uploaded:
            name, data = uploaded.name, uploaded.getvalue()
    else:
        text = st.text_area('Solidity source', height=300, key='scanner_paste')
        data = text.encode('utf-8')
    if not data:
        st.info('Choose an example, upload a .sol file, or paste Solidity source.')
        return
    try:
        upload = _current_upload(name, data)
        compilers = compatible_compilers(upload.source)
        if not compilers:
            st.error('No compatible compiler is installed. Install a release matching the source pragma before scanning.')
            return
        with st.expander('Contract source', expanded=False):
            st.code(upload.source, language='solidity', line_numbers=True)
        st.caption(f'{name} · Source hash {upload.digest[:12]} · Compatible compilers: ' + ', '.join(compilers))
        if kind.startswith('Local'):
            compiler = st.selectbox('Compiler', compilers, key='scanner_compiler')
            if st.button('Run local scan', key='scanner_static_run', type='primary'):
                st.session_state.pop('scanner_report', None)
                with st.spinner('Compiling and scanning locally…'):
                    st.session_state.scanner_report = scan_static(upload, compiler)
        else:
            st.subheader('1. Prepare source')
            st.caption('Compiles and indexes locally. This step makes no model requests.')
            if st.button('Prepare contract', key='scanner_prepare'):
                with st.spinner('Compiling and building the function catalog…'):
                    st.session_state.scanner_prepared = prepare_upload(upload)
            prepared = st.session_state.get('scanner_prepared')
            if prepared:
                st.success(f"Prepared {prepared['analyzable_functions']} of {prepared['function_count']} function rows · {prepared['batch_count']} discovery batches · solc {prepared['compiler']}")
                st.subheader('2. Discover and verify')
                provider = st.selectbox('LLM access', ['Codex subscription', 'OpenAI API (separate billing)'], key='scanner_provider')
                use_codex = provider == 'Codex subscription'
                if use_codex:
                    model = st.text_input('Codex model', 'gpt-6-luna', key='scanner_codex_model')
                    api_key = None
                    from context_audit.codex_transport import login_status
                    try:
                        codex_ready = login_status()
                    except (OSError, RuntimeError):
                        codex_ready = False
                    if codex_ready:
                        st.success('Codex is signed in with ChatGPT. This route uses your existing plan allowance.')
                    else:
                        st.info('Sign into the installed Codex CLI with ChatGPT to enable subscription scanning.')
                else:
                    model = st.text_input('Model ID', os.environ.get('OPENAI_MODEL', 'gpt-5.4-mini-2026-03-17'), key='scanner_model')
                    api_key = st.text_input('OpenAI API key (session only)', type='password', key='scanner_session_api_key',
                        help='Optional if configured on the server. Never saved to reports.')
                    if api_key:
                        st.button('Forget session key', on_click=forget_session_key, key='scanner_forget_key')
                profile_names = {'Current settings':None,'More investigation steps':'rounds',
                    'More related code':'context','More candidates':'coverage','Expanded review':'expanded'}
                def reset_limit_controls():
                    for key in ('scanner_candidate_limit','scanner_round_limit','scanner_fragment_limit',
                                'scanner_source_limit','scanner_verification_tokens'):
                        st.session_state.pop(key,None)
                selected_profile = st.selectbox('Review depth',list(profile_names),
                    key='scanner_limit_profile',on_change=reset_limit_controls)
                profile = profile_names[selected_profile]
                defaults = (ScannerSettings.for_profile(model,profile,provider='codex' if use_codex else 'openai')
                    if profile else ScannerSettings(model))
                columns = st.columns(2)
                candidates = columns[0].number_input('Maximum candidates to verify', 1, 10, defaults.max_candidates, key='scanner_candidate_limit')
                rounds = columns[1].number_input('Maximum rounds per candidate', 1, 6, defaults.max_rounds, key='scanner_round_limit')
                fragments = columns[0].number_input('Maximum related code fragments',0,64,defaults.max_fragments,key='scanner_fragment_limit')
                source_tokens = columns[1].number_input('Source context token limit',1,64000,defaults.max_source_tokens,key='scanner_source_limit')
                ready = bool(model.strip() and prepared['analyzable_functions'] and
                    (codex_ready if use_codex else (api_key or os.environ.get('OPENAI_API_KEY'))))
                if not use_codex and not (api_key or os.environ.get('OPENAI_API_KEY')):
                    st.info('Enter an API key for paid API scanning, or choose Codex subscription above.')
                token_budget = st.number_input('Verification token budget', min_value=4000, max_value=1000000,
                    value=defaults.max_verification_tokens, step=1000, key='scanner_verification_tokens')
                ceiling = prepared['batch_count'] + candidates * rounds
                if use_codex:
                    st.caption(f'At most {ceiling} Codex turns. Uses your plan limits; no API fallback or credit purchases. No automatic application retries.')
                    observed_cap = ScannerSettings(model,max_verification_tokens=int(token_budget),max_input_tokens=defaults.max_input_tokens).observed_token_cap(prepared['batch_count'])
                    st.caption(f'Verification budget: {int(token_budget):,} tokens; total observed-token stop: {observed_cap:,}, including discovery. The last response may exceed that threshold. Estimates are not a hard provider cap.')
                    consent = st.checkbox('Use my existing Codex allowance for this scan.', key='scanner_codex_ack')
                else:
                    st.caption(f'At most {ceiling} model requests. Verification budget: {int(token_budget):,} reported tokens; discovery usage is additional. No automatic retries.')
                    consent = st.checkbox('I understand this scan sends source fragments to OpenAI and may incur API charges.', key='scanner_cost_ack')
                if st.button('Run LLM scan', key='scanner_live_run', type='primary', disabled=not (ready and consent)):
                    settings = ScannerSettings(model=model.strip(), max_rounds=int(rounds), max_candidates=int(candidates),
                        provider='codex' if use_codex else 'openai', max_verification_tokens=int(token_budget),
                        max_fragments=int(fragments),max_source_tokens=int(source_tokens),
                        max_input_tokens=defaults.max_input_tokens,max_output_tokens=defaults.max_output_tokens)
                    st.session_state.pop('scanner_report', None)
                    with st.spinner('Discovering hypotheses and verifying source evidence…'):
                        response = scan_direct(upload, prepared, settings, api_key=api_key or None)
                        st.session_state.scanner_report = direct_report(upload, response, settings)
        report = st.session_state.get('scanner_report')
        if report:
            expected = 'local_static' if kind.startswith('Local') else 'direct_llm_v2'
            if report['analysis_kind'] == expected:
                render_report(report)
        if st.button('Clear scanner workspace', key='scanner_clear'):
            clear_workspace()
            st.rerun()
    except (UnicodeDecodeError, ApplicationError) as exc:
        st.error(str(exc) if isinstance(exc, ApplicationError) else 'The Solidity source must be UTF-8 text.')
    except OSError:
        st.error('The local source or workspace is unavailable. Load the source again.')

"""Streamlit presentation for the single-file application service workflow."""
import os
from importlib.metadata import PackageNotFoundError, version

import streamlit as st

from context_audit.app.compilers import compatible_compilers
from context_audit.app.config import ApplicationError, DEFAULT_ROUNDS, MAX_ROUNDS, VerificationSettings
from context_audit.app.services import export_analysis
from context_audit.app.session import AuditSession


def render_verification(report: dict) -> None:
    """Display one verdict together with the source fragments and measured usage."""
    result, summary = report['result'], report['summary']
    assessment = result['assessment']
    verdict = assessment['verdict']
    display = {'confirmed': st.error, 'false_positive': st.success, 'inconclusive': st.warning}
    display[verdict](verdict.replace('_', ' ').upper())
    st.write(assessment['explanation'])
    st.caption(f"Model: {report['model']} · Compiler: {report['compiler']}")
    columns = st.columns(4)
    for column, label, value in zip(columns,
                                   ('Rounds', 'Input tokens', 'Output tokens', 'Total tokens'),
                                   (summary['rounds'], summary['input_tokens'], summary['output_tokens'], summary['total_tokens'])):
        column.metric(label, value, border=True)
    target = report['initial_payload']['target']
    fragments = {target['id']: target, **{item['id']: item for item in result['provided_context']}}
    with st.expander('Evidence and requested context', expanded=False):
        st.write('Evidence IDs', assessment['evidence_ids'])
        for fragment_id in assessment['evidence_ids']:
            fragment = fragments.get(fragment_id)
            if fragment:
                st.caption(fragment_id)
                st.code(fragment['source'], language='solidity', line_numbers=True)
        for round_info in result['rounds']:
            decision = round_info['result']['assessment']
            st.write(f"Round {round_info['round']}: {decision['action']}")
            st.write(decision['explanation'])
            for fragment_id in decision['requested_ids']:
                st.caption(f'Requested: {fragment_id}')
                if fragment_id in fragments:
                    st.code(fragments[fragment_id]['source'], language='solidity', line_numbers=True)

    st.subheader('Context efficiency')
    metrics = report['context_efficiency']
    columns = st.columns(3)
    columns[0].metric('Full source · estimated tokens', metrics['full_source_tokens'])
    columns[1].metric('Initial payload · estimated tokens', metrics['initial_payload_tokens'])
    columns[2].metric('Requested fragments', summary['requested_fragments'])
    st.caption(f"Full source: {report['source_bytes']:,} bytes · Initial target: {metrics['initial_source_tokens']:,} estimated tokens")
    reduction = metrics['initial_payload_reduction']
    cumulative = metrics['cumulative_input_reduction']
    st.write(f"Initial payload reduction: {reduction:.1%}" if reduction is not None else 'Initial reduction: undefined')
    st.write(f"Cumulative API input reduction: {cumulative:.1%}" if cumulative is not None else 'Cumulative reduction: undefined')
    st.caption('Source and payload estimates use characters ÷ 4. API tokens are actual reported usage. '
               'Cumulative input includes repeated context and request overhead; reduction can be negative.')


def render_sidebar(default_model: str) -> tuple[str, int]:
    """Select a session-local model and make the recommended round budget explicit."""
    with st.sidebar:
        st.markdown("### :material/policy: Context audit")
        st.caption('SMART CONTRACT VERIFICATION')
        st.divider()
        st.subheader('Verification settings')
        max_rounds = st.slider(
            'Maximum verification rounds', 1, MAX_ROUNDS, DEFAULT_ROUNDS,
            key='verification_rounds',
            help='Each round is one model request. The verifier stops early when it reaches a final verdict.',
        )
        st.badge('4 rounds recommended', icon=':material/check_circle:', color='blue')
        st.caption('Allow up to 10 rounds for findings that need more source context. '
                   'Additional rounds can increase token usage and waiting time.')
        st.divider()
        options = list(dict.fromkeys(value.strip() for value in (
            default_model, *os.environ.get('OPENAI_MODELS', '').split(','),
        ) if value and value.strip()))
        selection = st.selectbox(
            'OpenAI model', [*options, ''], key='verification_model',
            format_func=lambda value: value or 'Enter a model ID…',
            help='Starts with OPENAI_MODEL. Choose a configured model or enter another ID.',
        )
        model = selection
        if not selection:
            model = st.text_input(
                'Model ID', key='custom_verification_model',
                placeholder='Enter an exact model ID',
                help='Use a model available to your API account that supports structured responses.',
            )
        model = model.strip()
        st.caption('Applies to your next verification. Switching models does not start a request.')
        configured = bool(model and os.environ.get('OPENAI_API_KEY'))
        st.badge('Verification ready' if configured else 'API configuration needed',
                 color='green' if configured else 'orange')
        st.caption('STATIC ANALYZER')
        try:
            st.text(f'Slither {version("slither-analyzer")}')
        except PackageNotFoundError:
            st.warning('Slither is not installed.')
        st.divider()
        st.caption('Single-file analysis · Local compiler. '
                   'Source context is sent to the model only when you click Verify.')
    return model, max_rounds


def render_empty_state() -> None:
    """Explain the three-step workflow before a source has been uploaded."""
    for column, title, description in zip(
        st.columns(3, gap='medium'),
        ('01 · Upload', '02 · Analyze', '03 · Verify'),
        ('Choose a self-contained Solidity file.',
         'Inspect warnings from your local Slither analyzer.',
         'Review one finding with selective source evidence.'),
    ):
        with column.container(border=True):
            st.markdown(f'**{title}**')
            st.caption(description)


def render_findings(session: AuditSession, model: str, max_rounds: int) -> None:
    """Show findings beside their selected detail and explicitly triggered verification."""
    analysis = session.analysis
    left, right = st.columns([1.15, 1], gap='large')
    with left:
        st.subheader('Findings')
        st.caption('Select a warning to inspect its source claim and verify it.')
        st.dataframe(
            [{'Detector': f.detector, 'Impact': f.impact, 'Confidence': f.confidence,
              'Contract': f.contract, 'Function': f.function_signature,
              'Lines': ', '.join(map(str, f.lines))} for f in analysis.findings],
            hide_index=True, width='stretch',
            alt='Slither findings with severity, contract, function, and source lines',
        )
        index = st.selectbox(
            'Finding to inspect', range(len(analysis.findings)), key='selected_finding',
            format_func=lambda i: f'{i + 1}. {analysis.findings[i].detector} · '
                                 f'{analysis.findings[i].function_signature or "no function"}',
        )
        finding = analysis.findings[index]
        with st.container(border=True):
            st.markdown(f'#### {finding.detector}')
            severity = {'High': 'red', 'Medium': 'orange', 'Low': 'yellow'}
            with st.container(horizontal=True):
                st.badge(f'{finding.impact} impact', color=severity.get(finding.impact, 'gray'))
                st.badge(f'{finding.confidence} confidence', color='blue')
            st.text(f'{finding.contract or "Source"} · {finding.function_signature or "No function target"}')
            st.caption(f"Source lines: {', '.join(map(str, finding.lines)) or 'Not provided'}")
            st.text(finding.description)
    with right:
        st.subheader('Finding verification')
        with st.container(border=True):
            st.caption(f'ROUND BUDGET · {max_rounds} maximum · stops on a final verdict')
            configured = bool(model and os.environ.get('OPENAI_API_KEY'))
            resolvable = bool(finding.contract and finding.function_signature)
            if not configured:
                st.info('Configure OPENAI_API_KEY in the server environment and select a model in the sidebar.')
            if not resolvable:
                st.warning('This finding has no function target. Automatic verification is unavailable.')
            st.caption('Checks this warning using relevant source fragments. Uses OpenAI API tokens.')
            if st.button('Verify selected finding', type='primary', icon=':material/fact_check:',
                         width='stretch', disabled=not (configured and resolvable)):
                with st.spinner('Reviewing the finding and retrieving relevant context…'):
                    session.verify(index, VerificationSettings(model, max_rounds))
            if index not in session.latest:
                st.caption('The verdict, supporting evidence, and token usage will appear here.')
        if index in session.latest:
            previous = session.latest[index]
            if previous.get('model') != model:
                st.info(f"Showing the saved result from {previous.get('model')}. Verify again to use {model or 'a selected model'}.")
            render_verification(previous)


def main() -> None:
    """Render the workspace; only explicit buttons start analysis or inference."""
    st.set_page_config(page_title='Smart Contract Vulnerability Verifier',
                       page_icon=':material/policy:', layout='wide')
    st.caption('CONTEXT AUDIT / SOLIDITY')
    st.title('Smart contract vulnerability verifier')
    st.markdown('Turn static-analysis warnings into **evidence-backed decisions**.')
    if 'audit_session' not in st.session_state:
        st.session_state.audit_session = AuditSession()
    session = st.session_state.audit_session
    model, max_rounds = render_sidebar(os.environ.get('OPENAI_MODEL', ''))
    st.divider()
    with st.container(border=True):
        st.subheader('Contract workspace', icon=':material/code:')
        uploaded = st.file_uploader(
            'Upload Solidity source', type=['sol'],
            help='One self-contained UTF-8 .sol file, up to 1 MiB. Imports are not supported.',
        )
    if uploaded is None:
        session.clear()
        render_empty_state()
        return
    try:
        session.set_upload(uploaded.name, uploaded.getvalue())
        upload = session.upload
        compilers = compatible_compilers(upload.source)
        if not compilers:
            st.warning('No compatible compiler is installed. Install a matching release with solc-select before analysis.')
            return
        controls, action = st.columns([3, 1], vertical_alignment='bottom')
        with controls:
            compiler = st.selectbox('Installed compatible compiler', compilers)
            st.caption('Pragma: ' + ('; '.join(upload.pragmas) or 'Not declared'))
        with action:
            if st.button('Run Slither', type='primary', icon=':material/play_arrow:', width='stretch'):
                with st.spinner('Compiling and running Slither…'):
                    session.analyze(compiler)
        with st.expander('View Solidity source', icon=':material/code:'):
            st.code(upload.source, language='solidity', line_numbers=True)
        if session.analysis is None:
            st.info('Ready to analyze. Run Slither to discover findings in this contract.')
            return
        analysis = session.analysis
        metrics = st.columns(3)
        metrics[0].metric('Static findings', len(analysis.findings), border=True)
        metrics[1].metric('High impact', sum(f.impact == 'High' for f in analysis.findings), border=True)
        metrics[2].metric('Findings reviewed', len(session.latest), border=True)
        st.caption(f'Analyzed with solc {analysis.compiler}')
        st.divider()
        if analysis.findings:
            render_findings(session, model, max_rounds)
        else:
            st.success('Slither reported no findings for this source.')
        st.divider()
        st.download_button(
            'Export analysis JSON', export_analysis(upload, analysis, session.history),
            file_name='contract-analysis.json', mime='application/json', icon=':material/download:',
            on_click='ignore',
        )
    except ApplicationError as error:
        st.error(str(error))
    except OSError:
        st.error('The temporary workspace could not be read or written. Upload the source again.')


if __name__ == '__main__':
    main()

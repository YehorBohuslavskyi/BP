"""Streamlit presentation for the single-file application service workflow."""
import os
from importlib.metadata import PackageNotFoundError, version

import streamlit as st

from context_audit.app.compilers import compatible_compilers
from context_audit.app.config import ApplicationError, DEFAULT_ROUNDS, MAX_ROUNDS, VerificationSettings
from context_audit.app.presentation import (
    compact_lines, finding_key, is_finding_verifiable, verification_ineligibility,
    requested_fragment_ids, source_fragments, marked_source_excerpt, target_function_lines, target_kind_label,
)
from context_audit.app.demos import DEMO_CONTRACTS, load_demo
from context_audit.app.batch import IMPACT_FILTERS, batch_plan, full_analysis, export_full_analysis
from context_audit.app.session import AuditSession, upgrade_session


def render_fragment(fragment: dict) -> None:
    """Show public catalog metadata and a bounded source preview."""
    st.markdown(f"**{fragment['kind'].replace('_', ' ').title()} · {fragment['name']}**")
    st.caption(fragment['id'])
    for reason in fragment['reasons']:
        st.text(f'Available because: {reason}')
    lines = fragment['source'].splitlines()
    st.code('\n'.join(lines[:10]), language='solidity')
    if len(lines) > 10:
        with st.expander(f"Full fragment · {fragment['name']}"):
            st.code(fragment['source'], language='solidity', line_numbers=True)
            st.caption('Line numbers are relative to this fragment.')


def render_verification(report: dict) -> None:
    """Separate verdict, source-only efficiency, and complete API request usage."""
    result, summary = report['result'], report['summary']
    assessment = result['assessment']
    verdict = assessment['verdict']
    styles = {
        'confirmed': ('red', ':material/report:', 'The static finding is supported by the supplied source.'),
        'false_positive': ('green', ':material/verified:', 'The static warning was rejected for this source.'),
        'inconclusive': ('orange', ':material/help:', 'The available evidence is insufficient for a reliable decision.'),
    }
    color, icon, description = styles[verdict]
    with st.container(border=True):
        st.caption('FINAL VERDICT')
        st.badge(verdict.replace('_', ' ').upper(), icon=icon, color=color)
        st.markdown(f"### {verdict.replace('_', ' ').upper()}")
        st.caption(description)
        st.write(assessment['explanation'])
        st.caption(f"Model: {report['model']} · Compiler: {report['compiler']}")

    fragments = {fragment['id']: fragment for fragment in source_fragments(report['initial_payload'], result)}
    metadata = {item['id']: item for item in report['initial_payload'].get('available_context', [])}
    with st.expander('Evidence and requested context'):
        st.markdown('#### Evidence fragments')
        if not assessment['evidence_ids']:
            st.caption('No source fragments were cited in the final assessment.')
        for identity in assessment['evidence_ids']:
            if identity in fragments:
                render_fragment(fragments[identity])
            else:
                st.caption(f'{identity} · source unavailable')
        st.markdown('#### Requested context')
        if not requested_fragment_ids(result):
            st.caption('No additional context was requested.')
        for round_info in result['rounds']:
            decision = round_info['result']['assessment']
            if not decision['requested_ids']:
                continue
            st.markdown(f"**Round {round_info['round']}**")
            st.caption('Structured request explanation')
            st.write(decision['explanation'])
            for identity in decision['requested_ids']:
                fragment = fragments.get(identity)
                if fragment:
                    render_fragment(fragment)
                    if not fragment['sent_to_model']:
                        st.caption('Requested, but not sent in a subsequent model call.')
                else:
                    st.caption(identity)
                    for reason in metadata.get(identity, {}).get('reasons', []):
                        st.text(f'Available because: {reason}')

    st.subheader('Context efficiency')
    metrics = report.get('context_efficiency', {})
    if 'source_context_reduction' in metrics:
        for labels, keys in (
            (('Full source', 'Initial selected code'),
             ('full_source_estimated_tokens', 'initial_selected_source_estimated_tokens')),
            (('Additional requested code', 'Cumulative selected code'),
             ('additional_selected_source_estimated_tokens', 'cumulative_selected_source_estimated_tokens')),
        ):
            for column, label, key in zip(st.columns(2), labels, keys):
                column.metric(f'{label} · est. tokens', f"{metrics[key]:,}", help='Estimated source tokens (characters / 4).')
        reduction = metrics['source_context_reduction']
        st.metric('Source-context reduction', f'{reduction:.1%}' if reduction is not None else 'N/A')
        st.caption('Estimated tokens for source fragments only. Each fragment is counted once after it is sent; '
                   'instructions, finding metadata, and JSON are excluded.')
        if reduction is None:
            st.caption('Reduction is undefined for empty source.')
        elif reduction <= 0:
            st.caption('No source-context reduction in this case. Small sources, rounding, or overlapping '
                       'fragments can make the selected-code estimate equal or exceed the full source.')
    else:
        st.info('This saved session result predates code-only metrics. New verifications use source-context accounting.')

    st.subheader('API usage')
    for column, label, key in zip(st.columns(3), ('Input tokens', 'Output tokens', 'Total tokens'),
                                   ('input_tokens', 'output_tokens', 'total_tokens')):
        column.metric(label, summary[key])
    columns = st.columns(2)
    columns[0].metric('Rounds', summary['rounds'])
    columns[1].metric('Requested fragments', len(requested_fragment_ids(result)))
    st.caption('Actual reported API usage. Input tokens cover complete requests, including instructions, '
               'metadata, and repeated context. They are not used to calculate source-context reduction.')


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
        finding_indices = {finding_key(finding): index for index, finding in enumerate(analysis.findings)}
        identity = st.selectbox(
            'Finding to inspect', list(finding_indices), key=f'selected_finding_{analysis.source_digest}',
            format_func=lambda key: f'{finding_indices[key] + 1}. '
                                   f'{analysis.findings[finding_indices[key]].detector} · '
                                   f'{analysis.findings[finding_indices[key]].function_signature or "no function"}',
        )
        index = finding_indices[identity]
        finding = analysis.findings[index]
        status = full_analysis(session)['findings'][index]['status']
        st.badge(status, color={'CONFIRMED': 'red', 'FALSE POSITIVE': 'green',
                               'INCONCLUSIVE': 'orange', 'ERROR': 'red'}.get(status, 'gray'))
        with st.container(border=True):
            st.markdown(f'#### {finding.detector}')
            severity = {'High': 'red', 'Medium': 'orange', 'Low': 'yellow'}
            with st.container(horizontal=True):
                st.badge(f'{finding.impact} impact', color=severity.get(finding.impact, 'gray'))
                st.badge(f'{finding.confidence} confidence', color='blue')
            st.caption('SLITHER CLAIM')
            st.text(f'Contract: {finding.contract or "Not provided"}')
            st.text(f'Target: {finding.function_signature or "Not provided"}')
            st.text(f'Kind: {target_kind_label(session.upload.source, finding)}')
            st.text(f'Lines: {compact_lines(finding.lines) or "Not provided"}')
            st.markdown('**Description**')
            st.text(finding.description)
            excerpt = marked_source_excerpt(session.upload.source, finding)
            if excerpt:
                with st.expander('Finding and target source', expanded=True):
                    st.caption('▶ Finding line · │ Target · Numbers are original source lines')
                    st.caption('Target lines: ' + (compact_lines(target_function_lines(session.upload.source, finding)) or 'Unknown'))
                    st.code(excerpt, language='text')
    with right:
        st.subheader('Finding verification')
        with st.container(border=True):
            st.caption(f'ROUND BUDGET · {max_rounds} maximum · stops on a final verdict')
            configured = bool(model and os.environ.get('OPENAI_API_KEY'))
            resolvable = is_finding_verifiable(finding, session.upload.source_path)
            if not configured:
                st.info('Configure OPENAI_API_KEY in the server environment and select a model in the sidebar.')
            if not resolvable:
                st.badge('Not eligible for LLM verification', color='gray')
                st.caption(verification_ineligibility(finding, session.upload.source_path))
            st.caption('Checks this warning using relevant source fragments. Uses OpenAI API tokens.')
            if st.button('Verify selected finding', type='secondary', icon=':material/fact_check:',
                         width='stretch', disabled=not (configured and resolvable)):
                with st.spinner('Reviewing the finding and retrieving relevant context…'):
                    session.verify(index, VerificationSettings(model, max_rounds))
            if identity in session.errors:
                st.warning('ERROR · ' + session.errors[identity])
            if identity not in session.latest:
                st.caption('The verdict, supporting evidence, and token usage will appear here.')
        if identity in session.latest:
            previous = session.latest[identity]
            if previous.get('model') != model:
                st.info(f"Showing the saved result from {previous.get('model')}. Verify again to use {model or 'a selected model'}.")
            render_verification(previous)


def render_batch_controls(session: AuditSession, model: str, max_rounds: int) -> None:
    """Run a batch only on an explicit click; keep partial results in session state."""
    st.subheader('2. LLM finding verification')
    st.caption('Our verifier checks eligible candidate warnings using selective source context.')
    impact_filter = st.segmented_control('Batch impact filter', IMPACT_FILTERS,
                                        default='High + Medium', selection_mode='single',
                                        key='batch_impact_filter') or 'High + Medium'
    if st.button('Clear verification results'):
        session.clear_verifications()
    plan = batch_plan(session.analysis.findings, session.upload.source_path, session.latest, impact_filter)
    pending = len(plan['pending'])
    st.caption(f"{len(plan['eligible'])} eligible findings · {len(plan['selected'])} match filter · "
               f"{pending} pending · {len(plan['selected']) - pending} completed results reused")
    st.caption(f'Estimated maximum API rounds for pending findings: {pending * max_rounds}. '
               'Batch verification uses OpenAI API tokens. Informational findings require All eligible.')
    if st.button('Verify all eligible findings', type='primary', width='stretch', icon=':material/playlist_add_check:',
                 disabled=not (pending and model and os.environ.get('OPENAI_API_KEY'))):
        bar = st.progress(0.0)
        current = st.empty()

        def progress(index, total, finding, completed):
            bar.progress((index if completed else index - 1) / total)
            current.text(f'Verifying findings: {index} / {total}\n'
                         f'Current: {finding.detector}\n'
                         f'{finding.contract}.{finding.function_signature}')

        session.verify_batch(VerificationSettings(model, max_rounds), impact_filter, progress)
        current.text('Batch finished. Completed results and errors are saved in this session.')


def render_batch_results(session: AuditSession) -> None:
    """Summarize latest outcomes and link result rows to the existing inspector."""
    exported = full_analysis(session)
    summary = exported['summary']
    left, right = st.columns(2)
    with left.container(border=True):
        st.subheader('SLITHER ONLY')
        st.metric('Candidate warnings', summary['static_findings'])
        st.caption('All require manual review')
    with right.container(border=True):
        st.subheader('SLITHER + OUR LLM VERIFIER')
        st.metric('False positives removed', summary['false_positive'])
        st.write(f"**{summary['confirmed']} confirmed** · **{summary['skipped']} skipped**")
        pending = summary['static_findings'] - summary['reviewed'] - summary['skipped'] - summary['errors']
        st.caption(f"{summary['inconclusive']} inconclusive · {summary['errors']} errors · {pending} not reviewed")
        st.caption('Removed means rejected by the LLM; live results have not been checked against ground truth. '
                   'Skipped, inconclusive, error, and unreviewed findings still need review.')
    st.subheader('Verification results')
    labels = {'static_findings': 'Slither findings', 'eligible_findings': 'Eligible findings',
              'reviewed': 'Findings reviewed', 'confirmed': 'Confirmed', 'false_positive': 'False positives',
              'inconclusive': 'Inconclusive', 'skipped': 'Skipped', 'errors': 'Errors'}
    for start in (0, 4):
        for column, (key, label) in zip(st.columns(4), list(labels.items())[start:start + 4]):
            column.metric(label, exported['summary'][key])
    usage = exported['usage']
    for column, key in zip(st.columns(4), ('api_calls', 'input_tokens', 'output_tokens', 'total_tokens')):
        column.metric(key.replace('_', ' ').capitalize(), usage[key])
    st.caption(f"Average rounds: {usage['average_rounds']:.2f} · "
               f"Requested fragments: {usage['requested_fragments']} · Failed attempts: {usage['failed_attempts']}")
    st.caption(exported['usage_note'])
    rows = []
    for entry in exported['findings']:
        finding = entry['finding']
        verification = entry.get('verification', {})
        rows.append({'Detector': finding['detector'], 'Function': finding['function'],
                     'Impact': finding['impact'], 'Slither result': 'Warning',
                     'LLM verdict': entry['status'], 'Rounds': verification.get('round_count'),
                     'Tokens': entry.get('usage', {}).get('total_tokens'),
                     'Status details': entry.get('reason', entry.get('error', ''))})
    table_key = f"batch_results_{session.analysis.source_digest}"

    def inspect_selected():
        selected = st.session_state[table_key]['selection']['rows']
        if selected:
            finding = session.analysis.findings[selected[0]]
            st.session_state[f'selected_finding_{session.analysis.source_digest}'] = finding_key(finding)

    st.dataframe(rows, hide_index=True, width='stretch', key=table_key,
                 on_select=inspect_selected, selection_mode='single-row',
                 column_config={'LLM verdict': st.column_config.TextColumn('LLM verdict', width='medium')},
                 alt='Verification results; select a row to inspect the full finding')


def main() -> None:
    """Default to read-only research evidence; analysis remains an explicit page."""
    st.set_page_config(page_title='Smart Contract Vulnerability Verifier',
                       page_icon=':material/policy:', layout='wide')
    st.title('Smart Contract Vulnerability Verifier')
    st.write('LLM-assisted verification of static-analysis findings')
    page = st.segmented_control('Workspace', ['Evaluation Dashboard', 'Analyze Contract'],
                                default='Evaluation Dashboard', key='workspace_page')
    if page != 'Analyze Contract':
        from context_audit.app.dashboard import render_dashboard
        render_dashboard()
        return
    render_analysis()


def render_analysis() -> None:
    """Render the interactive workspace without running work on navigation."""
    if 'audit_session' not in st.session_state:
        st.session_state.audit_session = AuditSession()
    session = upgrade_session(st.session_state.audit_session)
    st.session_state.audit_session = session
    model, max_rounds = render_sidebar(os.environ.get('OPENAI_MODEL', ''))
    st.divider()
    with st.expander('How our verifier changes the workflow', expanded=True):
        st.caption('Without our verifier')
        st.write('Contract → Slither → Candidate warnings → Manual review')
        st.caption('With our verifier')
        st.write('Contract → Slither → Candidate warnings → Selective context → LLM verification')
        st.write('→ Confirmed / False Positive / Inconclusive')
    with st.container(border=True):
        st.subheader('Contract workspace', icon=':material/code:')
        source_mode = st.segmented_control('Contract source', ['Upload', 'Demo'], default='Upload', key='source_mode')
        uploaded = None
        if source_mode == 'Demo':
            demo_id = st.selectbox('Load demo contract', list(DEMO_CONTRACTS),
                                   format_func=lambda key: DEMO_CONTRACTS[key].label)
            if st.button('Load selected demo'):
                try:
                    name, content = load_demo(demo_id)
                    session.set_upload(name, content)
                except ApplicationError as error:
                    st.error(str(error))
        else:
            uploaded = st.file_uploader(
                'Upload Solidity source', type=['sol'], key='contract_upload',
                help='One self-contained UTF-8 .sol file, up to 1 MiB. Imports are not supported.',
            )
    if uploaded is None and session.upload is None:
        render_empty_state()
        return
    if uploaded is None:
        st.caption('Using the contract retained in this session. Upload another file to replace it.')
        if st.button('Remove retained contract'):
            session.clear()
            st.rerun()
    try:
        if uploaded is not None:
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
        st.subheader('1. Slither static analysis')
        st.caption('These are candidate vulnerabilities reported by the static analyzer. They may include false positives.')
        columns = st.columns(5)
        columns[0].metric('Total static findings', len(analysis.findings), border=True)
        for column, impact in zip(columns[1:], ('High', 'Medium', 'Low', 'Informational')):
            column.metric(impact, sum(f.impact == impact for f in analysis.findings), border=True)
        st.dataframe([{'Detector': f.detector, 'Impact': f.impact, 'Confidence': f.confidence,
                       'Function': f.function_signature, 'Lines': compact_lines(f.lines),
                       'Description': f.description} for f in analysis.findings],
                     hide_index=True, width='stretch',
                     column_config={'Lines': st.column_config.TextColumn('Lines', width='medium'),
                                    'Description': st.column_config.TextColumn('Description', width='large')},
                     alt='Slither candidate warnings before LLM verification')
        st.caption(f'Analyzed with solc {analysis.compiler}')
        st.divider()
        if analysis.findings:
            render_batch_controls(session, model, max_rounds)
            results_slot = st.container()
            with st.expander('Inspect a finding · source, evidence, and optional single verification'):
                render_findings(session, model, max_rounds)
            with results_slot:
                render_batch_results(session)
        else:
            st.success('Slither reported no findings for this source.')
        st.divider()
        st.download_button(
            'Export full analysis', export_full_analysis(session),
            file_name='contract-analysis.json', mime='application/json', icon=':material/download:',
            on_click='ignore',
        )
    except ApplicationError as error:
        st.error(str(error))
    except OSError:
        st.error('The temporary workspace could not be read or written. Upload the source again.')


if __name__ == '__main__':
    main()

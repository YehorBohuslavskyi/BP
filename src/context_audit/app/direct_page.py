"""Direct detection demo; all inference is gated by the Run button."""
import json
import os
from pathlib import Path
from uuid import uuid4
import streamlit as st
from context_audit.direct import prepare, run_function, aggregate
from context_audit.datasets.dappscan import DAppSCAN
from context_audit.direct_evaluation import evaluate


def index_paste(name, source, directory):
    if not source.strip():
        raise ValueError('Paste Solidity source first')
    path = directory / Path(name or 'source.sol').name
    if path.suffix != '.sol':
        raise ValueError('Source name must end with .sol')
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    return prepare(path)


def result_rows(results):
    rows = []
    for r in results:
        for finding in r['assessment']['findings'] or [{}]:
            rows.append({'Function': r['target']['signature'], 'Verdict': r['assessment']['verdict'],
                         'Vulnerability': finding.get('vulnerability_type', '—'), 'SWC': finding.get('swc_id'),
                         'Severity': finding.get('severity'), 'Rounds': r['round_count'],
                         'Requested fragments': r['requested_fragments']})
    return rows


def render_results(results):
    for report in aggregate(results):
        st.subheader(f"{report['contract']} — {report['source']}")
        st.write({'functions_analyzed': report['functions_analyzed'], **report['summary'], 'API calls': report['usage']['total_api_calls'], 'Total tokens': report['usage']['total_tokens']})
        st.dataframe(result_rows(report['function_results']), hide_index=True)
        st.markdown('### Vulnerabilities found')
        for r in report['function_results']:
            verdict = r['assessment']['verdict']
            if verdict == 'no_vulnerability_found':
                continue
            with st.expander(f"{r['target']['signature']} — {verdict}"):
                st.write(r['assessment']['explanation'])
                snippets = {r['target']['id']: r['target'], **{f['id']: f for f in r['provided_context']}}
                for finding in r['assessment']['findings']:
                    st.write(finding)
                    for fid in finding['evidence_ids']:
                        st.caption(fid)
                        st.code(snippets[fid]['source'], language='solidity')
                st.caption('Initial context')
                st.json(r['initial_context'])
                for round_info in r['rounds']:
                    assessment = round_info['result']['assessment']
                    st.write(f"Round {round_info['round']} → {assessment['action']}")
                    if assessment['action'] == 'request_context':
                        st.write(assessment.get('requested_ids', []))
                        st.write(assessment.get('reason', ''))
                st.write({'rounds': r['round_count'], 'requested_fragments': r['requested_fragments'], 'usage': r['usage']})
        st.markdown('### Functions with no vulnerability found')
        st.write(report['no_vulnerability_found_functions'])
        st.markdown('### Inconclusive functions')
        st.write(report['inconclusive_functions'])
        st.markdown('### Analysis statistics')
        st.json(report['usage'])


def render_direct():
    st.header('Direct LLM Detection')
    st.info('This mode does not use Slither findings.')
    st.caption('The shared indexer uses Slither parsing and source mappings; no detectors or findings are used.')
    mode = st.radio('Input source', ['Paste Solidity source', 'DAppSCAN dataset'])
    workspace = Path('examples/direct_detection/sessions') / st.session_state.setdefault('direct_session_id', uuid4().hex)
    dataset = None
    files = []
    if mode == 'Paste Solidity source':
        name = st.text_input('Source name', 'source.sol')
        source = st.text_area('Solidity source', height=350)
        fingerprint = (mode, name, source)
        clicked = st.button('Index contract')
    else:
        root = st.text_input('Dataset root', os.environ.get('DAPPSCAN_ROOT', ''))
        try:
            dataset = DAppSCAN(root)
            project = st.selectbox('Project / DApp', dataset.projects())
            files = st.multiselect('Solidity files', dataset.files(project))
        except (ValueError, OSError) as exc:
            st.info(str(exc))
        fingerprint = (mode, root, tuple(files))
        clicked = st.button('Index selected', disabled=not files)
    if clicked:
        st.session_state.pop('direct_results', None)
        jobs = []
        try:
            if dataset:
                for file in files:
                    payloads, catalog = prepare(dataset.source_path(file))
                    jobs.extend((file, p, catalog) for p in payloads)
            else:
                payloads, catalog = index_paste(name, source, workspace / 'source')
                jobs = [(None, p, catalog) for p in payloads]
            st.session_state.direct_index = (fingerprint, jobs)
        except Exception as exc:
            st.session_state.pop('direct_index', None)
            st.error(f'Indexing failed: {exc}')
    indexed = st.session_state.get('direct_index')
    if not indexed or indexed[0] != fingerprint:
        st.caption('Index the current input to choose functions.')
        return
    jobs = indexed[1]
    contracts = sorted({p['target']['contract'] for _, p, _ in jobs})
    selected_contracts = st.multiselect('Contracts', contracts, default=contracts)
    candidates = [j for j in jobs if j[1]['target']['contract'] in selected_contracts]
    st.write({'contracts': contracts, 'functions': len(jobs),
              'fragments': len({f for _,_,c in jobs for f in c.fragments}),
              'full_source_tokens_estimate': sum({file or 'manual': p.get('full_source_estimated_tokens', 0) for file,p,_ in jobs}.values())})
    all_functions = st.checkbox('Analyze all functions', value=False)
    choices = st.multiselect('Functions', range(len(candidates)),
                            format_func=lambda i: f"{candidates[i][0] or 'manual'} · {candidates[i][1]['target']['contract']}.{candidates[i][1]['target']['signature']}",
                            disabled=all_functions)
    selected = candidates if all_functions else [candidates[i] for i in choices]
    st.write(f'{len(selected_contracts)} contracts selected; {len(selected)} functions / LLM sessions')
    if len(selected) > 20:
        st.warning('Many functions selected. This can incur substantial API usage.')
    rounds = st.number_input('Maximum rounds', min_value=1, max_value=12, value=4)
    st.caption(f"OPENAI_MODEL: {os.environ.get('OPENAI_MODEL', '(not configured)')}")
    if st.button('Run direct detection', disabled=not selected):
        run_dir = workspace / uuid4().hex
        results = []
        progress = st.progress(0.0)
        for i, (file, payload, catalog) in enumerate(selected):
            with st.spinner(f"Analyzing {payload['target']['signature']}"):
                result = run_function(payload, catalog, run_dir / f'function-{i}.json', int(rounds))
                result['dataset_file'] = file
                (run_dir / f'function-{i}.json').write_text(json.dumps(result, indent=2))
                results.append(result)
            progress.progress((i+1)/len(selected))
        (run_dir / 'contract_reports.json').write_text(json.dumps(aggregate(results), indent=2))
        st.session_state.direct_results = results
        st.caption(f'Saved to {run_dir}')
    results = st.session_state.get('direct_results', [])
    if results:
        render_results(results)
        if dataset:
            with st.expander('Ground truth — evaluation only', expanded=False):
                st.caption('Hidden from LLM')
                cases = [{'file': file, 'labels': dataset.labels(file)} for file in files]
                st.json(evaluate(cases, results))
                st.caption('Source-only labels do not establish a reliable function/location match.')

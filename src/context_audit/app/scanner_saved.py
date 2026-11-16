"""Read-only demonstration of genuine saved model assessments; never inference."""
import hashlib
import json
from pathlib import Path

import streamlit as st

from context_audit.verdict_consistency import check

ROOT = Path(__file__).resolve().parents[3]
SAVED_REPORT = 'runs/mode-b-v2-protocol-hardened-retry-2026-11-09-01/analysis/report.json'
WALLET_REPORT = 'runs/mode-b-v2-unseen-evidence-continuation-2026-11-09/report.json'
EXPECTED_SHA256 = 'c9a4d68ebdcb036a162191a7ce10043c9d2e0d2d605937a94d9fde574b4f9240'
WALLET_SHA256 = '107aa556d5490d5fd29f5b8e653395e2d057b4a3df4c4e7a67e9eac0c070771c'
EXAMPLES = {
    'Confirmed hypothesis': 'changeOwner(address)',
    'Rejected hypothesis': '_transferOwnership(address)',
    'Insufficient evidence': 'setAuthoriser(address)',
}


def load_saved_example(label, root=ROOT):
    report_path, expected_hash = ((SAVED_REPORT, EXPECTED_SHA256) if label == 'Confirmed hypothesis'
                                  else (WALLET_REPORT, WALLET_SHA256))
    data = (root / report_path).read_bytes()
    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError('Saved report checksum differs from the preserved demonstration.')
    report = json.loads(data)
    r = next(i['result'] for i in report['issues'] if i['result']['candidate']['primary_function'] == EXAMPLES[label])
    last = r['rounds'][-1]
    request = json.loads(last['messages'][1]['content'])
    supplied = {f['id']: f for f in [request['target'], *request['provided_context']]}
    a = last['response']['assessment']
    if r['status'] != 'completed' or a['verdict'] != r['verdict'] or set(a['evidence_ids']) - supplied.keys():
        raise ValueError('Saved assessment or supplied evidence is inconsistent.')
    validation = check(a, {fid: f['source'] for fid, f in supplied.items()}, historical=True)
    if not validation['passed']:
        raise ValueError('Saved example no longer passes the limited historical consistency review.')
    return {'kind': 'saved_model_assessment', 'new_scan': False, 'source_report': report_path,
        'report_sha256': actual_hash, 'model': last['response'].get('model'),
        'function': r['candidate']['primary_function'], 'original_verdict': a['verdict'],
        'explanation': a['explanation'], 'execution_flow': a['execution_flow'],
        'incomplete_evidence': a['incomplete_evidence'],
        'evidence': [supplied[fid] for fid in a['evidence_ids']],
        'target': request['target'], 'recorded_usage': r['usage'], 'round_count': r['round_count'],
        'retrieved_fragments': r['retrieved_fragments'], 'consistency_review': validation,
        'rounds': [{'round': row['round'], 'action': row['response']['assessment']['action'],
            'requested_ids': row['response']['assessment']['requested_ids']} for row in r['rounds']]}


def render_saved():
    st.title('Saved LLM evidence')
    st.info('Recorded development run from 9 November 2026. This page makes no API calls and does not scan your current contract.')
    st.caption('These are original model assessments, not ground truth or exploit proofs. Legacy responses receive limited historical consistency checks.')
    label = st.selectbox('Saved assessment', list(EXAMPLES), key='scanner_saved_example')
    try:
        e = load_saved_example(label)
    except (OSError, ValueError, KeyError, StopIteration):
        st.error('The preserved demonstration report is unavailable or failed its integrity check.')
        return
    st.subheader(e['function'])
    st.write('Original model assessment: **' + e['original_verdict'].upper() + '**')
    st.write(e['explanation'])
    st.caption(f"Recorded model: {e['model']} · Rounds: {e['round_count']} · Additional retrieved fragments: {e['retrieved_fragments']}")
    st.caption(f"Recorded verification usage: {e['recorded_usage']['api_calls']} requests · {e['recorded_usage']['total_tokens']:,} tokens. No new usage on this page; discovery usage is excluded here.")
    for fragment in e['evidence']:
        st.caption(fragment['name'] + ' · original supplied evidence')
        st.code(fragment['source'], language='solidity')
    if not e['evidence']:
        st.caption('No evidence IDs were cited in this abstention.')
        st.code(e['target']['source'], language='solidity')
    if e['incomplete_evidence']:
        st.write('Missing evidence: ' + '; '.join(e['incomplete_evidence']))
    with st.expander('Execution flow and audit trail'):
        for step in e['execution_flow']:
            st.write('• ' + step)
        st.write('Source report: ' + e['source_report'])
        st.code(e['report_sha256'], language=None)
        st.caption('SHA-256 verified against the preserved report. Historical consistency coverage is limited; this is not a new live-protocol acceptance.')
    st.download_button('Download saved evidence', json.dumps(e, indent=2), file_name='saved-llm-evidence.json',
        mime='application/json', on_click='ignore')

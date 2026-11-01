"""Presentation of saved research results; this module never invokes inference."""
import streamlit as st
from context_audit.app.research import load_research, pilot_metrics, finding_rows, evidence_fragments, slither_claim


def case_details(item: dict) -> None:
    """Display public structured explanations and saved source evidence only."""
    finding = item['result']['finding']
    st.write(f"**{finding['detector']}** · {finding['contract']}.{finding['function']}")
    st.caption('Slither claim: ' + (slither_claim(item) or finding.get('description',
               f"{finding['detector']} candidate in {finding['function']} (full claim not saved in pilot result).")))
    st.badge(item['verdict'].replace('_', ' ').upper())
    st.write(item['explanation'])
    for fragment in evidence_fragments(item):
        st.caption(fragment.get('name', 'Evidence fragment'))
        if fragment.get('source'):
            st.code(fragment['source'], language='solidity')
        else:
            st.caption(f"{fragment['id']} · source fragment not available in saved evidence")


def render_dashboard() -> None:
    """Keep headline pilot results separate from cohort and detection baselines."""
    data = load_research()
    st.caption('Solidity → Slither → Static Finding → Selective Context → LLM Verification')
    st.caption('Final decision: Confirmed / False Positive / Inconclusive')
    st.header('10-finding balanced pilot')
    st.write('Slither produces candidate findings. The verifier checks those claims using selective source context to identify false positives.')
    st.info('Balanced cohort: 5 true findings + 5 false findings. These pilot metrics do not describe Slither precision across CGT.')
    summary = data['pilot']
    if summary:
        metrics = pilot_metrics(summary)
        before, after = metrics['before'], metrics['after']
        left, right = st.columns(2)
        with left.container(border=True):
            st.subheader('False Positive Reduction')
            st.metric('False positives removed', f"{metrics['fp_reduction']:.0%}")
            st.write(f"**{after['TN']} of {before['FP']} false positives removed**")
            st.caption(f"Before: {before['FP']} false positives → After LLM: {after['FP']}")
        with right.container(border=True):
            st.subheader('True Vulnerabilities Retained')
            st.metric('True findings retained', f"{metrics['tp_retention']:.0%}")
            st.write(f"**{after['TP']} / {before['TP']} retained**")
            st.caption(f"True findings incorrectly filtered: {after['FN']} · FN introduced by LLM: {after['FN']}")
        for col, title, values in zip(st.columns(2), ('SLITHER ONLY', 'SLITHER + LLM'), (before, after)):
            with col.container(border=True):
                st.subheader(title)
                st.caption('Balanced 10-finding pilot')
                st.write(' · '.join(f'{key}: {values[key]}' for key in ('TP', 'FP', 'TN', 'FN')))
                st.write(f"Precision **{values['precision']:.2%}** · Recall **{values['recall']:.0%}** · F1 **{values['f1']:.2%}**")
        left, right = st.columns(2)
        with left:
            st.subheader('False positives remaining')
            st.bar_chart({'Method': ['Slither', 'Slither + LLM'], 'False positives': [before['FP'], after['FP']]},
                         x='Method', y='False positives', color='#d97706', alt='False positives fall from five to two')
        with right:
            st.subheader('Precision and F1 (%)')
            st.bar_chart({'Method': ['Slither', 'Slither + LLM'],
                          'Precision': [100 * before['precision'], 100 * after['precision']],
                          'F1': [100 * before['f1'], 100 * after['f1']]}, x='Method', stack=False,
                         alt='Pilot precision and F1 before and after verification')
        st.caption(f"Inconclusive: {after['verdict_counts']['inconclusive']} · Runtime errors: {after['verdict_counts']['error']}")
    else:
        st.warning('Research result artifact not available')

    findings = data['findings']
    if findings:
        with st.expander('Pilot findings · all saved results'):
            st.dataframe(finding_rows(findings), hide_index=True, width='stretch', alt='Ten pilot findings and evaluation outcomes')
        st.subheader('Filtered false positives')
        negatives = [f for f in findings if not f['label']]
        filtered = sum(f['verdict'] == 'false_positive' for f in negatives)
        retained = sum(f['verdict'] == 'confirmed' for f in negatives)
        st.write(f'{filtered} correctly filtered · {retained} still confirmed by the LLM')
        for item in negatives:
            with st.expander(f"{item['result']['finding']['contract']} · {item['verdict'].replace('_', ' ').upper()}"):
                case_details(item)
        example = next((f for f in findings if f['label'] and f['verdict'] == 'confirmed'), None)
        if example:
            st.subheader('Example verification')
            st.caption('Example finding · saved pilot result, not an experiment-wide context average')
            with st.expander('Inspect a confirmed finding and selective context', expanded=True):
                case_details(example)
                context = example.get('context_efficiency', {})
                if 'initial_source_reduction' in context:
                    for col, label, value in zip(st.columns(3),
                        ('Full Solidity source · est. tokens', 'Initial selected source · est. tokens', 'Initial source-context reduction'),
                        (context['full_source_tokens'], context['initial_source_tokens'], f"{context['initial_source_reduction']:.1%}")):
                        col.metric(label, value)
                    st.caption('Source-only estimates for this example; additional requested fragments are shown above. API tokens include instructions and metadata.')
    else:
        st.warning('Research result artifact not available')

    st.subheader('Selective context, on demand')
    with st.container(border=True):
        st.caption('Whole-contract approach: Whole Contract → LLM')
        st.write('**Target Function + Modifiers + State Variables + Relevant Writers → LLM**')
        st.write('The LLM receives only source fragments relevant to the static finding and can request additional fragments when necessary.')
        if summary:
            for col, label, value in zip(st.columns(4), ('Average rounds', 'Requested fragments', 'API calls', 'Total tokens'),
                    (summary['average_rounds'], summary['requested_fragments'], summary['api_calls_attempted'], f"{summary['actual_usage']['total_tokens']:,}")):
                col.metric(label, value)
            st.caption(f"{summary['sample_completed']} findings · Input tokens: {summary['actual_usage']['input_tokens']:,} · Output tokens: {summary['actual_usage']['output_tokens']:,}")
    with st.expander('Dataset context · full reviewed CGT-linked cohort', expanded=True):
        cohort = data['cohort']
        if cohort:
            baseline = cohort['baseline']
            st.write(f"CGT local dataset: **{cohort['assessment_rows']:,} property records**")
            st.write(f"Defensibly linked/reproduced Slither cohort: **{cohort['reviewed_eligible_findings']} findings** · {baseline['TP']} true · {baseline['FP']} false")
            st.write(f"Baseline precision on this selected reviewed cohort: **{baseline['precision']:.2%}**")
            st.caption('The 10-finding balanced pilot was selected from this reviewed cohort for the first LLM experiment.')
        else:
            st.warning('Research result artifact not available')
    with st.expander('Secondary experiment · SmartBugs access_control baseline'):
        if data['smartbugs']:
            sb = data['smartbugs']['summary']
            st.write(f"{sb['selected_contracts']} contracts · {sb['ground_truth_total']} known vulnerabilities · {sb['detected']} detected · {sb['missed']} missed")
            st.metric('Detection recall', f"{sb['recall']:.2%}")
            st.write('This experiment measures vulnerability detection recall. The CGT experiment measures false-positive filtering.')
        else:
            st.warning('Research result artifact not available')
    if summary:
        st.subheader('Research conclusions')
        st.markdown(f"- False positives reduced by {metrics['fp_reduction']:.0%}.\n"
                    f"- {after['TP']} of {before['TP']} true findings retained.\n"
                    f"- Precision improved from {before['precision']:.1%} to {after['precision']:.2%}.\n"
                    f"- F1 improved from {before['f1']:.1%} to {after['f1']:.1%}.\n"
                    f"- Inconclusive verdicts: {after['verdict_counts']['inconclusive']}.\n"
                    f"- Average verification rounds: {summary['average_rounds']}.")
    st.caption('These results are from the balanced 10-finding pilot and are not yet the final full-cohort evaluation. Recall here measures retention of known true candidates, not detection of all vulnerabilities in CGT.')

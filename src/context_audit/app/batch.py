"""Batch planning and public reporting without inference or Streamlit dependencies."""
from dataclasses import asdict
import json

from context_audit.app.presentation import (
    finding_key, verification_ineligibility, verification_export, requested_fragment_ids,
)

IMPACT_FILTERS = ('High only', 'High + Medium', 'All eligible')


def batch_plan(findings, source_path, completed, impact_filter='High + Medium') -> dict:
    """Partition findings by source eligibility, severity, and cached completion."""
    if impact_filter not in IMPACT_FILTERS:
        raise ValueError('Unsupported impact filter')
    eligible, selected, pending, skipped = [], [], [], {}
    seen = set()
    for index, finding in enumerate(findings):
        identity = finding_key(finding)
        if identity in seen:
            continue
        seen.add(identity)
        reason = verification_ineligibility(finding, source_path)
        if reason:
            skipped[identity] = reason
            continue
        eligible.append(index)
        allowed = (impact_filter == 'All eligible' or finding.impact == 'High'
                   or (impact_filter == 'High + Medium' and finding.impact == 'Medium'))
        if not allowed:
            skipped[identity] = f'Excluded by impact filter: {impact_filter}'
            continue
        selected.append(index)
        if identity not in completed:
            pending.append(index)
    return dict(eligible=eligible, selected=selected, pending=pending, skipped=skipped)


def full_analysis(session) -> dict:
    """Export latest outcomes and cumulative reported usage, including explicit reruns.

    Failed worker calls may consume tokens before failing without returning usage.
    Such costs cannot be reconstructed and are explicitly marked as unknown.
    """
    analysis, upload = session.analysis, session.upload
    findings = []
    summary = dict(static_findings=len(analysis.findings), eligible_findings=0, reviewed=0,
                   confirmed=0, false_positive=0, inconclusive=0, skipped=0, errors=0)
    for finding in analysis.findings:
        identity = finding_key(finding)
        reason = verification_ineligibility(finding, upload.source_path)
        summary['eligible_findings'] += reason is None
        if identity in session.latest:
            entry = verification_export(session.latest[identity])
            verdict = entry['verification']['verdict']
            summary['reviewed'] += 1
            summary[verdict] += 1
            entry['status'] = verdict.replace('_', ' ').upper()
        else:
            fields = asdict(finding)
            fields['function'] = fields.pop('function_signature')
            entry = {'finding': fields}
            if identity in session.errors:
                entry.update(status='ERROR', error=session.errors[identity])
                summary['errors'] += 1
            elif reason or identity in session.skipped:
                entry.update(status='SKIPPED', reason=reason or session.skipped[identity])
                summary['skipped'] += 1
            else:
                entry['status'] = 'NOT REVIEWED'
        findings.append(entry)
    usage = {key: sum(report['summary'].get(key, 0) or 0 for report in session.history)
             for key in ('input_tokens', 'output_tokens', 'total_tokens')}
    rounds = sum(report['summary'].get('rounds', 0) for report in session.history)
    usage.update(api_calls=rounds, average_rounds=rounds / len(session.history) if session.history else 0,
                 requested_fragments=sum(len(requested_fragment_ids(r['result'])) for r in session.history),
                 failed_attempts=session.failed_attempts, complete=session.failed_attempts == 0)
    return dict(schema_version=3, source=upload.source, source_sha256=upload.digest,
                compiler=analysis.compiler, summary=summary, usage=usage, findings=findings,
                usage_note='Cumulative reported usage, including explicit single-finding reruns. '
                           'API calls count completed reported rounds. Failed attempts may have '
                           'additional unreported calls and tokens.')


def export_full_analysis(session) -> str:
    """Serialize only public result fields; never serialize session configuration."""
    return json.dumps(full_analysis(session), indent=2)

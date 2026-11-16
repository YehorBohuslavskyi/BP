"""Explicit current-protocol mock fixtures, never applied to historical artifacts."""
import copy


def with_basis(assessment, fragments):
    a = copy.deepcopy(assessment)
    verdict = a['verdict']
    if a['action'] == 'request_context':
        a['verdict_basis'] = None
        return a
    a['verdict_basis'] = dict(
        mechanism_status={'confirmed': 'supported', 'rejected': 'contradicted', 'inconclusive': 'unknown'}[verdict],
        core_conditions={'confirmed': 'established', 'rejected': 'not_established', 'inconclusive': 'unknown'}[verdict],
        mitigation_status={'confirmed': 'none_identified', 'rejected': 'effective', 'inconclusive': 'unknown'}[verdict],
        mechanism=a['explanation'], mitigation_reason=a['explanation'] if verdict == 'rejected' else '',
        unresolved_conditions=a['incomplete_evidence'] if verdict == 'inconclusive' else [],
        evidence_claims=[dict(fragment_id=f['id'], source_quote=f['source'],
            role={'confirmed':'dangerous_behavior','rejected':'protection','inconclusive':'uncertainty'}[verdict])
            for f in fragments if f['id'] in a['evidence_ids']])
    return a

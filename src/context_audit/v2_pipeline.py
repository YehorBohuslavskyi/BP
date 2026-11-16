"""Manifest-checked orchestration, conservative deduplication and Mode B v2 reports."""
import json
from pathlib import Path

from context_audit import direct_verification as verification
from context_audit.v2_artifacts import atomic_json, digest, validate_discovery


def groups_for(candidates):
    groups = {}
    ids = set()
    for raw in candidates:
        cid = raw.get('candidate_id')
        if not isinstance(cid, str) or not cid or cid in ids:
            raise ValueError('Candidate IDs must be nonempty and unique across the artifact')
        ids.add(cid)
        # Merge only identical claims with identical primary target and context sets.
        # Different explanations/uncertainties may identify different defects.
        normalized = {k: v for k, v in raw.items() if k not in ('candidate_id', 'model_candidate_id')}
        for key in ('related_fragment_ids', 'requested_context_ids'):
            if isinstance(normalized.get(key), list):
                normalized[key] = sorted(set(normalized[key]))
        key = digest(normalized)
        group = groups.setdefault(key, {'issue_id': 'issue-' + key[:20], 'key': key,
                                        'candidate': raw, 'original_candidate_ids': []})
        group['original_candidate_ids'].append(cid)
    return list(groups.values())


def unfinished(group, code):
    return {'candidate_id': group['candidate']['candidate_id'], 'candidate': group['candidate'],
            'status': 'skipped_limit' if code == 'CANDIDATE_BUDGET' else 'pending',
            'verdict': None, 'severity': None, 'explanation': '', 'evidence_ids': [],
            'source_locations': {}, 'execution_flow': [], 'incomplete_evidence': [code],
            'errors': [{'code': code}], 'rounds': [], 'requests': [], 'provided_context': [],
            'usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'api_calls': 0},
            'round_count': 0, 'retrieved_fragments': 0, 'selected_source_estimated_tokens': 0,
            'full_source_estimated_tokens': 0}


def aggregate(discovery, contracts, catalog, groups, sessions, reused):
    issues = []
    for group in groups:
        session = sessions.get(group['key'], unfinished(group, 'NOT_STARTED'))
        issues.append({'issue_id': group['issue_id'], 'original_candidate_ids': group['original_candidate_ids'],
                       'result': session, 'reused': group['key'] in reused,
                       'session_artifact': 'sessions/' + group['key'] + '.json' if group['key'] in sessions and not any(e['code'] == 'CANDIDATE_BUDGET' for e in session['errors']) else None})
    verification_usage = {k: sum(i['result']['usage'].get(k, 0) for i in issues)
                          for k in ('input_tokens', 'output_tokens', 'total_tokens', 'api_calls')}
    new_usage = {k: sum(i['result']['usage'].get(k, 0) for i in issues if not i['reused']) for k in verification_usage}
    discovery_usage = {k: discovery['usage'].get(k, 0) for k in verification_usage}
    counts = {**discovery['coverage_counts'], 'candidates_generated': len(discovery['candidates']),
              'unique_candidates': len(groups), 'candidates_verified': sum(i['result']['status'] == 'completed' for i in issues),
              **{v + '_candidates': sum(i['result']['verdict'] == v for i in issues) for v in ('confirmed', 'rejected', 'inconclusive')},
              'processing_failures': sum(i['result']['status'] in ('processing_failed', 'interrupted') for i in issues),
              'semantic_consistency_failures': sum(any(e['code'] == 'SEMANTIC_CONSISTENCY_FAILED' for e in i['result']['errors']) for i in issues),
              'skipped_candidates': sum(i['result']['status'] in ('skipped_limit', 'budget_exhausted') for i in issues),
              'pending_candidates': sum(i['result']['status'] in ('pending', 'running') for i in issues)}
    reports = []
    for contract in contracts:
        own = [i for i in issues if i['result']['candidate'].get('contract') == contract['contract']]
        reports.append({'contract': contract['contract'], 'source_file': contract['file'],
                        'compiler': catalog.preparation_metadata.get('compiler_used'),
                        'preparation_modes': sorted({f['preparation_mode'] for f in contract['functions']}),
                        'coverage': [r for r in discovery['coverage'] if r['contract'] == contract['contract']],
                        'verified_findings': [i for i in own if i['result']['verdict'] == 'confirmed'],
                        'other_candidates': [i for i in own if i['result']['verdict'] != 'confirmed']})
    overlaps = []
    for index, left in enumerate(groups):
        a = left['candidate']
        for right in groups[index + 1:]:
            b = right['candidate']
            if a.get('contract') == b.get('contract') and a.get('suspected_type') == b.get('suspected_type'):
                shared = {a.get('primary_fragment_id'), *a.get('related_fragment_ids', [])} & {b.get('primary_fragment_id'), *b.get('related_fragment_ids', [])}
                if shared:
                    overlaps.append({'issue_ids': [left['issue_id'], right['issue_id']], 'shared_fragment_ids': sorted(shared),
                                     'merged': False, 'reason': 'Possible overlap only; claims and verdicts retained independently'})
    selected = sum(i['result']['selected_source_estimated_tokens'] for i in issues if i['result']['round_count'])
    baseline = sum(i['result']['full_source_estimated_tokens'] for i in issues if i['result']['round_count'])
    return {'mode': 'direct_detection_v2', 'discovery_artifact_sha256': discovery['manifest']['artifact_sha256'] if 'manifest' in discovery else digest(discovery),
            'discovery_recovery': discovery.get('recovery_import'),
            'coverage_counts': counts, 'contracts': reports, 'issues': issues, 'possible_overlaps': overlaps,
            'discovery_errors': discovery['errors'],
            'efficiency': {'discovery': discovery_usage, 'verification': verification_usage,
                'total': {k: discovery_usage[k] + verification_usage[k] for k in verification_usage},
                'verification_this_invocation': new_usage,
                'unknown_usage_calls': sum(i['result'].get('unknown_usage_calls', 0) for i in issues) +
                    sum(not all(k in (r.get('response', {}).get('usage') or {}) for k in ('input_tokens', 'output_tokens', 'total_tokens')) for r in discovery['rounds']),
                'rounds': sum(i['result']['round_count'] for i in issues),
                'retrieved_fragments': sum(i['result']['retrieved_fragments'] for i in issues),
                'selected_source_estimated_tokens': selected, 'full_source_baseline_tokens': baseline,
                'verification_context_reduction': 1 - selected / baseline if baseline else None},
            'limitations': ['LLM confirmation is not a dynamically validated exploit.',
                'Unselected functions and rejected candidates do not establish security.',
                'Context reduction measures source selection, not accuracy; discovery prompts are excluded.',
                'Usage totals include reused artifacts once; current invocation usage is separate.']}


def markdown(report):
    lines = ['# Mode B v2 — discovery and selective verification', '',
             'LLM assessments only; confirmation is not dynamic exploit validation. Unselected functions are not safe.', '',
             '## Coverage', '', '```json', json.dumps(report['coverage_counts'], indent=2), '```', '']
    for contract in report['contracts']:
        lines += [f'## {contract["contract"]} ({contract["source_file"]})', '',
                  f'Compiler: {contract["compiler"]}; preparation: {", ".join(contract["preparation_modes"])}.', '']
        for issue in contract['verified_findings'] + contract['other_candidates']:
            r = issue['result']; c = r['candidate']
            lines += [f'- **{r["verdict"] or r["status"]}** {c.get("primary_function", "unknown")} — {c.get("suspected_type", "unknown")}',
                      f'  Candidate IDs: {", ".join(issue["original_candidate_ids"])}. Severity: {r.get("severity") or "unspecified"}.',
                      f'  {r["explanation"]}', f'  Evidence: {", ".join(r["evidence_ids"]) or "none"}.',
                      f'  Locations: {json.dumps(r["source_locations"])}',
                      f'  Execution flow: {"; ".join(r["execution_flow"]) or "not established"}.',
                      f'  Incomplete evidence/errors: {json.dumps(r["incomplete_evidence"])}', '']
            if r.get('consistency_validation'):
                lines += [f'  Consistency validation: {json.dumps(r["consistency_validation"])}', '']
    lines += ['## Efficiency', '', '```json', json.dumps(report['efficiency'], indent=2), '```', '',
              'Source-context reduction is not detection accuracy. Full details and discovery coverage are in JSON.', '']
    return '\n'.join(lines)


def run_verification(discovery, contracts, catalog, output, *, resume=False, limits=None, analyze_fn=None, recovery_path=None, input_token_estimator=None):
    limits = limits or verification.Limits()
    if recovery_path is None:
        validate_discovery(discovery, contracts, catalog)
    else:
        import os
        from context_audit.discovery_recovery import validate_import
        validate_import(discovery, recovery_path, contracts, catalog, os.environ.get('OPENAI_MODEL'))
    groups = groups_for(discovery['candidates'])
    output = Path(output)
    manifest = {'version': 1, 'source': catalog.source_identity,
                'discovery_sha256': digest(discovery), 'configuration': verification.configuration(limits)}
    manifest_path = output / 'verification_manifest.json'
    if resume:
        if not manifest_path.is_file() or json.loads(manifest_path.read_text()) != manifest:
            raise ValueError('Verification resume manifest mismatch; use matching inputs/configuration or a fresh output')
    elif manifest_path.exists() or (output / 'sessions').exists() or (output / 'report.json').exists():
        raise ValueError('Existing verification artifacts require explicit resume')
    if not resume and output.exists():
        unexpected = {p.name for p in output.iterdir()} - {'discovery.json', 'summary.md'}
        if unexpected or ((output / 'discovery.json').exists() and json.loads((output / 'discovery.json').read_text()) != discovery):
            raise ValueError('Output directory contains unrelated artifacts')
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(manifest_path, manifest)
    sessions, reused = {}, set()

    def report_now():
        report = aggregate(discovery, contracts, catalog, groups, sessions, reused)
        atomic_json(output / 'report.json', report)
        (output / 'report.md').write_text(markdown(report))
        return report

    # Validate all saved sessions before making any additional API calls.
    for group in groups:
        path = output / 'sessions' / (group['key'] + '.json')
        if resume and path.exists():
            saved = json.loads(path.read_text())
            if saved.get('manifest_sha256') != digest(manifest) or saved.get('result_sha256') != digest(saved.get('result')):
                raise ValueError('Saved verification checksum/provenance mismatch')
            result = saved['result']
            if result.get('candidate') != group['candidate']:
                raise ValueError('Saved candidate mismatch')
            verification.validate_saved_result(result, contracts, catalog)
            if result['status'] == 'running':
                result['status'] = 'interrupted'
                result['errors'].append({'code': 'INTERRUPTED_TRANSPORT_OUTCOME_UNKNOWN'})
                result['incomplete_evidence'].append('INTERRUPTED_TRANSPORT_OUTCOME_UNKNOWN')
            sessions[group['key']] = result
            reused.add(group['key'])
    report_now()
    try:
        for index, group in enumerate(groups):
            if group['key'] in reused:
                continue
            if index >= limits.max_candidates:
                sessions[group['key']] = unfinished(group, 'CANDIDATE_BUDGET')
                report_now()
                continue
            def checkpoint(result):
                sessions[group['key']] = result
                atomic_json(output / 'sessions' / (group['key'] + '.json'),
                            {'manifest_sha256': digest(manifest), 'result_sha256': digest(result), 'result': result})
                report_now()
            consumed = sum(s['usage']['total_tokens'] for s in sessions.values())
            verification.verify_candidate(group['candidate'], contracts, catalog, limits=limits,
                analyze_fn=analyze_fn, checkpoint=checkpoint, token_budget=limits.max_total_tokens - consumed, input_token_estimator=input_token_estimator)
    finally:
        report = report_now()
    return report

"""Post-inference matching only; this module is never imported by the worker."""
from context_audit.direct import aggregate


def analyzed_session(result):
    """A returned model response counts even if context validation ended the session.

    Legacy successful sessions may lack round details. Error-bearing sessions
    require a saved response, so a failed transport attempt alone is insufficient.
    """
    if result.get('target', {}).get('preparation_mode', 'FULL_INDEX') not in ('FULL_INDEX', 'SOURCE_FALLBACK'):
        return False
    if result.get('round_count', 0) < 1 or result.get('assessment', {}).get('verdict') not in ('vulnerable', 'no_vulnerability_found', 'inconclusive'):
        return False
    returned_response = any(
        r.get('result', {}).get('assessment', {}).get('action') in ('request_context', 'final')
        for r in result.get('rounds', [])
    )
    return returned_response or not result.get('errors')


def relevant_sessions(label, sessions):
    """Resolve signatures exactly; bare names require lines or a unique overload."""
    function = ''.join((label.get('function') or '').split())
    lines = set(label.get('lines') or [])
    candidates = []
    for session in sessions:
        signature = ''.join(session['target']['signature'].split())
        if function and (signature != function if '(' in function else signature.split('(')[0] != function):
            continue
        if lines and not lines.intersection(session['target'].get('lines', [])):
            continue
        candidates.append(session)
    if function and '(' not in function and not lines:
        if len({r['target']['signature'] for r in candidates}) > 1:
            return [], 'ambiguous_overload'
    return candidates, 'resolved' if candidates else 'not_analyzed_or_unresolved'


def render_markdown(report):
    """Render classifications alongside metrics so missing a label is visible."""
    rows = ['# DAppSCAN direct detection', '', '## Metrics', '']
    rows.extend(f'- {key}: {value}' for key, value in report['metrics'].items())
    rows.extend(['', '## Ground-truth classifications', '',
                 '| SWC | Ground-truth function | Lines | Relevant sessions | Classification |',
                 '| --- | --- | --- | --- | --- |'])
    for item in report['labels']:
        label = item['label']
        lines = label.get('lines') or []
        span = f'{min(lines)}–{max(lines)}' if lines else 'Unavailable'
        functions = ', '.join(r['function'] for r in item['relevant_sessions']) or item['resolution']
        rows.append(f"| {label['swc_id']} | {label.get('function') or 'Unavailable'} | {span} | {functions} | {item['status']} |")
    rows.extend(['', '## Additional unlabeled findings', ''])
    rows.extend(f"- {item['function']}: {item['vulnerability_type']} ({item.get('swc_id') or 'No SWC'}). ADDITIONAL_UNLABELED_FINDING" for item in report['additional_findings'])
    return '\n'.join(rows) + '\n'


def evaluate(cases, results):
    labels = []
    additional = []
    for case in cases:
        sessions = [r for r in results if r.get('dataset_file') == case['file']]
        # Session evidence takes precedence over coarse file preparation status.
        sessions = [r for r in sessions if analyzed_session(r)]
        matched = set()
        for label in case['labels']:
            relevant, resolution = relevant_sessions(label, sessions)
            relevant = [r for r in relevant if r['target'].get('preparation_mode') != 'UNEVALUABLE']
            hits = []
            for r in relevant:
                for i, finding in enumerate(r['assessment']['findings']):
                    if finding.get('swc_id') == label['swc_id']:
                        hits.append(finding)
                        matched.add((r['target']['id'], i))
            # Without reliable location, category matches are explicitly source-level only.
            status = 'DETECTED' if hits else ('UNEVALUABLE' if not relevant else ('INCONCLUSIVE' if any(r['assessment']['verdict'] == 'inconclusive' for r in relevant) else 'MISSED'))
            labels.append({'label': label, 'status': status,
                           'resolution': resolution,
                           'target_preparation_modes': sorted({r['target'].get('preparation_mode', 'FULL_INDEX') for r in relevant}) or ['UNEVALUABLE'],
                           'relevant_sessions': [{'function': r['target']['signature'], 'verdict': r['assessment']['verdict'], 'preparation_mode': r['target'].get('preparation_mode', 'FULL_INDEX'), 'errors': r.get('errors', [])} for r in relevant],
                           'match_scope': 'location' if label.get('function') or label.get('lines') else 'source_only',
                           'location_reliable': bool(label.get('function') or label.get('lines'))})
        for r in sessions:
            for i, finding in enumerate(r['assessment']['findings']):
                if (r['target']['id'], i) not in matched:
                    additional.append({'status': 'ADDITIONAL_UNLABELED_FINDING', 'file': case['file'],
                                       'function': r['target']['signature'], **finding})
    counts = {s.lower(): sum(x['status'] == s for x in labels) for s in ('DETECTED', 'MISSED', 'INCONCLUSIVE', 'UNEVALUABLE')}
    evaluable = len(labels) - counts['unevaluable']
    located = [x for x in labels if x['location_reliable'] and x['status'] != 'UNEVALUABLE']
    analyzed_files = {r.get('dataset_file') for r in results if analyzed_session(r)}
    ready_files = sum(c.get('preparation_status') in ('READY', 'PARTIALLY_READY') or (c.get('preparation_status') is None and not c.get('preparation_error') and c.get('file') in analyzed_files) for c in cases)
    n = len(results)
    full = sum(r.get('full_source_estimated_tokens', 0) for r in results)
    selected = sum(r.get('selected_context_estimated_tokens', 0) for r in results)
    return {'labels': labels, 'additional_findings': additional, 'contract_reports': aggregate(results),
            'metrics': {**counts, 'labeled_vulnerabilities': len(labels),
                'additional_unlabeled_findings': len(additional),
                'selected_files': len(cases), 'ready_files': ready_files, 'analyzed_files': len(analyzed_files),
                'preparation_failures': len(cases)-ready_files,
                'evaluable_labels': evaluable, 'unevaluable_labels': counts['unevaluable'],
                'evaluation_coverage': evaluable/len(labels) if labels else None,
                'recall': counts['detected']/evaluable if evaluable else None,
                'type_accuracy_among_detected': 1.0 if counts['detected'] else None,
                'type_accuracy_note': 'SWC compatibility is required by the matching rule; not an independent classifier metric.',
                'location_match_rate': sum(x['status']=='DETECTED' for x in located)/len(located) if located else None,
                'total_api_calls': sum(r['round_count'] for r in results),
                'total_tokens': sum(r['usage']['total_tokens'] for r in results),
                'average_rounds': sum(r['round_count'] for r in results)/n if n else None,
                'average_requested_fragments': sum(r['requested_fragments'] for r in results)/n if n else None,
                'context_reduction': 1-selected/full if full else None}}

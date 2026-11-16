"""Post-inference scoring only. Never imported into prompt construction."""
import csv
import json
from collections import Counter
from pathlib import Path
from context_audit.v2_artifacts import atomic_json, digest

SCORING_PROTOCOL = {'strict_recall': 'DETECTED / (DETECTED + MISSED + INCONCLUSIVE)', 'conclusive_only_recall': 'DETECTED / (DETECTED + MISSED)', 'evaluation_coverage': '(DETECTED + MISSED + INCONCLUSIVE) / all_GT_labels', 'conclusive_coverage': '(DETECTED + MISSED) / all_GT_labels', 'matching': 'Reviewed semantic SWC + exact canonical contract + target source fragment and exact source location + explicit post-inference GT root-cause match review; broad category alone never sufficient.', 'processing_errors': 'INCONCLUSIVE for unmatched evaluable labels; never convert processing failure to MISSED.', 'unresolvable_GT': 'UNEVALUABLE; excluded from recall, included in coverage denominator.', 'precision': 'VALID / (VALID + LIKELY_FALSE_POSITIVE), confirmed findings with nonempty adjudication rationale only; PLAUSIBLE/UNRESOLVED/DUPLICATE excluded; disclose decided coverage.', 'adjudication': ['VALID', 'PLAUSIBLE', 'LIKELY_FALSE_POSITIVE', 'DUPLICATE', 'UNRESOLVED'], 'context': 'B v2 verification source-context reduction only; discovery API tokens reported separately.'}

ADJUDICATION = {'VALID', 'PLAUSIBLE', 'LIKELY_FALSE_POSITIVE', 'DUPLICATE', 'UNRESOLVED'}


def metrics(rows):
    counts = Counter(r['status'] for r in rows)
    n = len(rows); evaluable = n - counts['UNEVALUABLE']; conclusive = counts['DETECTED'] + counts['MISSED']
    return {'labels': n, 'evaluable_labels': evaluable, **{s.lower(): counts[s] for s in
        ('DETECTED', 'MISSED', 'INCONCLUSIVE', 'UNEVALUABLE')},
        'strict_recall': counts['DETECTED'] / evaluable if evaluable else None,
        'conclusive_only_recall': counts['DETECTED'] / conclusive if conclusive else None,
        'evaluation_coverage': evaluable / n if n else None,
        'conclusive_coverage': conclusive / n if n else None,
        'inconclusive_rate': counts['INCONCLUSIVE'] / evaluable if evaluable else None}


def score_labels(labels, report, assignments):
    """A hit requires explicit reviewed type AND source/contract/function evidence match."""
    rows = []
    for label in labels:
        targets = label['targets']; hits = []; relevant = []
        uncertain_type = False
        for issue in (report or {}).get('issues', []):
            r = issue['result']; c = r['candidate']
            assignment = assignments.get(issue['issue_id'], {})
            matched = [t for t in targets if c['contract'] == t['contract'] and
                (c['primary_fragment_id'] == t['fragment_id'] or t['fragment_id'] in r.get('evidence_ids', []))]
            if not matched:
                continue
            relevant.append(r)
            if r.get('verdict') == 'confirmed':
                # Broader category alone can never be counted as a hit.
                grounded = any(t['fragment_id'] in r['evidence_ids'] and
                    r.get('source_locations', {}).get(t['fragment_id']) == t['location'] for t in matched)
                if not assignment.get('swc_id') or not assignment.get('rationale'):
                    uncertain_type = True
                elif assignment['swc_id'] == label['swc_id'] and grounded and r.get('status') == 'completed':
                    if not assignment.get('gt_match_reviewed') or not assignment.get('match_rationale'):
                        uncertain_type = True
                    elif label['label_id'] in assignment.get('matched_label_ids', []):
                        hits.append(issue['issue_id'])
        if not targets:
            status = 'UNEVALUABLE'
        elif hits:
            status = 'DETECTED'
        else:
            coverage = (report or {}).get('coverage_counts', {})
            examined = [x for c in (report or {}).get('contracts', []) for x in c['coverage']
                        if any(x['contract'] == t['contract'] and x['fragment_id'] == t['fragment_id'] for t in targets)]
            unresolved = (not report or not examined or any(x['status'] not in ('selected', 'not_selected') for x in examined) or
                (report or {}).get('discovery_errors') or uncertain_type or
                any(r.get('status') != 'completed' or r.get('verdict') == 'inconclusive' for r in relevant) or
                coverage.get('pending_candidates', 0) or coverage.get('processing_failures', 0) or
                coverage.get('skipped_candidates', 0) or (report or {}).get('transport_this_run', {}).get('stopped'))
            status = 'INCONCLUSIVE' if unresolved else 'MISSED'
        rows.append({'label_id': label['label_id'], 'swc_id': label['swc_id'], 'status': status,
                     'matched_issue_ids': hits, 'targets': targets, 'original_label': label['original_label']})
    return rows


def summarize(manifest, evaluation, reports, reviews=None, ledgers=None):
    reviews = reviews or {}; labels = []; findings = []; efficiencies = []; reliability = Counter({k:0 for k in ('contracts_not_finalized','discovery_failures','verification_failures','invalid_model_responses','budget_stops','unselected_functions','resume_reused_issues')}); modes = Counter(); function_coverage = Counter()
    for case in manifest['cases']:
        report = reports.get(case['id']); assignments = reviews.get(case['id'], {})
        case_rows = score_labels(evaluation[case['id']]['labels'], report, assignments)
        for row in case_rows: row.update(case=case['id'], cohort=case['cohort'])
        labels.extend(case_rows)
        if not report:
            reliability['contracts_not_finalized'] += 1
            continue
        efficiency = report['efficiency']; transport = report.get('transport_this_run', {})
        efficiencies.append({'case': case['id'], 'cohort': case['cohort'], 'efficiency': efficiency, 'transport': transport})
        reliability['discovery_failures'] += len(report['discovery_errors'])
        reliability['verification_failures'] += report['coverage_counts']['processing_failures']
        reliability['budget_stops'] += bool('BUDGET' in transport.get('stop_reason','') or report['coverage_counts'].get('skipped_candidates'))
        reliability['invalid_model_responses'] += sum(x.get('error')=='DISCOVERY_PROTOCOL_ERROR' for x in report['discovery_errors'])
        reliability['invalid_model_responses'] += sum(any(e['code'] in ('UNSEEN_EVIDENCE_ID','REPEATED_CONTEXT_ID','INVALID_CONTEXT_ID','MODEL_PROTOCOL_ERROR') for e in i['result']['errors']) for i in report['issues'])
        reliability['resume_reused_issues'] += sum(i.get('reused',False) for i in report['issues'])
        for k in ('total_functions','included','examined','selected','not_selected','unevaluable','pending'):
            function_coverage[k] += report['coverage_counts'].get(k,0)
        reliability['unselected_functions'] += report['coverage_counts']['not_selected']
        for row in case['coverage']: modes['summary_' + ('incomplete_metadata' if row['incomplete_metadata'] else 'complete_metadata')] += 1
        matched = {x for r in case_rows for x in r['matched_issue_ids']}
        for issue in report['issues']:
            r = issue['result']; review = assignments.get(issue['issue_id'], {})
            adjudication = review.get('adjudication') or None
            if adjudication is not None and adjudication not in ADJUDICATION:
                raise ValueError('INVALID_MANUAL_ADJUDICATION')
            findings.append({'case': case['id'], 'issue_id': issue['issue_id'], 'candidate_ids': issue['original_candidate_ids'],
                'candidate': r['candidate'], 'verification_verdict': r['verdict'], 'severity': r['severity'],
                'explanation': r['explanation'], 'execution_flow': r.get('execution_flow', []),
                'source_locations': r['source_locations'], 'evidence_ids': r['evidence_ids'],
                'duplicates': [x for x in report.get('possible_overlaps', []) if issue['issue_id'] in x['issue_ids']],
                'matched_gt': issue['issue_id'] in matched, 'adjudication': adjudication,
                'swc_id': review.get('swc_id'), 'rationale': review.get('rationale', '')})
    decided = [f for f in findings if f['verification_verdict'] == 'confirmed' and f['adjudication'] in ('VALID', 'LIKELY_FALSE_POSITIVE') and f['rationale'].strip()]
    actual = actual_usage(ledgers or {})
    reliability['invalid_model_responses'] += sum(e.get('status')=='response_parse_failed' for ledger in (ledgers or {}).values() for e in ledger.get('events',[]))
    total = {k: sum(e['efficiency']['total'][k] for e in efficiencies) for k in ('input_tokens','output_tokens','total_tokens')}
    selected = sum(e['efficiency']['selected_source_estimated_tokens'] for e in efficiencies)
    baseline = sum(e['efficiency']['full_source_baseline_tokens'] for e in efficiencies)
    return {'metrics': metrics(labels), 'per_cohort': {c: metrics([r for r in labels if r['cohort'] == c]) for c in ('development','held_out')},
        'per_swc': {s: metrics([r for r in labels if r['swc_id'] == s]) for s in sorted({r['swc_id'] for r in labels})},
        'labels': labels, 'findings': findings, 'additional_findings': [f for f in findings if not f['matched_gt'] and f['verification_verdict']=='confirmed'],
        'other_candidates': [f for f in findings if f['verification_verdict']!='confirmed'],
        'manual_precision_decided_only': sum(f['adjudication']=='VALID' for f in decided)/len(decided) if decided else None,
        'precision_decided_count': len(decided), 'manual_uncertain_count': sum(f['adjudication'] not in ('VALID','LIKELY_FALSE_POSITIVE','DUPLICATE') for f in findings),
        'tokens_including_imported_history_once': total,
        'actual_transport_this_experiment': actual,
        'api_endpoints_this_experiment': actual['generation_calls']+actual['count_calls'],
        'average_context_rounds_per_candidate': sum(e['efficiency']['rounds'] for e in efficiencies)/len(findings) if findings else None,
        'actual_tokens_per_verified_candidate': sum(e['efficiency']['verification']['total_tokens'] for e in efficiencies)/sum(f['verification_verdict'] is not None for f in findings) if any(f['verification_verdict'] is not None for f in findings) else None,
        'declared_preparation_modes': {k:sum(c['preparation'].get(k,0) for c in manifest['cases']) for k in ('FULL_INDEX','SOURCE_FALLBACK','UNEVALUABLE')},
        'per_contract_efficiency': efficiencies, 'verification_source_context_reduction': 1-selected/baseline if baseline else None,
        'reliability': dict(reliability), 'function_coverage':dict(function_coverage), 'preparation_statistics': dict(modes),
        'note': 'Not-run/infrastructure cases are inconclusive; unlabelled findings are not automatic false positives.'}


def write_summary(output, summary):
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    atomic_json(output/'summary.json', summary)
    with (output/'labels.csv').open('w', newline='') as f:
        writer=csv.DictWriter(f, fieldnames=['case','cohort','label_id','swc_id','status','matched_issue_ids']); writer.writeheader()
        writer.writerows({k:r[k] for k in writer.fieldnames} for r in summary['labels'])
    with (output/'contracts.csv').open('w', newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['case','cohort','input_tokens','output_tokens','total_tokens']);writer.writeheader()
        writer.writerows({'case':e['case'],'cohort':e['cohort'],**{k:e['efficiency']['total'][k] for k in ('input_tokens','output_tokens','total_tokens')}} for e in summary['per_contract_efficiency'])
    atomic_json(output/'additional_findings.json', summary['additional_findings'])
    atomic_json(output/'adjudication_template.json', {c:{f['issue_id']:{'swc_id':None,'rationale':'','adjudication':None,'duplicate_of':None,'gt_match_reviewed':False,'matched_label_ids':[],'match_rationale':''}
        for f in summary['findings'] if f['case']==c} for c in {f['case'] for f in summary['findings']}})
    (output/'report.md').write_text('# Mode B v2 dataset evaluation\n\nNo exploit validation is implied.\n\n```json\n'+
        json.dumps({k:summary[k] for k in ('metrics','per_cohort','per_swc','tokens_including_imported_history_once','reliability','manual_precision_decided_only')},indent=2)+'\n```\n')


def actual_usage(ledgers):
    result = {'generation_calls':0,'count_calls':0,'input_tokens':0,'output_tokens':0,'total_tokens':0,'unknown_generation_usage':0,'per_contract':{}}
    for case, ledger in ledgers.items():
        row = {k:0 for k in ('input_tokens','output_tokens','total_tokens')}; known=0
        for event in ledger.get('events',[]):
            usage=event.get('usage',{})
            if all(type(usage.get(k)) is int and usage[k]>=0 for k in row):
                for k in row:row[k]+=usage[k]
                known+=1
        row.update(generation_calls=ledger['generation_calls'],count_calls=ledger['count_calls'],
                   unknown_generation_usage=max(0,ledger['generation_calls']-known))
        result['per_contract'][case]=row
        for k,v in row.items():result[k]+=v
    return result

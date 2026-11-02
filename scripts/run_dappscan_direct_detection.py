"""Small, explicit DAppSCAN runs; preparation is the default."""
import argparse
import json
import hashlib
from pathlib import Path
from context_audit.datasets.dappscan import DAppSCAN, select_pilot
from context_audit.direct import prepare, run_function, aggregate
from context_audit.direct_preparation import PreparationError
from context_audit.app.compilers import detect_pragmas
from context_audit.direct_evaluation import evaluate, render_markdown, relevant_sessions


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def main(argv=None):
    p = argparse.ArgumentParser(__doc__)
    for name in ('dataset-root', 'project', 'contract', 'swc'):
        p.add_argument('--' + name)
    p.add_argument('--function', action='append')
    p.add_argument('--file', action='append')
    p.add_argument('--limit', type=int, help='Maximum files; defaults to all explicit --file selections, otherwise one')
    p.add_argument('--max-functions', type=int, default=20)
    p.add_argument('--max-rounds', type=int, default=4)
    for name in ('prepare', 'run', 'summarize'):
        p.add_argument('--' + name, action='store_true')
    p.add_argument('--manifest', type=Path)
    p.add_argument('--output', type=Path, default=Path('examples/dappscan/evaluation/direct_detection/local_run'))
    args = p.parse_args(argv)
    out = args.output
    if out.resolve().name == 'pilot10':
        p.error('pilot10_debug_prefixed is preserved; choose a different output directory')
    if args.summarize:
        cases = json.loads((out / 'prepared_targets.json').read_text())['cases']
        results = [json.loads(f.read_text()) for f in sorted((out / 'results').glob('*.json'))]
        report = evaluate(cases, results)
        save(out / 'evaluation_results.json', report)
        (out / 'evaluation_results.md').write_text(render_markdown(report))
        return report
    if args.limit is not None and args.limit < 1:
        p.error('--limit must be positive')
    dataset = DAppSCAN(args.dataset_root)
    if args.manifest and args.manifest.exists():
        cases = json.loads(args.manifest.read_text()).get('cases', [])
    else:
        cases = []
    if not cases:
        projects = [args.project] if args.project else dataset.projects()
        cases = [{'project': project, 'file': file, 'labels': dataset.labels(file)} for project in projects
                 for file in dataset.files(project) if not args.file or file in args.file]
        if not args.file and not args.project:
            cases = select_pilot(cases)
    cases = [c for c in cases if (not args.project or c['project']==args.project)
             and (not args.file or c['file'] in args.file)
             and (not args.swc or any(l['swc_id']==args.swc for l in c['labels']))]
    # Keep source/manifest order; repeated selectors or manifest entries must not
    # create duplicate sessions. Apply only an explicit cap to explicit files.
    unique_cases = {}
    for case in cases:
        unique_cases.setdefault(case['file'], case)
    cases = list(unique_cases.values())
    limit = args.limit if args.limit is not None else (None if args.file else 1)
    cases = cases[:limit]
    for case in cases:
        digest = hashlib.sha256(dataset.source_path(case['file']).read_bytes()).hexdigest()
        if case.get('source_sha256') and case['source_sha256'] != digest:
            p.error('Manifest source hash mismatch: ' + case['file'])
        case['source_sha256'] = digest
    save(out / 'pilot_manifest.json', {'cases': cases, 'selection_policy': 'Prespecified SWC categories; lexicographic source order; selected before inference'})
    prepared = []
    jobs = []
    for case in cases:
        metadata = {'selected': True, 'pragma': '; '.join(detect_pragmas(dataset.source_path(case['file']).read_text())), 'compiler_used': None, 'compiler_version_attempted': None, 'preparation_error': None, 'session_count': 0}
        try:
            payloads, catalog = prepare(dataset.source_path(case['file']))
            payloads = [x for x in payloads if (not args.function or any(x['target']['signature'] == f if '(' in f else x['target']['signature'].split('(')[0] == f for f in args.function))
                        and (not args.contract or x['target']['contract']==args.contract)]
            jobs.extend((case['file'], x, catalog) for x in payloads)
            prepared.append({**case, **metadata, **getattr(catalog, 'preparation_metadata', {}), 'preparation_status': getattr(catalog, 'preparation_metadata', {}).get('preparation_status', 'READY') if payloads else 'NO_ANALYZABLE_FUNCTIONS', 'functions': len(payloads), 'session_count': len(payloads)})
        except Exception as exc:
            prepared.append({**case, **metadata, 'preparation_status': 'COMPILATION_FAILED', 'preparation_error': str(exc), **(exc.metadata if isinstance(exc, PreparationError) else {})})
    for case in prepared:
        records = [{'target': r} for r in case.get('function_readiness', [])]
        case['ground_truth_readiness'] = []
        for label in case['labels']:
            matched, resolution = relevant_sessions(label, records)
            case['ground_truth_readiness'].append({'label': label, 'resolution': resolution, 'preparation_modes': sorted({r['target']['preparation_mode'] for r in matched}) or ['UNEVALUABLE']})
    save(out / 'prepared_targets.json', {'cases': prepared, 'sessions': len(jobs)})
    for case in prepared:
        print(f"{case['file']}: {case['preparation_status']}\nTotal source functions: {case.get('total_source_functions', 0)}\nFULL_INDEX sessions: {case.get('FULL_INDEX', 0)}\nSOURCE_FALLBACK sessions: {case.get('SOURCE_FALLBACK', 0)}\nUNEVALUABLE functions: {case.get('UNEVALUABLE', 0)}")
    ready = sum(c['preparation_status'] in ('READY', 'PARTIALLY_READY') for c in prepared)
    print(f'Selected files: {len(cases)}\nReady files: {ready}\nFailed preparation: {len(cases)-ready}\nFunction sessions: {len(jobs)}')
    if ready < len(cases):
        print('Only READY/PARTIALLY_READY files with safe sessions will be analyzed.')
    if not args.run:
        return prepared
    if len(jobs) > args.max_functions:
        p.error('Selected functions exceed --max-functions; narrow selection or explicitly raise the cap')
    if (out / 'results').exists():
        p.error('Results already exist; choose a fresh --output to preserve sessions')
    results = []
    for i, (file, payload, catalog) in enumerate(jobs):
        result = run_function(payload, catalog, out / 'results' / f'{i:04}.json', args.max_rounds)
        result['dataset_file'] = file
        save(out / 'results' / f'{i:04}.json', result)
        save(out / 'prompt_journals' / f'{i:04}.json', result['prompt_journal'])
        results.append(result)
    for i, report in enumerate(aggregate(results)):
        save(out / 'contract_reports' / f'{i:04}.json', report)
    evaluation = evaluate(prepared, results)
    save(out / 'evaluation_results.json', evaluation)
    (out / 'evaluation_results.md').write_text(render_markdown(evaluation))
    return results


if __name__ == '__main__':
    main()

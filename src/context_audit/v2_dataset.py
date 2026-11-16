"""B v2-only, sequential, frozen cohort execution. No ground-truth loader here."""
import json
import os
from pathlib import Path
from openai import OpenAI
from context_audit import direct_discovery as d, direct_verification as v
from context_audit.discovery_recovery import build_import
from context_audit.development_experiment import JournalTransport, identity as base_identity
from context_audit.v2_artifacts import atomic_json, digest, file_hash, implementation_hash
from context_audit.v2_pipeline import run_verification, markdown

LIMITS = v.Limits(max_candidates=3, max_rounds=3, max_fragments=8, max_source_tokens=8000,
                  max_input_tokens=12000, max_output_tokens=4000, max_total_tokens=60000)


def identity():
    return {**base_identity(), 'dataset': implementation_hash(['v2_dataset', 'discovery_recovery', 'v2_dataset_scoring']),
            'dataset_cli': file_hash(Path(__file__).resolve().parents[2] / 'scripts/run_v2_dataset.py')}


def case_plan(source, model, output, recovery=None):
    contracts, catalog = d.prepare(Path(source))
    batches, coverage = d.make_batches(contracts)
    if not batches or any(not x['included'] for x in coverage):
        raise ValueError('INCOMPLETE_PREPARATION')
    imported = build_import(recovery, contracts, catalog, model) if recovery else None
    calls = (0 if recovery else len(batches)) + LIMITS.max_candidates * LIMITS.max_rounds
    return {'source': str(Path(source).resolve()), 'source_identity': catalog.source_identity,
            'model': model, 'output': str(Path(output).resolve()), 'limits': LIMITS.model_dump(),
            'budget': {'max_discovery_calls': 0 if recovery else len(batches), 'max_generation_calls': calls,
                       'max_count_calls': calls, 'max_reserved_tokens': 60000, 'max_input_tokens_per_call': 12000},
            'recovery_path': str(Path(recovery).resolve()) if recovery else None,
            'recovery_sha256': file_hash(recovery) if recovery else None,
            'import_sha256': digest(imported) if recovery else None,
            'preparation': catalog.preparation_metadata, 'coverage': coverage,
            'discovery_batches': len(batches), 'summary_prompt_estimated_tokens':
                sum(len(json.dumps(d.messages(b))) // 4 + 1 for b in batches)}


def preflight_case(case):
    contracts, catalog = d.prepare(Path(case['source']))
    if case['source_identity'] != catalog.source_identity:
        raise ValueError('SOURCE_COMPILER_CATALOG_MISMATCH')
    imported = None
    if case['recovery_path']:
        if file_hash(case['recovery_path']) != case['recovery_sha256']:
            raise ValueError('RECOVERY_HASH_MISMATCH')
        imported = build_import(case['recovery_path'], contracts, catalog, case['model'])
        if digest(imported) != case['import_sha256']:
            raise ValueError('RECOVERY_IMPORT_MISMATCH')
    return contracts, catalog, imported


def execute_case(case, configuration, *, resume=False, client_factory=None):
    if configuration != identity():
        raise ValueError('IMPLEMENTATION_CHANGED')
    if os.environ.get('OPENAI_MODEL') != case['model']:
        raise ValueError('MODEL_MISMATCH')
    if not os.environ.get('OPENAI_API_KEY'):
        raise ValueError('CREDENTIAL_MISSING')
    if os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/') != 'https://api.openai.com/v1':
        raise ValueError('OFFICIAL_ENDPOINT_REQUIRED')
    contracts, catalog, imported = preflight_case(case)
    output = Path(case['output']); analysis = output / 'analysis'
    plan = {'case': case, 'configuration': configuration, 'model': case['model'], 'budget': case['budget']}
    manifest = {'plan': plan, 'sha256': digest(plan)}
    if resume:
        if json.loads((output / 'run_manifest.json').read_text()) != manifest:
            raise ValueError('RESUME_MANIFEST_MISMATCH')
    else:
        output.mkdir(parents=True, exist_ok=False)
        atomic_json(output / 'run_manifest.json', manifest)
    transport = JournalTransport(output, plan, client_factory or OpenAI, resume=resume)
    # Initialize a zero-call ledger, including for an empty recovered candidate set.
    if not resume:
        atomic_json(output / 'budget_ledger.json', {'model': case['model'], 'budget': case['budget'],
            'generation_calls': 0, 'count_calls': 0, 'discovery_calls': 0, 'reserved_tokens': 0,
            'stopped': False, 'events': []})
        atomic_json(output / 'transport_checkpoint.json', {'plan_sha256': digest(plan),
            'ledger_sha256': digest(json.loads((output / 'budget_ledger.json').read_text()))})
    found = imported if imported is not None else d.run_discovery(contracts, catalog, execute=True,
        analyze_fn=lambda batch: transport.call('discovery', d.messages(batch), d.DiscoveryResponse, 8000))
    atomic_json(analysis / 'discovery.json', found)
    (analysis / 'summary.md').write_text(d.markdown(found))
    report = run_verification(found, contracts, catalog, analysis,
        recovery_path=case['recovery_path'], resume=resume and (analysis / 'verification_manifest.json').exists(),
        limits=v.Limits(**case['limits']), analyze_fn=lambda p, s, **kw:
            transport.call('verification', v.messages(p, s), v.VerificationResponse,
                           kw['max_output_tokens'], p['candidate']['candidate_id']))
    ledger = json.loads((output / 'budget_ledger.json').read_text())
    report['transport_this_run'] = {k: x for k, x in ledger.items() if k != 'events'}
    report['accounting_note'] = 'Efficiency includes historical imported discovery once; transport counts only this run.'
    atomic_json(analysis / 'report.json', report)
    (analysis / 'report.md').write_text(markdown(report))
    atomic_json(output / 'finalized.json', {'report_sha256': digest(report), 'ledger_sha256': digest(ledger),
        'configuration_sha256': digest(configuration), 'case_sha256': digest(case)})
    return report


def execute_cohort(manifest, cohort, *, resume=False, client_factory=None, acknowledge_partial=()):
    if cohort not in ('development', 'held_out') or manifest['configuration'] != identity():
        raise ValueError('COHORT_OR_CONFIGURATION_MISMATCH')
    cases = [c for c in manifest['cases'] if c['cohort'] == cohort]
    if acknowledge_partial and (not resume or set(acknowledge_partial) - {c['id'] for c in cases}):
        raise ValueError('INVALID_PARTIAL_ACKNOWLEDGEMENT')
    totals = manifest['cohort_budgets'][cohort]
    for key in ('max_generation_calls', 'max_count_calls', 'max_reserved_tokens'):
        if sum(c['budget'][key] for c in cases) != totals[key]:
            raise ValueError('COHORT_BUDGET_MISMATCH')
    # Validate all sources/imports and existing finalization records before any API access.
    for case in cases:
        preflight_case(case)
        output = Path(case['output'])
        if output.exists() and not resume:
            raise ValueError('EXISTING_OUTPUT_REQUIRES_EXPLICIT_RESUME')
        if case['id'] in acknowledge_partial and not (output / 'finalized.json').exists():
            raise ValueError('PARTIAL_ACK_REQUIRES_FINALIZED_RESULT')
        if (output / 'finalized.json').exists():
            validate_finalized(case, manifest['configuration'])
    results = []
    for case in cases:
        output = Path(case['output'])
        try:
            if (output / 'finalized.json').exists():
                report = json.loads((output / 'analysis/report.json').read_text())
            else:
                report = execute_case(case, manifest['configuration'], resume=resume and output.exists(), client_factory=client_factory)
            counts = report['coverage_counts']
            status = 'partial' if (report['discovery_errors'] or counts['processing_failures'] or
                counts['skipped_candidates'] or counts['pending_candidates'] or report['transport_this_run']['stopped']) else 'completed'
            if status == 'partial' and resume and case['id'] in acknowledge_partial:
                status = 'reviewed_partial'
            results.append({'case': case['id'], 'status': status})
        except (Exception, KeyboardInterrupt) as exc:
            # No raw exception messages or source/request bodies in ordinary diagnostics.
            from context_audit.v2_errors import exception_metadata, safe_id
            results.append({'case': case['id'], 'status': 'interrupted_or_failed',
                            'diagnostic': {**exception_metadata(exc), 'case_id': safe_id(case['id'])}})
            status = 'partial'
        atomic_json(Path(manifest['output']) / (cohort + '-execution.json'),
                    {'manifest_sha256': digest(manifest), 'cohort': cohort, 'cases': results})
        if status not in ('completed', 'reviewed_partial'):
            break  # Do not silently spend on the next contract after a partial result.
    return results


def validate_finalized(case, configuration):
    output = Path(case['output'])
    seal = json.loads((output / 'finalized.json').read_text())
    report = json.loads((output / 'analysis/report.json').read_text())
    ledger = json.loads((output / 'budget_ledger.json').read_text())
    if seal != {'report_sha256': digest(report), 'ledger_sha256': digest(ledger),
                'configuration_sha256': digest(configuration), 'case_sha256': digest(case)}:
        raise ValueError('FINALIZED_RESULT_MISMATCH')

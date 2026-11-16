"""Private synthetic unit fixtures; original research artifacts remain immutable.

Recorded model responses are test inputs only. Updated request/index envelopes
are explicitly synthetic and never represent fresh model inference or approval.
"""
import copy
import json
from pathlib import Path
from unittest.mock import patch
from context_audit import direct_discovery as d
from context_audit.v2_artifacts import digest, file_hash, implementation_hash
from context_audit.discovery_recovery import build_import

HISTORICAL_RECOVERY = Path('experiments/mode-b-v2-identity-fix-2026-11-09/offline_reprocessing.json')


def recovery_fixture(root, contracts, catalog, model):
    root.mkdir(parents=True, exist_ok=True)
    old = json.loads(HISTORICAL_RECOVERY.read_text())
    original = json.loads(Path(old['source_artifact']).read_text())
    recorded = copy.deepcopy(original['rounds'][0]['response'])
    with patch.dict('os.environ', {'OPENAI_MODEL': model}):
        current = d.run_discovery(contracts, catalog, execute=True, analyze_fn=lambda _: recorded)
    assert not current['errors']
    source = root / 'synthetic-discovery.json'
    source.write_text(json.dumps(current))
    batches, _ = d.make_batches(contracts)
    diagnostics = []
    parsed = d.validate_response(recorded['assessment'], batches[0], catalog, candidate_diagnostics=diagnostics)
    fixture = {**old, 'fixture_kind': 'synthetic_current_protocol_unit_test',
        'source_artifact': str(source), 'source_artifact_sha256': file_hash(source),
        'original_manifest': current['manifest'], 'current_source_identity': catalog.source_identity,
        'normalizer_implementation_sha256': implementation_hash(['direct_discovery']),
        'candidate_validation': diagnostics, 'accepted_candidates': [c.model_dump() for c in parsed.candidates],
        'examined_functions': [f.model_dump() for f in parsed.examined_functions]}
    result = root / 'synthetic-recovery.json'
    result.write_text(json.dumps(fixture))
    return result


def continuation_fixture(root, parent_path, case_id, contracts, catalog, model):
    fixture = copy.deepcopy(json.loads(parent_path.read_text()))
    case = next(c for c in fixture['cases'] if c['id'] == case_id)
    old_output = Path(case['output'])
    recovery = recovery_fixture(root / 'recovery', contracts, catalog, model)
    imported = build_import(recovery, contracts, catalog, model)
    destination = root / 'synthetic-finalized-parent'
    case.update(output=str(destination), source_identity=catalog.source_identity,
                recovery_path=str(recovery), recovery_sha256=file_hash(recovery), import_sha256=digest(imported))
    destination.mkdir()
    report = json.loads((old_output / 'analysis/report.json').read_text())
    ledger = json.loads((old_output / 'budget_ledger.json').read_text())
    paths = ['analysis/report.json', 'analysis/verification_manifest.json', 'budget_ledger.json']
    paths += ['analysis/' + issue['session_artifact'] for issue in report['issues']]
    for relative in paths:
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((old_output / relative).read_bytes())
    (destination / 'finalized.json').write_text(json.dumps(dict(report_sha256=digest(report),
        ledger_sha256=digest(ledger), configuration_sha256=digest(fixture['configuration']), case_sha256=digest(case))))
    path = root / 'synthetic-parent-manifest.json'
    path.write_text(json.dumps(fixture))
    return path

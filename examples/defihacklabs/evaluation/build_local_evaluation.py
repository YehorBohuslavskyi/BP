"""Integrate the sole locally documented incident; no compilation, inference or network calls.

Refuse to overwrite evaluation outputs. This does not manufacture a 20-case cohort.
"""
from dataclasses import asdict
from pathlib import Path
import csv
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
PILOT = BASE.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    names = ['incident_inventory.csv', 'manifest.json', 'manifest.md',
             'slither_baseline.json', 'slither_baseline.csv', 'verification_targets.json']
    if any((BASE / name).exists() for name in names):
        raise SystemExit('Evaluation outputs exist; refusing to overwrite. Use check_integrity.py.')
    source = PILOT / 'SpankChain.sol'
    preflight = json.loads((PILOT / 'SpankChain_preflight.json').read_text())
    assert digest(source) == preflight['source_sha256']
    from context_audit.findings import parse_slither_findings
    raw = json.loads((PILOT / 'SpankChain_slither.json').read_text())
    findings = parse_slither_findings(raw)
    finding, = [f for f in findings if f.detector == 'reentrancy-eth'
                and f.contract == 'LedgerChannel' and f.function_signature == 'LCOpenTimeout(bytes32)']
    folder = BASE / 'contracts/spankchain'
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source, folder / source.name)
    shutil.copyfile(PILOT / 'LICENSE-SpankChain.txt', folder / 'LICENSE.txt')
    incident = dict(incident_id='spankchain', project='SpankChain', date='2018-10-07',
        chain='Ethereum', poc_path=None,
        referenced_upstream_poc_path='src/test/2018-10/SpankChain_exp.sol',
        attack_tx='0x21e9d20b57f6ae60dac23466c8395d47f42dc24628e5a31f224567a2b4effa88',
        victim_address='0xf91546835f756DA0c10cFa0CDA95b15577b84aA7',
        source_origin='examples/defihacklabs/SpankChain.sol',
        provenance_document='examples/defihacklabs/SpankChain_ground_truth.md',
        source_path=str((folder / source.name).relative_to(ROOT)), source_sha256=digest(source),
        compiler_version='0.4.25', known_root_cause='Token callback before deletion of channel state',
        affected_contract='LedgerChannel', affected_function='LCOpenTimeout(bytes32)',
        vulnerability_class='reentrancy', expected_detector_family=['reentrancy-eth'],
        ground_truth_label='REAL_VULNERABILITY', source_availability='AVAILABLE_LOCAL_ARCHIVE',
        selection_reason='Reuse the explicitly permitted already-completed pilot with local source and documented incident linkage.',
        already_completed_pilot=True,
        limitations=['No local DeFiHackLabs checkout or PoC file found; upstream PoC path is referenced by local documentation only.',
            'Archived source with normalized whitespace; no deployed-bytecode match established.',
            'Slither outcome was known before integration: pilot is not a prospective blind selection.',
            'Cannot supply 19 additional local incident records or faithful sources.'])
    manifest = dict(schema_version=1, status='INCOMPLETE_LOCAL_MATERIALS', requested_subset_size=20,
        actual_subset_size=1, missing_case_count=19, primary_20_case_subset_frozen=False,
        pilot_integration_frozen=True, new_slither_evaluations_started=False,
        selection_policy='Local documented static-code incidents with faithful victim source; no selection by detector success.',
        search_scope=['/home/coca-cola/projects', '/tmp'],
        exclusions=[], exclusions_note='Only one locally documented incident found; no other incident-level exclusions can be evidenced. Missing slots are not incidents.',
        records=[incident])
    (BASE / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    with (BASE / 'incident_inventory.csv').open('w', newline='') as handle:
        fields=['incident_id','project','date','chain','poc_path','referenced_upstream_poc_path',
                'victim_address','attack_tx','source_origin','affected_contract','affected_function',
                'vulnerability_class','source_availability','compiler_version','selection_reason']
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader()
        writer.writerow({key:incident[key] for key in fields})
    selected = dict(detector=finding.detector, impact=finding.impact, confidence=finding.confidence,
        contract=finding.contract, function=finding.function_signature, lines=finding.lines,
        description=finding.description, finding_id=finding.id)
    row=dict(incident_id='spankchain', known_vulnerability='reentrancy in LCOpenTimeout(bytes32)',
        result='DETECTED', detector=finding.detector, finding_id=finding.id,
        compilation_status='REUSED_PASSED', slither_status='REUSED_ANALYZABLE',
        evidence_scope='Existing detector-scoped raw JSON; full-run counts imported from preflight metadata.')
    imported=dict(row, corresponding_finding=selected,
        compilation=dict(compiler=preflight['compiler'],status='REUSED_PASSED', errors=None,
            errors_note='Historical compiler output not saved here; existing preflight records successful compilation.',
            historical_command='SOLC_VERSION=0.4.25 .venv/bin/solc --bin --abi examples/defihacklabs/SpankChain.sol',
            source_bytes=source.stat().st_size,source_lines=len(source.read_text().splitlines()),
            full_source_estimated_tokens=(len(source.read_text())+3)//4,estimate_method='ceil(characters / 4)'),
        additional_findings=[dict(asdict(f),evaluation_label='UNLABELED_ADDITIONAL_FINDING') for f in findings if f.id!=finding.id],
        full_default_run=dict(total_findings=preflight['full_slither_total_findings'],
            detector_counts=preflight['full_slither_counts'],
            raw_full_run_available=False,
            note='Only counts and selected finding descriptions are preserved locally; do not invent missing full-run findings.'),
        existing_independent_labels=dict(path='examples/defihacklabs/SpankChain_fp_validation.md',
            note='Preserved in original document; disputed labels not converted. Baseline does not relabel additional findings.'))
    baseline=dict(schema_version=1,status='PILOT_ONLY_NOT_20_CASE_BASELINE',
        manifest_sha256=digest(BASE/'manifest.json'),
        metrics=dict(selected=1,compiled=1,analyzable=1,detected=1,missed=0,ambiguous=0,not_analyzable=0,
            recall=1.0,denominator=1,scope='Imported pilot only; not prospective 20-case recall or generalization evidence.'),
        records=[imported], llm_calls_made=0)
    (BASE/'slither_baseline.json').write_text(json.dumps(baseline,indent=2)+'\n')
    with (BASE/'slither_baseline.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    targets=dict(schema_version=1,manifest_sha256=digest(BASE/'manifest.json'),
        status='PILOT_ONLY_ALREADY_COMPLETED',new_paid_targets=0,technical_targets=[dict(
            target_id='case_001',incident_id='spankchain',slither_finding_id=finding.id,
            detector=finding.detector,function=finding.function_signature,
            source_path=str(source.relative_to(ROOT)),source_sha256=digest(source),compiler='0.4.25',
            finding=asdict(finding),already_completed_pilot=True)],
        payload_policy='Only Finding + production prepare_finding output may reach inference; never pass this file or the manifest as the model payload.')
    (BASE/'verification_targets.json').write_text(json.dumps(targets,indent=2)+'\n')
    (BASE/'manifest.md').write_text('''# Local DeFiHackLabs evaluation integration

Status: **INCOMPLETE_LOCAL_MATERIALS**. Requested: 20 incidents. Available: **1 pilot**.
The 20-case primary subset is **not frozen**. No prospective Slither evaluation began.
The pilot integration manifest is immutable for this snapshot; SHA-256 is recorded
in the baseline and targets. Selection bias from the already-known pilot is explicit.

| ID | Project | Date | Category | Function | Source | Compiler |
|---|---|---|---|---|---|---|
| spankchain | SpankChain | 2018-10-07 | reentrancy | LedgerChannel.LCOpenTimeout(bytes32) | local archived victim source | 0.4.25 |

The local search found the existing SpankChain source, ground-truth documentation,
preflight, detector-scoped Slither JSON, and independent validation. No local
DeFiHackLabs checkout/catalog or additional incident PoCs were located under
`/home/coca-cola/projects` or `/tmp`. The PoC path referenced in the documentation
is an upstream reference, not an available local file. Missing metadata stays null.
SmartBugs and CGT sources cannot establish new DeFiHackLabs incident provenance
and were not substituted. There are no fabricated excluded incidents or 19 placeholder
cases. No candidate replacements were possible from the local evidence.

## Imported baseline

| ID | Known category/function | Detector | Result |
|---|---|---|---|
| spankchain | reentrancy / LCOpenTimeout(bytes32) | reentrancy-eth | DETECTED |

Selected 1; previously compiled 1; previously analyzable 1; detected 1; missed 0;
ambiguous 0; not analyzable 0. Pilot-only recall = 1/1 = 100%; this is not a
20-case real-world recall estimate. No new compilation, Slither run or inference
was needed for integration. The original outputs are not overwritten.

The full-default run's 126 findings are supported by preflight counts, but its
complete raw output is not in the pilot directory. Available raw output has two
reentrancy-eth findings. The other raw finding is retained as
UNLABELED_ADDITIONAL_FINDING. Do not interpret missing full-run records as zero
additional warnings. Existing equality FP and disputed labels stay in their
original independent-validation document and are not merged into binary metrics.

## Reproduction and next step

Check all integration hashes without inference:

```bash
.venv/bin/python examples/defihacklabs/evaluation/check_integrity.py
```

`build_local_evaluation.py` creates this integration once and refuses overwrites.
19 additional locally documented incidents with faithful victim sources are needed
before a prospective 20-case manifest can be frozen and the remaining baseline run.
There are **zero new unpaid/completed-pilot-excluded LLM targets**. No new batch
verification command is applicable yet. To open the existing production workflow:

```bash
.venv/bin/streamlit run streamlit_app.py
```

The one technical target is retained for integration, marked already-completed.
Do not rerun it as a new cohort observation. Ground truth is stored in the manifest,
separate from the production payload. No batch inference runner is introduced in
this incomplete cohort. Do not send manifest, labels, incident notes or this report
to the model. Local sources may retain original names/comments as production source
data; no root-cause annotations were added to victim code.
''')
    protected=[p for p in PILOT.iterdir() if p.is_file()]
    (BASE/'integration_hashes.json').write_text(json.dumps({
        'protected_inputs':{str(p.relative_to(ROOT)):digest(p) for p in protected},
        'outputs':{name:digest(BASE/name) for name in names},
        'victim_snapshot_sha256':digest(folder/source.name)},indent=2)+'\n')
    print('Created pilot-only integration: 1 available case; 19-case shortfall; no inference.')


if __name__=='__main__': main()

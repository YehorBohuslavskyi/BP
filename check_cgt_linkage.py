"""Offline inventory, historical group baseline, and bounded unique-group rerun.

All five archived validation files are inventoried. Live reproduction is scoped
to all unique archive groups that agree with consolidated labels; no API calls are possible here.
"""
import argparse
import json
import os
import re
import subprocess
from collections import Counter
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

from check_cgt import write_csv, write_json
from context_audit.cgt_archive import audit_archive
from context_audit.cgt_dataset import load_cgt
from context_audit.cgt_findings import sha256
from context_audit.classification_metrics import classification_metrics
from context_audit.findings import parse_slither_findings

ROOT = Path(__file__).resolve().parent


def expression_keys(detector: dict) -> list[str]:
    return sorted(re.sub(r"\s+", "", e["name"]) for e in detector.get("elements", []) if e.get("type") == "node")


def run(root: Path, out: Path, reproduce: bool = True) -> dict:
    root = root.resolve()
    out.mkdir(parents=True, exist_ok=True)
    dataset = load_cgt(root)
    properties = Counter((a.dataset, a.property, a.swc, a.original_label) for a in dataset.assessments)
    property_rows = [{"dataset": key[0], "property": key[1], "swc": key[2], "property_holds": key[3], "count": n}
                     for key, n in sorted(properties.items(), key=lambda x: str(x[0]))]
    inventory = {
        "total_records": dataset.total_rows, "parsed_records": len(dataset.assessments),
        "labels": dict(Counter(a.original_label for a in dataset.assessments)),
        "unique_dataset_entries": len({(a.dataset, a.entry_id) for a in dataset.assessments}),
        "unique_source_fingerprints": len({a.raw['fp_sol'] for a in dataset.assessments if a.raw.get('fp_sol')}),
        "unique_source_contract_pairs": len({(a.raw['fp_sol'], a.contract_name) for a in dataset.assessments if a.raw.get('fp_sol') and a.contract_name}),
        "unique_chain_addresses": len({(a.raw['chain'], a.raw['addr']) for a in dataset.assessments if a.raw.get('addr')}),
        "unique_property_names": len({a.property for a in dataset.assessments}),
        "unique_dataset_properties": len({(a.dataset, a.property) for a in dataset.assessments}),
        "source_files_on_disk": len(list((root/'source').glob('*.sol'))),
        "source_availability": dict(Counter(a.source_status for a in dataset.assessments)),
        "issues": dict(Counter(i['kind'] for i in dataset.issues)),
    }
    records = audit_archive(root, dataset)
    baseline = classification_metrics([r['label'] for r in records], ['confirmed'] * len(records))
    metadata = {"csv_sha256": dataset.csv_sha256, "dataset_commit": None,
                "dataset_version_note": "Local data copy has no .git; pinned by content hashes, not parent repository commit",
                "slither_version": version('slither-analyzer'), "runner_sha256": sha256(Path(__file__)),
                "archive_parser_sha256": sha256(ROOT/'src/context_audit/cgt_archive.py'),
                "historical_slither_version": "not recorded in archived JSON",
                "live_scope": "all unique, CGT-consistent archive groups across five categories; exact expression reproduction only",
                "api_calls": 0}
    raw_dir = out/'raw'
    raw_dir.mkdir(exist_ok=True)
    live = []
    if reproduce:
        for record in records:
            item = {**record, "live_status": "not_attempted"}
            if record['issues']:
                live.append(item)
                continue
            source = Path(record['consolidated_source'])
            try:
                # Use an installed 0.4 compiler for this historical cohort.
                # Compiler still validates compatibility; do not rewrite pragmas.
                compiler = '0.4.25'
                env = {**os.environ, 'SOLC_VERSION': compiler}
                target = raw_dir/(source.stem+'.'+record['detector']+'.json')
                command = ['slither', str(source), '--detect', record['detector'], '--json', '-', '--fail-none']
                process = subprocess.run(command, capture_output=True, text=True, env=env, timeout=120)
                target.write_text(process.stdout)
                target.with_suffix('.stderr.txt').write_text(process.stderr)
                item.update(compiler_version=compiler, command=command, slither_json=str(target.resolve()))
                if process.returncode:
                    raise ValueError('Compilation/Slither failure: '+process.stderr[-1500:])
                raw = json.loads(process.stdout)
                findings = parse_slither_findings(raw)
                old_raw = json.loads(Path(record['raw_path']).read_text())['results']['detectors'][record['historical_indices'][0]]
                candidates = [(f,d) for f,d in zip(findings,raw['results']['detectors'])
                              if f.contract == record['contract'] and f.function_signature == record['function']
                              and f.detector == record['detector'] and expression_keys(d) == expression_keys(old_raw)]
                item['live_status'] = 'unique_expression_match' if len(candidates)==1 else 'unresolved_expression_match'
                item['live_matches'] = len(candidates)
                if len(candidates)==1:
                    f,d=candidates[0]
                    item.update(finding=asdict(f), slither_json_sha256=sha256(target),
                                expression_keys=expression_keys(d), source_sha256=sha256(source))
                    # Actual source excerpt for explicit semantic review, not inferred label expansion.
                    data=source.read_bytes()
                    item['function_source']=data[f.function_start:f.function_start+f.function_length].decode()
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                item.update(live_status='analysis_error', error=str(error))
            live.append(item)
            print(item['file'],item['contract'],item['live_status'],flush=True)
    summary = {"inventory": inventory, "historical_validation_rows": len(records),
               "historical_group_baseline": baseline,
               "historical_group_labels": dict(Counter(r['original_label'] for r in records)),
               "archive_linkage_issues": dict(Counter(i for r in records for i in r['issues'])),
               "unique_consistent_archive_groups": sum(not r['issues'] for r in records),
               "live_status": dict(Counter(r['live_status'] for r in live)),
               "note": "Historical metrics are file/contract/property-group judgments, not 419 individual warnings. Live matches still require semantic review."}
    write_json(out/'summary.json',summary)
    write_json(out/'metadata.json',metadata)
    write_json(out/'archive_links.json',records)
    write_json(out/'live_links.json',live)
    write_json(out/'tx_origin_links.json',[r for r in live if r['category']=='tx_result'])
    write_json(out/'errors.json',[r for r in records if r['issues']]+[r for r in live if r['live_status']=='analysis_error'])
    write_csv(out/'properties.csv',property_rows,['dataset','property','swc','property_holds','count'])
    write_csv(out/'findings.csv',records,['validation_file','row','file','contract','category','original_label',
                                       'historical_warning_count','status','issues','assessment_key','consolidated_label',
                                       'raw_sha256','source_sha256'])
    print(json.dumps(summary,indent=2))
    return summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-root',type=Path,default=ROOT/'datasets/cgt')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/cgt_linkage')
    args=parser.parse_args()
    run(args.dataset_root,args.output_dir)

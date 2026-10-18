"""Run and export the audited SmartBugs access-control baseline."""
import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
from dataclasses import asdict, replace
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from context_audit.dataset import load_smartbugs_curated
from context_audit.evaluation import (
    CATEGORY_DETECTOR_MAP, FUNCTION_SCOPE_DETECTORS,
    evaluate_ground_truth_detection, match_findings_to_ground_truth,
)
from context_audit.findings import parse_slither_findings

ROOT = Path(__file__).resolve().parent
CATEGORY = "access_control"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_batch(dataset_root: Path, output: Path, timeout: int = 120) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    raw = output / "raw"
    raw.mkdir(exist_ok=True)
    contracts = [replace(c, vulnerabilities=[v for v in c.vulnerabilities if v.category == CATEGORY])
                 for c in load_smartbugs_curated(dataset_root)
                 if any(v.category == CATEGORY for v in c.vulnerabilities)]
    audit_path = ROOT / "benchmarks/access_control_audit.json"
    audits = json.loads(audit_path.read_text()) if audit_path.exists() else []
    records, contract_records = [], []
    print(f"Selected contracts: {len(contracts)}", flush=True)
    for contract in contracts:
        info = {"contract": contract.name, "pragma": contract.pragma,
                "source_sha256": sha256(contract.path)}
        command = ["slither", str(contract.path), "--json", "-", "--fail-none"]
        info["command"] = command
        try:
            if not contract.pragma:
                raise ValueError("No compiler version in metadata")
            # solc-select supports a per-process version, avoiding global changes.
            env = {**os.environ, "SOLC_VERSION": contract.pragma}
            compiler = subprocess.run(["solc", "--version"], env=env, capture_output=True,
                                      text=True, check=True, timeout=timeout)
            info["compiler"] = compiler.stdout.strip()
            process = subprocess.run(command, env=env, capture_output=True,
                                     text=True, timeout=timeout)
            (raw / f"{contract.name}.json").write_text(process.stdout)
            (raw / f"{contract.name}.stderr.txt").write_text(process.stderr)
            info["raw_json_sha256"] = sha256(raw / f"{contract.name}.json")
            if process.returncode:
                raise ValueError(f"Slither exit {process.returncode}: {process.stderr[-2000:]}")
            findings = parse_slither_findings(json.loads(process.stdout))
            matches, unmatched = match_findings_to_ground_truth(contract, findings)
            results = evaluate_ground_truth_detection(contract, matches)
            info.update(status="ok", slither_findings_count=len(findings),
                        unmatched_findings_count=len(unmatched),
                        matches=[asdict(m) for m in matches])
            for result in results:
                record = {"contract": contract.name, "pragma": contract.pragma,
                          "source_sha256": info["source_sha256"], "status": "ok",
                          **asdict(result), "slither_findings_count": len(findings)}
                audit = next((a for a in audits if a["contract"] == contract.name
                              and a["category"] == result.category and a["lines"] == result.lines
                              and a["source_sha256"] == info["source_sha256"]
                              and a["slither_version"] == version("slither-analyzer")), None)
                record["manual_classification"] = (
                    audit["classification"] if audit and not result.detected else None)
                record["audit_note"] = audit["note"] if audit and not result.detected else None
                records.append(record)
                print(f"{contract.name} {result.lines}: "
                      f"{'DETECTED' if result.detected else 'MISSED'} "
                      f"{result.matched_detectors} {result.matching_methods}", flush=True)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            info.update(status="failed", error=str(error))
            # Failed analysis is neither a successful negative nor omitted from coverage.
            for vulnerability in contract.vulnerabilities:
                records.append({"contract": contract.name, "pragma": contract.pragma,
                                "source_sha256": info["source_sha256"], "status": "failed",
                                "category": vulnerability.category, "lines": vulnerability.lines,
                                "detected": None, "matched_detectors": [], "matching_methods": [],
                                "slither_findings_count": None, "manual_classification": None,
                                "audit_note": None})
            print(f"{contract.name}: FAILED: {error}", flush=True)
        contract_records.append(info)
    successful = sum(c["status"] == "ok" for c in contract_records)
    analyzed = [r for r in records if r["status"] == "ok"]
    detected = sum(r["detected"] for r in analyzed)
    summary = {"selected_contracts": len(contracts), "successfully_analyzed": successful,
               "failed_contracts": len(contracts) - successful,
               "ground_truth_total": len(records), "ground_truth_analyzed": len(analyzed),
               "ground_truth_unanalyzed": len(records) - len(analyzed),
               "detected": detected, "missed": len(analyzed) - detected,
               "recall": detected / len(records) if records and successful == len(contracts) else None,
               "recall_on_analyzed": detected / len(analyzed) if analyzed else None}
    report = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "category": CATEGORY, "python_version": platform.python_version(),
        "slither_version": version("slither-analyzer"), "solc_select_version": version("solc-select"),
        "metadata_sha256": sha256(dataset_root / "vulnerabilities.json"),
        "evaluation_sha256": sha256(ROOT / "src/context_audit/evaluation.py"),
        "findings_parser_sha256": sha256(ROOT / "src/context_audit/findings.py"),
        "runner_sha256": sha256(Path(__file__)),
        "category_detector_map": {k: sorted(v) for k, v in CATEGORY_DETECTOR_MAP.items()},
        "function_scope_detectors": sorted(FUNCTION_SCOPE_DETECTORS),
        "summary": summary, "vulnerabilities": records, "contracts": contract_records,
    }
    (output / "baseline.json").write_text(json.dumps(report, indent=2) + "\n")
    fields = ["contract", "pragma", "category", "lines", "status", "detected",
              "matched_detectors", "matching_methods", "slither_findings_count",
              "manual_classification", "audit_note", "source_sha256"]
    with (output / "baseline.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow({key: json.dumps(value) if isinstance(value, list) else value
                             for key, value in row.items()})
    print(json.dumps(summary, indent=2))
    print(f"Results: {output / 'baseline.json'} and baseline.csv")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=ROOT / "datasets/smartbugs-curated")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs/access-control-baseline")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    report = run_batch(args.dataset_root.resolve(), args.output_dir.resolve(), args.timeout)
    return int(report["summary"]["failed_contracts"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())

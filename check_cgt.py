"""Inventory CGT and evaluate an explicitly reviewed Slither candidate cohort.

Never infer finding labels from contract-property labels without review.
No API calls by default. --run-sample is capped at 20 findings; there is no
full paid run option. Missing data produces blocked evidence, not fake metrics.
"""
import argparse
import csv
import json
import os
import platform
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from context_audit.cgt_dataset import load_cgt
from context_audit.cgt_findings import load_reviewed_findings, sha256
from context_audit.classification_metrics import compare_verification

ROOT = Path(__file__).resolve().parent


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, default=str) + "\n")


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def run(root: Path, output: Path, manifest: Path | None = None, run_sample: int = 0) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    errors, rows, warnings = [], [], []
    summary = {"status": "blocked", "assessment_rows": None, "reviewed_eligible_findings": None,
               "sample_actual_tokens": None, "estimated_full_run_tokens": None,
               "baseline": None}
    metadata = {"date": datetime.now(timezone.utc).isoformat(), "dataset_url": "https://github.com/gsalzer/cgt",
                "dataset_commit": None, "python_version": platform.python_version(),
                "slither_version": version("slither-analyzer"), "schema": "CGT contract/property assessments",
                "inference_label_policy": "explicit reviewed finding link; never category-positive propagation",
                "runner_sha256": sha256(Path(__file__)), "api_calls_made": 0}
    try:
        dataset = load_cgt(root)
        metadata["csv_sha256"] = dataset.csv_sha256
        if (root / ".git").exists():
            process = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
            metadata["dataset_commit"] = process.stdout.strip() if process.returncode == 0 else None
        warnings.extend(i for i in dataset.issues if i["kind"] in {"source_not_provided", "source_missing"})
        errors.extend(i for i in dataset.issues if i["kind"] not in {"source_not_provided", "source_missing"})
        summary.update(status="inventory_only", assessment_rows=dataset.total_rows,
                       parsed_assessments=len(dataset.assessments),
                       invalid_rows=sum(i["kind"] == "invalid_row" for i in dataset.issues),
                       original_labels=dict(Counter(a.original_label for a in dataset.assessments)),
                       contributing_datasets=dict(Counter(a.dataset for a in dataset.assessments)),
                       source_status=dict(Counter(a.source_status for a in dataset.assessments)),
                       distinct_source_fingerprints=len({a.raw["fp_sol"] for a in dataset.assessments if a.raw.get("fp_sol")}),
                       tool_filter_supported=False, reviewed_eligible_findings=0)
        write_csv(output / "assessments.csv", [asdict(a) for a in dataset.assessments],
                  ["row_number", "dataset", "entry_id", "property", "original_label", "property_holds",
                   "source_path", "source_status", "contract_name", "swc", "dasp", "raw"])
        candidates = []
        if manifest:
            candidates, review_errors = load_reviewed_findings(dataset, manifest)
            errors.extend(review_errors)
            metadata["review_manifest_sha256"] = sha256(manifest)
        else:
            warnings.append({"kind": "review_required", "error": "CGT has no direct Slither finding labels; reviewed links are required"})
        summary["reviewed_eligible_findings"] = len(candidates)
        for c in candidates:
            rows.append({"review_id": c.review_id, "assessment_key": c.assessment.key,
                         "finding_id": c.finding.id, "detector": c.finding.detector,
                         "label": c.label, "source_sha256": c.source_sha256,
                         "compiler_version": c.compiler_version, "slither_version": c.slither_version})
        if candidates:
            summary["status"] = "reviewed_baseline"
            summary["baseline"] = compare_verification([c.label for c in candidates], ["confirmed"] * len(candidates))["slither_candidate_baseline"]
            if run_sample:
                from context_audit.cgt_sample import run_pilot
                summary["pilot"] = run_pilot(candidates, output / "pilot", run_sample)
                summary["sample_actual_tokens"] = summary["pilot"]["actual_usage"]
                summary["estimated_full_run_tokens"] = summary["pilot"]["projected_full_usage"]
                metadata["api_calls_made"] = summary["pilot"]["api_calls_attempted"]
        if errors:
            summary["has_errors"] = True
    except (OSError, ValueError) as error:
        errors.append({"kind": "blocked", "error": str(error)})
        summary["status"] = "blocked"
    write_json(output / "summary.json", summary)
    write_json(output / "metadata.json", metadata)
    write_json(output / "errors.json", errors)
    write_json(output / "warnings.json", warnings)
    write_csv(output / "findings.csv", rows, ["review_id", "assessment_key", "finding_id", "detector", "label",
                                              "source_sha256", "compiler_version", "slither_version"])
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=ROOT / "datasets/cgt")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/cgt_slither_baseline")
    parser.add_argument("--review-manifest", type=Path)
    parser.add_argument("--run-sample", type=int, default=0, help="Explicit paid pilot size, maximum 20")
    args = parser.parse_args()
    if not 0 <= args.run_sample <= 20:
        parser.error("Pilot size must be between 0 and 20. Full paid runs require a separate decision.")
    summary = run(args.dataset_root.resolve(), args.output_dir.resolve(), args.review_manifest, args.run_sample)
    print(json.dumps(summary, indent=2))
    return int(summary["status"] == "blocked" or summary.get("has_errors", False))


if __name__ == "__main__":
    raise SystemExit(main())

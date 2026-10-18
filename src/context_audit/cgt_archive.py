"""Audit historical Slither validation groups distributed inside CGT.

These labels are upstream group judgments, not automatically consolidated CGT
labels or labels for every warning in a group. Never expand one label to many.
"""
import csv
import json
from pathlib import Path

from context_audit.cgt_dataset import CGTDataset
from context_audit.cgt_findings import sha256
from context_audit.findings import parse_slither_findings

# Exact detector names observed in the supplied historical outputs. This table
# retrieves candidates only; it does not assert detector/property equivalence.
ARCHIVE_RULES = {
    "tx_result": "tx-origin", "selfdestruct_result": "suicidal",
    "lowlevelcall_result": "unchecked-lowlevel", "reentrancy": "reentrancy-eth",
    "unexpectedrevert_result": "calls-loop",
}


def audit_archive(root: Path, dataset: CGTDataset) -> list[dict]:
    """Audit archived Slither groups against consolidated assessments without inventing links."""
    base = root / "construction/originalSets/Doublade"
    with (base / "address.csv").open() as stream:
        addresses = {r["file"]: r["address"].removesuffix(".sol").lower()
                     for r in csv.DictReader(stream, delimiter=";")}
    assessments = {}
    for a in dataset.assessments:
        assessments.setdefault(a.key, []).append(a)
    records = []
    for path in sorted((base / "validation_results").glob("slither_*.csv")):
        category = path.stem.removeprefix("slither_")
        with path.open() as stream:
            for line, row in enumerate(csv.DictReader(stream, delimiter=";"), 2):
                record = {"validation_file": path.name, "row": line, "category": category,
                          "original_label": row.get("classification"), "file": row.get("file"),
                          "contract": row.get("contractname"), "issues": []}
                try:
                    filename = row["file"]
                    if Path(filename).name != filename or not filename.endswith(".json"):
                        raise ValueError("Invalid archive filename")
                    if row["classification"] not in {"TP", "FP"}:
                        raise ValueError("Unsupported original label")
                    source_name = Path(filename).with_suffix(".sol").name
                    source = base / "source_code" / source_name
                    raw_path = base / "outputs/slither" / filename
                    raw = json.loads(raw_path.read_text())
                    parsed = parse_slither_findings(raw)
                    indices = [i for i, f in enumerate(parsed)
                               if f.detector == ARCHIVE_RULES[category] and f.contract == row["contractname"]]
                    key = ("Doublade", addresses[source_name] + "-" + row["contractname"] + "-" + category, category)
                    matches = assessments.get(key, [])
                    record.update(label=row["classification"] == "TP", assessment_key=key,
                                  historical_warning_count=len(indices), historical_indices=indices,
                                  original_source=str(source), source_sha256=sha256(source),
                                  raw_path=str(raw_path), raw_sha256=sha256(raw_path),
                                  validation_sha256=sha256(path))
                    if len(indices) != 1:
                        record["issues"].append("ambiguous_warning_group" if indices else "no_archived_warning")
                    if len(matches) != 1:
                        record["issues"].append("no_unique_consolidated_assessment")
                    else:
                        a = matches[0]
                        record.update(consolidated_label=a.property_holds, consolidated_source=str(a.source_path),
                                      consolidated_source_sha256=sha256(a.source_path) if a.source_status == "available" else None)
                        if a.property_holds != record["label"]:
                            record["issues"].append("label_conflict")
                        if a.source_status != "available":
                            record["issues"].append("source_unavailable")
                    if len(indices) == 1:
                        f = parsed[indices[0]]
                        record.update(function=f.function_signature, detector=f.detector, historical_lines=f.lines)
                    record["status"] = "needs_source_and_semantic_review" if not record["issues"] else "unresolved"
                except (KeyError, ValueError, OSError) as error:
                    record["status"] = "unresolved"
                    record["issues"].append(str(error))
                records.append(record)
    return records

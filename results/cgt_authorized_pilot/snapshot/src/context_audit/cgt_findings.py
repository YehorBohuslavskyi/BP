"""Explicit human-reviewed links from CGT assessments to exact Slither findings.

A positive contract-property label alone must never label every warning true.
Review metadata stays outside inference and must be backed by pinned artifacts.
"""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from context_audit.cgt_dataset import CGTDataset, CGTAssessment
from context_audit.findings import Finding, parse_slither_findings


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class ReviewedFinding:
    review_id: str
    assessment: CGTAssessment
    finding: Finding
    label: bool
    compiler_version: str
    source_sha256: str
    slither_version: str


def load_reviewed_findings(dataset: CGTDataset, manifest: Path) -> tuple[list[ReviewedFinding], list[dict]]:
    rows = json.loads(manifest.read_text())
    if not isinstance(rows, list):
        raise ValueError("Reviewed-finding manifest must be a JSON array")
    accepted, errors = [], []
    seen = set()
    review_ids = set()
    for index, row in enumerate(rows):
        try:
            required = {"review_id", "assessment_key", "review_status", "reviewer", "rationale",
                        "property_is_weakness", "label", "source_sha256", "slither_json", "slither_json_sha256",
                        "finding_id", "compiler_version", "slither_version", "leakage_reviewed"}
            if not isinstance(row, dict) or not required.issubset(row):
                raise ValueError("Missing required review fields")
            if not isinstance(row["review_id"], str) or not row["review_id"] or row["review_id"] in review_ids:
                raise ValueError("Missing or duplicate review_id")
            if row["review_status"] != "accepted" or row["property_is_weakness"] is not True:
                raise ValueError("Requires accepted finding-level review and validated weakness semantics")
            if row["leakage_reviewed"] is not True or not row["reviewer"] or not row["rationale"]:
                raise ValueError("Review provenance/leakage check missing")
            assessments = [a for a in dataset.assessments if list(a.key) == row["assessment_key"]]
            if len(assessments) != 1:
                raise ValueError("Assessment missing or duplicate/ambiguous")
            assessment = assessments[0]
            if type(row["label"]) is not bool or row["label"] != assessment.property_holds:
                raise ValueError("Label disagrees with reviewed weakness assessment")
            source = assessment.source_path
            if source is None or assessment.source_status != "available":
                raise ValueError("Source unavailable")
            if sha256(source) != row["source_sha256"]:
                raise ValueError("Source SHA256 mismatch")
            artifact = (manifest.parent / row["slither_json"]).resolve()
            if sha256(artifact) != row["slither_json_sha256"]:
                raise ValueError("Slither JSON SHA256 mismatch")
            findings = [f for f in parse_slither_findings(json.loads(artifact.read_text())) if f.id == row["finding_id"]]
            if len(findings) != 1:
                raise ValueError("Finding ID missing or ambiguous")
            finding = findings[0]
            if not finding.contract or not finding.function_signature:
                raise ValueError("Finding has no resolvable contract/function")
            if assessment.contract_name and finding.contract != assessment.contract_name:
                raise ValueError("Finding belongs to another contract")
            if not finding.file or Path(finding.file).resolve() != source.resolve():
                raise ValueError("Finding source identity missing or mismatched")
            if not row["compiler_version"] or not row["slither_version"]:
                raise ValueError("Compiler/Slither version missing")
            identity = (row["source_sha256"], finding.detector, finding.contract,
                        finding.function_signature, finding.function_start, finding.function_length,
                        tuple(finding.lines))
            if identity in seen:
                raise ValueError("Duplicate candidate across CGT assessments")
            seen.add(identity)
            review_ids.add(row["review_id"])
            accepted.append(ReviewedFinding(row["review_id"], assessment, finding, row["label"],
                                            row["compiler_version"], row["source_sha256"], row["slither_version"]))
        except (ValueError, KeyError, TypeError, OSError) as error:
            errors.append({"manifest_index": index, "error": str(error)})
    return accepted, errors

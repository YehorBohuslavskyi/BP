from dataclasses import dataclass, field
from pathlib import Path

from context_audit.dataset import DatasetContract
from context_audit.findings import Finding


# Validated on the access-control subset; not a general semantic equivalence.
CATEGORY_DETECTOR_MAP = {
    "access_control": {
        "controlled-delegatecall", "controlled-array-length", "suicidal",
        "tautology", "tx-origin", "unprotected-upgrade", "protected-vars",
    },
}

# mapping_write: array expansion at line 17 enables the write at GT line 20.
# Do not extend this to unrelated statements reported by other detectors.
FUNCTION_SCOPE_DETECTORS = {"controlled-array-length"}


@dataclass
class EvaluationMatch:
    ground_truth_category: str
    ground_truth_lines: list[int]
    detector: str
    finding_lines: list[int]
    matched_lines: list[int]
    matching_method: str = "exact_line"
    finding_id: str = ""


@dataclass
class GroundTruthResult:
    category: str
    lines: list[int]
    detected: bool
    matched_detectors: list[str]
    matching_methods: list[str] = field(default_factory=list)


def _source_range_to_lines(
    contract: DatasetContract, start: int | None, length: int | None,
) -> list[int]:
    """Decode a half-open Solidity byte range, including old solc JSON."""
    if start is None or length is None or start < 0 or length <= 0:
        return []
    if not contract.path.is_file():
        return []
    source = contract.path.read_bytes()
    end = start + length
    if end > len(source):
        return []
    first = source[:start].count(b"\n") + 1
    last = source[:end - 1].count(b"\n") + 1
    return list(range(first, last + 1))


def _same_file(contract: DatasetContract, filename: str | None) -> bool:
    # Old solc 0.4.0/0.4.9 JSON omits filenames. This fallback is valid for
    # the current single-source inputs, not arbitrary multi-file projects.
    return not filename or Path(filename).resolve() == contract.path.resolve()


def _location_lines(contract: DatasetContract, mappings: list[dict]) -> list[int]:
    lines: set[int] = set()
    for mapping in mappings:
        filename = mapping.get("filename_absolute") or mapping.get("filename_relative")
        if not _same_file(contract, filename):
            continue
        lines.update(mapping.get("lines") or _source_range_to_lines(
            contract, mapping.get("start"), mapping.get("length"),
        ))
    return sorted(lines)


def _get_exact_finding_lines(contract: DatasetContract, finding: Finding) -> list[int]:
    if finding.locations is not None:
        # Reconstruct the selected node itself, never its enclosing function.
        return _location_lines(contract, finding.locations)
    if not _same_file(contract, finding.file):
        return []
    # Compatibility with legacy callers that supply only a function range.
    return finding.lines or _source_range_to_lines(
        contract, finding.function_start, finding.function_length,
    )


def _get_function_lines(contract: DatasetContract, finding: Finding) -> list[int]:
    if finding.locations is not None:
        return _location_lines(contract, finding.function_locations)
    if not _same_file(contract, finding.file):
        return []
    return _source_range_to_lines(contract, finding.function_start, finding.function_length)


def match_findings_to_ground_truth(
    contract: DatasetContract, findings: list[Finding],
) -> tuple[list[EvaluationMatch], list[Finding]]:
    matches = []
    unmatched = []
    for finding in findings:
        matched = False
        exact = set(_get_exact_finding_lines(contract, finding))
        scope = set(_get_function_lines(contract, finding))
        for vulnerability in contract.vulnerabilities:
            if finding.detector not in CATEGORY_DETECTOR_MAP.get(vulnerability.category, set()):
                continue
            overlap = exact.intersection(vulnerability.lines)
            method = "exact_line"
            if not overlap and finding.detector in FUNCTION_SCOPE_DETECTORS:
                overlap = scope.intersection(vulnerability.lines)
                method = "function_scope"
            if not overlap:
                continue
            matches.append(EvaluationMatch(
                ground_truth_category=vulnerability.category,
                ground_truth_lines=sorted(vulnerability.lines),
                detector=finding.detector,
                finding_lines=sorted(exact),
                matched_lines=sorted(overlap),
                matching_method=method,
                finding_id=finding.id,
            ))
            matched = True
        if not matched:
            unmatched.append(finding)
    return matches, unmatched


def evaluate_ground_truth_detection(
    contract: DatasetContract, matches: list[EvaluationMatch],
) -> list[GroundTruthResult]:
    results = []
    for vulnerability in contract.vulnerabilities:
        # Match the complete annotation, not an overlap with another GT item.
        relevant = [m for m in matches
                    if m.ground_truth_category == vulnerability.category
                    and set(m.ground_truth_lines) == set(vulnerability.lines)]
        results.append(GroundTruthResult(
            category=vulnerability.category,
            lines=vulnerability.lines,
            detected=bool(relevant),
            matched_detectors=sorted({m.detector for m in relevant}),
            matching_methods=sorted({m.matching_method for m in relevant}) or ["none"],
        ))
    return results


def summarize_ground_truth_detection(results: list[GroundTruthResult]) -> dict:
    total = len(results)
    detected = sum(r.detected for r in results)
    return {"ground_truth_total": total, "detected": detected,
            "missed": total - detected, "recall": detected / total if total else 0.0}

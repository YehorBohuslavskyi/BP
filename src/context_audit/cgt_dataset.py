"""CGT contract/property assessments, not analyzer findings.

Schema: https://github.com/gsalzer/cgt#the-consolidated-data
Labels retain property_holds semantics; True is not universally a vulnerability.
"""
import csv
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED = {"dataset", "id", "property", "property_holds"}
FINGERPRINTS = ("fp_sol", "fp_sol2", "fp_bytecode", "fp_runtime")


@dataclass
class CGTAssessment:
    """One original contract/property assessment with unmodified label provenance."""
    row_number: int
    dataset: str
    entry_id: str
    property: str
    original_label: str
    property_holds: bool
    source_path: Path | None
    source_status: str
    contract_name: str | None
    swc: int | None
    dasp: int | None
    raw: dict[str, str]

    @property
    def key(self) -> tuple[str, str, str]:
        """Return the dataset-qualified assessment identity."""
        return self.dataset, self.entry_id, self.property


@dataclass
class CGTDataset:
    """Parsed assessments and explicit inventory or validation issues."""
    assessments: list[CGTAssessment] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    total_rows: int = 0
    csv_sha256: str = ""

    def filter_tool(self, tool: str) -> list[CGTAssessment]:
        """Reject tool filtering because CGT dataset names identify provenance."""
        raise ValueError(f"Cannot filter CGT by tool {tool!r}: dataset denotes provenance, not an analyzer")


def _taxonomy(value: str, field_name: str) -> int | None:
    """Validate a nonempty taxonomy identifier against the supported numeric range."""
    if not value:
        return None
    number = int(value)
    allowed = set(range(100, 137)) | set(range(995, 1000)) if field_name == "swc" else set(range(1, 10))
    if number not in allowed:
        raise ValueError(f"Unsupported {field_name}: {value}")
    return number


def load_cgt(root: Path) -> CGTDataset:
    """Load local semicolon-separated assessments, preserving invalid-row diagnostics."""
    root = root.resolve()
    path = root / "consolidated.csv"
    result = CGTDataset(csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    seen: dict[tuple[str, str, str], list[CGTAssessment]] = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("CGT header must contain: " + ", ".join(sorted(REQUIRED)))
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Duplicate CGT header columns")
        for row_number, raw in enumerate(reader, 2):
            result.total_rows += 1
            try:
                if None in raw or any(v is None for v in raw.values()):
                    raise ValueError("CSV field count differs from header")
                if any(not raw[k].strip() for k in REQUIRED):
                    raise ValueError("Empty required field")
                if raw["property_holds"] not in {"t", "f"}:
                    raise ValueError("Unsupported property_holds; expected t or f")
                for key in FINGERPRINTS:
                    if raw.get(key) and not re.fullmatch(r"[0-9a-fA-F]{32}", raw[key]):
                        raise ValueError(f"Invalid MD5 fingerprint: {key}")
                source = root / "source" / (raw["fp_sol"] + ".sol") if raw.get("fp_sol") else None
                if source is not None and not source.resolve().is_relative_to(root):
                    raise ValueError("Source path escapes dataset root")
                status = "available" if source and source.is_file() else "missing" if source else "not_provided"
                assessment = CGTAssessment(
                    row_number, raw["dataset"], raw["id"], raw["property"], raw["property_holds"],
                    raw["property_holds"] == "t", source, status, raw.get("contractname") or None,
                    _taxonomy(raw.get("swc", ""), "swc"), _taxonomy(raw.get("dasp", ""), "dasp"), raw,
                )
                previous = seen.setdefault(assessment.key, [])
                if previous:
                    kind = "conflicting_label" if any(a.property_holds != assessment.property_holds for a in previous) else "duplicate_key"
                    result.issues.append({"row": row_number, "kind": kind, "key": assessment.key,
                                          "previous_rows": [a.row_number for a in previous]})
                previous.append(assessment)
                result.assessments.append(assessment)
                if status != "available":
                    result.issues.append({"row": row_number, "kind": "source_" + status})
            except (ValueError, KeyError) as error:
                result.issues.append({"row": row_number, "kind": "invalid_row", "error": str(error), "raw": raw})
    return result

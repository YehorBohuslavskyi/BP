"""Load SmartBugs Curated contract annotations without inferring warning labels."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GroundTruthVulnerability:
    """One annotated vulnerability category and its source lines."""
    category: str
    lines: list[int]


@dataclass
class DatasetContract:
    """A source contract and the benchmark annotations associated with it."""
    name: str
    path: Path
    pragma: str | None
    vulnerabilities: list[GroundTruthVulnerability]


def load_smartbugs_curated(
    dataset_root: Path,
) -> list[DatasetContract]:
    """Load contract metadata and preserve each ground-truth annotation separately."""
    metadata_path = dataset_root / "vulnerabilities.json"

    if not metadata_path.is_file():
        raise ValueError(
            f"SmartBugs vulnerabilities.json not found: {metadata_path}"
        )

    with metadata_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    contracts = []

    for item in raw_data:
        vulnerabilities = []

        for vulnerability in item.get("vulnerabilities", []):
            vulnerabilities.append(
                GroundTruthVulnerability(
                    category=vulnerability["category"],
                    lines=vulnerability.get("lines", []),
                )
            )

        contract = DatasetContract(
            name=item["name"],
            path=dataset_root / item["path"],
            pragma=item.get("pragma"),
            vulnerabilities=vulnerabilities,
        )

        contracts.append(contract)

    return contracts

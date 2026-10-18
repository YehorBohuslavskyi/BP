"""Reusable offline evaluation reports for CLI inspection of saved Slither JSON."""
import json
from dataclasses import asdict
from pathlib import Path

from context_audit.dataset import load_smartbugs_curated
from context_audit.evaluation import (
    evaluate_ground_truth_detection,
    match_findings_to_ground_truth,
    summarize_ground_truth_detection,
)
from context_audit.findings import parse_slither_findings


def evaluate_saved_contract(dataset_root: Path, contract_name: str, artifact: Path) -> dict:
    """Evaluate saved warnings for exactly one named SmartBugs contract."""
    contracts = [contract for contract in load_smartbugs_curated(dataset_root)
                 if contract.name == contract_name]
    if len(contracts) != 1:
        raise ValueError(f"Expected one contract named {contract_name!r}; found {len(contracts)}")
    contract = contracts[0]
    findings = parse_slither_findings(json.loads(artifact.read_text(encoding="utf-8")))
    matches, unmatched = match_findings_to_ground_truth(contract, findings)
    outcomes = evaluate_ground_truth_detection(contract, matches)
    return {
        "contract": contract.name,
        "ground_truth": [asdict(item) for item in contract.vulnerabilities],
        "matches": [asdict(item) for item in matches],
        "unmatched": [asdict(item) for item in unmatched],
        "outcomes": [asdict(item) for item in outcomes],
        "summary": summarize_ground_truth_detection(outcomes),
    }

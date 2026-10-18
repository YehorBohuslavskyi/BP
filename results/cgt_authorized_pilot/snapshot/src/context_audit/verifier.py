from pathlib import Path

from slither.slither import Slither

from context_audit.catalog import FragmentCatalog
from context_audit.context import build_function_context
from context_audit.findings import Finding
from context_audit.indexer import find_function
from context_audit.llm import analyze
from context_audit.payload import (
    build_initial_payload,
    resolve_context_request,
)

def summarize_verification(result: dict) -> dict:
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0

    requested_ids = set()

    for round_info in result["rounds"]:
        round_result = round_info["result"]

        usage = round_result.get("usage")

        if usage is not None:
            total_input_tokens += usage.get("input_tokens", 0)
            total_output_tokens += usage.get("output_tokens", 0)
            total_tokens += usage.get("total_tokens", 0)

        assessment = round_result["assessment"]

        for fragment_id in assessment.get("requested_ids", []):
            requested_ids.add(fragment_id)

    return {
        "finding_id": result["finding"]["id"],
        "detector": result["finding"]["detector"],
        "contract": result["finding"]["contract"],
        "function": result["finding"]["function"],
        "verdict": result["assessment"]["verdict"],
        "rounds": result["round_count"],
        "requested_fragments": len(requested_ids),
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
    }   


def prepare_finding(
    source_path: Path,
    project_root: Path,
    finding: Finding,
) -> tuple[dict, FragmentCatalog]:
    slither = Slither(str(source_path))

    catalog = FragmentCatalog(project_root)

    if finding.contract is None:
        raise ValueError(
            "Finding is not associated with a contract."
        )

    if finding.function_signature is None:
        raise ValueError(
            "Finding is not associated with a function."
        )

    function = find_function(
        slither,
        finding.contract,
        finding.function_signature,
        finding.file,
    )

    if function is None:
        raise ValueError(
            "Could not match finding to a Solidity function: "
            f"{finding.contract}.{finding.function_signature}"
        )

    context = build_function_context(
        function,
        catalog,
    )

    initial_payload = build_initial_payload(
        context,
        catalog,
        finding,
    )

    return initial_payload, catalog


def verify_finding(
    source_path: Path,
    project_root: Path,
    finding: Finding,
    max_rounds: int = 4,
) -> dict:
    initial_payload, catalog = prepare_finding(source_path, project_root, finding)
    return verify_prepared_finding(finding, initial_payload, catalog, max_rounds)


def verify_prepared_finding(
    finding: Finding,
    initial_payload: dict,
    catalog: FragmentCatalog,
    max_rounds: int = 4,
    analyze_fn=None,
) -> dict:
    """Verify prebuilt context, allowing dry preparation and an inference adapter."""
    if max_rounds < 1:
        raise ValueError("max_rounds must be positive")
    analyze_fn = analyze_fn or analyze
    provided_context = []

    rounds = []

    for round_number in range(1, max_rounds + 1):
        result = analyze_fn(
            initial_payload,
            provided_context,
        )

        rounds.append({
            "round": round_number,
            "result": result,
        })

        assessment = result["assessment"]

        if assessment["action"] == "final":
            return {
                "finding": {
                    "id": finding.id,
                    "detector": finding.detector,
                    "contract": finding.contract,
                    "function": finding.function_signature,
                    "file": finding.file,
                },
                "assessment": assessment,
                "rounds": rounds,
                "round_count": round_number,
                "provided_context": provided_context,
            }

        requested_ids = assessment["requested_ids"]

        resolved = resolve_context_request(
            requested_ids,
            initial_payload,
            catalog,
        )

        if resolved["errors"]:
            raise ValueError(
                f"Context resolution failed: {resolved['errors']}"
            )

        provided_context.extend(
            resolved["fragments"]
        )

    return {
        "finding": {
            "id": finding.id,
            "detector": finding.detector,
            "contract": finding.contract,
            "function": finding.function_signature,
            "file": finding.file,
        },
        "assessment": {
            "action": "final",
            "requested_ids": [],
            "verdict": "inconclusive",
            "explanation": (
                f"Maximum context rounds ({max_rounds}) reached "
                "without a final assessment."
            ),
            "evidence_ids": [],
        },
        "rounds": rounds,
        "round_count": max_rounds,
        "provided_context": provided_context,
    }   
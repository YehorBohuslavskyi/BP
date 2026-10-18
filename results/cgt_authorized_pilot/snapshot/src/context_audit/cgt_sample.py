"""Bounded paid pilot. Call only after a reviewed cohort is available."""
import csv
import hashlib
import json
import os
from pathlib import Path

from context_audit.cgt_findings import ReviewedFinding
from context_audit.cgt_inference import BlindAnalyzer, estimated_tokens, strip_comments
from context_audit.classification_metrics import compare_verification, context_efficiency


def choose_sample(candidates: list[ReviewedFinding], size: int) -> list[ReviewedFinding]:
    if not 1 <= size <= 20:
        raise ValueError("Pilot size must be 1..20")
    # Balance labels while cycling detector families, preventing an alphabetical
    # sample containing only unchecked-lowlevel positives.
    groups = {}
    for label in (True, False):
        by_detector = {}
        for candidate in sorted(candidates, key=lambda c: c.review_id):
            if candidate.label == label:
                by_detector.setdefault(candidate.finding.detector, []).append(candidate)
        groups[label] = [by_detector[key] for key in sorted(by_detector)]
    selected = []
    while len(selected) < size and any(groups.values()):
        for label in (True, False):
            if groups[label] and len(selected) < size:
                group = groups[label].pop(0)
                selected.append(group.pop(0))
                if group:
                    groups[label].append(group)

    return selected


def run_pilot(candidates: list[ReviewedFinding], output: Path, size: int) -> dict:
    from context_audit.llm import analyze, SYSTEM_PROMPT
    from context_audit.verifier import prepare_finding, verify_prepared_finding
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_MODEL"):
        raise ValueError("Paid pilot requires OPENAI_API_KEY and OPENAI_MODEL; no request sent")
    if output.exists():
        raise ValueError("Pilot output already exists; refusing to overwrite or repeat paid requests")
    selected = choose_sample(candidates, size)
    output.mkdir(parents=True)
    config = {"model": os.environ["OPENAI_MODEL"], "max_rounds": 4,
              "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
              "candidate_ids": [c.review_id for c in selected],
              "selection": "alternating labels and cycling sorted detector families, then sorted IDs; sample-only comparison",
              "context_policy": "existing selective context; comment stripping and neutral ID/file aliases",
              "token_estimator": "ceil(characters / 4), planning heuristic, not model tokenizer"}
    (output / "config.json").write_text(json.dumps(config, indent=2))
    results = []
    calls = 0
    actual = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    unknown_usage_calls = 0
    for candidate in selected:
        usage = {k: 0 for k in actual}
        rounds = []
        previous_compiler = os.environ.get("SOLC_VERSION")
        record = {"review_id": candidate.review_id, "label": candidate.label, "verdict": "error"}
        phase = "source_or_function_resolution"
        try:
            os.environ["SOLC_VERSION"] = candidate.compiler_version
            payload, catalog = prepare_finding(candidate.assessment.source_path,
                                               candidate.assessment.source_path.parent, candidate.finding)
            def measured_analyze(initial, provided):
                nonlocal calls, unknown_usage_calls
                calls += 1
                try:
                    response = analyze(initial, provided)
                except Exception:
                    unknown_usage_calls += 1
                    raise
                rounds.append(response)
                if response.get("usage") is None:
                    unknown_usage_calls += 1
                for key in usage:
                    value = (response.get("usage") or {}).get(key, 0)
                    usage[key] += value
                    actual[key] += value
                return response
            adapter = BlindAnalyzer(payload, measured_analyze)
            initial, _ = adapter.payload(payload, [])
            (output / f"payload_{len(results):03}.json").write_text(json.dumps(initial, indent=2))
            phase = "inference_or_context_resolution"
            result = verify_prepared_finding(candidate.finding, payload, catalog, 4, adapter)
            record.update(verdict=result["assessment"]["verdict"], result=result)
            full = strip_comments(candidate.assessment.source_path.read_text())
            record["context_efficiency"] = context_efficiency(
                estimated_tokens(full), estimated_tokens(initial["target"]["source"]),
                estimated_tokens(json.dumps(initial)), usage["input_tokens"])
            record["source_bytes"] = candidate.assessment.source_path.stat().st_size
            record["source_LOC"] = len(full.splitlines())
            record["solidity_files"] = 1
            record["context_requests"] = sum(r["assessment"]["action"] == "request_context" for r in rounds)
            record["requested_fragments"] = len({x for r in rounds for x in r["assessment"]["requested_ids"]})
        except Exception as error:
            record["error"] = {"phase": phase, "type": type(error).__name__, "message": str(error)}
        finally:
            if previous_compiler is None:
                os.environ.pop("SOLC_VERSION", None)
            else:
                os.environ["SOLC_VERSION"] = previous_compiler
        assessment = record.get("result", {}).get("assessment", {})
        record["explanation"] = assessment.get("explanation")
        record["evidence_ids"] = assessment.get("evidence_ids", [])
        record["api_rounds"] = rounds
        record["requested_fragment_ids"] = sorted({
            key for response in rounds for key in response["assessment"]["requested_ids"]})
        record["requested_fragments"] = len(record["requested_fragment_ids"])
        record.update(usage)
        record["actual_usage"] = usage
        record["round_count"] = len(rounds)
        results.append(record)
        # Save progress after every candidate, including failures and partial usage.
        (output / "findings.json").write_text(json.dumps(results, indent=2))
    completed = sum(r["verdict"] != "error" for r in results)
    projection = None
    if completed == len(selected) and not unknown_usage_calls and completed:
        projection = {k: round(v * len(candidates) / completed) for k, v in actual.items()}
    summary = {"eligible_findings": len(candidates), "sample_size": len(selected),
               "sample_completed": completed, "api_calls_attempted": calls,
               "average_rounds": sum(r["round_count"] for r in results) / len(results) if results else None,
               "requested_fragments": sum(r["requested_fragments"] for r in results),
               "source_function_resolution_failures": sum(
                   r.get("error", {}).get("phase") == "source_or_function_resolution" for r in results),
               "calls_with_unknown_usage": unknown_usage_calls, "actual_usage": actual,
               "projected_full_usage": projection,
               "projected_full_calls": calls * len(candidates) / completed if projection else None,
               "full_run_request_cap": 4 * len(candidates),
               "full_run_output_token_cap": 16000 * len(candidates),
               "comparison": compare_verification([r["label"] for r in results], [r["verdict"] for r in results])}
    with (output / "findings.csv").open("w", newline="") as stream:
        fields = ["review_id", "label", "verdict", "round_count", "actual_usage", "context_efficiency", "error",
                  "explanation", "evidence_ids", "requested_fragment_ids", "requested_fragments",
                  "input_tokens", "output_tokens", "total_tokens"]
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            writer.writerow({key: json.dumps(value) if isinstance(value, (dict, list)) else value
                             for key, value in row.items() if key in fields})
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    (output / "errors.json").write_text(json.dumps([r for r in results if "error" in r], indent=2))
    return summary

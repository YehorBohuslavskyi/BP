"""Finding classification metrics on a fixed, explicitly labeled candidate cohort."""
from collections import Counter

VERDICTS = {"confirmed": True, "false_positive": False, "inconclusive": None, "error": None}


def divide(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def classification_metrics(labels: list[bool], verdicts: list[str]) -> dict:
    if len(labels) != len(verdicts) or any(type(label) is not bool for label in labels):
        raise ValueError("One boolean label is required for every verdict")
    if any(v not in VERDICTS for v in verdicts):
        raise ValueError("Unknown verdict")
    counts = Counter(verdicts)
    tp = fp = tn = fn = 0
    for label, verdict in zip(labels, verdicts):
        prediction = VERDICTS[verdict]
        if prediction is None:
            continue
        tp += label and prediction
        fp += not label and prediction
        tn += not label and not prediction
        fn += label and not prediction
    decided = tp + fp + tn + fn
    return {"total": len(labels), "decided": decided, "TP": tp, "FP": fp, "TN": tn, "FN": fn,
            "precision": divide(tp, tp + fp), "recall": divide(tp, tp + fn),
            "f1": divide(2 * tp, 2 * tp + fp + fn), "false_positive_rate": divide(fp, fp + tn),
            "false_discovery_rate": divide(fp, tp + fp),
            "coverage": divide(decided, len(labels)),
            "abstention_rate": divide(counts["inconclusive"], len(labels)),
            "error_rate": divide(counts["error"], len(labels)),
            "verdict_counts": {v: counts[v] for v in VERDICTS}}


def compare_verification(labels: list[bool], verdicts: list[str]) -> dict:
    baseline = classification_metrics(labels, ["confirmed"] * len(labels))
    verified = classification_metrics(labels, verdicts)
    negatives = sum(not label for label in labels)
    rejected_negatives = sum(not label and v == "false_positive" for label, v in zip(labels, verdicts))
    retained_negatives = sum(not label and v != "false_positive" for label, v in zip(labels, verdicts))
    return {"slither_candidate_baseline": baseline, "llm_non_abstained": verified,
            # Abstentions/errors are retained in the practical filtering policy.
            # Removing them from FP_llm would spuriously reward non-decisions.
            "conservative_retained_FP": retained_negatives,
            "false_positive_reduction": divide(rejected_negatives, negatives),
            "true_findings_incorrectly_filtered": verified["FN"],
            "true_finding_rejection_rate": divide(verified["FN"], sum(labels))}


def context_efficiency(full_source_tokens: int, initial_source_tokens: int,
                       initial_payload_tokens: int, cumulative_input_tokens: int) -> dict:
    if min(full_source_tokens, initial_source_tokens, initial_payload_tokens, cumulative_input_tokens) < 0:
        raise ValueError("Token counts cannot be negative")
    def reduction(value: int) -> float | None:
        return 1 - value / full_source_tokens if full_source_tokens else None
    return {"full_source_tokens": full_source_tokens, "initial_source_tokens": initial_source_tokens,
            "initial_payload_tokens": initial_payload_tokens, "cumulative_input_tokens": cumulative_input_tokens,
            "initial_source_reduction": reduction(initial_source_tokens),
            "initial_payload_reduction": reduction(initial_payload_tokens),
            "cumulative_input_reduction": reduction(cumulative_input_tokens)}

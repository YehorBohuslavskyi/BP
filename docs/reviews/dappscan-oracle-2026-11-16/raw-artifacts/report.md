# Mode B v2 — discovery and selective verification

LLM assessments only; confirmation is not dynamic exploit validation. Unselected functions are not safe.

## Coverage

```json
{
  "total_functions": 9,
  "included": 9,
  "examined": 9,
  "incomplete_metadata": 0,
  "selected": 4,
  "not_selected": 5,
  "unevaluable": 0,
  "pending": 0,
  "candidates_generated": 1,
  "unique_candidates": 1,
  "candidates_verified": 0,
  "confirmed_candidates": 0,
  "rejected_candidates": 0,
  "inconclusive_candidates": 0,
  "processing_failures": 1,
  "semantic_consistency_failures": 1,
  "skipped_candidates": 0,
  "pending_candidates": 0
}
```

## IACL (source.sol)

Compiler: 0.6.12; preparation: FULL_INDEX.

## Oracle (source.sol)

Compiler: 0.6.12; preparation: FULL_INDEX.

- **processing_failed** setACL(address) — access_control
  Candidate IDs: batch-0002:oracle-access-control-001. Severity: unspecified.
  
  Evidence: none.
  Locations: {}
  Execution flow: not established.
  Incomplete evidence/errors: ["SEMANTIC_CONSISTENCY_FAILED"]

  Consistency validation: {"version": "verdict-consistency-v2", "mode": "structured", "passed": false, "failed_rules": ["REJECTION_UNRESOLVED_OR_DANGEROUS_CLAIM"], "original_model_verdict": "rejected", "evidence_ids": ["fragment-0eb34657cac548556e68"]}

## Efficiency

```json
{
  "discovery": {
    "input_tokens": 3516,
    "output_tokens": 581,
    "total_tokens": 4097,
    "api_calls": 2
  },
  "verification": {
    "input_tokens": 3727,
    "output_tokens": 288,
    "total_tokens": 4015,
    "api_calls": 1
  },
  "total": {
    "input_tokens": 7243,
    "output_tokens": 869,
    "total_tokens": 8112,
    "api_calls": 3
  },
  "verification_this_invocation": {
    "input_tokens": 3727,
    "output_tokens": 288,
    "total_tokens": 4015,
    "api_calls": 1
  },
  "unknown_usage_calls": 0,
  "rounds": 1,
  "retrieved_fragments": 0,
  "selected_source_estimated_tokens": 32,
  "full_source_baseline_tokens": 449,
  "verification_context_reduction": 0.9287305122494433
}
```

Source-context reduction is not detection accuracy. Full details and discovery coverage are in JSON.

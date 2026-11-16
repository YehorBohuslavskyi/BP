# Mode B v2 — discovery and selective verification

LLM assessments only; confirmation is not dynamic exploit validation. Unselected functions are not safe.

## Coverage

```json
{
  "total_functions": 2,
  "included": 2,
  "examined": 2,
  "incomplete_metadata": 0,
  "selected": 2,
  "not_selected": 0,
  "unevaluable": 0,
  "pending": 0,
  "candidates_generated": 1,
  "unique_candidates": 1,
  "candidates_verified": 1,
  "confirmed_candidates": 1,
  "rejected_candidates": 0,
  "inconclusive_candidates": 0,
  "processing_failures": 0,
  "semantic_consistency_failures": 0,
  "skipped_candidates": 0,
  "pending_candidates": 0
}
```

## VulnerableVault (source.sol)

Compiler: 0.8.24; preparation: FULL_INDEX.

- **confirmed** withdraw() — reentrancy
  Candidate IDs: batch-0001:VulnerableVault#withdraw-reentrancy. Severity: high.
  The source shows a classic reentrancy pattern in withdraw(): it reads the caller’s balance, makes a low-level external call to msg.sender before updating state, and only afterwards sets balances[msg.sender] to 0. Because the balance is not cleared before the external call, a malicious recipient can reenter withdraw() while their balance is still nonzero and withdraw again.
  Evidence: fragment-3dbf42a41965b0485b75.
  Locations: {"fragment-3dbf42a41965b0485b75": {"file": "source.sol", "lines": [11, 12, 13, 14, 15, 16, 17], "start": 230, "length": 277}}
  Execution flow: withdraw() loads balances[msg.sender] into amount and checks it is > 0.; withdraw() performs msg.sender.call{value: amount}("") before any state update.; The balance is only zeroed after the external call returns, leaving the old balance usable during reentry..
  Incomplete evidence/errors: []

  Consistency validation: {"version": "verdict-consistency-v2", "mode": "structured", "passed": true, "failed_rules": [], "original_model_verdict": "confirmed", "evidence_ids": ["fragment-3dbf42a41965b0485b75"]}

## Efficiency

```json
{
  "discovery": {
    "input_tokens": 1114,
    "output_tokens": 258,
    "total_tokens": 1372,
    "api_calls": 1
  },
  "verification": {
    "input_tokens": 3364,
    "output_tokens": 402,
    "total_tokens": 3766,
    "api_calls": 1
  },
  "total": {
    "input_tokens": 4478,
    "output_tokens": 660,
    "total_tokens": 5138,
    "api_calls": 2
  },
  "verification_this_invocation": {
    "input_tokens": 3364,
    "output_tokens": 402,
    "total_tokens": 3766,
    "api_calls": 1
  },
  "unknown_usage_calls": 0,
  "rounds": 1,
  "retrieved_fragments": 0,
  "selected_source_estimated_tokens": 70,
  "full_source_baseline_tokens": 128,
  "verification_context_reduction": 0.453125
}
```

Source-context reduction is not detection accuracy. Full details and discovery coverage are in JSON.

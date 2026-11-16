# Mode B v2 Phase 3A — preflight and approval proposal

Status update: the user approved and executed this proposal; verification failed.
See [the partial live result and diagnostic correction](mode_b_v2_smoke_result.md).
The proposal below is retained as the pre-run record; its old implementation hash
is no longer executable after the diagnostic correction. This is an engineering smoke
test, not a held-out accuracy benchmark. No OpenAI API request, including input-token
counting, was made during the offline preparation described below. Documentation browsing was read-only.

## Proposed run

| Item | Proposal / offline observation |
| --- | --- |
| Source | `examples/AccessDemoUnrestricted.sol`, unchanged existing development/demo source |
| Eligibility | Four functions: constructor, `setValue(uint256)`, `getValue()`, `changeOwner(address)` |
| Why appropriate | Small, import-free fixture with shared ownership state and an authorization modifier; suitable for cross-function source retrieval |
| Compiler | Installed Solidity 0.8.24; READY, 4 FULL_INDEX, 0 SOURCE_FALLBACK, 0 UNEVALUABLE |
| Active model | Not configured in the current shell |
| API credential | `OPENAI_API_KEY` absent in the current shell; value never read into output; credentials unchanged |
| Proposed model | `gpt-5.4-mini-2026-03-17`, pinned snapshot, standard service tier |
| Expected generation calls | Approximately 3–5; one if discovery selects nothing |
| Maximum generation calls | 7: 1 discovery + 2 candidates × 3 verification rounds |
| Maximum token-count requests | 7; no retries |
| Maximum total endpoint requests | 14 (counting + generation) |
| Shared token reservation ceiling | 40,000 input + maximum output tokens across discovery and verification |
| Input limit | 6,000 provider-counted tokens per generation request, including the schema |
| Output caps | 8,000 discovery; 2,500 per verification call |
| Context limits | 4 additional fragments, 4,000 estimated unique source tokens per candidate |
| Discovery structural limit | Default 24,000 characters; this fixture fits one complete batch |
| New output root | `runs/mode-b-v2-smoke-2026-11-09-01/` (not created yet) |

The model supports Responses and structured outputs. Its documented standard token
prices are $0.75/M input and $4.50/M output. A rough generation-cost estimate is
$0.01–$0.04. At the configured caps, the maximum generation-token charge is about
$0.11625: 23,000 maximum output tokens plus 17,000 input tokens within the combined
40,000-token ceiling. This excludes taxes and any separate token-count-endpoint
charges; the inspected token-counting documentation did not establish such fees.
Account model access and network reachability remain untested.
Sources: [official model/pricing documentation](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
[official token-counting documentation](https://developers.openai.com/api/docs/guides/token-counting).

## Bounded path

The original v2 CLI bounds verification using estimates, but does not enforce an
overall discovery-plus-verification token limit. `scripts/run_v2_smoke.py` adds an
opt-in wrapper using the existing preparation, discovery messages/schema,
verification messages/schema, context resolver, checkpoints and report builder.
It does not change prompts or Mode A/B v1/C behavior.

Before each generation, the wrapper sends identical model/input/strict-schema fields
to `responses.input_tokens.count`. It reserves the returned input count plus the full
output cap before calling `responses.parse`. Reservations are never refunded, even
when a call fails or uses fewer tokens. The gate refuses calls exceeding the shared
token/call limits. Counting and generation attempts are checkpointed separately.

Counting errors, missing usage, count/usage discrepancies, incomplete structured
responses, and uncertain transport outcomes stop further network requests. There
are no automatic retries or smoke-run resume; an existing output directory is refused.
The exact-count/output-cap guarantee relies on the provider honoring those documented
semantics. Any discrepancy is recorded and stops further execution rather than being
silently treated as zero usage.

`budget_ledger.json` records actual endpoint attempts, exact counted inputs, reserved
tokens, requests/schemas, response IDs and returned usage. These counts are authoritative
for this smoke run: ordinary v2 `api_calls` count analyzer attempts, which can include
attempts blocked locally by the budget gate. `analysis/` contains the normal discovery,
candidate, verification, source-context and contract-report artifacts.

## Reviewed plan and execution gate

The offline plan is [mode_b_v2_smoke_plan.json](mode_b_v2_smoke_plan.json).
Its SHA256 is:

```text
aaa372b32ef0a3b84ec902e2905ff50de1aa8c0cee89b060c954ca8e73ad23b5
```

The plan binds source/catalog/sanitizer/compiler identity, implementation hashes,
SDK version, model, limits and output location. Changes require a new reviewed plan.
The user must explicitly approve the proposal and make `OPENAI_MODEL` and
`OPENAI_API_KEY` available in the execution environment. Do not paste credentials
into reports or chat. The runner does not modify credentials.

Only after that approval, the reviewed invocation is:

```bash
.venv/bin/python scripts/run_v2_smoke.py execute \
  --plan docs/mode_b_v2_smoke_plan.json \
  --approved-plan-sha256 aaa372b32ef0a3b84ec902e2905ff50de1aa8c0cee89b060c954ca8e73ad23b5 \
  --run
```

## Offline validation and pending live checks

Full regression suite: **240 passed, 0 failures, 0 errors, 0 skips**, including 14
new budget/provenance/mock-integration tests. Real OpenAI client construction was
blocked during the full suite. Historical hash checks: **1,274 files unchanged**.
No commits or pushes. No source-contract or prompt changes.

Live candidate counts, verdicts, retrieved source, billed tokens and context reduction
are not yet available. After approval, inspect supplied source for each confirmation,
check annotation leakage, and distinguish failed/skipped sessions from security
verdicts. If discovery selects nothing or verification requests no extra context,
report that the retrieval branch was not exercised; do not fabricate candidates or
silently rerun. A successful engineering test is not evidence of held-out accuracy
or dynamic exploitability. The next research milestone remains a separately frozen
held-out B v1/B v2 comparative evaluation.

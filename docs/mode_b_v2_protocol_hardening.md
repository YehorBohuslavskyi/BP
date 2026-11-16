# Verification protocol hardening — offline audit

The saved verification retry returned 1,016 input and 183 output tokens before one
local Pydantic ValidationError. Its response text and field/rule were not saved, so
the exact original violation cannot be recovered. A cross-field violation is a
hypothesis, not an established cause. No new inference was performed for this audit.

## Protocol findings and changes

There was no field-name mismatch. The old prompt under-specified requirements that
the parser enforced: all eight fields must be present, nullable fields must be
explicit nulls, severity must be null except on confirmation, and confirmation
requires an empty incomplete_evidence list. It also lacked complete response examples.

The verification prompt now states these rules, array types, exact enums, unique
context requests, and the prohibition on extra fields and Markdown. Its user payload
includes field definitions derived from the actual Pydantic schema and examples
validated against that model. Examples are explicitly syntax-only, contain no
benchmark answers, and use catalog IDs; context examples exclude already supplied
fragments. No acceptance or evidence-validation rule was relaxed.

Strict structured outputs were **already enabled**. The installed OpenAI SDK and
saved successful API envelope establish compatibility for the configured
`gpt-5.4-mini-2026-03-17` request. This is local evidence, not a fresh availability
check. The wire schema supports both request_context and final responses, but does
not encode Python's cross-field validators. Adding untested conditional schemas or
changing the protocol to a union was unnecessary. The existing strict schema remains
unchanged; explicit guidance and offline contract tests address this gap.

`v2_response.py` centralizes SDK schema construction and parsing. Both the ordinary
verifier and bounded smoke transport retain response usage before local validation.
The ordinary verifier now uses responses.create followed by the same strict SDK
parser rather than responses.parse, which could lose the envelope on validation
failure. No automatic retry was added. The implementation depends on SDK parsing
helpers, so SDK upgrades require regression testing.

Future failures retain candidate ID, processing stage, exception class, safe error
category, available HTTP status, allowlisted field path and validation rule, and
available token usage. The smoke ledger also records attempt metadata. Cross-field
failures have a root path and a stable rule code. Unknown field names are redacted;
raw responses, validation inputs, exception messages, headers and credentials are
not emitted to ordinary diagnostics. Parsing failures retain a null security verdict.

## Files and validation

Created: `src/context_audit/v2_response.py`, `tests/test_v2_protocol_contract.py`,
this audit, and `docs/mode_b_v2_protocol_hardening_retry_plan.json`.
Modified: `src/context_audit/direct_verification.py`, `src/context_audit/v2_smoke.py`,
`tests/test_direct_verification.py`, and `docs/mode_b_v2_pipeline.md`.

The 18 new tests exercise examples emitted by the actual prompt through the wire
schema, SDK parser and verifier. They cover context rounds, all verdicts, missing
fields, enum/type errors, unexpected fields, malformed JSON, fabricated or unseen
IDs, missing confirmation evidence, unresolved evidence, empty discovery results,
source budgets, and usage/diagnostic preservation in both client paths.

Full regression results are recorded below after completion. Real OpenAI client
construction was blocked during the suite; test clients were mocked. The first
external test harness invocation lacked the repository root on sys.path and produced
three import errors; the harness was corrected without changing any project tests.

## Proposed verification-only retry — NOT EXECUTED

Saved discovery provenance validates against the current source, sanitizer, catalog,
compiler, discovery configuration and model. Reuse candidate `batch-0001:C1` from
`runs/mode-b-v2-smoke-2026-11-09-01/analysis/discovery.json`. Do not replay either
previous verification session. The new plan binds the updated implementation.

- Model: `gpt-5.4-mini-2026-03-17`.
- New output: `runs/mode-b-v2-protocol-hardened-retry-2026-11-09-01/`.
- Discovery: zero calls; one candidate; at most three verification rounds.
- Maximum: three generation requests and three input-count requests (six endpoints).
- Shared reservation budget: 18,000 tokens; input cap 6,000 per request;
  output cap 2,500 per generation; source cap 4,000 estimated tokens; four fragments.
- Expected: one to three generations, each preceded by a count. Exact usage and cost
  remain unknown; the longer protocol guidance adds input overhead.
- On interruption, uncertain execution, parsing failure or budget violation: stop,
  preserve partial report/ledger, never automatically retry. A budget may prevent
  all three rounds from executing.
- Artifacts: copied discovery/provenance, verification checkpoints and context
  records, consolidated JSON/Markdown reports and transport budget ledger.

Only after separate explicit approval of this new plan:

```bash
OPENAI_MODEL=gpt-5.4-mini-2026-03-17 \
.venv/bin/python scripts/run_v2_smoke.py execute \
  --plan docs/mode_b_v2_protocol_hardening_retry_plan.json \
  --approved-plan-sha256 d0b7287307633544e9fc6abf5790491df576b76ce57a74152401aba83147d98b \
  --run
```

Offline tests cannot establish improved live reliability or vulnerability accuracy.
Complete the controlled smoke test before freezing a separate held-out evaluation.

Final validation: **279 tests passed, 0 failures, 0 errors, 0 skips**. Python compile
checks and `git diff --check` passed. All **1,290 historical artifact files** under
results, benchmarks, examples and runs retained their SHA256 hashes, including both
live smoke runs and the frozen pilot. No real API calls, commits or pushes occurred.

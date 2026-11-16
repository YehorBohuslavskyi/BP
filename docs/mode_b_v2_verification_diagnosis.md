# Verification failure: offline diagnosis and proposed verification-only retry

Status: **diagnosis and mocked tests complete; retry prepared, not executed**.
No API requests, including token counting, were made during this task. The partial
run and all historical inference artifacts remain unchanged.

## Confirmed facts and uncertainty

The original run is `runs/mode-b-v2-smoke-2026-11-09-01/`.
Its discovery request succeeded, and the verification request passed token counting
and reservation checks before failing inside the generation/parsing call. The old
runner discarded the exception class/status. No response body or verification usage
was saved, so the historical cause cannot be recovered from these artifacts.

| Property | Successful discovery | Failed verification |
| --- | --- | --- |
| Model | `gpt-5.4-mini-2026-03-17` | Same |
| Base URL | `https://api.openai.com/v1` | Same client |
| Generation endpoint | `/responses` | Same |
| Counting endpoint | `/responses/input_tokens` | Same; counting succeeded |
| Authentication | SDK environment configuration | Same client/credential |
| Timeout / retries | 60 seconds / 0 | Same |
| Service tier / storage / truncation | default / false / disabled | Same |
| Tools, temperature, reasoning overrides | None | None |
| Input tokens counted | 1,494 | 1,016 |
| Maximum output tokens | 8,000 | 2,500 |
| Response schema | `DiscoveryResponse` | `VerificationResponse` |
| Source input | Structural summary | Candidate + primary function source + fragment menu |
| Local protocol validation | Candidate identity and coverage | Cross-field action/verdict/evidence/severity constraints |

Both strict schemas are object-rooted, forbid additional properties, and require
all properties. Verification uses nullable verdict/severity for `request_context`,
with arrays for requested/evidence IDs and execution flow. The saved request schemas
and both system/user messages compare equal to the current versions. No prompt,
verdict rule or source content was tuned or weakened.

The verification manifest mtime is 12:16:35.901364 UTC and the final ledger mtime is
12:16:40.383823 UTC: approximately **4.482 seconds** apart. This is filesystem timing,
not a recorded request-duration measurement. It makes a full 60-second read timeout
less likely, but cannot rule out early connection failure, interruption or a quick
provider error.

The leading implementation-specific hypothesis is **local response/protocol
validation inside `responses.parse()`**. The installed SDK invokes Pydantic validators
before returning the response to our caller. We reproduced, offline, a response that
passes the transmitted JSON schema but fails the Python protocol validator (for
example, `confirmed` together with unresolved required evidence). The old caller
would record exactly the generic failure class seen here and lose access to usage.
This proves a possible mechanism, not that it caused this particular live failure.
HTTP rejection, rate limiting and transient service/network errors remain possible.
There is no evidence that the key was absent, the model differed, or the input budget
was exceeded. Unsupported common parameters are less supported as an explanation
because discovery used the same common settings; server-side schema rejection remains
untested offline.

## Changes

- `v2_errors.py`: shared allowlisted exception class, HTTP status, category and
  validation-error count. It never serializes exception messages, bodies, headers,
  credential strings or validation input. Unusual candidate IDs are hashed.
- `direct_verification.py`: retains safe diagnostics with candidate ID, verifier
  stage and round. Infrastructure/protocol failures remain null-verdict processing
  failures; interruptions remain explicit. No rejection or inconclusive verdict is
  synthesized from an error.
- `v2_smoke.py`: uses `responses.create` with the identical counted strict schema,
  saves response ID/model/usage, then invokes the installed SDK's same structured
  parser locally. Parsing errors therefore preserve known usage. Transport errors
  remain uncertain. The ledger records phase, candidate, attempt, timings, caps and
  request hash rather than duplicate request contents. Source prompt journals remain
  in the existing pipeline artifacts; diagnostic objects contain no source text.
- `v2_artifacts.py`: permits explicit expected-model validation during offline plan
  preparation, without changing environment variables or relaxing any other check.
- `run_v2_smoke.py`: `prepare --candidates` prepares a bounded verification-only run.
  It retains the checksum/explicit-execution gate and refuses an existing output.

`responses.create` and `responses.parse` use the same generation endpoint. The
change separates receipt/accounting from local parsing; it does not alter the JSON
schema or accept responses the verifier previously rejected. Exact input-count and
output reservations, 60-second timeout, zero retries and stop-on-error remain intact.

## Regression evidence

**259 passed, 0 failures, 0 errors, 0 skips** in the complete offline suite, with real
OpenAI client construction blocked. Seventeen new tests cover timeout, connection
failure, HTTP 400/401/429/500, unsupported parameters, malformed JSON/envelopes,
schema-valid but protocol-invalid output, incomplete output, valid context rounds,
interruption, known-usage retention, safe diagnostics, and retry provenance/no-replay.
Existing transport tests now check `create` receives the exact schema counted by the
input endpoint. Compilation and whitespace checks passed.

All **1,282 files** under `results/`, `benchmarks/`, `examples/` and `runs/` retain their
start-of-task hashes, including the original partial smoke and frozen DAppSCAN pilot.
The retry output directory has not been created. No commits or pushes were made.

## Saved discovery reuse and retry proposal

Saved discovery passed full validation against freshly prepared source: target hash,
sanitized dependency-project hash, compiler, catalog, structure, locations, sanitizer/
preparation code, discovery implementation, prompt, schema and model. Its artifact
checksum and candidate identity also validate. It can be reused **without another
discovery call**. Do not rewrite its manifest.

Candidate file:
`runs/mode-b-v2-smoke-2026-11-09-01/analysis/discovery.json`

Candidate: `batch-0001:C1`, `AccessDemoUnrestricted.changeOwner(address)`.

New output root: `runs/mode-b-v2-verification-retry-2026-11-09-01/`.

[Prepared plan](mode_b_v2_verification_retry_plan.json), SHA256:
`aae73c44ddfa569c2a79a66468b84eede39fdc9bcba1b028697088c8f0d03157`.

| Control | Retry |
| --- | --- |
| Model | `gpt-5.4-mini-2026-03-17` |
| Discovery calls | **0** |
| Candidates | **1** |
| Verification rounds/generation calls | **At most 3** |
| Input-token-count requests | **At most 3** |
| Total new endpoint requests | **At most 6** |
| Shared reservation ceiling | **18,000 counted input + capped output tokens** |
| Per-call counted input limit | **6,000** |
| Per-call output cap | **2,500** |
| Additional source fragments | **4 maximum** |
| Unique source size limit | **4,000 estimated tokens** |
| Timeout / automatic retries | **60 seconds / 0** |

Expected usage is 1–3 generation calls plus 1–3 count requests, depending on source
requests and failures. The original first input counted 1,016 tokens; later inputs
can grow when context is supplied. Output lengths are unknown, with an aggregate
7,500 output-token cap inside the combined 18,000 reservation ceiling. This budget
applies to the NEW attempt, not to the previous attempt's unknown charges.

Only after separate explicit approval, the exact invocation is:

```bash
OPENAI_MODEL=gpt-5.4-mini-2026-03-17 \
.venv/bin/python scripts/run_v2_smoke.py execute \
  --plan docs/mode_b_v2_verification_retry_plan.json \
  --approved-plan-sha256 aae73c44ddfa569c2a79a66468b84eede39fdc9bcba1b028697088c8f0d03157 \
  --run
```

The API credential must already be available in that execution environment. This
command was **not executed**. The original failed request is not resumed, replayed
or treated as having completed: this is a separately approved new attempt using only
the saved discovery artifact. No automatic retry occurs after interruption or error.
Unknown outcomes retain their reservations; existing output prevents rerunning the
same plan. Source, candidate-file or implementation changes invalidate the plan.

Expected outputs: `smoke_manifest.json`, `budget_ledger.json`, and under `analysis/`,
a copy of the saved discovery, `summary.md`, `verification_manifest.json`, per-candidate
session checkpoints, `report.json` and `report.md`. Reports retain original candidate
IDs and distinguish reused discovery usage from new verification usage. The ledger
is authoritative for actual new endpoint counts; locally blocked analyzer attempts
must not be counted as network requests. Previous failed usage stays unknown in the
unchanged old run.

The retry may confirm/reject/abstain, fail again with useful diagnostics, or request no
extra source. None of these possibilities establishes exploitability or improved
held-out accuracy. The live smoke milestone is still incomplete.

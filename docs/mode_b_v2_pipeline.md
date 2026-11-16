# Mode B v2: discovery → selective candidate verification

Mode B v2 now prepares sanitized Solidity, builds structural summaries, discovers
candidate hypotheses, verifies them against bounded source context, and aggregates
contract reports. Mode A, Mode B v1 and Mode C retain their existing behavior. The
GUI is unchanged. No detection improvement has been established.

## Interfaces and verdicts

`direct_discovery.prepare(path)` returns the structural contracts and sanitized
opaque-ID catalog. `run_discovery(..., execute=True)` returns candidates and a
provenance manifest. `v2_pipeline.run_verification(discovery, contracts, catalog,
output, resume=False, limits=Limits(), analyze_fn=None)` validates that manifest,
groups exact duplicate claims, checkpoints verification and writes reports.
`direct_verification.verify_candidate(...)` is the lower-level mocked-testable
component. Preparation and summary-only execution do not instantiate API clients.

The current development protocol adds a required ninth field, `verdict_basis`,
and a deterministic consistency gate after supplied-evidence validation. Legacy
eight-field responses are readable only through explicit historical replay; they
are not accepted as new live responses. See [consistency hardening](mode_b_v2_consistency.md)
for the schema, failure semantics and comparability limits.

The strict `VerificationResponse` schema contains:

- `action`: `request_context` or `final`;
- `requested_ids`, `explanation`, `evidence_ids`, `execution_flow`, `incomplete_evidence`;
- `verdict`: null during requests, otherwise `confirmed`, `rejected`, or `inconclusive`;
- `severity`: null unless supported by a confirmed result.
- `verdict_basis`: null during requests; a structured mechanism/condition/mitigation
  assessment and source-quote claims for final responses.

Confirmation means the LLM assesses the source as supporting the particular
hypothesis, not that an exploit has been dynamically reproduced. Rejection requires
source evidence contradicting the hypothesis or establishing a protection; it does
not establish function/contract security. Missing evidence permits abstention.
Both confirmation and rejection require supplied evidence IDs. A confirmation
cannot simultaneously declare unresolved required evidence.

A candidate session additionally records candidate/contract/function identity,
suspected type, processing status, preparation mode, evidence locations, requests,
supplied source, round messages/responses, errors, usage and source-size estimates.
Processing statuses (`processing_failed`, `interrupted`, `skipped_limit`,
`budget_exhausted`, `pending`/`running`) have null verdicts. Only `completed` sessions
carry security verdicts. Budgets and malformed responses never become rejections.

## Source and selective context

The primary function must match the contract, full signature and a validated
function fragment. Phase 1 related/requested IDs must exist in the real catalog.
The primary source is supplied initially; discovery's source requests remain hints
for the verifier, rather than automatic bulk retrieval.

The existing `payload.resolve_context_request` resolves requests against an explicit
menu of validated function, modifier and state-variable IDs. The menu includes the
prepared catalog so fallback analysis is not constrained by a missing dependency
graph. Source is retrieved only on request. Repeated, unknown or unseen evidence IDs
are rejected. Requests, supplied IDs and snippets are recorded. No full-contract
fragment is created. Context source is checked again for annotation contamination
before transport; invalid catalogs fail rather than silently changing source bytes.
Source files/locations are kept in reports, not exposed as benchmark path metadata
to the model. Raw provider exceptions are not saved; errors use stage-specific codes.

FULL_INDEX uses indexed structure and validated source. SOURCE_FALLBACK retains
compiler-backed source/AST structure and explicitly unknown IR relationships. The
prompt checks reachability, ordering, data flow, authorization, guards and invariants
against source; absent IR never proves independence or safety. Additional source can
be requested in either mode, and insufficient evidence remains inconclusive.

## Commands

Use fresh output directories and an installed compatible compiler. These commands
operate on one local Solidity file and its resolved dependencies.

```bash
# Offline preparation and structural summaries: no model required, no API calls
.venv/bin/python scripts/run_direct_discovery.py path/to/Contract.sol \
  --stage prepare --output /tmp/bv2-prepared

# LIVE discovery only (--run without --stage remains discovery-only for compatibility)
OPENAI_MODEL=your-pinned-model .venv/bin/python scripts/run_direct_discovery.py \
  path/to/Contract.sol --stage discover --run --output /tmp/bv2-discovery

# LIVE verification of saved discovery candidates; discovery is not repeated
OPENAI_MODEL=your-pinned-model .venv/bin/python scripts/run_direct_discovery.py \
  path/to/Contract.sol --stage verify --run \
  --candidates /tmp/bv2-discovery/discovery.json --output /tmp/bv2-verification

# LIVE combined pipeline
OPENAI_MODEL=your-pinned-model .venv/bin/python scripts/run_direct_discovery.py \
  path/to/Contract.sol --stage all --run --output /tmp/bv2-combined

# Explicit resume: unchanged source, configuration, prompts and model required
OPENAI_MODEL=your-pinned-model .venv/bin/python scripts/run_direct_discovery.py \
  path/to/Contract.sol --stage all --run --resume --output /tmp/bv2-combined
```

Verification-only resume uses the same `--stage verify --candidates ... --output ...`
command plus `--resume`. An entirely completed resume makes no model calls.
All live stages require `--run`; preparation rejects it. Nonempty output directories
are refused without compatible explicit resume. Exit 1 indicates errors or incomplete
processing/limits; exit 130 indicates interruption. Inspect JSON for precise status.

Default verification limits, configurable via the corresponding CLI flags:

| Flag | Default | Scope |
| --- | ---: | --- |
| `--max-rounds` | 4 | Calls per unique candidate |
| `--max-fragments` | 20 | Additional source fragments per candidate |
| `--max-source-tokens` | 16000 | Estimated unique supplied source per candidate |
| `--max-input-tokens` | 24000 | Estimated full message input per call |
| `--max-output-tokens` | 4000 | Provider output cap per call |
| `--max-candidates` | 50 | Deterministically ordered unique hypotheses |
| `--max-total-tokens` | 200000 | Verification planning budget across saved/new sessions |
| `--max-summary-chars` | 24000 | Phase 1 structural batch size |

Token estimates use the existing character-based estimator, not the model tokenizer.
The verifier reserves estimated input plus the output cap before each call and uses
returned actual usage for subsequent decisions. This is a planning budget, not an
exact billing cap: tokenizer differences, schema overhead or interrupted calls may
exceed estimates. Discovery has its existing separate per-batch output cap; the
verification total budget does not cap discovery expenditure. Candidate limits are
applied before calls, not by inventing security verdicts.

## Artifacts, provenance and resume

- `discovery.json`: candidates, structural summaries, coverage, discovery usage and manifest.
- `summary.md`: Phase 1 summary when discovery/preparation is run locally.
- `verification_manifest.json`: source identity, discovery checksum, verification configuration.
- `sessions/<stable-hypothesis-hash>.json`: atomic per-candidate checkpoints with checksums.
- `report.json` and `report.md`: consolidated contract findings, other candidates, coverage and efficiency.

The manifest checks original target-source hash, sanitized dependency-project hash,
compiler version, catalog/structure/location hashes, sanitizer/preparation code,
discovery and verifier model/prompt/schema/configuration, and implementation hashes.
The complete discovery artifact and each session have checksums. Completed sessions
also undergo schema, source, evidence, location and usage consistency checks on reuse.
These are local integrity checks, not cryptographic authentication of an artifact's author.

Saved candidates must be a full `discovery.json` with its manifest, not a bare list.
Old Phase 1 artifacts lacking provenance are refused; never retrofit frozen artifacts.
Source edits, different models, changed budgets or changed implementations require a
fresh output/run. Use a pinned model where possible; a provider alias may change
behind an unchanged name, and manifests cannot detect such provider-side changes.

Resume loads discovery without calling it again and reuses all saved verification
sessions explicitly. Pending candidates without sessions continue. Failed, exhausted
or interrupted saved sessions are retained, not silently retried. To deliberately
retry them, use saved discovery with a fresh verification output directory.

A checkpoint is written before every call. Keyboard interruption produces a partial
report; an abrupt process termination leaves a pending-call checkpoint. An uncertain
transport outcome is marked interrupted on resume and never automatically replayed.
Provider usage for that call may be unknown. Discovery itself is not resumable
mid-batch; the checkpoint mechanism applies to saved-candidate verification.

## Deduplication, coverage and metrics

Only identical hypotheses are merged: same contract, primary signature/ID, type,
reason, uncertainty, and related/requested context sets. Candidate IDs and original
model IDs are retained through the discovery artifact and issue-to-candidate mapping.
Distinct claims, evidence requirements or uncertainties remain independent. Potential
overlaps sharing a flow fragment and vulnerability type are listed without merging;
conflicting verdicts therefore remain visible. There is no semantic equivalence model.

Reports retain discovery function coverage and distinguish generated candidates,
unique hypotheses, verified, confirmed, rejected, inconclusive, processing failures,
skipped/limited and pending candidates. Function counts are per contract/function
pair, including inherited declarations. Unselected functions are not safe. Discovery
can miss vulnerabilities entirely; verification cannot recover missing hypotheses.

Usage totals count discovery once and each deduplicated verification session once,
including explicitly reused sessions. `verification_this_invocation` separates new
work from saved totals. `api_calls` counts attempts, including interrupted/error
attempts; `unknown_usage_calls` flags absent provider accounting, rather than implying
that an unknown call cost zero.

Verification context reduction follows v1's source-size definition:
`1 - sum(unique selected source tokens per session) / sum(full target file tokens per session)`.
It excludes discovery prompts and repeated round prompts, counts only sessions with
attempts, and can be negative when imported context exceeds the target-file baseline.
Actual API totals include all returned discovery and verification usage. Context
reduction is efficiency evidence, never detection accuracy.

## Offline example and validation

The synthetic compiler fixture in `tests/test_direct_verification.py` exercises this
mocked flow: discovery selects `Vault.withdraw(uint256)`; verification requests its
`auth()` modifier, then `deposit()`, then returns a source-cited mocked confirmation.
The verification session has 3 calls, 2 retrieved fragments and 45 mocked tokens.
The fixture's 2 discovery calls add 30 mocked tokens: 75 total. These values test
accounting and protocol behavior, not the validity of the synthetic vulnerability.
Other tests cover rejection, abstention, fallback, malformed responses, unseen
references, budgets, GT isolation, API failures, interruptions and provenance mismatches.

Run offline regressions using the repository's unittest workflow:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

During implementation, real OpenAI client construction was blocked for the full suite.
The suite passed **226 tests, 0 failures, 0 errors, 0 skips** (35 new Phase 2 tests).
No real model calls were made. Hash checks preserved all 1,274 files under `results/`,
`benchmarks/`, `examples/` and `runs/`, including the frozen clean pilot.

## Evaluation next steps

Select and freeze a separate held-out DAppSCAN cohort, pin code/model/prompts/budgets,
and predeclare metrics for discovery coverage, verification outcomes, strict recall,
additional findings and cost. Compare Mode B v1 and v2 fairly with the existing A/C
baselines. Manually adjudicate additional findings and inspect disagreements without
using evaluation labels to tune prompts. Retain the three-contract pilot only as
development/debug evidence. Discovery omissions, cross-batch reasoning limits,
source-model limitations and infrastructure abstentions must remain visible.

## Controlled smoke execution

The ordinary CLI's estimated budgets remain unchanged. For a small approved live
engineering test, use the [Phase 3A preflight and bounded runner](mode_b_v2_smoke.md).
It adds a shared provider-counted token reservation budget and endpoint-call caps
across both stages, without changing discovery or verification prompts.

For the first partial smoke failure, see the [offline diagnosis and verification-only
retry proposal](mode_b_v2_verification_diagnosis.md). Saved discovery is reused only
after provenance checks; the uncertain failed verification is never silently replayed.

For the subsequent response-validation failure, see the [offline protocol audit,
strict prompt/schema contract tests and fresh bounded retry proposal](mode_b_v2_protocol_hardening.md).
The retry remains unexecuted and requires separate approval.

The [three-contract development experiment](mode_b_v2_development_experiment.md)
provides separate ground truth, matched B v1/B v2 resource plans, offline Slither
baselines and a counted transport with conservative checkpoint resume. Its inference
runs require explicit approval; the initial approval scope is one B v2 contract.

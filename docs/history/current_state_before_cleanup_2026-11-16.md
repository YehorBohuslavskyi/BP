# Current state and next session

## Current thesis direction

Primary goal: **Mode B — direct LLM vulnerability detection from Solidity source
using selective context**.

Comparison modes: **A — Slither static baseline** and **C — Slither + selective-context
LLM verification**. Mode C retains its existing confirmed/false_positive/inconclusive
protocol. Mode B independently discovers findings without a Slither hypothesis.

## Completed

- SmartBugs baseline and its existing regression checks.
- CGT false-positive-reduction pilot.
- DeFiHackLabs hybrid evaluation.
- Scalability experiments and their existing tooling.
- Direct Detection infrastructure: GUI, CLI, multi-round context requests,
  compiler selection, local dependency resolution, sanitized source staging,
  FULL_INDEX/SOURCE_FALLBACK sessions and function-level readiness.
- Clean DAppSCAN pilot3 and saved additional-finding manual adjudication.

These experiments have different populations and metrics; do not combine them.

## Frozen current Mode B pilot

Authoritative artifacts:

- `examples/dappscan/evaluation/direct_detection/clean-pilot3-run-v2/`
- `examples/dappscan/evaluation/direct_detection/clean-pilot3-prepared-v2/`
- Manual review: `additional_findings_adjudication.json` and `.csv` in the run directory.

| Measure | Frozen result |
| --- | ---: |
| Analyzed files | 3 |
| Function sessions | 45 |
| FULL_INDEX / SOURCE_FALLBACK | 43 / 2 |
| Evaluable GT labels / selected labels | 6 / 6 |
| Evaluation coverage | 100% |
| Detected / missed / inconclusive / unevaluable | 0 / 4 / 2 / 0 |
| Raw additional findings | 14 |
| API calls | 90 |
| Tokens | 342,564 |
| Average rounds | 2.0 |
| Average requested fragments | 4.4 |
| Estimated context reduction | 92.43374417268024% |
| Detected GT annotation leakage | None in the clean pilot |

Manual review currently suggests 7 VALID, 1 PLAUSIBLE, 4 DUPLICATE and
2 LIKELY_FALSE_POSITIVE findings: **8 unique VALID/PLAUSIBLE issue instances**.
These are manual judgments, not a clean-negative-set precision estimate.

The two relevant inconclusive sessions received model responses and then ended
with context-request protocol errors. They remain evaluable abstentions, with
errors preserved, rather than preparation failures. UNEVALUABLE is reserved for
missing/invalid relevant analysis sessions. Preparation readiness and model
verdicts are separate concepts.

## Known limitation

The clean pilot has **0 strict GT detections, 4 misses and 2 inconclusive labels**,
alongside multiple additional plausible findings. Infrastructure works, but the
vulnerability discovery methodology needs improvement. This small development
pilot does not establish general detection performance.

Preserve `clean-small-run`, clean pilot3 preparation/results, all prompt journals,
contract/evaluation reports and adjudication files. Preserve pre-fix/debug runs
as historical evidence. In particular, `pilot10` is `pilot10_debug_prefixed` in
status: incomplete preparation coverage and possible annotation leakage make it
unsuitable as a clean thesis result. Never edit inference outputs to improve metrics.

## Offline validation and commit hygiene

Run the unittest suite with OpenAI clients mocked/blocked; no experiments or
saved summaries need rerunning. Sanitization tests cover developer-comment
preservation, line/source mappings, requested fragments and source fallback.
Compiler binaries are selected locally without global state changes or downloads.

Keep local virtual environments, credentials, editor caches and scratch output
out of commits. Keep intentional evaluation artifacts and historical empty logs.
Large reports repeat sessions by design; review size without deleting evidence.
No automatic formatter is configured; use compilation and `git diff --check`.

## Mode B v2 implemented: discovery and selective verification

The CLI now supports offline preparation, discovery-only, verification of saved
candidates, and combined discovery plus verification. Verification reuses sanitized
fragments and the existing selective-context resolver, with strict evidence checks,
bounded requests, per-candidate checkpoints and provenance-checked explicit resume.
Mode A, Mode B v1, Mode C and the GUI remain available.

See [the pipeline workflow and protocol](mode_b_v2_pipeline.md) and
[the structural discovery design](mode_b_v2_discovery.md).

Next milestone: define a separately selected, frozen held-out evaluation cohort,
pin models/prompts/budgets, and compare v1 and v2 under a predeclared evaluation plan.
No real v2 API experiments or detection-accuracy claims accompany implementation.
The existing three-contract pilot remains development/debug evidence.


## Latest offline development work — 2026-11-16

PRA remains a finalized partial development run; do not rerun it or advance the
cohort automatically. Its three saved semantic failures were diagnosed without
GT input or model requests. Generic consistency v2 permits mechanism paraphrases
while retaining substantive contradiction and evidence checks. Separate offline
review accepts only the original lock inconclusive assessment; unlock and set
remain blocked. See [the diagnosis](mode_b_v2_pra_offline_diagnosis.md).
Frozen execution plans and approvals are not updated by this code change.

Validation: 72 focused tests pass; the full offline suite runs 467 tests with no
test failures but one pre-existing class-setup error from malformed historical
JSON. All 2,386 files under runs/ and experiments/ remain byte-for-byte unchanged.
The malformed report must receive an explicit integrity diagnosis, not a silent
rewrite, before reporting a fully passing suite.


## Interactive scanner — 2026-11-16

The new Scanner landing page and `scripts/scanner.py` expose real local static
scans, Mode B v2 preparation and explicit discovery/verification, and JSON/HTML
reporting. Local vulnerable/guarded examples provide a genuine before/after
static scan demonstration. Saved LLM evidence is a separate read-only page with
original assessments and integrity checks. See [the demonstration guide](scanner_demo.md).

No new paid inference was performed: current API/model access and the updated
live prompt still need a separately authorized provider check. The historical
malformed report remains unchanged; unit-test scope fixtures are isolated from it,
and a separate integrity test verifies the real reuse audit still fails closed.
The interactive scanner never advances frozen pilot cohorts or writes to their
output directories. Existing research and legacy UI remain available.

Final scanner validation: 496 offline tests pass; genuine local and browser scans verified. Fresh provider validation remains pending an API key and bounded-run authorization. Historical files under runs/ and experiments/ remain unchanged.

Session-only masked key entry is available for the scanner, with child-only credential injection and no report serialization. Final offline suite: 498 tests passed. The user authorized one four-request demonstration check, pending local API-key entry; do not repeat it automatically.


## Final scanner provider verification — 2026-11-16

The previously pending, explicitly authorized demonstration is complete. A fresh
Mode B v2 run examined 2/2 function rows and confirmed high-severity reentrancy in
VulnerableVault.withdraw(), with one discovery and one verification request,
5,138 tokens, no consistency/processing failures and no retries. The temporary
session key was cleared afterwards. Raw artifacts and public reports are stored
separately under docs/reviews/scanner-live-2026-11-16/. The existing 498-test
offline suite passes, and all 2,386 runs/experiments files remain unchanged.
See [final verification](scanner_final_verification.md). No additional run is
authorized by this completed one-time check. The demonstration scanner is ready.


## Real DAppSCAN Oracle demonstration — 2026-11-16

User-requested ForTube Oracle.sol scan completed once, separately from frozen
evaluation: 9/9 function rows examined; eight local warnings (four low/four info).
The LLM generated one setACL candidate and returned rejected, but its mixed
protection/dangerous_behavior evidence roles failed consistency. The saved result
remains partial with no accepted security verdict. Usage: three generation
requests, 8,112 tokens, no retries or count requests. Source/history unchanged;
temporary key cleared. See docs/reviews/dappscan-oracle-2026-11-16/scan-status.md.
Do not automatically rerun this contract or rewrite its rejection into a verdict.


## Subscription backend and fresh evaluation — 2026-11-16

The scanner now defaults to ChatGPT-authenticated Codex CLI for direct scans,
with no API key, API fallback or credit purchases. The optional separately billed
API backend is explicit. All 514 offline tests passed before the new evaluation.
The CLI is already signed in with ChatGPT. Model/backend and consistency v3
changes define a separate study condition; historical results stay unchanged.
See [subscription scanning](scanner_subscription.md) for request limits,
source-only isolation and the frozen 73-source/58-project DAppSCAN plan.
Evaluation results are recorded separately after inference; no accuracy claim
follows from raw finding counts. The earlier one-time API authorizations are
completed and do not authorize additional paid inference.


Subscription evaluation result: the free local baseline completed all 73 files.
Codex attempted 10 development files (3 complete, 7 partial) before a failed turn
stopped the runner; 63 files remain unrun. There were 40 attempted turns, 682,827
reported tokens, one unknown-usage turn and zero API-key requests. One rejection
was accepted; zero confirmations were accepted. GT labels remain unread and no
accuracy score is claimed. See reviews/scanner-subscription-2026-11-16/results.md.
The evaluated code is saved separately. Subsequent diagnostic and exposure
tracking fixes must use a fresh plan; they do not change or resume this run.
Validation: 515 full offline tests passed, then 3 focused exposure tests passed.


## Source-request hardening follow-up — 2026-11-16

Context-bound Codex schemas, explicit retrieval capacity and CLI-overhead budgeting
passed a fresh two-file development pilot: seven turns, 133,450 reported tokens,
zero API-key calls, zero source-ID failures or budget skips. One inconclusive
verdict was accepted; one original abstention remains a saved v3 consistency
failure. Its separate v4 review is inconclusive only. The v4 correction is tested
offline (535 full tests passed), with no new live check after that rule change.
GT labels and validation/held-out files remain isolated. See
reviews/scanner-source-request-hardening-2026-11-16/report.md for limits and evidence.


## Function navigation and explicit limit profiles — 2026-11-16

The current implementation adds compiler-backed source-ID links for calls,
callers, modifiers and state dependencies, passes them to verification and
prioritizes context menus by graph distance. Dynamic/unavailable paths stay
unknown. Source is still requested explicitly and cited only after delivery.
See [function navigation and investigation limits](function_navigation.md).

Fresh-run profiles separately expand rounds, fragments or candidate coverage;
the combined profile is six candidates, five rounds and twelve extra fragments.
Scanner controls and actual transport budgets carry those limits end to end.
Frozen API case limits and historical artifacts remain unchanged. Existing
prepared bundles and approvals cannot authorize the new index/prompt identity.
No live model check or accuracy scoring accompanied these implementation changes.


Final navigation/limit validation: all 575 offline tests pass. The separately
authorized one-source LinkedWithdrawal development check used five Codex turns
and 73,863 reported tokens, confirmed one high-severity reentrancy hypothesis
after seven retrieved fragments/four verification rounds, and had zero processing
failures or skips. Source, request and session envelopes were revalidated.
This is a handcrafted development control, not precision/recall or exploit proof.
All 2,386 historical runs/experiments files remain unchanged. The one-time model
check is complete; no rerun or cohort advancement is authorized.

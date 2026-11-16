# Three-contract development experiment — awaiting approval

Prepared offline on 2026-11-09 for `gpt-5.4-mini-2026-03-17`. **No inference has
been executed for this cohort.** After approval, run only ProjectWalletAuthoriser
with B v2, inspect its results, then stop. Approval of that run does not authorize
B v1, the remaining contracts, or a continuation after an uncertain request.

The selection, summaries, source/dependency hashes, sanitized-catalog checks, six
method plans and separate evaluation metadata are in
[`experiments/mode-b-v2-development-2026-11-09/`](../experiments/mode-b-v2-development-2026-11-09/).
[All six exact execution commands](../experiments/mode-b-v2-development-2026-11-09/commands.md)
are provided individually, not as an executable batch.

## Selection and readiness

All are real project sources from the existing local DAppSCAN checkout, with one
reported vulnerability each. These are development cases, not held-out evaluation.
No prior inference/baseline artifact for these exact three filenames was found in
local examples, runs, results or benchmarks. Timvi LeverageService shares a project
with the previously examined BondService/ExchangeService pilot; that project exposure
prevents a claim of independent held-out selection. Unknown model-training exposure
is also not measurable here.

| Case | GT category (evaluation only) | B v1 declared sessions | B v2 summary rows | Discovery batches | Compiler/readiness |
|---|---|---:|---:|---:|---|
| ProjectWalletAuthoriser | SWC-104, unchecked return | 2 | 6 | 1 | 0.4.25; FULL_INDEX |
| CoreVoting | SWC-107, reentrancy | 12 | 18 | 2 | 0.8.24; FULL_INDEX |
| LeverageService | SWC-115, tx.origin authorization | 9 | 9 | 1 | 0.5.11; 8 FULL_INDEX + 1 SOURCE_FALLBACK |

The B v2 counts include inherited functions. All 33 summary rows are included; all
23 declared functions are preparable. Successful inclusion is not yet LLM examination.
The two added scopes are 4 inherited rows for ProjectWalletAuthoriser and 6 for
CoreVoting. B v1 retains its existing declared-function scope and can retrieve
inherited sources. Evaluation uses the same declared-source GT units for both modes;
report the architectural scope difference rather than pretending session counts match.

Exact source paths (prefix `/home/coca-cola/projects/DAppSCAN/DAppSCAN-source/contracts/`):

```text
Iosiro-ixo Smart Contract Audit/ixo-solidity-417c40f1bd6600e5d1d8b49d136f2b97a098591c/contracts/project/ProjectWalletAuthoriser.sol
Runtime_Vеrification-Element_Finance_Governance_Security_Audit_Report/council-3d751c959b42573c78ccd0bccbc80424bf6d9a90/contracts/CoreVoting.sol
Coinfabrik-Timvi Smart Contract Audit/Timvi-9324706d1160996f7847e1989c8567168261382e/contracts/services/leverage-exchange/LeverageService.sol
```

The Element project name contains a Cyrillic character; use the prepared JSON paths
rather than retyping it. The three dependency graphs contain 3, 3 and 5 local source
files. No downloads, dependency edits, compiler installation or global compiler
selection were needed. LeverageService's `create(uint256)` has validated source but
unavailable IR relationships, so the verifier must request source or abstain rather
than treating missing metadata as empty dependencies.

Screening used existing manifests plus local label/source size and dependency checks,
not model outputs. DeFiHackLabs' catalog manifest establishes only SpankChain as an
available faithful local victim archive; it is an already-examined development pilot.
Other candidates were excluded for missing local dependencies (BrickblockAccount,
MarketOracle), unavailable compatible installed compiler (MonstaPresale), or ambiguous
GT (RocketMinipool names a getter but points at fallback lines). No source was repaired
or downloaded to force eligibility. Ground truth for CoreVoting has an unparsed spaced
line range; its unique `execute` function resolves unambiguously without inventing lines.

## Bounded execution and fair comparison

The new `scripts/run_development_experiment.py` wrapper reuses existing B v1 and
B v2 preparation, prompts, schemas, resolver and reports, plus the smoke runner's
`CountedTransport`. The old smoke runner permits only one discovery batch; the
ordinary discovery CLI has no provider-counted shared budget. Neither is used as an
unbounded fallback. Modes A, B v1 and C implementations were not modified.

The following caps apply **independently to each method on each contract**:

| Case | Max generation requests | Max token-count requests | Max reserved input + output tokens | B v2 max discovery requests |
|---|---:|---:|---:|---:|
| ProjectWalletAuthoriser | 12 | 12 | 40,000 | 1 |
| CoreVoting | 36 | 36 | 120,000 | 2 |
| LeverageService | 27 | 27 | 90,000 | 1 |

Count calls are endpoint requests too: maximum 24, 72 and 54 endpoints per method,
respectively. B v2 also allows at most 3 verification candidates, 3 rounds/candidate,
8 retrieved fragments/candidate and 8,000 estimated source tokens/candidate. Actual
B v2 generation ceilings from those stage limits are 10, 11 and 10, below the shared
transport caps. Extra candidates are explicitly skipped, never rejected.

Both methods have a 12,000 provider-counted input-token cap and 4,000 output-token cap
per function/candidate call. Discovery retains its existing 8,000 output cap. B v1
uses 3 rounds/function and its existing resolver. Its fragment policy differs from
B v2; this is a resource-matched architectural comparison, not identical prompts or
work units. Budgets are fixed before inference; do not raise them after seeing a miss.

Reservations are input count plus output maximum, never refunded, including failed
requests. Thus a run can stop before exhausting the nominal call cap. Token count
failures, unknown generation outcomes and parse failures stop transport; no automatic
paid retry. No pricing estimate is claimed without a verified price schedule.

Offline estimates use characters/4 and are approximate, excluding provider schema
accounting and later retrieved fragments:

| Case | B v1 initial prompt tokens, all functions | B v2 initial discovery prompt tokens | B v1 generation range | B v2 planning scenario |
|---|---:|---:|---:|---|
| ProjectWalletAuthoriser | 1,630 | 2,017 | 2–6 | 2–7 calls; roughly 10–35k tokens |
| CoreVoting | 19,973 | 7,898 | 12–36 | 3–8 calls; roughly 20–65k tokens |
| LeverageService | 18,569 | 2,276 | 9–27 | 2–7 calls; roughly 12–45k tokens |

The B v2 scenario assumes 1–3 candidates and 1–2 verification rounds, not a prediction
of findings. Zero candidates needs only discovery. B v1 planning ranges including
responses/context are approximately 3–15k, 30–110k and 25–85k tokens. Exact counting
happens only after approval; hard caps override these estimates.

Only the first B v2 run is proposed now:

```bash
OPENAI_MODEL=gpt-5.4-mini-2026-03-17 \
.venv/bin/python scripts/run_development_experiment.py execute \
  --plan experiments/mode-b-v2-development-2026-11-09/prepared/ixo-authoriser/b2-plan.json \
  --approved-plan-sha256 b46498fce8755bdf72f521c689d26f5731777a9e377b8a0d629d9a5a57ebf26e \
  --run
```

Output: `runs/mode-b-v2-development-2026-11-09/ixo-authoriser/b2/`.
Other output directories use the case ID and `b1`/`b2`, recorded in each plan.
`analysis/report.json` and B v2 `analysis/report.md` contain findings and coverage;
`analysis/discovery.json`, `analysis/sessions/`, `requests/`, the experiment manifest,
transport checkpoint and budget ledger preserve prompts, candidates, supplied context,
verdicts, safe diagnostics, usage and provenance. Raw invalid model text is not saved.
Credentials are read from the environment, never saved.

Explicit `--resume` uses the same plan/checksum and original output. Completed
request records can be reused with zero new calls; counters/reservations continue
from the saved ledger. Source/compiler/sanitizer/catalog/code/model/configuration,
manifest, request-journal and ledger checks must match. Missing, pending or uncertain
requests refuse resume; a stopped transport cannot make new requests. Crash gaps fail
closed, even when this sacrifices resumability. No broad cross-run cache is used.
A separate review is required before executing any continuation. Do not substitute
an ordinary unbounded CLI when this runner stops.

## Ground-truth isolation and evaluation

`prepared/evaluation_only/` contains GT reports, matching rules and Slither output.
The inference worker never imports the dataset loader or evaluator, and reads only
its source plan. Slither detector results never enter either model's prompts. Source
preparation uses the existing annotation sanitizer and opaque fragment catalog, not
synthetic source fragments. All 100 catalog fragments were checked; annotations were
removed in one source file per case, preserving positions. Full source dependency
hashes are retained. The source-size/preparation checks used no API client.

The predeclared [evaluation protocol](../experiments/mode-b-v2-development-2026-11-09/prepared/evaluation_only/protocol.json)
uses these statuses for each GT label:

- DETECTED: supported confirmed/vulnerable finding, matching SWC and resolved source
  function or evidenced execution flow. A matching suspicion alone is insufficient.
- MISSED: target was evaluable and examined but no supported match; includes successful
  discovery that omitted it. This evaluation status does not mean the function is safe.
- INCONCLUSIVE: source exists but relevant analysis failed, was budget-skipped, incomplete
  or abstained. Keep these labels in the recall denominator.
- UNEVALUABLE: source/GT location cannot be established; exclude and report separately.

Strict SWC-aware recall is `DETECTED / (DETECTED + MISSED + INCONCLUSIVE)` with
preparation/evaluation coverage alongside it. There are three currently resolvable GT
units. The existing B v1 historical evaluator's transport-failure denominator differs;
do not reuse its headline recall without applying these same cohort rules.

B v2 has free-text types rather than a mandatory SWC result field. Assign semantic
SWCs to every emitted finding, including unlabelled ones, before opening GT metadata;
retain uncertain mappings for manual review. Do not add target SWCs to prompts or map
only findings near expected labels. Matching evidence must reference supplied source.
Keep exact duplicate IDs and overlap/disagreement records; count each GT unit once.
Unmatched findings are additional unlabelled findings pending source review, not
automatic false positives. LLM confirmation is not dynamic exploit validation.

Report actual count/generation endpoints, input/output/total tokens and unknown-usage
attempts from the ledger, without adding cached usage twice. Report eligible, included,
examined, selected, unselected, failed and budget-skipped functions/candidates. Source
context reduction uses `1 - selected_source / repeated_full_source_baseline` and is
reported separately for B v2 verification, excluding discovery prompt tokens; it is
not an accuracy metric or a full API-token saving estimate.

## Offline baseline and current comparison

New Slither runs used the same sanitized source/dependency graphs and installed
compilers, with a 60-second subprocess timeout. No historical Slither artifact was
reused as if model/configuration matched. Matching is category plus GT function and
available lines; records and matching detector IDs are stored separately.

| Contract | GT vulnerabilities | Slither (new offline) | B v1 | B v2 |
|---|---:|---|---|---|
| ProjectWalletAuthoriser | 1 | DETECTED: unchecked-transfer | Not run | Not run |
| CoreVoting | 1 | DETECTED: reentrancy-no-eth | Not run | Not run |
| LeverageService | 1 | MISSED: no tx-origin match | Not run | Not run |

Total raw Slither findings, including dependencies: 10, 29 and 31. They are not
additional true vulnerabilities by default. This is static matching, not exploit
confirmation. No B v2 accuracy claim is possible before inference and adjudication.

## Reproduction and validation

Offline preparation can be repeated in a **new** preparation directory:

```bash
.venv/bin/python scripts/prepare_development_experiment.py \
  --selection experiments/mode-b-v2-development-2026-11-09/selection.json \
  --output experiments/mode-b-v2-development-2026-11-09/reprepared
```

This never constructs an API client. Plans are checksum-bound and output locations
must remain unused. To reproduce a static baseline, pass the exact source path from
`cohort.json` to `scripts/run_development_slither.py SOURCE --output NEW.json`.

Added `development_experiment.py`, three CLI scripts, 13 mocked/offline runner tests,
the experiment artifacts and this document. Full offline regression: **292 passed,
0 failures, 0 errors, 0 skips** with real OpenAI client construction blocked. Tests
cover both methods, completed-request reuse, call/token budget continuity, uncertain
interruptions, corrupted/missing journals, changed manifests/configuration and input
caps. Historical artifact checks covered 1,298 files. No inference API calls, source
modifications, commits or pushes were made.

Known limits: only three development cases; adjacent-project exposure for Timvi;
inherited scope differs between architectures; SOURCE_FALLBACK lacks IR relationships;
three-candidate verification cap can lower recall; manual semantic SWC mapping needs
an adjudication record; crash gaps deliberately block uncertain replay. The next
step is approval of **only the first B v2 case**, inspection of its supplied evidence,
usage and failure status, then a decision whether to authorize more runs. Freeze a
separate held-out cohort and evaluation protocol later.

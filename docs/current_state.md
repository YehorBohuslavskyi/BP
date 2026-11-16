# Current state — 16 November 2026

## Implementation

Mode B direct detection is the main research method. It combines structural
hypothesis discovery with source-grounded selective verification. Mode A local
Slither and Mode C Slither-plus-LLM verification remain available for comparison.

Current code includes `function-index-v1`, `verdict-consistency-v4` and
`investigation-limits-v1`. The compiler index links exact source IDs for calls,
callers, modifiers, state declarations and direct writers. Verification receives
navigation metadata and explicitly requests source before citing it. Unresolved
dynamic targets and incomplete caller sets remain unknown.

The scanner provides local preparation, Codex subscription or optional API
execution, explicit consent, JSON/HTML reports and configurable limits. Source-only
reindexing rebuilds explicit development cases without loading evaluation labels.
See [navigation and limits](function_navigation.md) and
[subscription setup](scanner_subscription.md).

## Latest validated result

- Full local offline suite: **580 tests passed**, no failures, errors or skips
  after the documentation/import cleanup using `scripts/run_offline_tests.py`.
- All **2,386 historical files** under `runs/` and `experiments/` remain unchanged.
- Twelve separate historical saved-response reviews retain their prior outcomes.
- One authorized handcrafted LinkedWithdrawal control confirmed high-severity
  reentrancy through an unguarded caller after seven retrieved fragments and four
  verification rounds. Five Codex turns used 73,863 reported tokens, with no
  processing/consistency failures or skips. The one-time approval is consumed.
- Compact [summary](reviews/function-navigation-2026-11-16/summary.json) and exact
  [final evidence view](reviews/function-navigation-2026-11-16/final-assessment.json)
  accompany the source. Full original journals remain separate locally.

This control establishes the analysis path works. It does not measure independent
precision/recall, prove a model-wide improvement or demonstrate an executed exploit.

## Preserved limitations and research gates

PRA remains finalized partial. Its saved `unlock()` confirmation and `set(...)`
rejection remain blocked; `lock()` passes only as the original inconclusive
assessment in a separate read-only review. `setACL` remains skipped.

The malformed historical report at
`runs/mode-b-v2-verification-retry-2026-11-09-01/analysis/report.json` remains
unchanged. The original reuse audit still fails closed on it. Isolated unit
fixtures allow the remaining scope tests to run; a green suite does not remove
that integrity gate. No historical artifact was repaired to obtain passing tests.

The latest larger saved v4 pilot examined 65 function rows across two development
files: four inconclusive results, five budget skips and no accepted confirmations
or rejections. The navigation update retains all 65 rows but needs seven summary
batches instead of five. Frozen preparations and approvals cannot be reused under
the changed implementation; regenerate source-only proposals into new directories.

## Next step

After cleanup and publication, prepare a small three-contract development plan.
Use predeclared source-only ordering, distinct projects and exposure registries.
Do not use labels or prior model verdicts to choose convenient cases. Keep all
three outside validation/held-out cohorts, preserve source and compiler proofs,
freeze model/backend, code and limits, and obtain fresh execution approval.

Track confirmed, rejected, inconclusive, processing failures, skipped candidates
and full usage separately. Accuracy evaluation comes after the protocol and
evaluation plan are frozen. No automatic PRA rerun, retry or cohort advancement.

## Historical context

Earlier pilot metrics and the chronological development record are preserved in
[the pre-cleanup state](history/current_state_before_cleanup_2026-11-16.md),
[the previous README](history/README_before_cleanup_2026-11-16.md), and the original
protocol/review documents. Those records describe different study conditions;
do not combine their metrics with the current development control.


Exposure review during the next pilot preparation also checks legacy direct-run
function request journals against their source hashes. Prepared/unrun manifest
cases remain eligible; actual requests, including unknown outcomes, do not.
The first preliminary plan was superseded before execution after this audit found
prior ExchangeService exposure. No labels or model verdicts drive the replacement.

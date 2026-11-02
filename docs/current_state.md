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

## NEXT SESSION: MODE B — DIRECT DETECTOR V2

Research direction only; not implemented in this cleanup:

1. Contract-level discovery pass.
2. Compact structural contract summary.
3. Systematic vulnerability-category sweep.
4. Cross-function reasoning.
5. Candidate vulnerability generation.
6. Selective-context candidate verification.
7. Whole-contract aggregation.
8. Separate development and held-out evaluation sets before experimentation.

Mode B is the next primary development target. Preserve Mode A/C comparisons,
GT isolation, frozen pilot evidence and bounded explicit execution controls.

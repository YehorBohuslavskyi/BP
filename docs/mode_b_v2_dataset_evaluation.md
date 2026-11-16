# Mode B v2 dataset evaluation — frozen offline plan

This experiment measures Mode B v2 alone. No baseline or other inference mode is
run or compared. All preparation is offline; live execution awaits explicit approval.
The prepared directory is `experiments/mode-b-v2-dataset-2026-11-09/`; the unused
execution directory is `runs/mode-b-v2-dataset-2026-11-09/`.

The [manifest](../experiments/mode-b-v2-dataset-2026-11-09/manifest.json) freezes source,
dependency/catalog/compiler provenance, model, prompts, schemas, code, verifier settings,
per-case caps, cohort totals, selection and scoring rules. Its SHA256 is
`2a98b83a1b3a8311924260f17acfa34957f84a1ddaa5a67e98e6c9391772ad4e`.
The [preparation report](../experiments/mode-b-v2-dataset-2026-11-09/preparation_report.json)
and selection log retain readiness results. Exact original paths are in each manifest
case's `source` and `dataset_file`; no source files were downloaded or edited.

## Selection and readiness

| Cohort | Contract/source basename | Declared functions | Summary rows | Compiler | Declared preparation | GT labels/resolvable | Max new generation + count calls |
|---|---|---:|---:|---|---|---:|---:|
| Development | ProjectWalletAuthoriser | 2 | 6 | 0.4.25 | FULL_INDEX | 1/1 | 9 + 9 |
| Development | CoreVoting | 12 | 18 | 0.8.24 | FULL_INDEX | 1/1 | 11 + 11 |
| Development | LeverageService | 9 | 9 | 0.5.11 | 8 FULL_INDEX, 1 SOURCE_FALLBACK | 1/1 | 10 + 10 |
| Held-out | BaseParaSwapAdapter | 7 | 17 | 0.6.12 | FULL_INDEX | 2/1 | 10 + 10 |
| Held-out | Main (Coalichain) | 7 | 7 | 0.4.25 | FULL_INDEX | 2/1 | 10 + 10 |
| Held-out | PRA | 6 | 7 | 0.6.12 | FULL_INDEX | 1/1 | 11 + 11 |
| Held-out | Governor (OriginDollar) | 12 | 12 | 0.5.11 | FULL_INDEX | 4/4 | 10 + 10 |
| Held-out | CompHelper | 3 | 3 | 0.7.6 | FULL_INDEX | 1/1 | 10 + 10 |
| Held-out | Fundraiser (Cosmos) | 7 | 7 | 0.4.25 | FULL_INDEX | 3/1 | 10 + 10 |
| Held-out | OVM_L1ERC20Gateway | 3 | 17 | 0.7.6 | FULL_INDEX | 2/2 | 10 + 10 |

There are **68 declared functions** and **103 structural-summary rows**, all included.
Additional rows are inherited functions. Declared preparation is 67 FULL_INDEX and
1 SOURCE_FALLBACK. LeverageService has nine rows with incomplete relationship metadata
because one failed IR analysis affects dependency completeness; validated source remains
available. Unknown relationships remain unknown.

The original three development cases are retained. The held-out candidates are the
first seven lexicographically eligible files from mirrored local DAppSCAN SWC reports,
with 2–12 lexical function declarations and <22,000 source characters, local dependencies,
installed compiler support, <=30 summary rows, <=2 batches and at least one unambiguous
GT target. Historical pilot-manifest projects and development projects are excluded.
Only one file per new project is selected. Whitespace/comment-normalized source token
fingerprints reject exact equivalent source copies. This is token equivalence screening,
not proof that arbitrary semantic clones do not exist. The full screening universe,
project exclusions and attempted preparation exclusions are retained. No selection
criterion uses LLM outcomes or predicted detection success.

The seven held-out cases have not been used for B v2 live inference or prompt tuning.
Their compilation and label metadata were inspected for readiness/selection. They are
a newly frozen, small held-out cohort, not evidence of population representativeness
or independence from model training data. Timvi development has prior project exposure.

## Ground truth and effective category diversity

Ground truth is stored only in `evaluation_only/labels.json`, separately hash-bound in
the manifest. It never enters discovery, candidate payloads or context retrieval.

| SWC | Total labels | Precisely resolvable labels |
|---|---:|---:|
| 104 | 9 | 9 |
| 107 | 5 | 4 |
| 115 | 1 | 1 |
| 102 | 2 | 0 |
| 101 | 1 | 0 |

Four labels are UNEVALUABLE under strict location rules: BaseParaSwapAdapter's named
`_pullAToken` location cannot be resolved consistently; Main's pragma-only SWC-102
label has no function; Fundraiser's arithmetic/compiler labels span the file without
an unambiguous function. These remain in coverage accounting. The potentially evaluable
set is **14/18 labels**, covering three effective SWC categories. Held-out potential
coverage is 11/15. No category-only or whole-file hits will inflate recall.

Each prepared case includes source/dependency hashes and catalog sanitization checks.
The existing annotation sanitizer blanks benchmark comments while preserving source
positions. Model messages use existing whitelists and opaque IDs. Original unsanitized
contracts, audit prose, known vulnerable line numbers, Slither findings and expected
answers are never sent to the model. Ordinary function source locations are permitted
as index metadata; GT locations are never separately supplied.

## ProjectWalletAuthoriser recovery

`discovery_recovery.py` validates the original discovery file checksum and manifest,
current source/catalog/structure/location hashes, original model/schema/request,
normalizer identity and every recovered candidate/audit entry. It rejects provenance
or candidate changes. All three candidates resolve to real FULL_INDEX functions:
`setAuthoriser(address)`, `transfer(address,address,uint256)`, and inherited
`_transferOwnership(address)`. Existing conservative deduplication yields three issues.

The import retains original model IDs, qualified original identity fields, normalized
identities, original prompt, historical 2,945 tokens and original response provenance.
It is explicitly marked `explicit_historical_discovery_import`, with no ordinary
executed discovery manifest. The verifier accepts it only through an explicit,
revalidated `recovery_path`; normal discovery validation still rejects it. No discovery
API request is permitted for this case (transport discovery cap = 0).

The original discovery prompt differs from the now-frozen prompt. This exception is
visible in development provenance; held-out cases all use the current frozen protocol.
Historical usage is included once in combined pipeline efficiency and separately from
new-call budgets. No previous verification exists to replay.

## Resource caps and estimated cost

Model: **gpt-5.4-mini-2026-03-17**, with no automatic substitution. Each case has a
**60,000-token reservation cap**, shared across discovery and verification. Per-call
input is provider-counted and capped at 12,000; discovery output cap is 8,000 and
verification output cap is 4,000. Each case permits at most three unique verification
candidates, three rounds each, eight retrieved fragments/candidate and 8,000 estimated
source tokens/candidate. Extra candidates remain explicitly skipped.

| Approval scope | Cases | Max generations | Max count endpoints | Max reserved tokens |
|---|---:|---:|---:|---:|
| Development | 3 | 30 | 30 | 180,000 |
| Held-out (separate approval) | 7 | 71 | 71 | 420,000 |
| Both, only if separately approved | 10 | 101 | 101 | 600,000 |

Counting requests are endpoints too: maximum 60 development endpoints and 142 held-out
endpoints. Reservations are counted input plus maximum output, never refunded after
failure. The token cap may stop a case before its call cap. Historical discovery's
2,945 actual tokens and two endpoints are outside these new-call caps and disclosed
separately; combined known history plus maximum new reserved tokens is 602,945.

Planning scenario only: 1–3 candidates/case and 1–2 verification rounds gives roughly
8–21 new generations for development and 15–50 for held-out, each preceded by a count
request. Discovery may return zero candidates; actual counts are not predicted findings.
Approximate new tokens are 10–40k per case (100–400k across ten), depending on retrieval,
responses and candidate count; hard caps override estimates. Initial discovery prompt
estimates range from 1,081 to 8,159 tokens (characters/4, excluding provider schema
accounting). ProjectWalletAuthoriser pays no new discovery input. Exact counting occurs
only after approval. No current monetary price was verified offline; a dollar estimate
would be unreliable. With approved input/output rates per million tokens, actual cost
is `(input_tokens * input_rate + output_tokens * output_rate) / 1e6`.

## Exact commands and separate approvals

Approval hashes bind both the manifest AND cohort; a development hash cannot authorize
held-out execution. No live command below has been executed.

After approval of development only:

```bash
OPENAI_MODEL=gpt-5.4-mini-2026-03-17 \
.venv/bin/python scripts/run_v2_dataset.py execute \
  --manifest experiments/mode-b-v2-dataset-2026-11-09/manifest.json \
  --cohort development \
  --approved-plan-sha256 3178e3948809a8f1a920ae0e9815dd2a53fd8130e49e19e7b7b69e15a3c38688 \
  --run
```

After development inspection and **separate held-out approval**:

```bash
OPENAI_MODEL=gpt-5.4-mini-2026-03-17 \
.venv/bin/python scripts/run_v2_dataset.py execute \
  --manifest experiments/mode-b-v2-dataset-2026-11-09/manifest.json \
  --cohort held_out \
  --approved-plan-sha256 6decc0c7e79946a8781be5679862e303cd40421b77285a7855ef3e0fae39be02 \
  --run
```

The runner processes exactly one cohort sequentially and writes checkpoints after each
contract. It validates every selected source/import before any API access. It stops on
partial/error/budget outcomes. Explicit `--resume` validates manifests, finalized report
seals, request journals and ledgers; completed work is reused without calls. Uncertain
requests never auto-replay, and reservations/counters cannot reset. After reviewing a
finalized partial case, `--resume --acknowledge-partial CASE_ID` may explicitly skip its
saved partial result and continue within the already approved cohort. It never reruns
that partial case. Acknowledgement is not allowed for an unfinalized uncertain request.
A changed model, prompt, code, catalog or source requires a new reviewed plan.

The existing `JournalTransport`, counted smoke transport, candidate verifier and resolver
are reused. No alternative detector, GT-based prioritization or detection heuristic was
added. Existing modes were not modified.

## Scoring and manual review

Scoring is a separate offline command and reads only finalized inference reports for
security classification. Partial ledgers still contribute known API usage and unknown
usage counts, even if a final report is unavailable. A failed/incomplete evaluable
case is INCONCLUSIVE; it cannot become an ordinary miss because its API call failed.

A detection requires reviewed semantic SWC, exact canonical contract, exact target
fragment and source mapping, and a recorded post-inference GT root-cause match review
(`gt_match_reviewed`, `matched_label_ids`, `match_rationale`). This prevents a different
issue in the same broadly classified function from becoming a hit. Assign types to all
findings before reviewing expected labels. Pending type/match review is inconclusive.
A rejected hypothesis does not establish function safety. Successful discovery that
omits an evaluable GT target counts as MISSED. Unresolvable GT is UNEVALUABLE.

- Strict recall: DETECTED / (DETECTED + MISSED + INCONCLUSIVE).
- Conclusive-only recall: DETECTED / (DETECTED + MISSED).
- Evaluation coverage: evaluable labels / all selected GT labels.
- Conclusive coverage: (DETECTED + MISSED) / all selected GT labels.
- Inconclusive rate: INCONCLUSIVE / evaluable labels.

Per-SWC and per-cohort results use the same denominators. Report four unresolvable
labels and category exclusions explicitly. Avoid drawing held-out conclusions from
development results or pooling the historical-prompt exception without disclosure.

Confirmed unmatched findings are exported for review with source, evidence, claimed
flow, severity and duplicate/overlap IDs. Other candidates retain their verdicts
separately. No manual label is auto-assigned. Allowed adjudication values are VALID,
PLAUSIBLE, LIKELY_FALSE_POSITIVE, DUPLICATE and UNRESOLVED. Decided-only precision is
VALID / (VALID + LIKELY_FALSE_POSITIVE), limited to confirmed findings with a written
rationale; disclose the decided count and remaining uncertain cases. Duplicates do
not increase detection counts. LLM confirmation is never dynamic exploit validation.

After finalizing development inference, generate a review template/report:

```bash
.venv/bin/python scripts/run_v2_dataset.py summarize \
  --manifest experiments/mode-b-v2-dataset-2026-11-09/manifest.json \
  --cohort development \
  --output runs/mode-b-v2-dataset-2026-11-09/development-summary-initial
```

Fill a copy of `adjudication_template.json` manually, then repeat summarize with
`--reviews PATH_TO_REVIEWED_COPY --output NEW_SUMMARY_DIRECTORY`. Summarize defaults
to development; `--cohort held_out` or `all` must be explicit. Reports for unexecuted
cases are incomplete, never evidence of a completed evaluation.

Source-context reduction remains the existing verification metric:
`1 - selected_source_estimated_tokens / repeated_full_source_baseline_tokens`.
Discovery API tokens are separately included in efficiency. This is not detection
accuracy or a direct measurement of all API-token savings. Tokens per contract and
candidate, average rounds, preparation modes, discovery/verification failures, budget
stops and unselected functions remain visible. Known partial-ledger usage and unknown
paid request usage are both reported; resume does not add historical tokens twice.

## Outputs and reproducibility

```text
experiments/mode-b-v2-dataset-2026-11-09/
  manifest.json, approval_checksums.json, preparation_report.json
  screening_universe.json, selection_log.json
  prepared/<case>/structure.json, sanitization.json
  evaluation_only/labels.json
runs/mode-b-v2-dataset-2026-11-09/       # created only after approval
  development-execution.json, held_out-execution.json
  <cohort>/<case>/
    run_manifest.json, requests/, budget_ledger.json, transport_checkpoint.json
    analysis/discovery.json, summary.md, verification_manifest.json
    analysis/sessions/, report.json, report.md
    finalized.json
  <summary>/summary.json, labels.csv, contracts.csv, report.md
  <summary>/additional_findings.json, adjudication_template.json
```

Raw invalid model response strings remain excluded from ordinary logs. Safe diagnostics,
returned usage and processing status are retained. Original datasets and historical
inference artifacts are preserved. Summaries use fresh directories; manual review does
not overwrite inference outputs.

Preparation can be reproduced with `scripts/prepare_v2_dataset.py --dataset-root
/home/coca-cola/projects/DAppSCAN --output NEW_PREPARATION_DIR --run-output NEW_RUN_DIR`.
Both destinations must be unused; changed absolute paths produce new checksums and need
new approval. No API client can be constructed during that preparation.

Implementation adds the explicit recovery importer, B v2 dataset runner, post-inference
scorer, two scripts and offline tests. The shared verifier gains an opt-in recovery
validation path and explicit recovery provenance in reports; ordinary validation remains
strict. Final test/integrity results are recorded in the preparation directory.

Known limits: small source-size-selected sample; four imprecise GT labels; only two
strictly scoreable held-out SWC categories; incomplete IR in one development function;
three-candidate caps can constrain recall; all type/root-cause/precision adjudication
requires manual work; crash gaps intentionally refuse uncertain replay. No detection
performance has yet been measured for this new dataset plan.

Final validation: **334 offline tests passed, 0 failures, 0 errors, 0 skips**. All
10 source/import preflights passed with API clients blocked. Python compile checks
and `git diff --check` passed. All **1,337 pre-existing artifact files** checked retained
their hashes. No live API calls, downloads, commits or pushes occurred. The new inference
output directory remains absent. The plan stops here pending development-cohort approval.

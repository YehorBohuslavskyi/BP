# Mode B v2 large benchmark — offline preparation v1

This workflow audits the local labelled DAppSCAN corpus and proposes a larger benchmark.
It has **no inference command**. Compilation, IR/index construction and structural
summary generation are offline preparation; no contract is deployed/executed and no
LLM is invoked. The original ten-contract benchmark and all historical experiments
remain unchanged.

## Run preparation

```bash
.venv/bin/python scripts/prepare_large_v2_benchmark.py prepare \
  --dataset-root /home/coca-cola/projects/DAppSCAN \
  --output experiments/NEW_LARGE_BENCHMARK_DIRECTORY \
  --max-source-bytes 40000 \
  --max-functions 30 \
  --max-summary-functions 80 \
  --max-batches 4 \
  --max-per-project 3 \
  --timeout-seconds 45 \
  --development-percent 20 \
  --validation-percent 20 \
  --near-duplicate-threshold 0.85 \
  --seed mode-b-v2-large-preparation-v1
```

The remaining 60% hash buckets are held-out. Historical groups override the bucket and
are development-only. Percentages apply to independent project groups before readiness
outcomes, not to final selected file counts. Projects can contribute multiple distinct
files, capped at three after preparation/deduplication. Changing limits/seed produces
a new proposal in a new directory; it does not change any frozen experiment.

Labelled files are discovered from all local mirrored SWC reports (with existing-loader
fallback for non-mirrored projects). Labels are parsed exclusively by `DAppSCAN.labels`.
No SWC-category subset is used. The audit unit is a labelled source file; multiple
contracts/inherited functions in a file are reported separately in source metadata.

## Project separation and duplicate protection

The script examines prior experiment JSON under examples, experiments, runs, benchmarks,
results and docs. Screening universes, evaluation-only records and audit inventories are
excluded as evidence of prior use: merely auditing a candidate is not model exposure.
Actual historical selected/source references are hashed in `history_provenance.json`.
Previously selected/reserved experiment projects are conservatively development-only,
including projects reserved in the earlier ten-contract plan.

Groups are computed over the entire labelled corpus **before** preparation filtering:

1. All sources in one DAppSCAN project stay together.
2. Comment/whitespace-independent token fingerprints detect exact source-content copies.
   String literal contents are preserved.
3. Normalized project names group obvious audit/vendor/version variants.
4. Exact Jaccard comparisons of five-token shingle sets group near-source variants at
   the configured threshold. A size-ratio prefilter is safe and does not drop threshold
   matches. Short sources use exact fingerprints and project-family grouping.
5. Links are transitive; if any member was historically selected, the whole group stays
   in development. Otherwise a seeded SHA256 bucket assigns development/validation/held-out.

Exact/near source copies also share a source group; only the first eligible prepared
representative is proposed. Distinct source files in a project may remain. All group,
source-equivalence and historical exclusion invariants are checked before publication.
This prevents crossing for detected copies/variants; it is not proof that arbitrary
semantic clones or transformations below the threshold cannot exist. Review group
links before freezing an actual held-out inference plan.

## Local-only compiler-backed preparation

The existing sanitizer, dependency graph, compiler compatibility rules, source indexer,
fragment catalog and structural discovery component are reused. The script first
selects the existing deterministic compatible installed compiler and records its exact
version and current binary hash. That version is passed as a pin to the worker and
checked against compiler-backed metadata. There is no installation, alternative-version
retry, dependency download, package install or fabricated dependency fragment.

Each worker has a deadline; timeout kills its process group and records a failure.
Workers strip API credentials from the child environment, block OpenAI construction
and network connection, and call structural discovery with execute=False. Full source
provenance, dependency hashes, sanitizer/indexer identities and source locations are
preserved. Every catalog fragment is matched to its sanitized UTF-8 source span.
Discovery transport is checked for benchmark fields. GT labels/descriptions/audit
references remain in `evaluation_only/records.json`, not worker model inputs.

`FULL_INDEX`, `SOURCE_FALLBACK`, null unknown IR relationships and per-function
`UNEVALUABLE` metadata remain as produced by the existing preparation. Audit-level
READY means within the configured complete-coverage limits, not full IR availability
or a security conclusion. Files excluded after successful compilation still retain
structural summaries and their exact failure/limit status.

Size exclusions occur before dependency/compiler work. Function limits are applied to
compiler-backed declared counts and summary rows, not guessed from regex. A worker
failure is not a vulnerability miss. Missing dependencies report the first unavailable
import encountered; fixing it may expose additional missing imports. Compiler version
unavailability is distinct from failure of the compiler-backed worker; diagnostics
for the latter retain the underlying cause.

## GT resolution and scoring

The existing frozen target-resolution helper and scoring protocol are reused. Full
signatures preserve overload distinctions. Multiple plausible locations remain
AMBIGUOUS; named-function versus reliable/raw-range contradictions are CONTRADICTORY;
missing/non-function locations remain UNRESOLVED. Raw spaced ranges are checked for
contradictions but do not silently widen the original frozen scoring locations.
Only RESOLVED targets qualify as resolvable labels. Unknown locations are never invented.

The audit reports resolution for compiler-prepared files and explicitly counts labels
on unprepared files as not compiler-resolved. It does not claim to have resolved or
fully diagnosed all GT locations on files excluded before compilation. A proposed case
must have at least one resolvable GT label; its other ambiguous/contradictory labels
remain visible. No recall, precision or vulnerability detection is measured here.

## Output publication and interruption recovery

Preparation writes to a private sibling staging directory. It publishes the final
directory through one rename only after processing every labelled file and validating
split/source invariants. Fatal preparation errors clean the staging directory and leave
no final directory. Existing final directories are refused. Forced process termination
can leave an unpublished hidden staging cache; this is never a completed benchmark.

An explicit `--resume-preparation-from PATH_TO_UNPUBLISHED_STAGING` can reuse completed
compiler-backed structures. It revalidates source, dependency content, sanitizer/indexer
identity, exact compiler version, catalog/structure/location hashes and every source
span, then recomputes GT resolution, limits and splits. No partial/missing entry is
accepted as a finished result; absent entries are freshly prepared. Cache provenance
mismatches abort rather than silently substituting data.

The first interrupted cache format records exact compiler version but not the original
compiler binary hash. That historical hash is explicitly null in cache provenance;
the currently pinned binary hash is recorded separately. No missing hash is invented.
Fresh non-resumed preparation records the binary hash at preparation. For provenance
policies requiring a historical binary hash for every worker, perform a fresh audit
rather than using this legacy interrupted cache.

Published files:

```text
manifest.json                 # Proposed cases, hashes, protocols, caps; approval_required=true
audit.json, audit.md           # Counts and exclusions
split_groups.json             # Project groups, splits and source-similarity links
history_provenance.json        # Historical references that force development placement
blockers.json                 # Missing imports, compiler/version, timeout/worker blockers
evaluation_only/records.json   # Full audit records and GT resolution, isolated from inference
prepared/<source-id>/
  structure.json              # Offline structural summaries, zero calls
  provenance.json             # Compiler/preparation metadata and sanitized fragment mappings
```

The concrete preparation report and validation seal for the completed run are stored
with its output directory. Detailed counts and proposed split budgets come from that
run's `audit.json`, not from manually estimated dataset sizes.

## Proposed inference budgets and approval boundary

The proposal preserves the current model `gpt-5.4-mini-2026-03-17`, prompts, schemas,
candidate selection, verifier settings and frozen scoring rules. Each proposed source
has a **60,000-token shared reservation cap**, <=12,000 input tokens/call, discovery
output cap 8,000, verification output cap 4,000, at most three verification candidates,
three rounds each, eight retrieved fragments and 8,000 estimated source tokens/candidate.

If a case has B discovery batches, maximum generation calls and count requests are each
B + 9 (up to 13 + 13 with four batches). Split/global caps are exact sums in audit and
manifest. All ceilings are joint: the shared token budget can stop a case before all
nominal calls execute. Large summaries may leave little budget for verification;
limits and incomplete coverage must remain visible in later evaluation.

These are conservative fresh-run upper bounds, **not authorization to replay existing
development work**. A future inference export must review reusable historical stages,
verify provenance and reserve only approved new work. The proposal is intentionally
not accepted automatically as an existing paid-run manifest. There is no live execution
or cohort-advance option in this script. Development, validation and held-out inference
need separately reviewed, explicit approvals and a validated budgeted execution export.
No current dollar price or detection-accuracy claim is made from offline preparation.

## Completed validated proposal

Canonical output: [mode-b-v2-large-preparation-v1-final-2026-11-10](../experiments/mode-b-v2-large-preparation-v1-final-2026-11-10/report.md).
It audits 948 labelled files / 606 labelled projects and proposes 78 cases:
42 development, 9 validation, 27 held-out, with 112 resolvable GT labels.
The earlier task-local proposal directories are superseded validation drafts.
The final regression result is 376 passing offline tests, including 25 preparation tests.
All 1,506 checked pre-existing artifact/runtime files were unchanged.

The exact proposed fresh-run cap is 834 generations + 834 count requests and
4,680,000 reserved tokens. This is an offline proposal requiring separate review,
validated execution export and approval; no cohort has advanced.

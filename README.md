# Smart Contract Vulnerability Verifier

A bachelor-thesis prototype for selective-context smart-contract vulnerability
analysis. **Mode B — Direct LLM Detection** is the primary research method;
Slither detection (Mode A) and Slither + LLM verification (Mode C) provide comparisons.
The model can request additional source fragments across bounded rounds.

See [current state and next milestone](docs/current_state.md) for frozen pilot
metrics, known limitations, and the next development session.

## Installation

Python 3.12 or newer is required. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[gui,dev]'
solc-select versions
```

Slither is a core dependency. Install the solc releases needed for your sources with `solc-select install VERSION`. The application selects an already-installed compatible compiler in a child process; it never installs compilers or changes the global solc selection. Supported GUI pragma forms are exact versions, caret, tilde, comparator conjunctions, and `||` alternatives. Other syntax produces an explicit unsupported-pragma message.

Set `OPENAI_API_KEY` in the environment that launches the application. `OPENAI_MODEL` supplies the initial model selection; you can select or type a different model ID in the sidebar. Optionally set `OPENAI_MODELS` to comma-separated IDs to populate the dropdown. Entered IDs must be available to your API account and support structured responses. Switching models affects only your session and makes no API request until you click Verify. Saved results retain their original model. The key is never shown in the GUI, saved in results, or accepted as a source upload. Keep credentials out of version control. Network access and model availability are required only for inference; Slither and context preparation run locally.

## GUI

```bash
.venv/bin/streamlit run streamlit_app.py
```

Open `http://localhost:8501`. Upload one self-contained UTF-8 `.sol` file (up to 1 MiB), choose an installed compiler, and click **Run Slither**. Select one finding and click **Verify selected finding** to send its source context to the configured model. This button can incur API charges; uploading, selecting a finding, downloading results, and Streamlit reruns do not start inference.

Verification defaults to **4 rounds (recommended)**; the sidebar allows **1–10 rounds**. The verifier stops early on a final verdict. This interactive limit does not change frozen research settings.

The GUI shows finding details, numbered source, verdict/explanation, cited evidence, requested context, rounds, reported tokens, and context-size estimates. Download JSON includes the current source, findings, successful verification history, and reported usage. `inconclusive` remains an abstention. Errors are displayed separately, with no automatic retries.

Uploads live in owned temporary directories, separate from datasets and research outputs. Replacing/removing an upload clears its analysis and releases its directory; normal object/process cleanup also removes temporary files. Abrupt termination may leave OS temporary files. A compiler change takes effect on the next explicit Slither run. Existing results display the compiler/model that actually produced them.

V1 supports a single source file without imports, and warnings with a resolvable contract/function. Its selective context includes modifiers, state declarations, and direct writers; it does not retrieve arbitrary external projects. Token-size estimates use characters/4, whereas API usage comes from responses. Code-context reduction compares unique source-fragment estimates with the full Solidity source only. It never uses API input tokens or JSON payload size. Distinct overlapping fragments can still produce zero or negative reduction; this is displayed without clamping. Failed calls may have usage that was not returned by the provider.

The server binds to localhost by default. This is a local demonstration, not an internet-facing untrusted-compilation service.

## Context metrics and result export

**Source context efficiency** uses `ceil(characters / 4)` for code strings only:

- Full Solidity source.
- Initial selected code (the target function).
- Additional requested code actually sent in a subsequent round.
- Cumulative selected code (initial plus additional).
- Reduction: `1 - cumulative_selected_source_estimated_tokens / full_source_estimated_tokens`.

Fragments are counted once per ID, not once per repeated API transmission. A request in the final allowed round has no later model call and is excluded from sent-code totals. Empty full source has undefined reduction. Fragment overlap and per-fragment rounding can make code totals exceed full-source estimates, especially for small sources; the UI reports that honestly.

**API usage** is separate: reported input/output/total tokens, rounds, and unique requested-fragment count. Input tokens include full requests with instructions, metadata, JSON structure, and repeated context. They never enter the source-reduction formula.

Findings show compact source ranges, explicit eligibility reasons, and original-line-number excerpts with `▶` marking finding lines and `│` marking the target function. Eligibility requires supported contract/function/file/range metadata; the core still performs exact resolution before inference. Global findings such as `solc-version` cannot enter the function verifier.

The reviewed counter counts unique stable finding IDs in the current analysis and updates immediately after verification. Explicit repeat runs remain in history for usage/export but do not increment the unique count. Replacing the upload or rerunning Slither clears prior analysis state. Neither selection changes nor normal rerenders repeat analysis or inference.

GUI JSON **schema v2** exports each completed run with `finding`, `verification`, `usage`, `context_efficiency`, model/compiler, public round explanations, and source fragments with availability reasons and transmission status. The cached export updates only when analysis or verification completes. Unknown model-response fields, credentials, and hidden reasoning are not serialized. Old in-memory session results lack the new metrics and are marked as legacy rather than displaying the old payload reduction. Research JSON schemas are unchanged.

### Manual demonstration contracts

- **True positive:** `datasets/smartbugs-curated/dataset/access_control/simple_suicide.sol`, compiler **0.4.25**, detector `suicidal`, `SimpleSuicide.sudicideAnyone()`. The function directly calls `selfdestruct(msg.sender)` without access control.
- **False positive observed in the frozen pilot:** `datasets/cgt/source/efe5ebd718c6afa9c24214bb4373b40d.sol`, compiler **0.4.25**, detector `suicidal`, `ValueTrader.die()`. The `owned` modifier checks `msg.sender == owner`; the saved pilot rejected the warning. This file can contain multiple contract declarations while remaining a single import-free source. Another model/run may return a different verdict.

Both were compiled locally for this update. The TP workflow was exercised with mocked model output; the FP model call was not repeated. Local test token fixtures are not new paid-run evidence.

## Architecture and public services

- `findings.py`: Slither JSON parsing and precise source locations.
- `catalog.py`, `context.py`, `indexer.py`, `payload.py`: stable fragment identities, dependency discovery, target resolution, and request validation.
- `llm.py`, `verifier.py`: the existing prompt/schema and bounded verification loop.
- `dataset.py`, `cgt_dataset.py`, `cgt_archive.py`, `cgt_findings.py`: dataset loading and reviewed linkage.
- `evaluation.py`, `classification_metrics.py`, `reporting.py`: annotation matching, fixed-cohort metrics, and offline reports.
- `app/services.py`: `create_upload`, `analyze_upload`, `verify_selected`, `export_analysis`.
- `app/compilers.py`, `app/slither_runner.py`, `app/worker.py`: compiler compatibility and isolated execution.
- `app/session.py`: temporary-workspace ownership, stable reviewed IDs, cached export, and stale-result invalidation.
- `app/presentation.py`: compact lines, structural finding eligibility, code-only accounting, fragment metadata, and allowlisted export serialization.
- `app/gui.py`: Streamlit presentation; it calls services rather than implementing analysis.

Core import paths and signatures remain compatible. Experiment runners remain available separately from the GUI. GUI code does not read or write benchmark results.

## CLI

The core remains usable without Streamlit:

```bash
python -m context_audit.indexer --help
python check_access_control_batch.py --help
python check_cgt.py --help
python check_cgt_preflight.py --help
```

The last three runners were restored unchanged from commit `e42f911` because the recent cleanup removed them while the test suite still imported them. Other removed demonstration scripts are not required by the GUI. `context_audit.verifier.verify_finding` remains the reusable single-finding inference API; calling it may incur API charges.

## Research evidence and reproduction

SmartBugs Curated is a vulnerability annotation dataset, not a verified-negative warning dataset. Its audited access-control baseline is **9 of 21 annotations detected across 18 contracts (42.86% recall)**. Unmatched warnings are not automatically false positives.

CGT consolidated rows are contract/property assessments. Exact Slither labels require the reviewed, hash-bound linkage ledger. The accepted local cohort is **27 findings (22 positive, 5 negative; 81.48% candidate precision)**. The saved balanced 10-finding pilot reports **TP 5, FP 2, TN 3, FN 0; 22,424 tokens across 16 calls**. This selected pilot is not a whole-CGT performance estimate. The other 17 findings have not been run as part of cleanup.

See [CGT local evaluation](docs/cgt_local_evaluation.md), [cleanup report](docs/cleanup_report.md), and the saved `results/cgt_authorized_pilot/pilot/summary.json` for the current completed pilot. Earlier connection-failure/preflight reports are historical; they are preserved rather than rewritten.

Offline reproduction should write to new output paths:

```bash
python check_access_control_batch.py --output-dir runs/access-control-reproduction
python check_cgt.py --review-manifest results/cgt_reviewed_baseline/reviews.json \
  --output-dir runs/cgt-reproduction
python check_cgt_preflight.py --help
```

Do not overwrite `results/`, `benchmarks/`, or frozen snapshots. Cleanup changes current source hashes; frozen snapshots retain the exact historical implementation. The frozen pilot runner deliberately rejects changed source hashes and must not be bypassed or used to rerun completed work. New experiments need new manifests and separate output directories.

## Tests

```bash
python -m pytest -q
# The same unittest suite can run without the pytest dependency:
python -m unittest discover -s tests -v
```

Tests cover the original evaluation semantics, real local CGT integration, upload/compiler validation, isolated service transport, JSON export, and actual local Slither plus context construction with mocked inference. They make no paid API requests. The optional Streamlit AppTest smoke test skips when Streamlit is unavailable. The real-data CGT checks skip if that dataset is absent; the application integration test requires installed solc 0.4.25.

Streamlit 1.66 is now available locally. Headless AppTest checks cover startup, the 4-round default, selecting 10 rounds, and the upload/analysis/verification workflow with mocked inference. Pytest remains unavailable; the suite runs with unittest. No paid API calls are used in these checks.

### Batch verification in the GUI

After Run Slither, choose **High only**, **High + Medium** (default), or **All eligible**,
then click **Verify all eligible findings**. This uses OpenAI API tokens; the GUI shows
pending findings and their maximum round budget before execution. Informational findings
are included only with All eligible, and unsupported function/source targets are skipped.

Verification runs sequentially through the existing service and selective-context verifier.
Completed results (including inconclusive verdicts) are reused by stable finding ID, even
if you switch models. Only an explicit single-finding verification reruns a completed item.
Errors are recorded individually and can be retried by a subsequent explicit batch action.
Normal widget rerenders run neither Slither nor inference.

Select a results-table row or use Finding to inspect to see source, evidence, explanation,
context efficiency, and actual usage. Export full analysis downloads schema-version-3 JSON
with every finding, status, skip/error details, latest verdicts, and cumulative reported
usage (including explicit reruns). Failed attempts can have unreported API calls/tokens;
the export marks usage incomplete in that case. Average rounds covers successful reports.
Clear verification results clears GUI results and usage only; upload and Slither analysis
remain, and no research files are modified.

Launch: `.venv/bin/streamlit run streamlit_app.py`

### Thesis presentation dashboard

The GUI opens on **Evaluation Dashboard**, a read-only view of the completed
**10-finding balanced pilot** (5 true + 5 false findings). The headline results are
60% false-positive reduction and 100% true-finding retention, followed by comparison
cards, two bar charts, saved finding outcomes, false-positive case details, and a
confirmed pilot example with its recorded source-only context estimates.

Pilot precision (50% → 71.43%) is explicitly separate from the reviewed 27-finding
CGT cohort precision (81.48%). SmartBugs detection recall appears as a separate
experiment. Pilot recall measures retention among known true candidates, not
whole-dataset detection recall. Missing artifacts show an availability message.

Read-only inputs:
- `results/cgt_authorized_pilot/pilot/summary.json`
- `results/cgt_authorized_pilot/pilot/findings.json`
- `results/cgt_reviewed_baseline/summary.json`
- `benchmarks/access_control_baseline.json`

Reviewed linkage records and their referenced raw Slither JSON provide exact claims;
local CGT sources resolve legacy byte-offset evidence IDs. Unavailable anonymous
fragments are marked explicitly. No model reasoning or raw response JSON is displayed.
The dashboard never starts Slither or API calls. **Analyze Contract** retains upload,
single/batch verification, model controls, and export. Navigation retains session results.

Analyze Contract presents two stages: **1. Slither static analysis** contains only
candidate warnings, severity counts, and source claims; **2. LLM finding verification**
makes batch verification the primary action. Comparison cards show warnings before
verification and confirmed/rejected/skipped outcomes afterwards. Live LLM rejections
are not independently validated ground truth. Pending, inconclusive, skipped, and error
cases remain visible as requiring review.

Use **Contract source → Demo → Load selected demo** for the local
`simple_suicide.sol` confirmed-vulnerability example. Loading does not run Slither or
make API calls. Additional validated sources can be registered in `app/demos.py`.
The expandable inspector retains source, explanations, evidence, usage, context metrics,
and the optional single-finding verification action.

## Analysis Modes

### Mode A — Static baseline

Solidity → Slither detection. Existing baseline tools and saved experiments remain
available independently of LLM inference.

### Mode B — Direct LLM Detection (primary method)

Solidity → source/indexing → function analysis → selective context → multi-round
LLM (`request_context`) → whole-contract findings.

Final verdicts: `vulnerable / no_vulnerability_found / inconclusive`.
No Slither finding is supplied as the vulnerability hypothesis.

### Mode C — Hybrid verification

Solidity → Slither candidate finding → selective-context LLM verification →
`confirmed / false_positive / inconclusive`.
The existing GUI calls this **Slither Verification**.

Select **Analysis mode → Direct LLM Detection** in the sidebar. Paste source or
choose a local DAppSCAN project and files, index, select contracts/functions,
and press **Run direct detection**. Indexing makes no model calls. Each function
starts with its source, signature, available metadata and a catalog
of requestable fragments. SOURCE_FALLBACK omits unavailable dependency metadata.
The shared indexer uses Slither's parser and source mappings, but direct mode never invokes detectors or consumes findings.
Compatible locally installed solc versions and resolvable imports are required.

Reports retain every function session, multiple findings, evidence snippets,
context requests, errors and token usage. Contract summaries collapse only
same-target, same-type/SWC findings with identical evidence sets. Raw findings
remain intact. Context reduction compares estimated unique source tokens
supplied per session against one full source file per session; it is not an API
billing reduction estimate.

Use fresh output directories for the commands below; do not reuse frozen run paths.

```bash
.venv/bin/python -m streamlit run streamlit_app.py
export DAPPSCAN_ROOT=/absolute/path/to/DAppSCAN
# Source-only preparation (no API calls)
.venv/bin/python scripts/run_direct_detection.py /path/to/Contract.sol --output /tmp/direct-prepared
# Explicit inference; OPENAI_MODEL and OPENAI_API_KEY must already be configured
.venv/bin/python scripts/run_direct_detection.py /path/to/Contract.sol --function 'withdraw(uint256)' --run --output /tmp/direct-run
# Prepare a deterministic small pilot, including compilation errors
.venv/bin/python scripts/run_dappscan_direct_detection.py --dataset-root "$DAPPSCAN_ROOT" --prepare --limit 15 --output examples/dappscan/evaluation/direct_detection/next-pilot-prepared
# One selected pilot source; caps analysis at 20 functions unless explicitly changed
.venv/bin/python scripts/run_dappscan_direct_detection.py --dataset-root "$DAPPSCAN_ROOT" --manifest examples/dappscan/evaluation/direct_detection/next-pilot-prepared/pilot_manifest.json --limit 1 --run --output examples/dappscan/evaluation/direct_detection/next-one-case
# Offline summary; requires neither dataset nor API credentials
.venv/bin/python scripts/run_dappscan_direct_detection.py --summarize --output examples/dappscan/evaluation/direct_detection/next-one-case
.venv/bin/python -m unittest discover -s tests -v
```

DAppSCAN is read only from a local checkout; no automatic downloads occur.
The loader reads `DAppSCAN-source/contracts` and `SWCsource` JSON metadata
(`filePath`, `SWCs`, `category`, `function`, `lineNumber`), also accepting explicit
normalized JSON labels. Evaluation metadata is loaded separately and never
passed to the inference worker. The GUI reveals evaluation only after results
exist. Source-only matches are explicitly marked when reliable function/line
locations are unavailable. Additional model findings are unlabeled, not false
positives. Recall includes inconclusive labels in its denominator; precision
is not computed. SWC accuracy among detections is conditional on the matching
rule and is not an independent classifier score.

The checked-in pilot policy selects the first three files per prespecified SWC,
deduplicated, before inference. The original policy-only manifest is historical;
materialized manifests live beside the saved runs. The current clean pilot is
`clean-pilot3-run-v2`, with its preparation in `clean-pilot3-prepared-v2`. Keep
selected manifests fixed; do not replace failures based on LLM outcomes.

### Direct-mode preparation and evaluation coverage

Direct detection stages sanitized copies of the source and its resolved local
imports before indexing. DAppSCAN/SWC annotation comments are blanked while
preserving line numbers and UTF-8 byte offsets. Ordinary developer comments
and string literals remain intact. Synthetic Slither constructor-variable
helpers are excluded from the direct catalog. The verifier mode is unaffected.

Preparation selects a compatible installed solc binary directly, without global
compiler changes or downloads. Local relative imports, node_modules packages,
remappings.txt entries and vendored OpenZeppelin packages are resolved when
available. Missing dependencies are never fabricated.

Every selected case records `selected`, `pragma`, `compiler_used`,
`compiler_version_attempted`, `preparation_error`, `session_count`, and one of:
`READY`, `PARTIALLY_READY`, `COMPILER_VERSION_UNAVAILABLE`, `MISSING_DEPENDENCY`,
`COMPILATION_FAILED`, `NO_ANALYZABLE_FUNCTIONS`. A null compiler means no
compiler was attempted, rather than an incompatible fallback. Only safe sessions
from READY or PARTIALLY_READY cases participate in inference. Compiler installation is a separate explicit setup step.

Evaluation distinguishes `UNEVALUABLE` (no successfully analyzed relevant
session) from analyzed-session `INCONCLUSIVE`. A returned model response followed
by a context-protocol failure remains inconclusive, with the error preserved; a
transport failure without a returned model response is unevaluable. Coverage is
evaluable labels divided by selected labels. Recall uses only evaluable labels, including genuine model
abstentions; UNEVALUABLE labels are excluded. Selected/ready/analyzed file
counts and preparation failures are reported separately from model metrics.

The saved [pilot10_debug_prefixed](examples/dappscan/evaluation/direct_detection/pilot10_debug_prefixed.md)
run is debugging evidence only, with incomplete preparation coverage and
possible ground-truth annotation leakage. Its recall must not be used as a
thesis result. The original `pilot10/` artifacts remain preserved.

Prepare a clean single-case check before authorizing any new inference:

```bash
.venv/bin/python scripts/run_dappscan_direct_detection.py \
  --dataset-root "$DAPPSCAN_ROOT" \
  --manifest examples/dappscan/evaluation/direct_detection/pilot10/pilot_manifest.json \
  --limit 1 --prepare \
  --output examples/dappscan/evaluation/direct_detection/next-small-prepared
```

### Function-level direct preparation

Direct preparation parses compiler ASTs/source mappings before attempting IR
analysis separately for each genuine function/modifier. A function with usable
IR receives `FULL_INDEX`; an IR failure with validated source mappings receives
`SOURCE_FALLBACK`. Fallback includes exact sanitized source, signature,
visibility and source lines, but omits unavailable read/write/dependency metadata.
Other genuine functions, modifiers and state declarations remain requestable by
opaque fragment IDs. No whole-contract source is supplied automatically.

Unrecoverable source mappings are recorded as `UNEVALUABLE`. Files containing
fallback or unrecoverable functions are `PARTIALLY_READY` when at least one safe
session exists. Preparation records all discovered functions and their readiness,
counts, warnings, and per-ground-truth target readiness. File-wide discovery
counts are distinct from `session_count`, which reflects the requested filters.
`--function` accepts full signatures or bare names and can be repeated; a bare
name selects all its overloads. Evaluation admits valid sessions from partially
ready files while missing/unrecoverable target sessions remain UNEVALUABLE.

DAppSCAN ground truth must never enter inference via source annotations,
manifest labels, audit metadata, or synthetic full-source fragments. The clean
pilot's source-bearing prompt fields have no detected GT annotation leakage;
regression tests cover sanitized fallback and multi-round requested context.
Preparation is offline; only `--run` starts inference. `--summarize` is offline
but rewrites evaluation reports, so do not point it at frozen runs during cleanup.
Repeated `--file` selects all distinct explicit files unless an explicit `--limit`
is supplied; unfiltered discovery still defaults to one file.

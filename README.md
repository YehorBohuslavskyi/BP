# Smart Contract Vulnerability Verifier

A bachelor-thesis prototype that verifies individual Slither warnings using dependency-aware source context. The model can request relevant fragments and returns `confirmed`, `false_positive`, or `inconclusive`.

```text
Solidity → Slither → Finding → Dependency-aware context → LLM verifier
                                                           ↓
                                      confirmed / false_positive / inconclusive
```

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

V1 supports a single source file without imports, and warnings with a resolvable contract/function. Its selective context includes modifiers, state declarations, and direct writers; it does not retrieve arbitrary external projects. Token-size estimates use characters/4, whereas API usage comes from responses. Cumulative input reduction includes repeated requests and may be negative. Failed calls may have usage that was not returned by the provider.

The server binds to localhost by default. This is a local demonstration, not an internet-facing untrusted-compilation service.

## Architecture and public services

- `findings.py`: Slither JSON parsing and precise source locations.
- `catalog.py`, `context.py`, `indexer.py`, `payload.py`: stable fragment identities, dependency discovery, target resolution, and request validation.
- `llm.py`, `verifier.py`: the existing prompt/schema and bounded verification loop.
- `dataset.py`, `cgt_dataset.py`, `cgt_archive.py`, `cgt_findings.py`: dataset loading and reviewed linkage.
- `evaluation.py`, `classification_metrics.py`, `reporting.py`: annotation matching, fixed-cohort metrics, and offline reports.
- `app/services.py`: `create_upload`, `analyze_upload`, `verify_selected`, `export_analysis`.
- `app/compilers.py`, `app/slither_runner.py`, `app/worker.py`: compiler compatibility and isolated execution.
- `app/session.py`: temporary-workspace ownership and stale-result invalidation.
- `app/gui.py`: Streamlit presentation; it calls services rather than implementing analysis.

Core import paths and signatures remain compatible. Experiment runners remain available separately from the GUI. GUI code does not read or write benchmark results.

## CLI

The inspection commands are import-safe and support `--help`:

```bash
python check_dataset.py --limit 5
python check_evaluation.py --contract FibonacciBalance.sol --slither-json fibonacci_slither.json
python -m context_audit.indexer --help
```

Single-finding inference is explicit and may be paid:

```bash
python check_verifier.py --source examples/AccessDemoUnrestricted.sol \
  --slither-json slither_result.json --finding-id FINDING_ID --max-rounds 4
```

This command now requires explicit source, saved JSON, and exact finding ID; it no longer executes a hard-coded example when imported.

## Research evidence and reproduction

SmartBugs Curated is a vulnerability annotation dataset, not a verified-negative warning dataset. Its audited access-control baseline is **9 of 21 annotations detected across 18 contracts (42.86% recall)**. Unmatched warnings are not automatically false positives.

CGT consolidated rows are contract/property assessments. Exact Slither labels require the reviewed, hash-bound linkage ledger. The accepted local cohort is **27 findings (22 positive, 5 negative; 81.48% candidate precision)**. The saved balanced 10-finding pilot reports **TP 5, FP 2, TN 3, FN 0; 22,424 tokens across 16 calls**. This selected pilot is not a whole-CGT performance estimate. The other 17 findings have not been run as part of cleanup.

See [CGT local evaluation](docs/cgt_local_evaluation.md), [cleanup report](docs/cleanup_report.md), and the saved `results/cgt_authorized_pilot/pilot/summary.json` for the current completed pilot. Earlier connection-failure/preflight reports are historical; they are preserved rather than rewritten.

Offline reproduction should write to new output paths:

```bash
python check_access_control_batch.py --output-dir runs/access-control-reproduction
python check_cgt.py --review-manifest results/cgt_reviewed_baseline/reviews.json \
  --output-dir runs/cgt-reproduction
python check_cgt_linkage.py --help
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

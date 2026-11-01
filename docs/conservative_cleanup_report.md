# Conservative project cleanup

No production source, tests, interfaces, verifier protocol, GUI implementation, research labels, cohorts, targets, saved results, or historical evidence were changed. Existing worktree changes were preserved. Classification was written to `cleanup_manifest.md` before deletion.

## Removed files

Removed 54 generated `.pyc` files across five empty `__pycache__` directories (492,122 bytes). The exact file list is in `cleanup_manifest.md` and `conservative_cleanup_validation.json`.

- `__pycache__/`: 9 bytecode files.
- `tests/__pycache__/`: 13 bytecode files.
- `scripts/__pycache__/`: 2 bytecode files.
- `src/context_audit/__pycache__/`: 17 bytecode files.
- `src/context_audit/app/__pycache__/`: 13 bytecode files.

## Retained production and reproducibility files

- Production: `src/context_audit/`, `streamlit_app.py`, `pyproject.toml`, `.streamlit/`, installed `.venv/` and editable package metadata.
- Reproduction: all `scripts/*.py`, `check_access_control_batch.py`, `check_cgt.py`, `check_cgt_preflight.py`, `tests/`, `test/defihacklabs/`, existing integrity/source preparation tools, and pinned OpenZeppelin dependencies (`package.json`, `package-lock.json`, `node_modules/`).
- Research: all `examples/`, `results/`, `datasets/`, `benchmarks/`, and `runs/`. In particular, all 578 files under `examples/defihacklabs/evaluation/final20/` are unchanged.
- Documentation: `README.md`, `CODEX_CONTEXT.md`, research notes and existing cleanup history.

An AST name-use scan found no obvious unused production imports. No speculative refactor, duplicate-helper merge or debug-code removal was justified; production hashes also form part of the frozen experiment protocol.

## REVIEW_REQUIRED — retained

- `fibonacci_slither.json`, `rubixi_slither.json`, `simple_suicide_slither.json`, `slither_result.json`: historical standalone outputs with unresolved evidentiary provenance.
- `restricted_run.txt`, `restricted_target_only.txt`: historical LLM console captures; not proven superseded.
- `docs/cleanup_plan.md`, `docs/cleanup_report.md`, `docs/cleanup_validation.json`: historical cleanup records that may contain stale entry points; retained unchanged.
- `.git/` and managed tool/configuration directories: outside automatic cleanup scope.

## Production entry points

- GUI: `.venv/bin/streamlit run streamlit_app.py`.
- Contract/context inspection CLI: `.venv/bin/python -m context_audit.indexer --help`.
- Verifier API: `context_audit.verifier.prepare_finding`, `verify_finding`, and `verify_prepared_finding`.
- GUI verification worker: `.venv/bin/python -m context_audit.app.worker` (JSON input; not invoked during cleanup).
- Research runners and `scripts/process_defihacklabs_case.py`, `scripts/run_defihacklabs_fp_cohort.py` remain available unchanged. No inference command was run.

## Verification

| Suite | Passed | Failed | Command |
|---|---:|---:|---|
| main_python | 120 | 0 | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests -v` |
| spankchain_regressions | 29 | 0 | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B test/defihacklabs/run_validation.py --match-contract '^SpankChainValidation$'` |
| finding_regressions | 9 | 0 | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B test/defihacklabs/finding_regressions/run.py` |
| fp_cohort_workflow | 4 | 0 | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests -p test_fp_cohort_workflow.py -v` |

158 distinct tests passed. The separate four-test FP workflow invocation repeats tests already included in the 120-test Python suite.

- PASS: PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B examples/defihacklabs/evaluation/check_integrity.py.
- PASS: PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B examples/defihacklabs/evaluation/check_catalog_v2.py.
- PASS: scripts/run_defihacklabs_fp_cohort.py: verify_freeze() imported and called without CLI inference.
- PASS: streamlit.testing.v1.AppTest: dashboard then Analyze Contract; analyze_upload and verify_selected patched and asserted not called.
- PASS: import context_audit.verifier; import context_audit.app.worker.
- PASS: git diff --check.

Streamlit startup was checked through AppTest on both the default dashboard and analysis page. Production verifier and worker imports succeed. This verifies local startup/import behavior; no paid model request or live inference was performed.

## Evidence preservation

Before/after SHA-256 comparison covered 75,917 existing files: zero changed, zero missing and zero unexpected additions in the protected scan. This includes raw victims, Slither evidence, adjudications, frozen cohort, prompt journals, saved LLM results, reports and regression evidence. SmartBugs and CGT corpora/results, and scalability source/results remain available and unchanged.

`protected_digest_before` and `protected_digest_after` both equal:

`e7b4d8653a29bfe27f17de57e06ea37b0a469cd7fe20899dc0909bf9975b4ba4`

The file comparison excludes disposable `__pycache__` and Foundry `.generated` directories. Local regression runs regenerated their `.generated` build artifacts; saved evidence files were included and unchanged. The matching counts/digests and removal list are saved in `docs/conservative_cleanup_validation.json`. The full per-file baseline was held in `/tmp/bp-cleanup-protected-before.json` during this check.

The only new project files are `cleanup_manifest.md`, this report, and `docs/conservative_cleanup_validation.json`. These additive cleanup records were written after the preservation check. No existing documentation/report was rewritten.

# Conservative cleanup manifest

Classification completed before deletion. Only SAFE_TO_REMOVE entries are authorized for removal. REVIEW_REQUIRED entries are retained. Existing worktree changes are preserved. No architecture, public interface, production prompt, context policy or evidence schema changes.

Pre-cleanup protected-file snapshot: 75917 files across research evidence, sources, code, tests and docs. The per-file baseline was held at `/tmp/bp-cleanup-protected-before.json`; matching aggregate digests and the baseline file SHA-256 are recorded in `docs/conservative_cleanup_validation.json`.

| File/path | Classification | Reason | References | Final action |
|---|---|---|---|---|
| src/context_audit/__init__.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/__init__.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/batch.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/compilers.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/config.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/dashboard.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/demos.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/gui.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/presentation.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/research.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/services.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/session.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/slither_runner.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/app/worker.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/catalog.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/cgt_archive.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/cgt_dataset.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/cgt_findings.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/cgt_inference.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/cgt_sample.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/classification_metrics.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/context.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/dataset.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/evaluation.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/findings.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/indexer.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/llm.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/payload.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/reporting.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| src/context_audit/verifier.py | KEEP_PRODUCTION | Public pipeline, context, reporting, dataset or GUI implementation; production hashes are frozen. | Imported by production/tests; protocol/source hashes recorded in frozen cohort. | KEEP unchanged |
| tests/fixtures/ModifierTargetTest.sol | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_access_control_batch.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_app.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_app_batch.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_cgt.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_cgt_real.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_demo_contracts.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_evaluation.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_fp_cohort_workflow.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_gui.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_gui_presentation.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_modifier_targets.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_process_defihacklabs_case.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| tests/test_research_dashboard.py | KEEP_REPRODUCIBILITY | Active tests/fixtures; no failing or obsolete test removed. | Discovered by unittest; GUI tests use AppTest. | KEEP unchanged |
| streamlit_app.py | KEEP_PRODUCTION | Runtime entry point, configuration, installed dependencies or editable-package metadata. | README, installed environment and tests. | KEEP unchanged |
| pyproject.toml | KEEP_PRODUCTION | Runtime entry point, configuration, installed dependencies or editable-package metadata. | README, installed environment and tests. | KEEP unchanged |
| .streamlit/ | KEEP_PRODUCTION | Runtime entry point, configuration, installed dependencies or editable-package metadata. | README, installed environment and tests. | KEEP unchanged |
| .venv/ | KEEP_PRODUCTION | Runtime entry point, configuration, installed dependencies or editable-package metadata. | README, installed environment and tests. | KEEP unchanged |
| src/context_audit.egg-info/ | KEEP_PRODUCTION | Runtime entry point, configuration, installed dependencies or editable-package metadata. | README, installed environment and tests. | KEEP unchanged |
| scripts/process_defihacklabs_case.py | KEEP_REPRODUCIBILITY | Reusable source processor, inventory builder or frozen cohort runner. | CLI/workflow documentation and tests; saved run configuration references runner hash. | KEEP unchanged |
| scripts/run_defihacklabs_fp_cohort.py | KEEP_REPRODUCIBILITY | Reusable source processor, inventory builder or frozen cohort runner. | CLI/workflow documentation and tests; saved run configuration references runner hash. | KEEP unchanged |
| scripts/summarize_defihacklabs_findings.py | KEEP_REPRODUCIBILITY | Reusable source processor, inventory builder or frozen cohort runner. | CLI/workflow documentation and tests; saved run configuration references runner hash. | KEEP unchanged |
| check_access_control_batch.py | KEEP_REPRODUCIBILITY | Historical experiment runner; deleting these previously broke imports. | README, CODEX_CONTEXT.md, CGT/access-control tests and research docs. | KEEP unchanged |
| check_cgt.py | KEEP_REPRODUCIBILITY | Historical experiment runner; deleting these previously broke imports. | README, CODEX_CONTEXT.md, CGT/access-control tests and research docs. | KEEP unchanged |
| check_cgt_preflight.py | KEEP_REPRODUCIBILITY | Historical experiment runner; deleting these previously broke imports. | README, CODEX_CONTEXT.md, CGT/access-control tests and research docs. | KEEP unchanged |
| examples/defihacklabs/evaluation/final20/ | KEEP_EVALUATION | Explicitly protected final sources, labels, reports, targets, inference results, prompt journals and source dependencies. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| examples/defihacklabs/evaluation/catalog_v2/ | KEEP_EVALUATION | Versioned catalog with integrity hashes; not superseded disposable data. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| examples/defihacklabs/evaluation/contracts/ | KEEP_EVALUATION | Original pilot integration source snapshot required by integrity checks. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| examples/defihacklabs/evaluation/*.py | KEEP_EVALUATION | Provenance/inventory/source-acquisition/integrity tools and historical integration workflow. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| examples/defihacklabs/evaluation/*.json,*.csv,*.md | KEEP_EVALUATION | Original pilot/source acquisition files and integrity manifests; protected historical versions. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| examples/defihacklabs/SpankChain* | KEEP_EVALUATION | Original victim, incident ground truth and independent finding validation. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| examples/scalability/ | KEEP_EVALUATION | LargeTreasury source variants used in scalability experiments. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| datasets/ | KEEP_EVALUATION | Local SmartBugs and CGT corpora, compiler versions and labels. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| results/ | KEEP_EVALUATION | SmartBugs/access-control, CGT pilot/baseline/snapshots and scalability outputs. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| benchmarks/ | KEEP_EVALUATION | Existing structured baseline and audit/report evidence. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| runs/ | KEEP_EVALUATION | Historical run outputs; their evidentiary value is not safely superseded by filename alone. | Referenced by reports, integrity checks, GUI dashboard and/or reproduction workflows. | KEEP byte-for-byte |
| test/defihacklabs/SpankChainValidation.t.sol | KEEP_REPRODUCIBILITY | Independent local regression code, fixtures, compiler adapters and evidence; includes recorded hashes. | Adjudication documents/JSON and reproduction commands. | KEEP unchanged; generated .generated outputs may be regenerated only by authorized test runs |
| test/defihacklabs/run_validation.py | KEEP_REPRODUCIBILITY | Independent local regression code, fixtures, compiler adapters and evidence; includes recorded hashes. | Adjudication documents/JSON and reproduction commands. | KEEP unchanged; generated .generated outputs may be regenerated only by authorized test runs |
| test/defihacklabs/foundry.toml | KEEP_REPRODUCIBILITY | Independent local regression code, fixtures, compiler adapters and evidence; includes recorded hashes. | Adjudication documents/JSON and reproduction commands. | KEEP unchanged; generated .generated outputs may be regenerated only by authorized test runs |
| test/defihacklabs/evidence/ | KEEP_REPRODUCIBILITY | Independent local regression code, fixtures, compiler adapters and evidence; includes recorded hashes. | Adjudication documents/JSON and reproduction commands. | KEEP unchanged; generated .generated outputs may be regenerated only by authorized test runs |
| test/defihacklabs/finding_regressions/ | KEEP_REPRODUCIBILITY | Independent local regression code, fixtures, compiler adapters and evidence; includes recorded hashes. | Adjudication documents/JSON and reproduction commands. | KEEP unchanged; generated .generated outputs may be regenerated only by authorized test runs |
| node_modules/ | KEEP_REPRODUCIBILITY | Pinned OpenZeppelin package used for historical Solidity import resolution; not frontend clutter. | Visor analysis imports and local dependency preparation. | KEEP unchanged |
| package.json | KEEP_REPRODUCIBILITY | Pinned OpenZeppelin package used for historical Solidity import resolution; not frontend clutter. | Visor analysis imports and local dependency preparation. | KEEP unchanged |
| package-lock.json | KEEP_REPRODUCIBILITY | Pinned OpenZeppelin package used for historical Solidity import resolution; not frontend clutter. | Visor analysis imports and local dependency preparation. | KEEP unchanged |
| README.md | KEEP_DOCUMENTATION | Research methodology, entry points, setup, source lineage and experiment limitations. | Referenced by users/reproduction workflows. | KEEP unchanged |
| CODEX_CONTEXT.md | KEEP_DOCUMENTATION | Research methodology, entry points, setup, source lineage and experiment limitations. | Referenced by users/reproduction workflows. | KEEP unchanged |
| docs/cgt_notes.md | KEEP_DOCUMENTATION | Research methodology, entry points, setup, source lineage and experiment limitations. | Referenced by users/reproduction workflows. | KEEP unchanged |
| docs/cgt_pilot_execution.md | KEEP_DOCUMENTATION | Research methodology, entry points, setup, source lineage and experiment limitations. | Referenced by users/reproduction workflows. | KEEP unchanged |
| docs/cgt_local_evaluation.md | KEEP_DOCUMENTATION | Research methodology, entry points, setup, source lineage and experiment limitations. | Referenced by users/reproduction workflows. | KEEP unchanged |
| docs/gui_presentation_update.md | KEEP_DOCUMENTATION | Research methodology, entry points, setup, source lineage and experiment limitations. | Referenced by users/reproduction workflows. | KEEP unchanged |
| docs/cleanup_plan.md | REVIEW_REQUIRED | Historical cleanup records mention removed legacy entry points; may be stale but preserve development/reproduction history. | README/docs history; cannot assume safely obsolete. | RETAIN; no automatic deletion or rewriting |
| docs/cleanup_report.md | REVIEW_REQUIRED | Historical cleanup records mention removed legacy entry points; may be stale but preserve development/reproduction history. | README/docs history; cannot assume safely obsolete. | RETAIN; no automatic deletion or rewriting |
| docs/cleanup_validation.json | REVIEW_REQUIRED | Historical cleanup records mention removed legacy entry points; may be stale but preserve development/reproduction history. | README/docs history; cannot assume safely obsolete. | RETAIN; no automatic deletion or rewriting |
| fibonacci_slither.json | REVIEW_REQUIRED | Old standalone analyzer output or model console capture; exact relationship to historical experiment evidence not established. | No direct current code/test reference found in scoped text search; evidentiary provenance remains uncertain. | RETAIN; do not delete or relabel |
| rubixi_slither.json | REVIEW_REQUIRED | Old standalone analyzer output or model console capture; exact relationship to historical experiment evidence not established. | No direct current code/test reference found in scoped text search; evidentiary provenance remains uncertain. | RETAIN; do not delete or relabel |
| simple_suicide_slither.json | REVIEW_REQUIRED | Old standalone analyzer output or model console capture; exact relationship to historical experiment evidence not established. | No direct current code/test reference found in scoped text search; evidentiary provenance remains uncertain. | RETAIN; do not delete or relabel |
| slither_result.json | REVIEW_REQUIRED | Old standalone analyzer output or model console capture; exact relationship to historical experiment evidence not established. | No direct current code/test reference found in scoped text search; evidentiary provenance remains uncertain. | RETAIN; do not delete or relabel |
| restricted_run.txt | REVIEW_REQUIRED | Old standalone analyzer output or model console capture; exact relationship to historical experiment evidence not established. | No direct current code/test reference found in scoped text search; evidentiary provenance remains uncertain. | RETAIN; do not delete or relabel |
| restricted_target_only.txt | REVIEW_REQUIRED | Old standalone analyzer output or model console capture; exact relationship to historical experiment evidence not established. | No direct current code/test reference found in scoped text search; evidentiary provenance remains uncertain. | RETAIN; do not delete or relabel |
| .git/ | REVIEW_REQUIRED | Version control, tool configuration or managed files are outside cleanup scope. | Environment/tool-owned; not treated as disposable project outputs. | LEAVE untouched |
| .agents/ | REVIEW_REQUIRED | Version control, tool configuration or managed files are outside cleanup scope. | Environment/tool-owned; not treated as disposable project outputs. | LEAVE untouched |
| .claude/ | REVIEW_REQUIRED | Version control, tool configuration or managed files are outside cleanup scope. | Environment/tool-owned; not treated as disposable project outputs. | LEAVE untouched |
| .codex/ | REVIEW_REQUIRED | Version control, tool configuration or managed files are outside cleanup scope. | Environment/tool-owned; not treated as disposable project outputs. | LEAVE untouched |
| .aws/ | REVIEW_REQUIRED | Version control, tool configuration or managed files are outside cleanup scope. | Environment/tool-owned; not treated as disposable project outputs. | LEAVE untouched |
| __pycache__/ | SAFE_TO_REMOVE | Generated interpreter bytecode only: 9 files, 57598 bytes. | No explicit code/test/report references; automatically regenerated by Python. Excludes all protected data, dependencies and environments. | DELETE only listed .pyc/.pyo files and empty cache directory; remove regenerated copies after tests |
| tests/__pycache__/ | SAFE_TO_REMOVE | Generated interpreter bytecode only: 13 files, 179490 bytes. | No explicit code/test/report references; automatically regenerated by Python. Excludes all protected data, dependencies and environments. | DELETE only listed .pyc/.pyo files and empty cache directory; remove regenerated copies after tests |
| scripts/__pycache__/ | SAFE_TO_REMOVE | Generated interpreter bytecode only: 2 files, 45837 bytes. | No explicit code/test/report references; automatically regenerated by Python. Excludes all protected data, dependencies and environments. | DELETE only listed .pyc/.pyo files and empty cache directory; remove regenerated copies after tests |
| src/context_audit/__pycache__/ | SAFE_TO_REMOVE | Generated interpreter bytecode only: 17 files, 93415 bytes. | No explicit code/test/report references; automatically regenerated by Python. Excludes all protected data, dependencies and environments. | DELETE only listed .pyc/.pyo files and empty cache directory; remove regenerated copies after tests |
| src/context_audit/app/__pycache__/ | SAFE_TO_REMOVE | Generated interpreter bytecode only: 13 files, 115782 bytes. | No explicit code/test/report references; automatically regenerated by Python. Excludes all protected data, dependencies and environments. | DELETE only listed .pyc/.pyo files and empty cache directory; remove regenerated copies after tests |
| Production import/debug/duplication scan | KEEP_PRODUCTION | AST name-use scan found no obvious unused production imports. Frozen production hashes prevent behavior/protocol changes. | Core prompt/schema/context and GUI behavior protected by saved research inputs. | NO source-code changes; no speculative helper consolidation |

## Exact initial removal list

- `__pycache__/check_access_control_batch.cpython-312.pyc`
- `__pycache__/check_cgt.cpython-312.pyc`
- `__pycache__/check_cgt_frozen_pilot.cpython-312.pyc`
- `__pycache__/check_cgt_linkage.cpython-312.pyc`
- `__pycache__/check_cgt_preflight.cpython-312.pyc`
- `__pycache__/check_dataset.cpython-312.pyc`
- `__pycache__/check_evaluation.cpython-312.pyc`
- `__pycache__/check_verifier.cpython-312.pyc`
- `__pycache__/streamlit_app.cpython-312.pyc`
- `tests/__pycache__/test_access_control_batch.cpython-312.pyc`
- `tests/__pycache__/test_app.cpython-312.pyc`
- `tests/__pycache__/test_app_batch.cpython-312.pyc`
- `tests/__pycache__/test_cgt.cpython-312.pyc`
- `tests/__pycache__/test_cgt_real.cpython-312.pyc`
- `tests/__pycache__/test_demo_contracts.cpython-312.pyc`
- `tests/__pycache__/test_evaluation.cpython-312.pyc`
- `tests/__pycache__/test_fp_cohort_workflow.cpython-312.pyc`
- `tests/__pycache__/test_gui.cpython-312.pyc`
- `tests/__pycache__/test_gui_presentation.cpython-312.pyc`
- `tests/__pycache__/test_modifier_targets.cpython-312.pyc`
- `tests/__pycache__/test_process_defihacklabs_case.cpython-312.pyc`
- `tests/__pycache__/test_research_dashboard.cpython-312.pyc`
- `scripts/__pycache__/process_defihacklabs_case.cpython-312.pyc`
- `scripts/__pycache__/run_defihacklabs_fp_cohort.cpython-312.pyc`
- `src/context_audit/__pycache__/__init__.cpython-312.pyc`
- `src/context_audit/__pycache__/catalog.cpython-312.pyc`
- `src/context_audit/__pycache__/cgt_archive.cpython-312.pyc`
- `src/context_audit/__pycache__/cgt_dataset.cpython-312.pyc`
- `src/context_audit/__pycache__/cgt_findings.cpython-312.pyc`
- `src/context_audit/__pycache__/cgt_inference.cpython-312.pyc`
- `src/context_audit/__pycache__/cgt_sample.cpython-312.pyc`
- `src/context_audit/__pycache__/classification_metrics.cpython-312.pyc`
- `src/context_audit/__pycache__/context.cpython-312.pyc`
- `src/context_audit/__pycache__/dataset.cpython-312.pyc`
- `src/context_audit/__pycache__/evaluation.cpython-312.pyc`
- `src/context_audit/__pycache__/findings.cpython-312.pyc`
- `src/context_audit/__pycache__/indexer.cpython-312.pyc`
- `src/context_audit/__pycache__/llm.cpython-312.pyc`
- `src/context_audit/__pycache__/payload.cpython-312.pyc`
- `src/context_audit/__pycache__/reporting.cpython-312.pyc`
- `src/context_audit/__pycache__/verifier.cpython-312.pyc`
- `src/context_audit/app/__pycache__/__init__.cpython-312.pyc`
- `src/context_audit/app/__pycache__/batch.cpython-312.pyc`
- `src/context_audit/app/__pycache__/compilers.cpython-312.pyc`
- `src/context_audit/app/__pycache__/config.cpython-312.pyc`
- `src/context_audit/app/__pycache__/dashboard.cpython-312.pyc`
- `src/context_audit/app/__pycache__/demos.cpython-312.pyc`
- `src/context_audit/app/__pycache__/gui.cpython-312.pyc`
- `src/context_audit/app/__pycache__/presentation.cpython-312.pyc`
- `src/context_audit/app/__pycache__/research.cpython-312.pyc`
- `src/context_audit/app/__pycache__/services.cpython-312.pyc`
- `src/context_audit/app/__pycache__/session.cpython-312.pyc`
- `src/context_audit/app/__pycache__/slither_runner.cpython-312.pyc`
- `src/context_audit/app/__pycache__/worker.cpython-312.pyc`

## Verification plan

- Run all Python tests offline, including GUI AppTest and FP cohort workflow tests.
- Run both local Foundry regression suites with installed compiler binaries; retain prior saved regression evidence.
- Run both evaluation integrity scripts and the frozen-cohort hash verifier.
- Import the production verifier/worker and render the Streamlit app through AppTest without inference.
- Compare protected source/evidence/report hashes before and after cleanup; remove only regenerated disposable bytecode afterward.

A missing pytest installation is not worked around by changing project dependencies or downloading packages; use the existing unittest-compatible suite. No paid batch or evaluation is run.

## Completed verification

Removed exactly the 54 listed bytecode files and five empty cache directories (492,122 bytes). All REVIEW_REQUIRED files were retained. No production or test source was edited.

120 Python tests, 29 SpankChain tests and 9 finding regressions passed (158 distinct tests, zero failures); four FP workflow tests also passed separately. Both evaluation integrity checks, the frozen-cohort integrity check, both GUI pages through AppTest, production imports and `git diff --check` passed. All 75,917 hashed pre-existing files were unchanged. See `docs/conservative_cleanup_report.md` and `docs/conservative_cleanup_validation.json` for commands, scope and limitations.

# Cleanup and GUI plan

## Repository audit

- Core: `catalog`, `context`, `indexer`, `payload`, `findings`, `llm`, `verifier`.
- Dataset and evaluation libraries: `dataset`, `cgt_*`, `evaluation`, `classification_metrics`.
- Experiment runners: `check_access_control_batch.py`, `check_cgt*.py`. Keep their historical entry points and evaluation policies.
- Legacy demonstrations: `check_dataset.py`, `check_evaluation.py`, `check_verifier.py`. Replace import-time execution and hard-coded single-contract debug output with argument-driven adapters.
- Tests: `tests/`; currently 44 unittest cases. Pytest is not installed in this environment.
- Generated evidence: `results/`, `benchmarks/`, root Slither JSON exports. Preserve byte-for-byte, including frozen source snapshots.
- Dataset: `datasets/`. Uploads must never be written here.
- Documentation: phase/context files and `docs/`. Main README is missing.

## Decisions

1. Keep public core imports stable instead of reorganizing all modules. Add focused application modules for new behavior.
2. Preserve prompt text, response schema, context order, detector mappings, labels, and metrics. A docstring on the Pydantic response class would change the generated schema; document that class with a comment instead.
3. Remove import-time demonstration work, extract reusable evaluation reporting, improve docstrings and typing, and simplify repeated direct-writer construction.
4. Run the original tests after core cleanup before adding the GUI.
5. Build services for upload ownership, installed compiler selection, subprocess Slither execution, isolated verification, and JSON export. Use child-process compiler/model configuration; never mutate global environment across Streamlit sessions.
6. Build a thin single-file Streamlit interface. No calls on upload, rerun, or finding selection; verification requires a button click.
7. Test compiler ranges, upload isolation, subprocess/error boundaries, serialization, session invalidation, context accounting, and real local Slither/context preparation. Mock the API; no paid calls.
8. Compare all protected artifact hashes at completion. Source cleanup naturally changes current source hashes; historical frozen snapshots remain authoritative. Do not rewrite frozen manifests to make a historical runner accept changed code.

Dependency installation was attempted locally but package-index DNS resolution failed. Continue with the installed unittest runner; record unperformed Streamlit/pytest checks explicitly if dependencies remain unavailable.

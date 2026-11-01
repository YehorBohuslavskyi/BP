# GUI presentation and source-context accounting update

## Scope and preserved results

This update changes the GUI and its application services. All 17 top-level core modules and all 195 files under `results/` and `benchmarks/` were checked against pre-edit SHA256 hashes and remain byte-for-byte unchanged. No detector mappings, labels, parser behavior, context construction, prompt/schema, benchmark metrics, frozen sources, or pilot results were edited. No paid requests were made; the remaining 17 CGT findings were not run.

The initial test suite exposed three missing-import failures from the prior cleanup. `check_access_control_batch.py`, `check_cgt.py`, and `check_cgt_preflight.py` were restored verbatim from `e42f911`. Their byte identity was checked; evaluation logic was not refactored or rerun against saved output paths.

## Changes

- `app/presentation.py` (new): `compact_lines`, `finding_key`, `verification_ineligibility`, `is_finding_verifiable`, `requested_fragment_ids`, `source_context_efficiency`, `source_fragments`, `verification_export`, `target_function_lines`, and `marked_source_excerpt`.
- `app/worker.py`: report complete finding metadata and code-only efficiency while using the existing verifier unchanged.
- `app/services.py`: use shared eligibility and allowlisted GUI export schema v2.
- `app/session.py`: track unique stable reviewed IDs, preserve explicit rerun history, cache exports, and migrate old in-memory sessions without invoking analysis/inference.
- `app/gui.py`: immediately refresh reviewed-count placeholders; compact line ranges and readable column width; explicit target eligibility; static-claim fields; native verdict badges/panels; source excerpts with original line numbers; evidence/request metadata; separate code-efficiency and API-usage sections.
- `tests/test_app.py`, `tests/test_gui.py`: updated GUI schema expectations and real-source headless workflow checks.
- `tests/test_gui_presentation.py` (new): pure service/helper tests.
- `README.md` and `CODEX_CONTEXT.md`: current workflow, metrics, export, validation, and manual examples.

No files were removed.

## Metric definitions

All source estimates use `ceil(characters / 4)` on source strings. Full source and selected code are compared in the same unit. Initial selection is target-function source. Additional selection sums unique fragment IDs that actually reached a later model call. A request at the final round remains in requested-fragment counts, but is excluded from code-transmission totals because there is no later model call. Repeated API transmissions do not repeatedly count the same source fragment.

`source_context_reduction = 1 - cumulative_selected_source_estimated_tokens / full_source_estimated_tokens`

For an empty full source, reduction is undefined. Distinct overlapping fragments and per-fragment rounding can produce zero or negative reduction; no clamping or artificial savings are applied. Source strings include comments present in the code actually supplied. API input/output/total usage is shown independently, never used as the reduction numerator.

## State and export

Reviewed findings are unique stable analyzer IDs in the current analysis, with a deterministic fallback for legacy warnings lacking IDs. Reverification contributes another completed history entry and its usage, but does not increment the unique count. Failures do not count as completed reviews. Upload replacement and explicit reanalysis reset analysis state. The count placeholder is updated after verification on the same render, without an extra action-triggering rerun.

Export schema v2 includes full static-finding fields, verdict, structured explanation, evidence IDs, round count, requested IDs/count, usage, code-only context metrics, source fragments, model/compiler, and public request metadata. Unknown response fields, credentials, and hidden reasoning are not exported. The source and its hash remain top-level. Old in-memory reports without new source metrics show a legacy notice rather than the misleading old reduction.

## Validation

76 unittest tests pass, including 12 newly added tests. Checks cover compact line ranges, structural eligibility, empty/full/oversized selected-code cases, metadata exclusion, deduplication, last-round requests, public-field serialization, UTF-8 target offsets, stable IDs, reruns/failures/reset, and hot-reload state migration.

The actual local `simple_suicide.sol` source was compiled with solc 0.4.25. Slither returned three findings; `suicidal` was eligible and `solc-version` was disabled. A headless Streamlit test used the real prepared source and a mocked CONFIRMED response. It checked the immediate reviewed count of 1, no duplicate count on explicit repeat, no calls on ordinary rerenders, nonnegative source-only reduction, separate API usage, and no application-error alert for CONFIRMED. Fixture usage of 733/157/890 tokens is synthetic test data, not a new API measurement.

Pytest is not installed; the complete suite ran using `python -m unittest discover -s tests -q`. Python compilation and whitespace checks also pass. No new interactive server or paid verification was launched.

## Manual demonstration

Launch: `.venv/bin/streamlit run streamlit_app.py`.

- TP: `datasets/smartbugs-curated/dataset/access_control/simple_suicide.sol`, solc **0.4.25**, `suicidal`, **SimpleSuicide.sudicideAnyone()**.
- FP observed in the existing frozen pilot: `datasets/cgt/source/efe5ebd718c6afa9c24214bb4373b40d.sol`, solc **0.4.25**, `suicidal`, **ValueTrader.die()**. The `owned` modifier asserts `msg.sender == owner`; `burnBlock` adds another guard. Local Slither reproduction and function eligibility passed. The recorded pilot verdict is `false_positive`; no new model call was made and another model/run may differ.

Remaining limits: single import-free source, structural eligibility followed by exact core resolution, no arbitrary external dependency retrieval, heuristic token estimates, and bounded read-only source excerpts (full source remains available). Missing API usage on failed requests cannot be inferred. Model-output variation is unchanged.

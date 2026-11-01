# Current application context — 2026-10-18

The Streamlit application runs through `context_audit.app` services. Launch:

```bash
.venv/bin/streamlit run streamlit_app.py
```

GUI-only changes in this phase:

- `app/presentation.py` provides compact line formatting, stable finding keys, structural function eligibility, original-line source excerpts, source-only efficiency, request aggregation, catalog metadata, and export allowlisting.
- `app/worker.py` computes source-only metrics from actual function/fragment strings. The core prompt, payload builder, context policy, parser, and verifier are unchanged.
- `app/session.py` stores stable reviewed IDs, latest results, completed run history, and cached JSON export. A placeholder updates the reviewed count after the action on the same Streamlit run. Only explicit buttons invoke Slither or inference.
- `app/gui.py` shows static claim → verification → verdict, marked source excerpts, unsupported-scope reasons, evidence and request metadata, and separate source estimates/API usage.
- GUI export schema v2 separates finding, verification, usage, source-context metrics, and supplied-fragment metadata. Research export schemas are unchanged.
- Interactive maximum remains 10 rounds, recommended/default 4; model selection stays session-local.

Source efficiency counts unique fragment IDs actually sent, excluding metadata, JSON, instructions, repeated transmissions, and requests made on the last round without a subsequent call. Reduction is undefined for empty full source and may be nonpositive with overlap/rounding. API input usage is never divided by source tokens.

Tests: 76 unittest cases pass, including a real local `simple_suicide.sol` Slither/GUI workflow with mocked inference, disabled global warnings, immediate unique review counts, and no rerender-triggered calls. Pytest is not installed. No paid API calls were made.

The initial suite had three missing-import errors after a prior cleanup deleted CLI runners. `check_access_control_batch.py`, `check_cgt.py`, and `check_cgt_preflight.py` were restored byte-for-byte from `e42f911`; no evaluation logic was edited.

Manual TP: `datasets/smartbugs-curated/dataset/access_control/simple_suicide.sol`, solc 0.4.25, `suicidal`, `SimpleSuicide.sudicideAnyone()`.
Manual FP: `datasets/cgt/source/efe5ebd718c6afa9c24214bb4373b40d.sol`, solc 0.4.25, `suicidal`, `ValueTrader.die()`. This exact finding received `false_positive` in the completed frozen pilot. Its local warning/eligibility was rechecked without inference.

Preserve all research evidence, labels, mappings, source snapshots, and completed pilot outputs. Do not run the remaining 17 CGT findings. See `docs/gui_presentation_update.md` for the change report.

## GUI batch verification

The application now supports explicit sequential batch verification, defaulting to High +
Medium. `app/batch.py` provides eligibility/impact planning and schema-3 full-analysis
export; `AuditSession.verify_batch` orchestrates the existing verifier and saves each
completion/error. Stable IDs prevent repeated batch calls for completed findings, including
abstentions. Single-finding explicit reruns remain available. Filters and normal rerenders
never start inference. GUI clearing retains upload/static analysis and touches no files.
Results-table selection opens the existing inspector. Aggregate usage includes successful
verification history; failed attempts may have unknown usage and are explicitly flagged.
Research pipeline, frozen pilot evidence, and remaining 17 findings are unchanged.

## Thesis dashboard

Default GUI page is Evaluation Dashboard; Analyze Contract preserves the interactive
workflow. `app/research.py` provides read-only artifact loading, pilot metrics, readable
outcomes, and source/claim retrieval. `app/dashboard.py` contains presentation only.
Pilot and full reviewed-cohort precision are shown separately; SmartBugs recall is a
separate detection experiment. The example uses actual saved PrivateDeposit pilot
source estimates, not illustrative simple_suicide values or an invented average.
No paid calls or research artifact writes occur when opening the dashboard.
Tests now include missing-artifact handling, experiment separation, metric extraction,
and default-dashboard no-inference checks (91 tests in total).

Analyze Contract now presents Slither-only candidates separately from LLM outcomes.
Batch verification is primary; single-finding verification is in the expandable detail
view. Comparison cards explicitly preserve pending/skipped/error/abstention counts.
`app/demos.py` registers the local simple_suicide source; loading is explicit and never
starts analysis or inference. No benchmark semantics or research evidence changed.

## Modifier-target verification — 2026-10-26

`verifier.prepare_finding` now resolves through `indexer.find_target`: exact
contract/signature function matches first, then modifiers, with file/byte-range
identity and line disambiguation. Ambiguous or absent targets fail before inference.
Slither's `Modifier` subclasses `Function` but resides in `contract.modifiers`;
its JSON output nevertheless labels it as a function. The previous resolver only
searched `contract.functions`, causing `LargeTreasury.onlyManager()` to fail.

The existing context dictionary is extended with `kind` and `contract` rather
than introducing a duplicate AnalysisTarget model. `context.build_target_context`
handles both kinds; `build_function_context` remains a compatible entry point.
`FragmentCatalog.add` receives the actual kind. State reads/writes, declarations,
and direct writers retain the existing selective request policy: only target
source is sent initially; dependency source is available by fragment ID.
`payload.build_initial_payload` exposes `target.kind`, and the neutral system
prompt now recognizes modifiers. No verdict is encoded in the payload or prompt.

Finding's legacy `function_signature`, function-range fields, and exported
`function` keys remain intact. GUI source fragments preserve the resolved kind;
the inspector displays Target and Kind (source-derived before compilation).
Function and modifier findings pass the same structural eligibility checks.
CLI entry points and detector mappings are unchanged.

Local regression fixture: `tests/fixtures/ModifierTargetTest.sol`.
Tests: `tests/test_modifier_targets.py` (10 tests), including read-only preparation
of the optional saved LargeTreasury finding. Full unittest discovery passed all
104 tests. Full pytest was attempted but pytest is absent; installation failed
because network/DNS access is unavailable. No paid calls or benchmark writes.

Retest only the saved onlyManager target/context without inference:

```bash
.venv/bin/python -m unittest tests.test_modifier_targets.ModifierTargetTests.test_large_treasury_saved_finding_prepares_locally -v
```

For an explicit paid single-finding retest, launch:

```bash
.venv/bin/streamlit run streamlit_app.py
```

Open Analyze Contract, load `examples/scalability/LargeTreasury.sol`, select solc
0.8.24, and run Slither if needed. In the finding detail view select
`incorrect-equality` / `onlyManager()` and click **Verify selected finding**.
This invokes `AuditSession.verify` → `services.verify_selected` → worker for only
that selected finding, not the other six. If an analysis is already loaded,
reuse it. Do not click the batch button. Expected semantic verdict is FALSE
POSITIVE for the intentional enum-role access check, but no live model verdict
was obtained in this implementation task.

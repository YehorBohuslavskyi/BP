# Mode B v2 — Phase 1: contract-level discovery

Mode B v1 remains the reproducible function-by-function selective-context detector.
Its CLI, GUI, prompts, outputs and defaults are unchanged. Mode B v2 Phase 1 is a
separate structural discovery component. It generates hypotheses, not vulnerability
verdicts. No improvement in recall has been established.

## Integration and interfaces

`context_audit.direct_discovery.prepare(source)` returns `(contracts, catalog)`.
It reuses direct preparation's sanitized temporary project, installed compiler
selection, validated compiler source mappings, per-function IR recovery, context
builder and opaque fragment catalog. The only change to v1 is an opt-in
`discovery=False` keyword on its internal preparation function. Collection runs
before the existing opaque-ID remapping; inherited fragments use the same IDs as
source declarations. No indexing, compiler installation or dataset pipeline is duplicated.

`make_batches(contracts, max_chars=24000)` returns deterministic batches and coverage
records. `run_discovery(contracts, catalog, execute=False, max_chars=24000,
analyze_fn=None)` returns a JSON-serializable report. Preparation and the default
runner never construct an LLM client. Tests inject `analyze_fn`; explicit execution
uses the existing direct mode's OpenAI Responses structured-output convention,
`OPENAI_MODEL`, standard API-key configuration, timeout, no retries and `store=False`.

The JSON report contains complete structural summaries, bounded batches, preparation
metadata, per-function coverage, candidates, raw responses, prompt messages, errors,
model/response IDs and API usage. Markdown presents coverage, reasons, hypotheses
and usage. Source text is not included in the discovery report or sent to the model.
No source request is executed in Phase 1.

## Structural summary

Every contract declared in the selected file has a summary with its basename,
inheritance, state variables and functions, including inherited functions. Imported
contracts are not independent targets, but their inherited declarations and relevant
fragments can appear. Full signatures preserve overloads. Functions include
visibility, declaring contract, implementation flag, source lines, modifiers,
state reads/writes, relevant state declarations, direct state writers, internal
calls, high-level external calls, low-level call destinations and Solidity globals
read (including `tx.origin` when present).

FULL_INDEX uses available Slither metadata. SOURCE_FALLBACK retains validated source
structure, signature, visibility, modifiers and locations; IR fields are `null`.
An unavailable writer makes the dependency set unknown. `metadata_unavailable`
explicitly lists missing IR fields. `[]` means a successfully collected empty set.
Unsafe mappings remain in coverage as unevaluable. Synthetic initializer functions
are excluded; actual constructors and abstract declarations remain represented.
Abstract declarations are marked `implemented=false`.

Reads/writes and calls are direct metadata, not an execution trace or a complete
transitive graph. Neither collection nor the prompt asserts call ordering. State
writer relationships carry IDs; internal-call labels preserve full signatures.
The offline contract summary retains the whole state-variable inventory. Model
batches carry relevant per-function declarations and dependencies to avoid repeating
an unbounded inventory. Fallback functions have unknown relevant declarations.

Example excerpt from an offline synthetic `DiscoveryExample.sol` run:

```json
{
  "fragment_id": "fragment-7fd2188013a5b3cb33bb",
  "signature": "withdraw(uint256)",
  "visibility": "public",
  "state_reads": ["balances"],
  "state_writes": ["balances"],
  "low_level_calls": ["msg.sender.call"],
  "preparation_mode": "FULL_INDEX"
}
```

This metadata does not establish a vulnerability or the order of these operations.
Opaque IDs depend on project-relative source identity and byte ranges, so edits or
moving a file within a project may change them.

## Protocol and coverage

`DiscoveryResponse` forbids extra fields and requires:

- `examined_functions`: exactly one `{fragment_id, reason}` record for every function
  in the batch, including those with no candidate.
- `candidates`: zero or more `Candidate` objects containing `candidate_id`, `contract`,
  `primary_function`, `primary_fragment_id`, `suspected_type`, `reason`,
  `related_fragment_ids`, `requested_context_ids`, and `uncertainty`.

Candidate primary functions must match the batch's contract, exact signature and ID.
All candidate references must exist in the catalog and be advertised in that batch,
including dependency/modifier IDs. Unknown IDs, missing or duplicate examinations,
duplicate candidate IDs, exact duplicate hypotheses, malformed responses and
incomplete model responses reject the batch. Rejected responses and returned usage
are retained for inspection; their functions are unevaluable. Other batches continue.
Accepted candidate IDs are prefixed with a deterministic batch number, preserving
the original as `model_candidate_id`.

Coverage is counted per contract/function pair: an inherited function can be examined
in both base and derived contract contexts. Counts track total, included, examined,
selected, not_selected, incomplete_metadata, unevaluable and pending functions.
`examined` means the model returned a valid explicit coverage acknowledgement, not
proof that it reasoned correctly. `selected` includes candidate primary and related
functions that were successfully examined. Selection cannot erase an error/limit
status. All raw candidate references remain available for future scheduling.

Batches greedily pack stable function order under a canonical-JSON character limit
(default 24,000). This is a structural payload limit, not an exact tokenizer or total
request limit; the system prompt and output schema add overhead. Every eligible
function is scheduled once in its contract. An indivisible function record larger
than the limit is explicitly unevaluable with a reason, never silently truncated.
The complete offline summary preserves it for review or a larger configured budget.
Offline functions are pending, not examined. Unselected never means safe or
`no_vulnerability_found`. Candidates are never fabricated to improve coverage.

Dependencies can advertise functions in other batches, but batch splitting limits
joint reasoning across functions without an explicit dependency. There is currently
no global synthesis pass, retry policy, or mechanism that guarantees recall.

## CLI workflow

Use an installed compatible local compiler and a fresh output directory. Preparation
resolves and sanitizes dependencies using the same rules as Mode B v1. It does not
install compilers or contact an LLM.

```bash
# Offline structural summaries only
.venv/bin/python scripts/run_direct_discovery.py path/to/Contract.sol \
  --output /tmp/discovery-summary

# Explicit discovery (API calls); documented here, not run during implementation
OPENAI_MODEL=your-model .venv/bin/python scripts/run_direct_discovery.py \
  path/to/Contract.sol --run --max-summary-chars 24000 \
  --output /tmp/discovery-execution
```

Outputs are `discovery.json` and `summary.md`. Preparation failures produce
`preparation_error.json` and a nonzero exit. Protocol/API failures are recorded and
also produce a nonzero exit. Nonempty output directories are refused unless explicitly resuming compatible Phase 2 verification.
Do not point this command at frozen experiment directories.

API usage records provider input/output/total token counts when returned, including
responses rejected by validation. `api_calls` counts discovery attempts, including
transport/configuration failures; it is not a claim that every attempt was billable.
`summary_estimated_tokens` uses the existing estimator and is distinct from billed
usage. There is no v2 context-reduction or recall claim.

## Validation and research integrity

The implementation adds 20 offline tests covering compiler-backed deterministic
structure, batching/limits, inherited functions, overloads, modifiers, state
relationships, internal/external/low-level calls, fallback and invalid mappings,
coverage, strict protocol failures, duplicate candidates, empty results, usage,
sanitization, transport whitelisting, offline CLI behavior and v1 reproducibility.
At Phase 1 completion the unittest suite passed **191 tests, 0 failures, 0 errors, 0 skips**.
Pytest is unavailable in the current environment; the supported unittest runner was
used. Real OpenAI client construction was blocked during the complete suite.

No real API calls or experiments were run. Hash checks across `results/`,
`benchmarks/`, `examples/` and `runs/` covered 1,274 files with no changes. Frozen
pilot results, journals, reports and adjudication artifacts were not regenerated.
The prompt uses a general taxonomy and no dataset labels, audit reports or expected
locations. Compiler-generated metadata is allowlisted for model transport, excluding
source text, filenames/paths, evaluation fields and preparation exception messages.

## Integration with Phase 2

Phase 2 now consumes these candidates through the same CLI. Discovery reports also
include a provenance manifest binding the source, sanitized project, compiler,
fragment catalog, structure, model, prompt and discovery configuration. Legacy
Phase 1 reports without this manifest are refused for live verification rather than
silently trusted. Existing frozen artifacts must not be rewritten to add manifests.

See [the integrated pipeline guide](mode_b_v2_pipeline.md) for selective verification,
checkpoint/resume behavior, verdict semantics, coverage and evaluation plans. The GUI
remains unchanged. Future evaluation needs separately selected held-out contracts;
the existing three-contract pilot remains development/debug evidence.

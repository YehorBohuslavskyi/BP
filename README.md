# Smart Contract Vulnerability Verifier

A bachelor-thesis prototype for selective-context Solidity analysis. Mode B
discovers vulnerability hypotheses independently, then asks for the source needed
to verify them. Local Slither analysis and Slither-plus-LLM verification remain
available as comparison modes.

## Start the scanner

```bash
.venv/bin/python scripts/scanner.py doctor
.venv/bin/python scripts/scanner.py serve
```

Open <http://127.0.0.1:8501>. Load an example, upload a self-contained `.sol`
file, or paste source. Local analysis and source preparation make no model calls.
Direct LLM analysis starts only after an explicit Run action and consent.

The default direct backend uses an installed Codex CLI signed in with ChatGPT.
It consumes the existing account allowance and has no API-key fallback. The
separately billed OpenAI API backend is optional. See
[scanner usage](docs/scanner_demo.md) and [backend setup](docs/scanner_subscription.md).

## What works now

- Compiler-backed source fragments and exact links between functions, callers,
  callees, modifiers and state dependencies.
- Two-stage discovery and source-grounded verification, with bounded context
  requests and checks against citing source the model has not received.
- Explicit round, fragment, candidate and token limits; checkpoints and usage
  records preserve partial, uncertain and failed results.
- JSON/HTML reports, local vulnerable/guarded examples and a read-only historical
  evidence page when the original local artifacts are available.

All **580 offline tests** pass after project cleanup. A separately authorized
handcrafted development check confirmed a reentrancy hypothesis after retrieving
seven fragments across four verification rounds: five Codex turns, 73,863 reported
tokens and no processing failures or skips. This is an end-to-end development
check, not an accuracy benchmark or an executed exploit. Compact evidence is in
[the navigation review](docs/reviews/function-navigation-2026-11-16/summary.json).

Read [current state](docs/current_state.md) for limitations and the next milestone,
and [function navigation and limit profiles](docs/function_navigation.md) for the
index semantics and profiles. Unknown external behavior remains unknown; no
findings does not establish contract safety.

## Installation

Python 3.12 or newer is required:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[gui,dev]'
solc-select versions
```

Install a compatible solc release separately when needed. The application uses
already-installed compilers and never downloads one automatically. The optional
vendored Solidity dependency is pinned by `package-lock.json`; `npm ci` restores
it when required. Neither installation nor downloads are part of offline tests.

Codex scanning requires ChatGPT sign-in in the installed CLI. API-based scanning
instead requires an available structured-response model and `OPENAI_API_KEY`,
or a session-only key entered in the interface. Keep credentials out of Git.

The interface is local, binds to localhost and uses owned temporary upload
directories. It is not an internet-facing untrusted-compilation service.

## Offline checks

```bash
.venv/bin/python scripts/run_offline_tests.py
.venv/bin/python scripts/run_offline_tests.py test_function_index test_verification_profiles
```

The runner blocks real model-client construction, Python network access and
writes to preserved research folders. Integration checks need compatible locally
installed compilers. Historical research tests also need the existing local
`runs/`, `experiments/` and external dataset checkouts. Those large/local artifacts
are intentionally not published as part of the application code. Missing research
fixtures must not be mistaken for passing historical checks.

## Commands and research workflows

```bash
# Local static scan
.venv/bin/python scripts/scanner.py scan --example vulnerable --output NEW_OUTPUT

# Source-only preparation
.venv/bin/python scripts/scanner.py scan Contract.sol --method prepare --output NEW_OUTPUT

# Rebuild explicit development cases under the current index, without labels
.venv/bin/python scripts/reindex_source_proposal.py \
  --parent-proposal OLD_PROPOSAL --output FRESH_PROPOSAL --case-id EXACT_CASE
```

Fresh model runs require a separately reviewed plan and explicit authorization.
`--method direct --live --provider codex --limit-profile expanded` is available
for an authorized scan; changing settings never authorizes a frozen experiment.
Expanded investigation profiles are separate study conditions. Use fresh output
directories, keep model/backend and code identities, and disclose skipped cases.

Legacy verification entry points remain available through
`context_audit.verifier`, `check_access_control_batch.py`, `check_cgt.py` and
`check_cgt_preflight.py`. Their populations and metrics must not be pooled with
new direct/subscription results. See [CGT evaluation](docs/cgt_local_evaluation.md)
and [Mode B v2 workflow](docs/mode_b_v2_pipeline.md).

## Project layout and preservation

| Location | Purpose |
| --- | --- |
| `src/context_audit/` | Analysis, indexing, verification, transports and interface |
| `scripts/` | Local checks, scanner and explicit research entry points |
| `tests/` | Unit, compiler and mocked-transport regression checks |
| `examples/scanner/` | Small demonstration contracts |
| `docs/` | Current guides and protocol notes |
| `docs/reviews/` | Compact, attributable evidence and exposure registries |
| `docs/history/` | Preserved earlier documentation |
| `results/`, `benchmarks/`, historical example evaluations | Existing frozen evidence |
| `runs/`, `experiments/` | Preserved local research artifacts, excluded from Git |

Do not rewrite historical reports, response journals, checkpoints, manifests or
finalization seals to improve results. Finalized PRA remains partial and cannot
be resumed automatically. Frozen approvals do not authorize a new protocol.
Source-context reduction, model usage and detection accuracy are separate metrics.
Independent precision/recall evaluation remains a future frozen research stage.

# CODEX PHASE - Code Cleanup, Documentation, and GUI

## Objective

The core Bachelor Thesis prototype is now functional and experimentally validated enough to move into a cleanup/productization phase.

Current verified state:

- SmartBugs access-control baseline completed:
  - 18 contracts analyzed
  - 21 ground-truth vulnerabilities
  - 9 detected by Slither
  - 12 genuine Slither misses
  - recall: 42.86%
- CGT local integration completed.
- 27 defensibly linked reviewed findings:
  - 22 true findings
  - 5 false positives
  - Slither cohort precision: 81.48%
- Frozen 10-finding LLM pilot completed:
  - 5 positive + 5 negative
  - TP = 5
  - FP = 2
  - TN = 3
  - FN = 0
  - precision = 71.43%
  - recall = 100%
  - F1 = 83.33%
  - false-positive reduction = 60%
  - no inconclusive verdicts
  - no runtime errors
  - no source/function-resolution failures
  - 16 API calls
  - average rounds = 1.6
  - requested fragments = 17
  - total tokens = 22,424

Do NOT alter completed research results or evaluation semantics during cleanup unless an actual reproducible bug is found.

The next work has three stages:

1. Code cleanup and structure.
2. Documentation / comments / docstrings.
3. GUI.

## Core Rule

Preserve behavior.

Before modifying anything:

```bash
git status
git diff
pytest
```

After every meaningful refactor:

```bash
pytest
```

Do not silently change:
- prompt behavior
- detector mappings
- CGT linkage rules
- SmartBugs matching rules
- pilot cohort
- metric definitions
- model configuration
- context retrieval semantics

## Stage 1 - Repository Audit

Inspect the repository and classify files as:
- core
- evaluation
- experiment runner
- test
- temporary/debug
- legacy
- generated evidence
- dataset
- documentation

Identify:
- duplicated logic
- dead code
- temporary debugging code
- stale comments
- inconsistent naming
- overly long functions
- mixed responsibilities
- magic strings/constants
- repeated subprocess logic
- repeated export logic
- inconsistent path handling
- missing type hints
- weak exception handling
- unused imports

Do not delete files immediately. Preserve generated research evidence.

## Stage 2 - Clean Architecture

Refactor incrementally toward clear separation between:
- Slither execution/parsing
- context construction
- LLM verification
- datasets
- evaluation/metrics
- application services
- CLI scripts
- GUI

Possible target structure:

```text
src/
  context_audit/
    analysis/
    context/
    llm/
    datasets/
    evaluation/
    app/

scripts/
tests/
```

This is a guideline, not a mandatory full rename.

## Stage 3 - Thin Scripts

Experiment scripts should mainly:
- parse arguments
- call reusable library functions
- print/export results

Move reusable logic into `src/context_audit`.

## Stage 4 - Configuration

Centralize useful constants/configuration:
- dataset paths
- result paths
- max rounds
- detector mappings
- function-scope detector sets
- experiment names

Keep secrets only in environment variables:

```text
OPENAI_API_KEY
OPENAI_MODEL
```

Never commit credentials.

## Stage 5 - Type Hints

Add or improve type hints across core modules.

Prefer `Path` for filesystem paths.

Use dataclasses for stable domain objects.

Avoid unnecessary `Any`.

## Stage 6 - Docstrings and Comments

The user explicitly wants professional comments and short explanations before functions.

Add concise docstrings to:
- every public function
- important private helpers
- important classes

Example:

```python
def build_function_context(
    function: Function,
    catalog: FragmentCatalog,
) -> dict:
    """Build dependency-aware context for a Solidity function.

    Includes state reads/writes, modifiers, state declarations, and
    direct writers that may affect verification.
    """
```

Simple helper:

```python
def _normalize_path(path: str) -> str:
    """Normalize a path to POSIX format for stable comparison."""
```

Class:

```python
class FragmentCatalog:
    """Store source fragments and provide stable fragment IDs."""
```

Use comments for WHY, not obvious WHAT.

Good:

```python
# Contract-level Slither ranges are context, not precise finding locations.
# Excluding them prevents broad ranges from creating false matches.
```

Avoid comment noise such as:

```python
# Loop through findings.
for finding in findings:
```

## Stage 7 - Module Docstrings

Add short module docstrings to important modules such as:
- findings
- context builder
- catalog
- payload
- verifier
- SmartBugs loader
- CGT loader
- evaluation
- metrics
- Slither runner
- GUI services

## Stage 8 - Naming Cleanup

Prefer clear names such as:
- `ground_truth_lines`
- `matched_lines`
- `function_source_lines`
- `requested_fragment_ids`

Avoid vague names like:
- `data`
- `obj`
- `res`
- `tmp`

Do not rename stable public APIs without updating callers/tests.

## Stage 9 - Error Handling

Create clear error messages for:
- Slither compilation failure
- unsupported compiler
- missing source file
- function resolution failure
- invalid dataset record
- invalid LLM context request
- OpenAI API failure
- missing environment variables
- invalid experiment configuration

Do not swallow exceptions silently.

## Stage 10 - Logging

Use Python `logging` in reusable modules.

```python
logger = logging.getLogger(__name__)
```

Suggested levels:
- DEBUG: source resolution details
- INFO: experiment progress
- WARNING: recoverable issue
- ERROR: failed finding/contract

Do not log secrets.

## Stage 11 - Remove Temporary Debugging

Remove stale contract-specific debug blocks, especially old manual baseline debugging.

If useful, convert them into optional `--debug` behavior.

Do not remove completed experiment evidence.

## Stage 12 - Tests

Preserve all current tests.

Add tests where needed for:
- finding parsing
- contract-level range exclusion
- node-line prioritization
- source offset to line conversion
- function-scope matching
- SmartBugs loading
- CGT loading
- CGT linkage
- classification metrics
- LLM verdict mapping
- context request validation
- token aggregation
- result serialization
- configuration validation

Run the complete suite after cleanup.

## Stage 13 - README

Create or update the main `README.md`.

Explain:
- project purpose
- architecture
- installation
- Slither
- solc-select
- environment variables
- basic CLI usage
- SmartBugs
- CGT
- evaluation reproduction
- tests
- GUI launch command

Architecture diagram:

```text
Solidity
   ↓
Slither
   ↓
Finding
   ↓
Dependency-aware context
   ↓
LLM verifier
   ↓
confirmed / false_positive / inconclusive
```

## Stage 14 - GUI Technology

Use Streamlit unless there is a strong reason not to.

Do not build a separate React frontend.

The GUI is a demonstration layer over existing library logic.

## Stage 15 - Application Service Layer

Do not put analysis logic inside Streamlit callbacks.

Create reusable service functions for:
- temporary upload handling
- pragma detection
- compiler checks
- Slither execution
- finding retrieval
- single-finding verification
- result export

The architecture should remain:

```text
GUI
 ↓
Application/service layer
 ↓
Slither runner
 ↓
Finding parser
 ↓
Context builder
 ↓
LLM verifier
```

## Stage 16 - Initial GUI Workflow

The GUI should support:

1. Upload one `.sol` file.
2. Store it in a safe temporary workspace.
3. Detect Solidity pragma/version.
4. Report/select available compiler.
5. Run Slither.
6. Display findings.
7. Select one finding.
8. Run LLM verification.
9. Display:
   - detector
   - impact
   - confidence
   - description
   - contract/function
   - source lines
   - LLM verdict
   - explanation
   - evidence
   - requested context
   - rounds
   - token usage
10. Allow JSON export.

Start with single-file Solidity upload.

Multi-file project upload can come later.

## Stage 17 - GUI Layout

Suggested title:

```text
Smart Contract Vulnerability Verifier
```

Subtitle:

```text
Static analysis with selective LLM-based finding verification
```

Sidebar:
- OpenAI model
- Slither status
- solc version
- max rounds

Never show the API key.

Main sections:
1. Upload Contract
2. Static Analysis
3. Findings
4. LLM Verification
5. Context Efficiency

## Stage 18 - Finding Cards

Display:
- Detector
- Impact
- Confidence
- Contract
- Function
- Lines
- Description

Use clear severity/status badges.

## Stage 19 - LLM Verdict

Display:
- CONFIRMED
- FALSE POSITIVE
- INCONCLUSIVE

Also show:
- explanation
- evidence fragments
- rounds
- input tokens
- output tokens
- total tokens
- requested fragments

Do not hide inconclusive results.

## Stage 20 - Source Display

Show Solidity source with line numbers.

Highlight finding lines when practical.

A read-only code display is enough for v1.

## Stage 21 - Context Efficiency UI

Show:
- full source size
- initial context size
- requested fragments
- total LLM input tokens
- rounds
- estimated context reduction %

Clearly distinguish estimated source tokens from actual API input tokens.

## Stage 22 - Upload Safety

Use temporary directories.

Do not write uploads into benchmark datasets.

Use safe filenames.

Run subprocesses with argument lists, never shell interpolation.

Good:

```python
subprocess.run(
    ["slither", str(source_path), "--json", "-"],
    ...
)
```

Bad:

```python
os.system(f"slither {user_input}")
```

## Stage 23 - Compiler Handling

Inspect Solidity pragma.

For v1:
- use an installed compatible compiler when available
- report clearly when the required version is missing

Do not silently install or globally change compilers without informing the user.

## Stage 24 - API Handling

Before LLM verification, check:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

If missing, show a clear configuration message.

Catch API failures and show user-friendly errors.

Do not expose stack traces by default.

## Stage 25 - Result Export

Allow downloading JSON analysis results.

Suggested structure:

```json
{
  "source": "...",
  "slither_findings": [],
  "verification": [],
  "usage": {}
}
```

Do not include secrets.

## Stage 26 - Preserve CLI

Streamlit must not become the only interface.

CLI, tests, and experiment runners must continue using the same core library.

## Stage 27 - Preserve Research Evidence

The GUI must not modify:
- SmartBugs baseline
- CGT baseline
- CGT pilot results
- frozen cohorts
- completed research evidence

GUI output should go to separate runtime/results paths if persisted.

## Stage 28 - Do Not Run Remaining Paid CGT Findings

This cleanup/GUI phase is separate from the full 27-finding evaluation.

Do not run the remaining 17 findings automatically.

Do not modify the frozen pilot results.

## Work Order

Follow this sequence:

```text
1. Inspect repository
2. Run current tests
3. Create cleanup plan
4. Refactor core code incrementally
5. Add module/class/function docstrings
6. Add useful WHY comments
7. Remove stale debug code
8. Improve typing/errors/logging
9. Run tests
10. Update README/docs
11. Create application/service layer
12. Add Streamlit GUI
13. Test GUI workflow
14. Run full test suite
15. Produce final cleanup report
16. Update CODEX_CONTEXT.md
```

## Completion Criteria

Cleanup is complete when:
- all tests pass
- reusable logic is separated from scripts
- important modules/functions/classes are documented
- comments explain non-obvious logic
- naming is consistent
- typing is improved
- debug code is removed
- README is accurate
- research evidence is preserved

GUI v1 is complete when the user can:

```text
upload Solidity file
→ run Slither
→ see findings
→ select finding
→ run LLM verification
→ see verdict/explanation
→ see context/token metrics
→ export result
```

## Final Report Required

When finished, report:
- files changed
- files added
- files removed
- refactors performed
- public APIs changed
- test count/status
- GUI launch command
- known GUI limitations
- research artifacts preserved

Update `CODEX_CONTEXT.md` with the cleaned architecture and GUI usage.

## Start Now

Read the current repository before editing.

Run:

```bash
git status
git diff
pytest
```

Then begin cleanup incrementally.

Work autonomously.

Do not ask the user to run routine commands.

Do not change completed research results.

Do not execute the remaining 17 paid CGT findings.

After cleanup is stable and tests pass, implement the Streamlit GUI on top of the cleaned service layer.

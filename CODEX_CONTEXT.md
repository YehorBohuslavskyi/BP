> **Model selection:** The GUI now supports a session-local model dropdown with custom IDs.
> `OPENAI_MODEL` supplies the default; optional `OPENAI_MODELS` supplies comma-separated options.
> Selection does not trigger inference or mutate server/frozen configuration.

> **GUI refinement (2026-10-18):** The interactive round limit is now 10, with
> 4 retained as the recommended default. The interface uses native cards,
> severity badges, a contrasting sidebar, and a two-column findings/review layout.
> Streamlit 1.66 is installed; headless UI tests exercise the workflow with mocked
> inference. Frozen research limits and evidence are unchanged.

> **Cleanup / Streamlit v1 (2026-10-17):** Core documentation and context-writer
> cleanup are complete; existing core imports, prompt/schema, matching rules,
> and metrics are preserved. `src/context_audit/app/` provides temporary upload,
> compiler, Slither, isolated verification, export, and session services. Launch
> with `.venv/bin/streamlit run streamlit_app.py` after installing the `gui`
> extra. See `README.md` and `docs/cleanup_report.md`.
>
> The current saved pilot is completed: TP=5, FP=2, TN=3, FN=0; 16 calls,
> 22,424 tokens. Earlier preflight/network-blocked reports below are historical.
> Cleanup made no paid calls and did not run the other 17 findings. Frozen
> evidence and snapshots must remain unchanged. Current source hashes differ
> because of cleanup; do not bypass the historical pilot's hash checks.
>
> Validation: 60 passing tests, one optional Streamlit runtime test skipped.
> pytest and Streamlit were unavailable; installation failed because package-index
> DNS resolution is blocked. Actual GUI launch/rendering remains unverified.

# Bachelor Thesis Prototype - Codex Working Context

> **Latest CGT status:** Local dataset evaluation completed; see
> `docs/cgt_local_evaluation.md`. 20,455 assessments parsed; 27 reviewed linked
> findings (22 positive, 5 negative) prepared without API calls. 392/419 archive
> rows remain ineligible/unresolved. Stop before ANY paid LLM run, per the latest
> user instruction. Earlier acquisition-blocked notes are historical.

> **Evaluation update (2026-10-17):** The access-control miss audit is complete.
> See `benchmarks/access_control_report.md`, the JSON/CSV baseline snapshots,
> and `benchmarks/access_control_audit.json`. Final result: 18/18 analyzed,
> 9/21 annotations detected, 12 audited Slither misses, recall 42.86%.
> Historical unresolved-case notes below describe the pre-audit state.
> The batch now exports reproducible evidence and uses per-process `SOLC_VERSION`.


## Goal

Continue development and evaluation of the Bachelor Thesis prototype for:

**LLM-based smart-contract vulnerability verification**

The prototype uses:

1. Slither as the static analyzer.
2. A dependency-aware context builder to collect only relevant Solidity fragments.
3. An LLM verifier that evaluates a specific Slither finding as:
   - `confirmed`
   - `false_positive`
   - `inconclusive`
4. Benchmark evaluation to measure:
   - Slither baseline performance
   - Slither + LLM verification performance
   - false-positive reduction
   - context/token efficiency

The main thesis goals are:

- reduce false positives produced by traditional static analyzers;
- support analysis of larger contracts/projects through selective context retrieval.

Do not build the GUI yet. Evaluation comes first.

---

# Environment

Project root:

```bash
~/projects/BP
```

Environment:

- WSL Ubuntu 24.04
- Python 3.12.3
- venv: `~/projects/BP/.venv`
- Slither installed
- `solc-select` installed
- multiple Solidity compiler versions are required for SmartBugs

Activate environment when needed:

```bash
cd ~/projects/BP
source .venv/bin/activate
```

SmartBugs Curated dataset:

```text
datasets/smartbugs-curated
```

Metadata:

```text
datasets/smartbugs-curated/vulnerabilities.json
```

---

# Important Working Rule

Work autonomously.

Do not ask the user to manually execute routine diagnostic commands if Codex can execute them itself.

For the evaluation workflow:

1. run commands;
2. inspect output / JSON;
3. inspect benchmark source and ground truth;
4. identify whether a miss is:
   - a real Slither false negative, or
   - an evaluation/matching problem;
5. refactor the evaluator only when evidence justifies the change;
6. rerun the batch;
7. continue with the next unresolved contract.

Do not increase recall by adding broad mappings without validating that the Slither finding actually corresponds to the benchmark vulnerability.

Correctness of the evaluation is more important than achieving a high recall number.

---

# Current Project Architecture

Important source files:

```text
src/context_audit/
    catalog.py
    context.py
    dataset.py
    evaluation.py
    findings.py
    indexer.py
    llm.py
    payload.py
    verifier.py
```

Evaluation runner:

```text
check_access_control_batch.py
```

Other previous test scripts may exist, including:

```text
check_verifier.py
check_evaluation.py
check_dataset.py
check_context_request.py
check_target_only.py
```

---

# Existing Prototype

## `catalog.py`

`FragmentCatalog` assigns source fragments IDs in this form:

```text
file:kind:start:length
```

It supports:

- functions
- modifiers
- state-variable declarations

and returns fragment metadata/source through `catalog.get(id)`.

---

# `context.py`

Main function:

```python
build_function_context(function, catalog)
```

It collects:

- target function
- direct state reads/writes
- modifier state reads/writes
- state-variable declarations
- direct writers of related state variables

Known limitation:

- direct writers are currently collected within the same contract;
- inheritance/cross-contract dependency handling is not complete.

Do not redesign this until the evaluation baseline is stable unless necessary.

---

# `payload.py`

The LLM receives a specific Slither finding, not a general auditing task.

Initial payload contains:

```text
task = verify_static_analysis_finding
finding
target
available_context
context_complete
```

Available context can include:

- modifiers
- state variable declarations
- direct writers

The LLM can request selected fragments.

---

# `llm.py`

The verifier is intentionally finding-specific.

Structured verdicts:

```text
pending
confirmed
false_positive
inconclusive
```

Important prompt behavior:

- verify only the supplied static-analysis finding;
- do not perform a general audit;
- finding description is a claim, not proof;
- unrelated vulnerabilities do not confirm the reported finding;
- request context only when necessary;
- evidence must come from supplied source fragments.

The OpenAI model is configured through:

```bash
OPENAI_MODEL
```

A previous working test used:

```text
gpt-5.6-luna
```

Do not expose or hardcode API keys.

---

# `verifier.py`

Main function:

```python
verify_finding(...)
```

Workflow:

```text
Slither finding
→ find target function
→ build selective context
→ build initial payload
→ LLM
→ optional context requests
→ final verdict
```

There is also:

```python
summarize_verification(...)
```

which records:

- verdict
- rounds
- requested fragments
- input tokens
- output tokens
- total tokens

This will later be used for context-efficiency experiments.

---

# Benchmark Dataset

Current benchmark:

**SmartBugs Curated**

There are 143 contracts total.

For the current first baseline experiment, only the SmartBugs category:

```text
access_control
```

is being analyzed.

There are currently:

```text
18 contracts
21 ground-truth vulnerabilities
```

in this subset.

Important methodological limitation:

SmartBugs Curated primarily annotates known vulnerabilities.

Therefore:

**An unmatched Slither finding is NOT automatically a false positive.**

Call it:

```text
unmatched finding
```

not:

```text
false positive
```

For a proper false-positive experiment, a benchmark with manually verified negatives, such as Consolidated Ground Truth (CGT), should be considered later.

---

# Solidity Compiler Versions

The access-control subset uses old Solidity versions including:

```text
0.4.0
0.4.9
0.4.15
0.4.22
0.4.23
0.4.24
0.4.25
```

`check_access_control_batch.py` automatically calls:

```bash
solc-select use <version>
```

before running each contract.

Slither is run with:

```bash
slither <contract> --json - --fail-none
```

`--fail-none` is important because findings must not make the process look like a failed analysis.

---

# `dataset.py`

It loads SmartBugs metadata into:

```python
GroundTruthVulnerability
DatasetContract
```

Each contract contains:

```text
name
path
pragma
vulnerabilities
```

Each vulnerability contains:

```text
category
lines
```

---

# Current Finding Parsing

Important lesson discovered during evaluation:

Slither JSON `elements` may contain broad contextual elements such as:

```text
type = contract
lines = entire contract range
```

and precise elements such as:

```text
type = node
lines = exact suspicious statement
```

Contract-level lines must NOT be treated as exact finding lines.

Current desired `Finding` model:

```python
@dataclass
class Finding:
    id: str
    detector: str
    impact: str
    confidence: str
    description: str
    contract: Optional[str]
    function_signature: Optional[str]
    file: Optional[str]
    lines: list[int]
    function_start: Optional[int]
    function_length: Optional[int]
```

`findings.py` should prioritize location precision:

```text
node lines
> function lines
> other non-contract lines
```

Never add contract-level ranges to `Finding.lines`.

When Slither provides empty line arrays but gives:

```text
start
length
```

the evaluator can reconstruct function line ranges from source byte offsets.

---

# Current Evaluation Logic

Current evaluation uses:

```python
CATEGORY_DETECTOR_MAP
```

for semantic compatibility between SmartBugs categories and Slither detectors.

Current relevant mapping should include approximately:

```python
CATEGORY_DETECTOR_MAP = {
    "access_control": {
        "controlled-delegatecall",
        "controlled-array-length",
        "suicidal",
        "tautology",
        "tx-origin",
        "unprotected-upgrade",
        "protected-vars",
    },
}
```

Do not assume this mapping is complete.

Every new detector mapping must be validated against:

1. SmartBugs ground-truth line(s);
2. contract source;
3. Slither output / JSON;
4. actual vulnerability semantics.

---

# Function-Scope Matching

Some detectors identify one statement involved in an exploit while SmartBugs labels another statement in the same vulnerable function.

Example:

`mapping_write.sol`

Slither:

```text
controlled-array-length
line 17:
map.length = key + 1
```

SmartBugs:

```text
access_control
line 20:
map[key] = value
```

Both are inside:

```text
set(uint256,uint256)
```

Therefore function-level fallback is permitted for selected detectors.

Current set:

```python
FUNCTION_SCOPE_DETECTORS = {
    "controlled-array-length",
}
```

Matching strategy:

```text
1. detector must be compatible with benchmark category;

2. try exact finding-line overlap;

3. if there is no exact overlap and detector is in
   FUNCTION_SCOPE_DETECTORS:
       try ground-truth line inside associated function range;

4. otherwise no match.
```

Do NOT make every detector function-scope matched.

---

# Important Bugs Already Found and Fixed

## 1. Slither nonzero return code

Using Slither without `--fail-none` caused valid analyses with findings to be counted as failed.

Fixed by:

```bash
--fail-none
```

---

## 2. `suicidal` matched every access-control vulnerability

A temporary rule allowed `suicidal` to match without line requirements.

This caused one finding in `parity_wallet_bug_1.sol`:

```text
suicidal
kill(address)
```

to match two unrelated GT vulnerabilities:

```text
line 223
line 437
```

That rule was removed.

Never match a finding solely because:

```text
detector category matches benchmark category
```

when there is no location evidence.

---

## 3. Old Slither JSON has empty lines

Example:

`simple_suicide.sol`

Slither JSON for `suicidal` contained:

```json
"lines": [],
"start": 301,
"length": 61
```

Therefore source offsets are used to reconstruct function lines.

This correctly allows `simple_suicide.sol` to match.

---

## 4. Contract-level source range caused false matches

Example:

`rubixi.sol`

Slither `controlled-array-length` JSON contained:

```text
contract Rubixi:
lines 10-162
```

plus the real suspicious node:

```text
participants.push(...)
line 61
```

The old parser merged all element lines, causing the benchmark ground truth on lines 23-24 to match accidentally.

Fix:

- exclude `type == "contract"` from exact `Finding.lines`;
- prefer node locations.

After the fix, `rubixi.sol` correctly returned to `MISSED`.

---

# Contracts Already Investigated

## FibonacciBalance.sol

Pragma:

```text
0.4.22
```

Ground truth:

```text
2 access_control vulnerabilities
```

Slither detects both through:

```text
controlled-delegatecall
```

Current result:

```text
Detected 2 / 2
```

---

## phishable.sol

Current result:

```text
Detected 1 / 1
```

---

## proxy.sol

Current result:

```text
Detected 1 / 1
```

---

## mycontract.sol

Current result:

```text
Detected 1 / 1
```

---

## simple_suicide.sol

Pragma:

```text
0.4.0
```

Slither:

```text
Detector: suicidal
SimpleSuicide.sudicideAnyone() allows anyone to destruct the contract
```

Old Slither JSON had empty line list but source offsets.

After source-range fallback:

```text
Detected 1 / 1
```

This is a valid detection.

---

## incorrect_constructor_name1.sol

Slither findings:

```text
solc-version
naming-convention
```

No detector corresponding to the SmartBugs access-control vulnerability.

Current interpretation:

```text
real Slither false negative
```

---

## incorrect_constructor_name2.sol

Slither only reported:

```text
solc-version
```

Current interpretation:

```text
real Slither false negative
```

---

## incorrect_constructor_name3.sol

Slither reported:

```text
solc-version
naming-convention
```

No actual access-control vulnerability detection.

Current interpretation:

```text
real Slither false negative
```

---

## arbitrary_location_write_simple.sol

SmartBugs:

```text
access_control [27]
```

Source:

```solidity
require(0 <= bonusCodes.length);
```

Slither:

```text
tautology
line 27
```

Therefore `tautology` was added to the access-control mapping.

Current result:

```text
Detected 1 / 1
```

Do not use `controlled-array-length` as the primary reason here because the exact GT line is detected by `tautology`.

---

## mapping_write.sol

SmartBugs:

```text
access_control [20]
```

Source:

```solidity
map[key] = value;
```

Slither:

```text
controlled-array-length
line 17:
map.length = key + 1
```

Both are in:

```text
set(uint256,uint256)
```

Function-scope matching for `controlled-array-length` makes this a valid detection.

Current result:

```text
Detected 1 / 1
```

---

## rubixi.sol

SmartBugs:

```text
access_control [23, 24]
```

Slither `controlled-array-length` points to:

```text
participants.push(...)
line 61
```

inside:

```text
addPayout(uint256)
lines 59-79
```

This is unrelated to GT lines 23-24.

Old parser falsely matched it because the detector also included a contract-level source range.

After excluding contract-level ranges:

```text
Detected 0 / 1
```

This is currently unresolved and should remain `MISSED` unless another genuinely relevant Slither finding is identified.

Other Slither findings observed in this contract include:

```text
msg-value-in-nonpayable
divide-before-multiply
unchecked-send
events-access
events-maths
missing-zero-check
incorrect-modifier
calls-loop
deprecated-standards
solc-version
naming-convention
reentrancy-unlimited-gas
```

Do not automatically map one of these without inspecting the GT code at lines 23-24.

---

## parity_wallet_bug_1.sol

Ground truth:

```text
access_control [223]
access_control [437]
```

Relevant source:

line 223:

```solidity
function initWallet(address[] _owners, uint _required, uint _daylimit)
```

line 437:

```solidity
_walletLibrary.delegatecall(msg.data);
```

Slither also reports:

```text
suicidal
kill(address)
```

but `kill(address)` is around lines 229-231 and is NOT either benchmark vulnerability.

Therefore `suicidal` must NOT match these GT items.

Current result:

```text
Detected 0 / 2
```

Needs further inspection because there may be other Slither findings among the ~90 results that correspond to lines 223 or 437.

---

## parity_wallet_bug_2.sol

Current result:

```text
Detected 1 / 2
```

Needs further inspection to identify which vulnerability is matched and which one is missed.

---

# Current Batch Result

After parser and matching fixes, current result is approximately:

```text
Selected contracts: 18
Successfully analyzed: 18
Failed: 0

Ground truth vulnerabilities: 21
Detected: 9
Missed: 12
Recall: 0.42857142857142855
```

Approximately:

```text
42.9% recall
```

DO NOT treat this as the final baseline yet.

There are still unresolved `MISSED` cases that must be audited.

---

# Current Unresolved / MISSED Contracts

At the latest run, unresolved contracts include:

```text
incorrect_constructor_name1.sol
incorrect_constructor_name2.sol
incorrect_constructor_name3.sol
multiowned_vulnerable.sol
parity_wallet_bug_1.sol
parity_wallet_bug_2.sol (one of two)
rubixi.sol
unprotected0.sol
wallet_02_refund_nosub.sol
wallet_03_wrong_constructor.sol
wallet_04_confused_sign.sol
```

The three `incorrect_constructor_name*` contracts have already been manually checked and appear to be real Slither false negatives.

Continue with the others.

---

# Immediate Next Task

The next contract to investigate is:

```text
multiowned_vulnerable.sol
```

Pragma:

```text
0.4.23
```

Codex should execute the equivalent of:

```bash
solc-select use 0.4.23
slither datasets/smartbugs-curated/dataset/access_control/multiowned_vulnerable.sol
```

Then inspect SmartBugs ground truth for this contract programmatically from:

```text
vulnerabilities.json
```

and inspect source lines around the GT location.

Determine:

```text
A. Slither has no relevant finding
   → real false negative

or

B. Slither has a relevant finding
   → evaluator mapping/location logic needs adjustment
```

If B:

- inspect Slither JSON;
- identify precise node/function locations;
- update `CATEGORY_DETECTOR_MAP` or `FUNCTION_SCOPE_DETECTORS` only if justified;
- rerun `check_access_control_batch.py`;
- verify that no unrelated contract becomes accidentally detected.

---

# Autonomous Evaluation Loop

Continue this loop for every unresolved contract.

## Step 1 - Read latest batch result

Run:

```bash
python check_access_control_batch.py
```

Identify all current `MISSED` vulnerabilities.

---

## Step 2 - Pick one unresolved contract

Prefer one contract at a time.

Switch compiler automatically:

```bash
solc-select use <contract pragma>
```

---

## Step 3 - Run Slither manually

```bash
slither <contract>
```

Inspect all detectors.

---

## Step 4 - Read benchmark ground truth

Use `dataset.py` or directly inspect `vulnerabilities.json`.

Print:

```text
category
lines
```

---

## Step 5 - Inspect source

Use tools such as:

```bash
nl -ba <contract>
```

or:

```bash
sed -n '<start>,<end>p'
```

with numbered lines.

Understand what the GT line actually represents.

---

## Step 6 - Compare against Slither findings

Classify the result:

### Real Slither false negative

Use this only when Slither does not report a finding that semantically identifies the benchmark vulnerability.

Examples already confirmed:

```text
incorrect_constructor_name1.sol
incorrect_constructor_name2.sol
incorrect_constructor_name3.sol
```

### Evaluation mismatch

Use this when Slither detects the vulnerability but the evaluator does not match it.

Possible fixes:

- add a justified detector/category mapping;
- repair source extraction;
- use precise node lines;
- allow function-scope matching for a specific detector when benchmark and detector point to different statements in the same vulnerability mechanism.

---

## Step 7 - Inspect Slither JSON when necessary

Save JSON:

```bash
slither <contract> \
  --json <temporary-name>.json \
  --fail-none
```

Inspect only the detector of interest.

Example Python:

```python
import json

with open("result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for detector in data["results"]["detectors"]:
    if detector["check"] == "<detector-name>":
        print(json.dumps(detector, indent=2))
```

Pay special attention to:

```text
elements
type
source_mapping.lines
source_mapping.start
source_mapping.length
type_specific_fields.parent
```

---

## Step 8 - Refactor carefully

After a justified fix:

```bash
python check_access_control_batch.py
```

Compare before/after.

A fix that detects the intended vulnerability but also causes unrelated vulnerabilities to match must be investigated.

Never accept a change solely because aggregate recall rises.

---

# Desired Final Access-Control Baseline Output

Eventually produce a stable report containing:

```text
contracts analyzed
contracts failed
ground-truth vulnerabilities
detected
missed
recall
```

Also produce per-vulnerability records such as:

```text
contract
GT category
GT lines
detected yes/no
matched detector(s)
matching method
```

Recommended matching-method values:

```text
exact_line
function_scope
none
```

Also record manually validated miss classifications where useful.

---

# Important Future Evaluation Improvements

Once the access-control baseline is stable:

## 1. Expand to other SmartBugs categories

Do not blindly reuse mappings.

Create category-specific detector mappings backed by validation.

---

## 2. Save structured baseline results

Prefer JSON/CSV output so results can later be used in thesis tables and charts.

Possible fields:

```text
contract
pragma
category
ground_truth_lines
detected
matched_detectors
matching_method
slither_findings_count
```

---

## 3. Add LLM verification experiment

The LLM should verify **Slither findings**, not discover vulnerabilities from scratch.

For each suitable Slither finding:

```text
Slither candidate
→ selective context builder
→ LLM verification
→ confirmed / false_positive / inconclusive
```

Collect:

```text
round_count
requested_fragments
input_tokens
output_tokens
total_tokens
verdict
```

---

## 4. False-positive benchmark

SmartBugs Curated is not sufficient for a rigorous false-positive reduction claim because unmatched findings are not necessarily false positives.

Later investigate a benchmark such as:

```text
Consolidated Ground Truth (CGT)
```

which contains manually validated positive and negative tool assessments.

This will be important for the main thesis claim:

```text
Slither baseline
vs
Slither + LLM verifier
```

with:

```text
precision
recall
F1
false-positive rate
```

---

## 5. Large-contract/context experiment

A second contribution should measure selective-context efficiency.

For each finding/project compare:

```text
full source size/tokens
vs
initial selective context tokens
vs
total tokens after context requests
```

Measure:

```text
context reduction %
rounds
requested fragments
token usage
```

Potential larger-project datasets can be investigated later, e.g. DAppSCAN or other multi-contract projects.

---

# Coding Guidelines

- Keep code readable and modular.
- Do not put benchmark-specific hacks tied to a filename unless absolutely necessary.
- Prefer detector semantics and source structure over filename-specific conditions.
- Preserve existing working architecture.
- Do not silently broaden mappings.
- Add comments explaining non-obvious evaluation decisions.
- Keep benchmark/evaluation code separate from core verifier code where practical.
- Use Python type hints.
- Avoid unnecessary dependencies.

---

# Git / Safety

Before large refactors:

```bash
git status
```

Review changes after modifications:

```bash
git diff
```

Do not delete working files or benchmark data.

Do not modify SmartBugs source contracts.

Generated temporary Slither JSON files can be kept out of source control or removed when no longer needed.

Do not commit secrets or `.env` API keys.

---

# Definition of Done for Current Phase

Do not move to the GUI yet.

Current phase is complete when:

1. the SmartBugs access-control baseline matcher is stable;
2. unresolved misses have been inspected or classified;
3. baseline results are exported reproducibly;
4. evaluation logic no longer has known false matching behavior;
5. the methodology is defensible in the thesis;
6. then the LLM-verification comparison can begin.

---

# Start Here

The access-control baseline audit is complete. Read:

- `benchmarks/access_control_report.md` for methodology and all miss decisions;
- `benchmarks/access_control_baseline.json` / `.csv` for the saved results;
- `benchmarks/access_control_audit.json` for the hash-bound manual miss ledger.

To reproduce the completed baseline:

```bash
source .venv/bin/activate
python check_access_control_batch.py
python -m unittest discover -s tests -v
```

The runner writes fresh JSON/CSV and raw Slither output to
`runs/access-control-baseline/`. All 12 regression tests pass. No detector
mappings were broadened; node byte offsets, file identity, half-open ranges,
and full ground-truth annotation identity are now preserved during matching.

Next phase: design and run the LLM-verification comparison over Slither findings,
recording verdicts, context requests, rounds, and token usage. Establish manually
verified negative assessments before claiming false-positive reduction. Do not
build the GUI yet. Do not repeat the completed miss audit unless source, tools,
or matching policy change.


# CGT Phase Update (2026-10-17)

Read `docs/cgt_notes.md` before continuing. CGT is contract/property ground truth,
not a table of labeled Slither findings. The schema-based loader, explicit
reviewed-finding linkage, metrics, and bounded pilot adapter are implemented.
All 36 tests pass, including the original 12. A real local SmartBugs context
preparation smoke test also passed without API calls.

Dataset acquisition is blocked: git cannot resolve github.com, and the web
reader rejects the 5.07 MB CSV at its size limit. No real CGT rows were downloaded;
compatibility is tested against documented-schema synthetic fixtures only.
`results/cgt_slither_baseline/` records blocked status and null metrics, not a
completed baseline. Eligible count and full-run usage are undetermined; no API
sample or paid calls have run. Model/key were absent from the process environment.

Next: acquire/pin CGT when network access is available, inspect actual rows,
validate narrow property mappings and exact Slither candidates locally, create
reviewed links, generate the real baseline, and run a small pilot. Stop and
report eligible count, sample usage, and full-run estimates before large paid runs.
Do not change the completed SmartBugs evidence or start GUI work.

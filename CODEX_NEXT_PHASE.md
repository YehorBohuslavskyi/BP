# CODEX NEXT PHASE - Bachelor Thesis Evaluation

## Project Goal

Continue the Bachelor Thesis prototype for:

**LLM-based smart-contract vulnerability verification**

The system architecture is:

```text
Static Analyzer (Slither)
        ↓
Candidate Finding
        ↓
Selective Dependency-Aware Context
        ↓
LLM Verification
        ↓
confirmed / false_positive / inconclusive
```

The thesis has two main goals:

1. Reduce false positives from traditional smart-contract static analyzers.
2. Reduce LLM context size so larger contracts/projects can be analyzed efficiently.

The GUI is NOT the priority yet.

The next priority is experimental evaluation.

---

# IMPORTANT: Current Baseline Is Finished

The SmartBugs Curated `access_control` baseline evaluation has been completed and manually audited.

Final result:

```text
Contracts analyzed: 18
Failed contracts: 0

Ground-truth vulnerabilities: 21
Detected by Slither: 9
Missed by Slither: 12

Recall: 42.86%
```

All unresolved misses were audited.

Final classification:

```text
9 detected vulnerabilities
12 genuine Slither misses
```

Do not change this baseline unless a real reproducible bug is found.

Do NOT broaden detector mappings just to increase recall.

---

# Current Quality Status

The evaluation implementation has already been improved to handle:

- Solidity compiler switching through `solc-select`;
- Slither `--fail-none`;
- old Slither JSON with empty line arrays;
- source offsets using `start` / `length`;
- precise node-level source locations;
- exclusion of broad contract-level source ranges;
- controlled function-scope matching for selected detectors;
- regression tests for location matching.

Current regression status:

```text
12 / 12 tests passing
```

Evidence has already been exported to:

```text
JSON
CSV
```

and the project context file has been updated.

Before changing evaluation code:

```bash
git status
git diff
```

Do not break the completed access-control baseline.

---

# Environment

Project root:

```bash
~/projects/BP
```

Environment:

```text
WSL Ubuntu 24.04
Python 3.12.3
virtualenv: ~/projects/BP/.venv
Slither installed
solc-select installed
```

Enter the project with:

```bash
cd ~/projects/BP
source .venv/bin/activate
```

Do not expose or commit API keys.

---

# Existing Source Architecture

Important files:

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

Important evaluation script:

```text
check_access_control_batch.py
```

Other test/evaluation scripts may also exist.

Before creating new code, inspect the current repository instead of assuming the exact file contents.

---

# Existing LLM Verifier

The verifier does NOT perform general vulnerability discovery.

It verifies a specific Slither finding.

Expected verdicts:

```text
confirmed
false_positive
inconclusive
```

The LLM should only evaluate the supplied static-analysis finding.

A different vulnerability does not confirm the supplied finding.

The finding description itself is not proof.

The LLM may request additional source fragments when required.

Selective context may include:

```text
target function
modifiers
state variable declarations
direct writers
related dependencies
```

Existing verifier statistics include:

```text
round_count
requested_fragments
input_tokens
output_tokens
total_tokens
```

Preserve this behavior.

---

# Why SmartBugs Is Not Enough For The Main Thesis Claim

SmartBugs Curated is useful for known-vulnerability detection / recall.

However:

```text
unmatched Slither finding != proven false positive
```

SmartBugs does not provide sufficiently strong verified negative labels for a rigorous false-positive reduction experiment.

Therefore the current SmartBugs experiment should be treated primarily as:

```text
Experiment 1:
Slither detection baseline
```

The main false-positive experiment now requires a benchmark containing manually validated positive and negative analyzer findings.

---

# NEXT PHASE: Consolidated Ground Truth (CGT)

The next major task is to investigate and integrate:

```text
Consolidated Ground Truth (CGT)
```

The purpose is to obtain reliable labels for static-analysis findings so that we can compare:

```text
Slither
vs
Slither + LLM verifier
```

on false-positive filtering.

---

# Codex Autonomous Working Rule

Work autonomously.

Do NOT ask the user to manually run routine commands that Codex can execute itself.

Codex should:

1. inspect the repository;
2. inspect current artifacts and tests;
3. research the CGT benchmark;
4. download/clone it if appropriate;
5. inspect its data format;
6. identify which records correspond to Slither;
7. implement a clean loader;
8. create reproducible baseline metrics;
9. connect the existing LLM verifier;
10. run experiments;
11. export results;
12. add tests;
13. update documentation.

Ask the user only if there is a real external blocker, credential requirement, paid resource, ambiguous product decision, or destructive action requiring approval.

---

# PHASE 1 - Research CGT

First determine the current authoritative CGT source.

Use web/repository documentation if necessary.

Document:

```text
repository / download source
paper / dataset reference
dataset version / commit if possible
license
number of contracts/projects
number of labeled assessments
which tools are represented
whether Slither is included
label format
finding location format
vulnerability taxonomy
```

Do not rely on remembered numbers if the actual dataset differs.

Save enough metadata so the experiment is reproducible.

Recommended output:

```text
docs/cgt_notes.md
```

or another appropriate project documentation file.

---

# PHASE 2 - Inspect CGT Structure

Before implementing a loader, inspect the raw files.

Determine whether records contain fields such as:

```text
contract/project
source path
tool
detector/rule
finding location
vulnerability category
positive/negative label
manual validation status
```

Also determine:

```text
Does one row represent a contract?
Does one row represent one analyzer finding?
Are labels per line, finding, category, or contract?
Are duplicate tool findings present?
```

Do not design the loader until the actual format is understood.

---

# PHASE 3 - Add A CGT Loader

Create a clean module, for example:

```text
src/context_audit/cgt_dataset.py
```

Exact naming can be adapted to repository conventions.

Use dataclasses where useful.

A possible conceptual representation is:

```python
@dataclass
class CGTFinding:
    contract: str
    source_path: Path | None
    tool: str
    detector: str | None
    category: str | None
    lines: list[int]
    label: str
```

BUT do not force this schema if the real CGT format suggests something better.

The loader should:

- validate required fields;
- preserve original labels;
- normalize paths carefully;
- avoid silently dropping records;
- report unsupported/ambiguous rows;
- support filtering for Slither.

Add unit tests.

---

# PHASE 4 - Build Slither False-Positive Baseline

The next important experiment is NOT another SmartBugs recall-only experiment.

We need a verified finding-level baseline.

For the CGT subset corresponding to Slither, calculate:

```text
TP
FP
TN
FN
Precision
Recall
F1
False Positive Rate
```

Depending on the exact CGT labeling structure, some metrics may need to be defined carefully.

Document the metric definition.

For binary finding validation, conceptually:

```text
positive label = finding is a real vulnerability
negative label = finding is not a real vulnerability
```

Then Slither's raw candidate findings are the baseline.

The most important baseline values for the thesis are:

```text
number of true findings
number of false-positive findings
precision
false-positive count/rate
```

Export structured evidence to:

```text
JSON
CSV
```

Do not only print terminal summaries.

---

# PHASE 5 - Connect Existing LLM Verifier

For each eligible labeled Slither finding:

```text
CGT Slither finding
       ↓
resolve source contract/function
       ↓
build selective context
       ↓
LLM verifier
       ↓
confirmed / false_positive / inconclusive
```

Do NOT ask the LLM to scan the whole contract for arbitrary vulnerabilities.

The LLM must verify the exact Slither finding represented by the benchmark record.

Use the existing:

```text
build_function_context()
build_initial_payload()
resolve_context_request()
verify_finding()
```

where practical.

Refactor reusable logic instead of duplicating it.

---

# PHASE 6 - Define LLM Classification Mapping

For evaluation, define clearly how LLM verdicts map to binary predictions.

Likely:

```text
confirmed       -> positive
false_positive  -> negative
inconclusive    -> abstain
```

Do NOT silently treat `inconclusive` as correct or incorrect without reporting it separately.

Report at least:

```text
confirmed count
false_positive count
inconclusive count
```

For metrics, provide both:

```text
1. metrics on non-abstained cases
2. coverage / abstention rate
```

if appropriate.

Document the exact evaluation policy.

---

# PHASE 7 - Compare Slither vs Slither + LLM

Produce a comparison table similar to:

```text
Metric                 Slither      Slither + LLM
-------------------------------------------------
True Positives         ...
False Positives        ...
False Negatives        ...
Precision              ...
Recall                 ...
F1                     ...
FP Rate                 ...
Inconclusive            N/A          ...
Coverage                100%         ...
```

Main thesis metric:

```text
False Positive Reduction =
(FP_slither - FP_llm) / FP_slither
```

Also report whether true positives were incorrectly filtered.

Reducing false positives is useful only if real vulnerabilities are retained.

So always examine:

```text
precision improvement
false-positive reduction
recall loss
```

together.

---

# PHASE 8 - Error Analysis

For incorrectly classified findings, export enough evidence for manual analysis.

Useful categories:

```text
LLM false rejection of true vulnerability
LLM failed to reject false positive
inconclusive due missing context
function resolution failure
unsupported source layout
compiler failure
context retrieval failure
```

Save sample cases for the thesis.

Do not hide failures from aggregate metrics.

---

# PHASE 9 - Selective Context Efficiency Experiment

This is the second major thesis contribution.

For every LLM-verified finding, measure:

```text
full source/project size
full source/project estimated token count
initial context size
initial context token count
number of context requests
number of requested fragments
total LLM input tokens
output tokens
total tokens
number of LLM rounds
```

Calculate context reduction such as:

```text
Context Reduction =
1 - selective_context_tokens / full_source_tokens
```

Be explicit about which token quantity is used:

```text
initial payload only
or
cumulative input across rounds
```

Prefer reporting both if useful.

---

# PHASE 10 - Large Contract / Project Experiment

After the CGT finding-level experiment works, evaluate the second thesis objective on larger projects.

Potential sources may include:

```text
DAppSCAN
CGT projects if large enough
other reproducible multi-contract datasets
```

Do not choose a dataset solely because it is large.

The project must compile or otherwise be analyzable reproducibly.

For each large project measure:

```text
number of Solidity files
LOC
full-source token count
candidate findings
selected fragments
context reduction
LLM rounds
LLM total token usage
```

The point is to demonstrate that the selective retrieval architecture does not need to send the entire codebase to the model.

---

# PHASE 11 - Experiment Outputs

Create reproducible experiment outputs under a clear directory, for example:

```text
results/
    smartbugs_access_control/
    cgt_slither_baseline/
    cgt_llm_verification/
    context_efficiency/
```

Use project conventions if a results directory already exists.

Each experiment should preferably contain:

```text
summary.json
findings.csv
errors.json
metadata.json
```

Possible metadata:

```text
date
git commit
Slither version
Python version
compiler versions
model name
dataset version/commit
experiment configuration
```

Do not include API secrets.

---

# PHASE 12 - Tests

Before considering each phase finished, add tests.

Important cases:

```text
CGT parser
positive label parsing
negative label parsing
Slither filtering
duplicate handling
source-location normalization
metric calculation
LLM verdict mapping
inconclusive handling
context-efficiency calculation
```

Keep existing 12 regression tests passing.

Run the full relevant test suite after refactors.

---

# PHASE 13 - Thesis-Ready Tables

Eventually produce data suitable for these thesis tables.

## Table A - SmartBugs Detection Baseline

Already approximately:

```text
Category: access_control
Contracts: 18
GT vulnerabilities: 21
Detected: 9
Missed: 12
Recall: 42.86%
```

---

## Table B - False-Positive Filtering

```text
Metric              Slither      Slither + LLM
------------------------------------------------
TP                  ...
FP                  ...
Precision           ...
Recall              ...
F1                  ...
FP reduction        -            ...
Inconclusive        -            ...
```

---

## Table C - Context Efficiency

```text
Metric
------------------------------------
Average full-source tokens
Average initial context tokens
Average cumulative LLM input tokens
Average requested fragments
Average rounds
Median context reduction
P95 context reduction
```

Exact metrics may be adjusted based on experiment results.

---

# PHASE 14 - GUI

Only after evaluation is stable, create a GUI.

Likely lightweight option:

```text
Streamlit
```

Possible UI:

```text
Upload Solidity contract/project
            ↓
Run Slither
            ↓
Show findings
            ↓
Run LLM verification

Finding:
Detector:
Impact:
Slither description:

LLM verdict:
confirmed / false_positive / inconclusive

Evidence fragments:
Rounds:
Tokens:
Context reduction:
```

Do NOT start GUI work before the CGT/LLM experiment and context-efficiency measurement are working.

---

# Research Methodology Rules

These rules are critical.

## Rule 1

Do not call every unmatched finding a false positive.

A false positive requires verified negative ground truth.

---

## Rule 2

Do not broaden a detector mapping merely because recall increases.

Mapping changes require semantic and source-location evidence.

---

## Rule 3

Do not use the benchmark label as an instruction to the LLM.

The label is only for evaluation after the model predicts.

Avoid leakage.

---

## Rule 4

Do not put expected verdicts into prompts, filenames, context explanations, or metadata visible to the LLM.

Benchmark labels must remain hidden from inference.

---

## Rule 5

Use the exact same labeled finding set when comparing baseline and LLM.

Do not cherry-pick successful LLM cases.

---

## Rule 6

Track failures and inconclusive cases.

Do not silently discard them.

---

## Rule 7

Freeze experiment configuration before final measurement.

Record:

```text
model
prompt version
max rounds
context policy
dataset version
Slither version
```

---

# Recommended Immediate Execution Plan

Start now with this exact sequence.

## 1. Inspect repository state

```bash
git status
git diff
```

Read:

```text
CODEX_CONTEXT.md
existing evaluation code
existing exported baseline JSON/CSV
existing tests
```

Do not overwrite completed evidence.

---

## 2. Research CGT

Find the authoritative dataset/repository and documentation.

Record:

```text
source
version
format
labels
Slither support
license
```

---

## 3. Acquire CGT

Put it in a logical dataset directory, for example:

```text
datasets/cgt/
```

unless the repository already uses another convention.

Do not commit huge generated/raw files if `.gitignore` conventions suggest otherwise.

---

## 4. Inspect the raw dataset

Use CLI/Python to print:

```text
top-level files
sample rows/records
label values
tools
detectors
source references
```

Write a concise dataset note.

---

## 5. Implement CGT loader

Add tests.

Run tests.

---

## 6. Extract Slither-labeled findings

Count:

```text
all records
Slither records
positive Slither findings
negative Slither findings
unknown/unsupported records
```

Export a clean intermediate dataset if useful.

---

## 7. Calculate baseline

Generate reproducible JSON/CSV.

---

## 8. Connect LLM verifier

Start with a SMALL validated sample first.

For example:

```text
5-10 true findings
5-10 false findings
```

Verify that:

- source resolution works;
- prompts do not leak labels;
- verdict mapping works;
- token statistics are saved.

Only after this succeeds, scale up.

---

## 9. Run full eligible CGT Slither subset

Export:

```text
per-finding result
aggregate metrics
errors
token/context metrics
```

---

## 10. Produce comparison and error analysis

Summarize:

```text
Slither baseline
Slither + LLM
FP reduction
precision change
recall change
inconclusive rate
context reduction
```

---

# IMPORTANT: Cost / API Usage

Before launching a large LLM experiment:

1. count eligible findings;
2. estimate approximate token usage;
3. run a small sample;
4. verify outputs;
5. only then run the full set.

Do not accidentally send hundreds/thousands of expensive requests before validating the pipeline.

If the number of API calls could be substantial, pause before the full run and report:

```text
eligible findings
sample token usage
estimated full-run token usage
```

The user can then decide whether to execute the full paid run.

Routine local analysis does not need confirmation.

---

# Current Definition of Success

The next phase is successful when Codex has produced:

1. a verified CGT dataset integration;
2. a reproducible Slither finding-level baseline;
3. labeled false-positive metrics;
4. an LLM verification pipeline over the same findings;
5. Slither vs Slither+LLM comparison;
6. token/context efficiency statistics;
7. regression/unit tests;
8. JSON/CSV evidence;
9. thesis-ready summary tables;
10. updated project documentation.

---

# Start Now

Begin by reading the current repository and `CODEX_CONTEXT.md`.

Then research and inspect the Consolidated Ground Truth benchmark.

Do not ask the user to manually execute routine commands.

Proceed autonomously through local setup, dataset inspection, loader implementation, tests, and baseline generation.

Before initiating a potentially large paid OpenAI API experiment, report the number of eligible findings and estimated token/API usage so the user can decide whether to run the full evaluation.

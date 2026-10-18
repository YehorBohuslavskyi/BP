# CGT integration and evaluation status

> **Current local evaluation:** CGT is now installed and tested. Read
> [cgt_local_evaluation.md](cgt_local_evaluation.md) for the real inventory,
> original Slither archive discovery, 27-finding baseline, exclusions, and
> pre-paid-run checkpoint. The acquisition-blocked narrative below is historical.
> The latest user instruction requires stopping before **any** paid LLM run.

## Status: implemented against the documented schema; real-data evaluation blocked

On 2026-10-17 the local command `git clone --depth 1 https://github.com/gsalzer/cgt.git datasets/cgt` failed with `Could not resolve host: github.com`. The web reader could read upstream documentation and taxonomy mapping, but rejected `consolidated.csv` at its 4 MiB limit. GitHub displays that file as 5.07 MB and does not render its records. No full CGT CSV or source collection was acquired. No actual CGT record counts, Slither baseline, paid sample, or large-project measurements can honestly be reported yet. Tests use explicitly synthetic in-memory fixtures, not purported CGT observations.

The completed SmartBugs baseline and its saved evidence were not modified. All 36 unit/regression tests pass, including the original 12. The pilot test uses a mocked API and temporary synthetic fixtures; its artificial token counts are not experiment evidence.

## Authoritative references

- Repository: [gsalzer/cgt](https://github.com/gsalzer/cgt).
- Paper: Monika di Angelo and Gernot Salzer, [Consolidation of Ground Truth Sets for Weakness Detection in Smart Contracts](https://arxiv.org/abs/2304.11624), extended WTSC 2023 paper; inspected PDF identifies v2, 2 May 2023.
- [Construction documentation](https://github.com/gsalzer/cgt/blob/main/construction/README.md).
- [Property taxonomy mapping](https://github.com/gsalzer/cgt/blob/main/construction/sql/02_mapping.csv).
- [Consolidated CSV](https://github.com/gsalzer/cgt/blob/main/consolidated.csv).

The inspected branch is `main`; its immutable commit was not retrievable in this environment. It must be recorded from the actual checkout before measurement. Published dataset counts are not substituted for a local inventory. Contract/project counts, assessment counts, source availability, and label frequencies remain unknown for the unacquired revision.

Licensing is mixed: repository Python/SQL code uses MIT, original datasets retain their licenses, and Solidity sources retain the original source licenses (often from Etherscan). The whole source collection must not be described as uniformly MIT.

## Schema and methodological correction

The published CSV uses semicolons. Required fields are `dataset`, `id`, `property`, `property_holds`. Other documented columns are `chain`, `addr`, `contractname`, `fp_sol`, `fp_sol2`, `fp_bytecode`, `fp_runtime`, `swc`, `dasp`.

A row is a **contract/property assessment**. `t`/`f` indicate whether that specific property holds. `dataset` names the originating benchmark; it is not the detecting tool. The consolidated schema contains no Slither tool column, detector name, finding ID, or line locations. There is no direct “Slither-labeled findings” filter. An assessment is identified by `(dataset, id, property)`; the same contract may occur in several datasets and for several properties.

Sources use `source/<fp_sol>.sol`; fingerprints are MD5 of normalized source, not raw-file checksums. Original source positions may differ from the consolidated source, so importing old line locations without checking is invalid. The loader preserves raw fields and labels, validates fingerprints and taxonomy values, and reports missing sources, invalid rows, duplicate keys, and conflicting labels. It never invents finding positions or interprets every property as a weakness. `filter_tool()` explicitly rejects unsupported tool filtering.

Contributing benchmarks listed upstream include CodeSmells, ContractFuzzer, Doublade, eThor, EthRacer, Ever Evolving Game, JiuZhou, Not So Smart Contracts, NPChecker, SmartBugs curated, SolidiFI, SWC registry, and Zeus. These are provenance datasets, not proof that tool outputs are preserved in consolidated rows. SWC/DASP identify taxonomies; they do not themselves establish exact equivalence to Slither rules.

## Correct experiment units

Two separate designs are possible after acquisition:

1. Contract/property classification: run Slither on the assessed source and named contract, validate rule-to-property semantics, and measure whether any relevant warning is emitted. This supports contract/property TP, FP, TN, FN. These are not finding-level metrics.
2. Finding verification (implemented review boundary): retain exact Slither output and explicitly review which candidate corresponds to the CGT property judgment. A contract having a genuine weakness does **not** establish that every warning of that category is true. Even negative propagation requires matching property semantics, source, and assessed contract scope.

The implementation currently supports design 2 once the review manifest exists. It deliberately does not manufacture an automatic mapping policy without inspecting the raw dataset. After acquisition, perform the source/semantic review locally and populate the manifest; this is evaluation work, not a demand that the user manually label routine results.

## Implemented entry points

- `src/context_audit/cgt_dataset.py`: documented-format loader and inventory issues.
- `src/context_audit/cgt_findings.py`: validates reviewed links, source/output SHA256, annotation identity, exact finding ID, contract/file identity, and duplicate candidates.
- `src/context_audit/classification_metrics.py`: fixed-cohort metrics, abstentions, conservative FP reduction, context denominators.
- `src/context_audit/cgt_inference.py`: inference allowlist, neutral fragment/file IDs, comment stripping, reversible context-request IDs.
- `src/context_audit/cgt_sample.py`: bounded pilot, frozen configuration, actual API usage, partial-error records, JSON/CSV, full-run projections when the sample succeeds.
- `check_cgt.py`: default offline inventory/baseline and explicitly enabled small pilot; no full-paid-run mode.
- `verifier.py`: preparation extracted from inference so contexts can be inspected without an API call; existing `verify_finding()` behavior retained.

Reproduction commands once dataset access is available:

```bash
source .venv/bin/activate
python check_cgt.py
python -m unittest discover -s tests -v
```

The default output is `results/cgt_slither_baseline/{summary.json,metadata.json,findings.csv,errors.json}`; `assessments.csv` is generated only after a CSV was loaded. Missing inputs produce an explicit blocked status and null metrics, with nonzero exit status. A real checkout's commit and CSV hash are recorded. Raw downloaded CGT content is ignored by Git.

### Reviewed manifest

`--review-manifest PATH` accepts a JSON array. Each entry requires:

- `review_id`: unique identifier; `assessment_key`: `[dataset, id, property]`.
- `review_status`: `accepted`; `reviewer` and `rationale`: finding-level semantic review provenance.
- `property_is_weakness`: true, after validating the property direction; `label`: boolean agreeing with that assessment.
- `source_sha256`, `slither_json` (relative to the manifest), `slither_json_sha256`, `finding_id`.
- `compiler_version`, `slither_version`, `leakage_reviewed`: true.

Reviews are separate evaluation metadata and never enter prompts. Missing function/file identity and ambiguous annotations are rejected and reported. Cross-dataset duplicates of the same source/rule/function/location are not silently counted twice. Human review must check semantic equivalence and leakage from identifiers/literals that comment stripping cannot remove. The manifest is an auditable input, not evidence that a review happened automatically.

## Metrics

On the reviewed candidate cohort, raw Slither predicts positive for every candidate. TP equals positive labels and FP negative labels; TN and FN are zero by construction. Candidate-conditioned recall is 1 when positives exist, and candidate-conditioned FPR is 1 when negatives exist. This says nothing about vulnerabilities Slither never reported. Precision is TP/(TP+FP); false-discovery fraction is FP/(TP+FP), distinct from FPR=FP/(FP+TN). Undefined denominators are null.

LLM `confirmed` predicts positive; `false_positive` predicts negative; `inconclusive` abstains. Runtime errors are separately counted, not folded into the confusion matrix. Precision, recall, F1, and FPR use only decided cases, alongside coverage, abstention rate, and error rate.

FP reduction uses a conservative filtering policy: retain inconclusive/error findings. Only explicit rejection of a negative counts as reduction. Otherwise simply abstaining on false positives would falsely improve the result. Incorrect rejection of positive findings and its rate are reported alongside FP reduction. Sample comparisons use the exact same sample cohort for both Slither and LLM; a balanced pilot is not presented as a full-dataset result.

Context metrics distinguish initial source, complete initial payload, and cumulative API input. Reduction is `1 - tokens/full_source_tokens`; negative values are allowed. Local planning counts currently use `ceil(characters/4)`, not a model tokenizer. API usage is measured from responses. Consequently cumulative reductions have an estimated source denominator and must be described as estimates. No claim of tokenizer-exact savings is supported yet.

## Executed evidence and cost checkpoint

`results/cgt_slither_baseline/` contains actual blocked-run evidence, not a numerical benchmark. `runs/cgt-preparation-smoke.json` records a real local Slither/context-preparation smoke test using the existing SmartBugs `phishable.sol` source: function resolution succeeded, two fragments were available, and the initial payload was approximately 254 tokens by the characters/4 heuristic. This is not a CGT sample and excludes system/schema overhead. No API calls were sent.

- Eligible CGT findings: **undetermined**, because the dataset and reviewed links are unavailable.
- Actual CGT sample tokens/API calls: **no sample; 0 calls**, not a zero-token successful sample.
- Estimated full-run usage: **unavailable**, pending cohort and pilot.
- API key and model were not configured in the current process environment when checked; no secrets were printed.

`--run-sample N` explicitly enables a paid pilot capped at 20 findings and four rounds each. Existing pilot directories are never overwritten. Before any larger run, inspect the pilot and report eligible findings, actual sample input/output/total tokens, actual calls, projected full-run tokens/calls, and uncertainty. The current code has no automatic escalation to a full run.

## Resume sequence

1. Restore dataset download access and acquire/pin CGT; inspect actual rows before declaring loader compatibility verified.
2. Run inventory and resolve/report all unsupported rows and overlap/conflict cases.
3. Select semantically narrow properties; run local Slither with pinned available compilers, preserving failures and raw artifacts.
4. Review exact findings against assessment scope and create the hash-bound manifest. Do not transfer category-positive labels indiscriminately.
5. Generate real reviewed-cohort baseline; dry-check all eligible source/function contexts.
6. Configure a model/API credential through the normal environment; execute a small balanced pilot and inspect predictions, context, and accounting.
7. Stop with the cost checkpoint before the full paid run, as explicitly requested.
8. Only after that experiment works, proceed to large-project and GUI work.

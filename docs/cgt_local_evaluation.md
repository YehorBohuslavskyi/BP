# Local CGT evaluation and pre-paid-run checkpoint

## Completed local work

The supplied CGT copy was inspected locally; no download or clone was attempted. All 20,455 assessments parse successfully. The 36 existing tests plus eight local integration/preflight checks pass: **44 tests total**. Real Slither 0.11.6 / solc 0.4.25 analyses were run for all 43 uniquely linked, label-consistent archive groups. All compiled successfully. All 27 finally accepted candidates also passed context preparation and original-versus-consolidated target-function equivalence checks. No API calls were made.

The completed SmartBugs baseline was preserved. Its evaluator, finding parser, and runner still match the code hashes recorded in the saved baseline.

## Actual inventory

| Quantity | Count |
| --- | ---: |
| Assessments, excluding header | 20,455 |
| `property_holds=t` | 5,619 |
| `property_holds=f` | 14,836 |
| Unique `(dataset,id)` entries | 4,190 |
| Unique source fingerprints / Solidity files | 3,103 |
| Unique `(source fingerprint, named contract)` pairs | 3,088 |
| Source-fingerprint/contract pairs including unnamed entries | 3,144 |
| Unique `(chain,address)` identities with an address | 2,559 |
| Property-name strings | 160 |
| Dataset-qualified properties | 178 |
| Assessments with an available source | 19,456 |
| Assessments without a source reference | 999 |
| Referenced source files missing from disk | 0 |
| Invalid rows / duplicate assessment keys / conflicting same keys | 0 / 0 / 0 |

“Unique contracts” is not one interchangeable number: an entry can reoccur across datasets, one source can define several contracts, and some rows omit contract names or addresses. The counts above state their identity definitions rather than calling 3,103 source files 3,103 distinct deployed contracts. There are 56 source hashes with unnamed contract assessments. The complete dataset/property/label counts are in `results/cgt_linkage/properties.csv`.

The actual columns are:

```
dataset;id;property;property_holds;chain;addr;contractname;
fp_sol;fp_sol2;fp_bytecode;fp_runtime;swc;dasp
```

The data copy has no `.git`. Running `git rev-parse` inside it would discover the parent BP repository, not a CGT revision, so that value is deliberately not reported as the dataset commit. The CSV is pinned by SHA256:

```
306f91a45c783494cbc9b6010c3e044ffcfcd9a67e80165f6d896528fa1d94ba
```

Source, validation-table, and archived/fresh output hashes are preserved in linkage records and reviews. Missing source references are coverage warnings, not malformed-row errors. The runner now writes them to `warnings.json` and reports successful inventory/baseline execution separately.

## What actually links to Slither

The consolidated CSV has no tool, detector, finding, or source-line columns. However, the local copy also includes:

```
construction/originalSets/Doublade/validation_results/slither_*.csv
construction/originalSets/Doublade/outputs/slither/test*.json
construction/originalSets/Doublade/source_code/test*.sol
construction/originalSets/Doublade/address.csv
```

The five Slither validation CSVs have `file;contractname;classification` columns. Their judgments are **file/contract/weakness groups**, not necessarily individual warnings. Their files and JSON outputs contain real Slither-specific evidence. The upstream `construction/scripts/bm/parsers/Doublade.py` consolidates `doublade_*.csv`, not `slither_*.csv`. Consequently, original Slither labels must not automatically be called consolidated CGT labels.

| Archived validation family | Rows | TP | FP |
| --- | ---: | ---: | ---: |
| Low-level call | 29 | 29 | 0 |
| Reentrancy | 133 | 21 | 112 |
| Selfdestruct | 17 | 3 | 14 |
| tx.origin | 18 | 8 | 10 |
| Unexpected revert | 222 | 23 | 199 |
| Total | 419 | 84 | 335 |

Historical **group-level** precision is 84/419 = **20.05%**. This is neither 419 individually labeled warnings nor the performance of current Slither over all CGT. The historical Slither version is not recorded in the archived JSON.

Linkage follows the original address lookup to `(Doublade, address-contract-property, property)`, checks original/consolidated label agreement, and requires exactly one archived warning of the corresponding detector in the named contract. Fresh analysis then must reproduce the detector, contract, function signature, and normalized node-expression set. Archived byte/line offsets are not reused: inspection showed they refer to reordered sources and can point at unrelated code in the supplied source files.

The 43 structurally unique, label-consistent groups were all reanalyzed. There were 37 exact expression reproductions and six mismatches. The six are recorded as linkage problems, not automatically declared Slither false negatives.

## Exclusions and reviewed cohort

These mutually exclusive reasons partition all 419 validation rows; their precedence is absence of counterpart, conflicting label, multiple warnings, current-expression mismatch, then semantic review.

| Outcome | Rows |
| --- | ---: |
| No unique consolidated counterpart | 324 |
| Archived label conflicts with consolidated label | 24 |
| Multiple historical warnings in otherwise consistent group | 28 |
| Current expression set does not reproduce exactly | 6 |
| `calls-loop` description does not establish unexpected-revert property | 8 |
| Uncertain negative-label semantics for tx.origin | 2 |
| Accepted | 27 |

Thus **392 archive rows remain unresolved/ineligible** under this conservative protocol. The overlapping diagnostic counts are also preserved: e.g. 191 groups contain multiple warnings overall, including groups excluded earlier for other reasons. These are not 392 missing vulnerability detections and are not a count over all 20,455 CGT assessments.

The two semantically uncertain tx.origin negatives are `MultiMonday.Today` and `GrungeTuesday.multi_x`. Their payouts return to `tx.origin`, but that does not settle the warning's authorization/forced-action claim; similar EtherTime code also exposes disagreement between the original and consolidated labels. Their labels were retained unchanged and excluded pending independent adjudication.

Accepted findings comprise:

| Detector | Positive | Negative |
| --- | ---: | ---: |
| unchecked-lowlevel | 16 | 0 |
| reentrancy-eth | 3 | 0 |
| suicidal | 2 | 3 |
| tx-origin | 1 | 2 |
| Total | 22 | 5 |

Each has a source rationale in `reviews.json`. Positive low-level-call findings discard the reported return value. Positive reentrancy findings call externally before decrementing the caller's balance. Positive suicidal findings expose unguarded self-destruction. The tx.origin positive uses the owner-origin test while writing a referral entry for `msg.sender`. Negative suicidal cases have actual owner/admin gates; negative tx.origin cases also enforce the configured ICO caller and compliance checks.

Reviews were performed by Codex using local source and artifacts; they are **not independent human adjudication**. Original benchmark labels remain separate provenance. The two Tokens refund functions are near-identical, several positives are related token templates, and two negative suicidal findings share a source. The 27 observations are finding occurrences, not 27 independent programs; a final thesis experiment should account for clone clusters and avoid treating this selected, consensus-only subset as representative of all Slither warnings.

## Real linked-finding baseline

| Metric | Value |
| --- | ---: |
| Eligible linked findings | 27 |
| TP | 22 |
| FP | 5 |
| TN / FN | 0 / 0 |
| Precision | 81.48% |
| False-discovery fraction, FP/(TP+FP) | 18.52% |
| Candidate-conditioned recall | 100% |
| Candidate-conditioned F1 | 89.80% |
| Candidate-conditioned FPR, FP/(FP+TN) | 100% |

All candidates are raw positive warnings, so TN/FN are zero by construction. Recall/FPR above do not measure vulnerability coverage or non-warning behavior. No Slither+LLM comparison exists yet. The historical 419-row group baseline and this selected 27-finding baseline have different denominators and must not be compared as an improvement.

## Pre-paid-run checkpoint

All **27** accepted candidates compile and resolve through the existing selective context builder. Each target function was also compiled from the original Doublade source and compared to the consolidated source after removing comments and insignificant whitespace while preserving string literals and identifier tokens. All passed. This verifies target-function equivalence, not full cross-contract semantic equivalence. Inherited/external dependencies remain a known context limitation: for example, Question's admin check calls its owner market, which may require context beyond the current catalog. Such cases must be retained as inconclusive if evidence is unavailable.

The frozen pilot is **10 findings: 5 positive and 5 negative**, selected deterministically by alternating labels and cycling detector families. It covers all four accepted detector families. IDs are in `results/cgt_preflight/summary.json`.

Token estimates include the system prompt, structured-response schema, and prepared payload. They use **ceil(characters/4)**, not a model tokenizer. The four-round estimate assumes all available fragments are included on every round; output figures are configured ceilings, not forecasts of typical consumption.

| Usage | Pilot (10) | All linked findings (27) |
| --- | ---: | ---: |
| First-round input estimate | 11,961 | 30,080 |
| API request range, 1–4 rounds | 10–40 | 27–108 |
| Four-round input estimate with all available context | 88,492 | 237,036 |
| Output-token cap, 4,000 per request | 160,000 | 432,000 |

Actual paid calls/tokens: **none**. No model is frozen yet, so no dollar-cost estimate is claimed. These estimates are not billing guarantees, particularly for reasoning tokens and tokenizer-specific overhead. **Stop here before any paid LLM call**, per the user's latest instruction. Approval of the pilot would not authorize the subsequent full paid run.

## Evidence and reproduction

- `results/cgt_linkage/summary.json`, `properties.csv`, `archive_links.json`, `findings.csv`: inventory and complete historical linkage audit.
- `results/cgt_linkage/live_links.json`, `raw/`: all 43 local analyses and unresolved rows.
- `results/cgt_reviewed_baseline/reviews.json`, `linkage_decisions.json`, `exclusion_summary.json`: explicit reviewed cohort and exclusion rationale.
- `results/cgt_reviewed_baseline/summary.json`, `findings.csv`, `metadata.json`, `errors.json`, `warnings.json`: real linked baseline.
- `results/cgt_preflight/summary.json`, `findings.json`, `findings.csv`, `errors.json`, individual neutral payloads: zero-cost context preparation and forecast.

From the repository root:

```bash
source .venv/bin/activate
python check_cgt_linkage.py
python check_cgt.py --review-manifest results/cgt_reviewed_baseline/reviews.json --output-dir results/cgt_reviewed_baseline
python check_cgt_preflight.py
python -m unittest discover -s tests -v
```

The review ledger is a frozen review artifact, not a script that automatically labels every structurally matched result. If input or output hashes change, review validation fails instead of silently reusing judgments. Full row exports (`assessments.csv`) remain available locally and reproducible but are ignored by Git to avoid duplicating the raw dataset. Earlier acquisition-blocked evidence is historical; use the paths above for the current experiment.

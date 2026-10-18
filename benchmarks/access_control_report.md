# SmartBugs access-control baseline audit

Completed 2026-10-17 with Slither 0.11.6, solc-select 1.2.0, and the exact compiler versions in the dataset metadata. All 18 contracts analyzed successfully: 21 annotated vulnerabilities, 9 detected, 12 missed, recall **42.86%**. All previously unresolved misses have been inspected against source and full Slither output. No new detector mappings were justified.

## Reproduce

From the repository root:

```bash
source .venv/bin/activate
python check_access_control_batch.py
python -m unittest discover -s tests -v
```

The runner selects each compiler through `SOLC_VERSION` (supported by the installed solc-select), runs `slither <source> --json - --fail-none`, and writes `runs/access-control-baseline/baseline.json`, `baseline.csv`, and raw JSON/stderr under `raw/`. Installed compilers are required; unavailable compilers are recorded as failures. The runner exits nonzero if any analysis fails. Failed annotations are reported as unanalyzed, not silently excluded or counted as confirmed misses; full-subset recall is null on partial runs.

Durable snapshots are `benchmarks/access_control_baseline.json` and `.csv`. They include per-annotation detection, detector names, matching methods, source hashes, tool/compiler versions, code hashes, match IDs, and manual audit notes. Regeneration does not overwrite these snapshots automatically. Raw outputs remain in the ignored `runs/` directory and can be regenerated with the command above. `access_control_audit.json` contains the separate manual miss ledger; it does not control matching. Audit notes are applied only when annotation, source hash, and Slither version agree.

## Matching policy and limits

Category compatibility is necessary but insufficient: a detector must also overlap the annotation using its most precise reported locations. Contract-wide ranges are excluded. Nodes take priority over functions, which take priority over other non-contract elements. Empty line arrays are reconstructed from the selected element's byte offsets, preserving UTF-8 byte indexing and half-open range boundaries. Known filenames must match the benchmark source. The old-solc missing-filename fallback assumes the current single-source inputs; multi-file evaluation requires additional provenance work.

`exact_line` means overlap with Slither's selected reported location, which can itself be a whole function for function-level detectors. In particular, `suicidal` reports functions in the old compiler JSON. This label does not assert statement-level precision. `function_scope` is an explicit relaxation used only for `controlled-array-length`: in `mapping_write.sol`, expansion at line 17 enables the arbitrary storage write at line 20 within `set`. Rubixi's array push at line 61 cannot match the wrong constructor at lines 23–24.

The `tautology` match at `arbitrary_location_write_simple.sol:27` identifies the ineffective unsigned-length guard enabling underflow and arbitrary storage writes; it is evidence for the annotated mechanism, not proof that Slither reconstructs the whole exploit. These mappings were validated for this subset and must be revisited before broader evaluation.

The 21 denominator items are dataset annotations, not necessarily 21 independent exploits. Parity has separate annotations for parts of an exploit. Only the `kill` annotation in Parity 2 is matched; its initializer remains missed. Parity 1's `suicidal` finding in another function does not match either annotated location.

SmartBugs supplies known positive annotations, not exhaustive negative labels. Unmatched findings are **unmatched findings**, not false positives. This run supports annotation recall; precision, F1, false-positive rate, and false-positive reduction cannot be inferred from it. Manual miss classifications mean no semantically corresponding finding in this installed/default detector run, not that every Slither configuration or future version must miss them.

## Per-annotation results

| Contract | GT lines | Result | Detector | Method |
| --- | --- | --- | --- | --- |
| FibonacciBalance.sol | 31 | detected | controlled-delegatecall | exact_line |
| FibonacciBalance.sol | 38 | detected | controlled-delegatecall | exact_line |
| arbitrary_location_write_simple.sol | 27 | detected | tautology | exact_line |
| incorrect_constructor_name1.sol | 20 | missed | — | none |
| incorrect_constructor_name2.sol | 18 | missed | — | none |
| incorrect_constructor_name3.sol | 17 | missed | — | none |
| mapping_write.sol | 20 | detected | controlled-array-length | function_scope |
| multiowned_vulnerable.sol | 38 | missed | — | none |
| mycontract.sol | 20 | detected | tx-origin | exact_line |
| parity_wallet_bug_1.sol | 223 | missed | — | none |
| parity_wallet_bug_1.sol | 437 | missed | — | none |
| parity_wallet_bug_2.sol | 226 | missed | — | none |
| parity_wallet_bug_2.sol | 233 | detected | suicidal | exact_line |
| phishable.sol | 20 | detected | tx-origin | exact_line |
| proxy.sol | 19 | detected | controlled-delegatecall | exact_line |
| rubixi.sol | 23, 24 | missed | — | none |
| simple_suicide.sol | 12, 13 | detected | suicidal | exact_line |
| unprotected0.sol | 25 | missed | — | none |
| wallet_02_refund_nosub.sol | 36 | missed | — | none |
| wallet_03_wrong_constructor.sol | 19, 20 | missed | — | none |
| wallet_04_confused_sign.sol | 30 | missed | — | none |

## Miss audit

- **incorrect_constructor_name1.sol:20** — Public wrong-name constructor assigns owner; version/naming findings do not identify ownership takeover.
- **incorrect_constructor_name2.sol:18** — Wrong-case constructor is publicly callable and assigns owner; only compiler-version findings.
- **incorrect_constructor_name3.sol:17** — Wrong-name constructor permits ownership takeover; version/naming findings do not identify it.
- **multiowned_vulnerable.sol:38** — newOwner lacks onlyOwner, allowing self-registration followed by withdrawAll. Only version/naming findings; naming at the same line is unrelated.
- **parity_wallet_bug_1.sol:223** — Public initWallet calls initDaylimit and initMultiowned without authorization. external-function and naming findings concern visibility/style, not reinitialization; suicidal concerns kill at 229-231.
- **parity_wallet_bug_1.sol:437** — Fallback forwards arbitrary calldata to a constant library. unchecked-lowlevel reports ignored return status and low-level-calls reports call usage, neither identifies unauthorized initialization through delegation. suicidal concerns a different function.
- **parity_wallet_bug_2.sol:226** — only_uninitialized prevents repeat initialization but permits anyone to initialize the library itself. No finding identifies this initializer vulnerability; suicidal identifies kill at 233-235 and matches the separate GT at 233.
- **rubixi.sol:23,24** — DynamicPyramid is a public wrong-name constructor assigning creator. naming-convention at 23-25 is style only. controlled-array-length at 61 belongs to addPayout at 59-79; events-access and missing-zero-check concern changeOwner at 108-110.
- **unprotected0.sol:25** — Public changeOwner lacks onlyowner. missing-zero-check at 28 concerns a zero address, not caller authorization; naming at 25 and version warnings are unrelated.
- **wallet_02_refund_nosub.sol:36** — refund transfers the recorded balance without clearing it, allowing repeated withdrawals. reentrancy-unlimited-gas concerns withdraw at 28-32, not refund; missing-zero-check concerns migrateTo.
- **wallet_03_wrong_constructor.sol:19,20** — Public initWallet assigns creator and enables migrateTo takeover. Findings concern withdraw reentrancy, migrateTo zero-check, and compiler version, not initialization.
- **wallet_04_confused_sign.sol:30** — withdraw uses amount >= balance instead of <=. reentrancy-unlimited-gas in the same function concerns transfer followed by state update, not the reversed comparison; zero-check/version findings are unrelated.

## Validation and next phase

The initial batch and final batch both produced 9/21 detections. Re-evaluating all captured raw outputs with the revised matcher agreed with the fresh run for every annotation and finding count. Twelve regression tests cover precise-node priority, missing-line reconstruction, source-file isolation, contract-range exclusion, opt-in function scope, byte boundaries, annotation identity, failed analysis accounting, invalid JSON, and category filtering.

The audited access-control baseline is complete for this subset. Next is a separately specified LLM verification experiment over Slither findings, retaining `confirmed` / `false_positive` / `inconclusive` decisions and token/context usage. False-positive reduction requires manually verified negative assessments; the unmatched SmartBugs findings cannot supply those labels automatically. No GUI work or paid LLM experiment was started during this audit.

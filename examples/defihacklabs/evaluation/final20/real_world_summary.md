# Current DeFiHackLabs real-world evaluation

**The nominated 20-case cohort is not frozen.** All nominated metrics below are provisional completed-case descriptions. Supplemental cases never enter nominated/frozen headline metrics.

## Completed SOURCE_READY cases

| Case | Role | Compiler | Status | Slither findings | Baseline | Matched detector / finding ID | Target? | LLM verdict | Rounds | Requested fragments | API input / output / total |
|---|---|---|---|---:|---|---|---|---|---:|---:|---|
| SpankChain | NOMINATED_PROVISIONAL | 0.4.25 | SOURCE_READY | 126 | DETECTED | reentrancy-eth / da49c1a96621ac0ec579d1887de3a8ce6ffd1be3d610c7819b78645f05e0e19f | Yes (LEGACY_PILOT) | Unavailable | Unavailable | Unavailable | Unavailable / Unavailable / Unavailable |
| XSURGE | NOMINATED_PROVISIONAL | 0.8.5 | SOURCE_READY | 21 | DETECTED | reentrancy-eth / 283e78f92682b97003c79c283ba78a6a978eb958c5d03c0c58416f345bf2ebc5 | Yes (FINAL20) | confirmed | 2 | 4 | 6682 / 1331 / 8013 |
| BurgerSwap | NOMINATED_PROVISIONAL | 0.6.6 | SOURCE_READY | 96 | MISSED | None | No | Unavailable | Unavailable | Unavailable | Unavailable / Unavailable / Unavailable |
| Visor Finance | NOMINATED_PROVISIONAL | 0.7.6 | SOURCE_READY | 41 | MISSED | None | No | Unavailable | Unavailable | Unavailable | Unavailable / Unavailable / Unavailable |
| Eleven Finance | SUPPLEMENTAL | 0.6.12 | SOURCE_READY | 58 | MISSED | None | No | Unavailable | Unavailable | Unavailable | Unavailable / Unavailable / Unavailable |
| bEarn | SUPPLEMENTAL | 0.6.12 | SOURCE_READY | 115 | MISSED | None | No | Unavailable | Unavailable | Unavailable | Unavailable / Unavailable / Unavailable |
| Spartan Protocol | SUPPLEMENTAL | 0.6.8 | SOURCE_READY | 76 | MISSED | None | No | Unavailable | Unavailable | Unavailable | Unavailable / Unavailable / Unavailable |

SpankChain: baseline/126-finding count imported from `../slither_baseline.json` (full raw default-run limitations remain). Matched ID is from that existing pilot record; its target is in `../verification_targets.json`. No detailed pilot LLM result is in final20, so verdict, rounds and usage remain unavailable. Historical user-reported confirmation is not substituted for a saved trace. XSURGE result comes from `llm_results/xsurge-reentrancy-eth-283e78f92682.json`. Other unavailable fields indicate no applicable/completed LLM result, not zero usage.

## Separate metrics

| Scope | SOURCE_READY | DETECTED | MISSED | Recall | Targets | Saved completed LLM results | Confirmed | Lost (false_positive) | Retention |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| Nominated, provisional completed cases | 4 | 2 | 2 | 50.00% | 2 | 1 | 1 | 0 | 100.00% |
| Supplemental only | 3 | 0 | 3 | 0.00% | 0 | 0 | 0 | 0 | N/A |
| Combined descriptive only | 7 | 2 | 5 | 28.57% | 2 | 1 | 1 | 0 | 100.00% |

Frozen-cohort metrics: **not available**. Baseline denominators are 4 nominated, 3 supplemental, 7 combined completed cases. Sixteen nominations are not SOURCE_READY and are not silently counted as misses. Final20 has one target; the target counts above additionally include the separately identified legacy SpankChain pilot target. Retention is **1/1 completed results**, not 1/2 targets: the pilot trace is unavailable. No supplemental known vulnerability generated a suitable detector match, so supplemental LLM retention is undefined. Slither misses are not LLM failures. XSURGE usage totals are 6,682 input + 1,331 output = 8,013 tokens; 2 rounds and 4 unique requested fragments. No unavailable pilot usage is imputed.

## Pipeline

| Case | Source ready? | Slither | LLM target? | LLM verdict |
|---|---|---|---|---|
| SpankChain | Yes | DETECTED | Yes | Unavailable |
| XSURGE | Yes | DETECTED | Yes | confirmed |
| BurgerSwap | Yes | MISSED | No | Unavailable |
| Visor Finance | Yes | MISSED | No | Unavailable |
| Eleven Finance | Yes | MISSED | No | Unavailable |
| bEarn | Yes | MISSED | No | Unavailable |
| Spartan Protocol | Yes | MISSED | No | Unavailable |

## Observed reasons for upstream misses

- **Visor:** missing receipt validation/contract-branch authorization semantics; the flagged ERC20 sink is in the other branch.
- **BurgerSwap:** stale precomputed amounts reused after callback-driven state changes; event-order findings do not identify this condition.
- **Eleven:** missing accounting action—underlying assets returned without burning shares.
- **bEarn:** cross-contract denomination mismatch (BUSD versus ibBUSD).
- **Spartan:** liquidity-share calculations relying on manipulable current pool balances.

These categories summarize only the existing case adjudication/integration records; they are not claims about Slither capabilities across all incidents. The full existing reasons are preserved in the JSON report.

## Methodological interpretation

The verifier reviews Slither candidate findings. A known vulnerability missed by static analysis is an upstream miss: a verifier cannot recover it when no suitable candidate is supplied. LLM retention must therefore be measured only on independently mapped, detected known vulnerabilities, with completion/missing-result counts explicit. Additional Slither findings remain unlabeled unless independently adjudicated; this report assigns no new TP/FP labels. Existing disputed cases are not converted into binary labels. Supplemental observations are descriptive and cannot change frozen-cohort headline results.

## Preservation

Only real_world_summary.md and real_world_summary.json are generated. Existing evaluation/evidence/target/result files are read only and hash checked. No source processing, compilation, Slither, inference or target generation occurs.

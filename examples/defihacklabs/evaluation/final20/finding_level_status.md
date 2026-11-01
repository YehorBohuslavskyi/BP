# Finding-level real-world evaluation status

Recovered individual findings: **421**. Recorded default-run totals: **533**. Inventory complete: **False**.
Label counts: `{"UNLABELED": 415, "KNOWN_TP": 2, "VALIDATED_FP": 2, "DISPUTED": 2}`.

SpankChain has 126 recorded default findings, but only 14 recoverable individual warnings across its detector-scoped pilot and existing independent-validation JSON. The latter was copied unchanged from the existing local temporary evidence to finding_inventory_inputs/ for durable provenance. The full run is not rerun. Missing SpankChain rows cannot receive labels or be included in individual counts.

## By case

| Case | Recovered findings | Labels |
|---|---:|---|
| spankchain | 14 | {"UNLABELED": 9, "KNOWN_TP": 1, "VALIDATED_FP": 2, "DISPUTED": 2} |
| xsurge | 21 | {"KNOWN_TP": 1, "UNLABELED": 20} |
| burgerswap | 96 | {"UNLABELED": 96} |
| visor-finance | 41 | {"UNLABELED": 41} |
| eleven | 58 | {"UNLABELED": 58} |
| bearn | 115 | {"UNLABELED": 115} |
| spartan | 76 | {"UNLABELED": 76} |

## By detector

| Detector | Findings | Labels |
|---|---:|---|
| arbitrary-send-erc20 | 1 | {"UNLABELED": 1} |
| arbitrary-send-eth | 2 | {"DISPUTED": 1, "UNLABELED": 1} |
| assembly | 11 | {"UNLABELED": 11} |
| calls-loop | 58 | {"UNLABELED": 58} |
| constable-states | 6 | {"UNLABELED": 6} |
| constant-function-asm | 3 | {"UNLABELED": 2, "DISPUTED": 1} |
| dead-code | 7 | {"UNLABELED": 7} |
| divide-before-multiply | 5 | {"UNLABELED": 5} |
| events-access | 3 | {"UNLABELED": 3} |
| events-maths | 7 | {"UNLABELED": 7} |
| external-function | 2 | {"UNLABELED": 2} |
| immutable-states | 9 | {"UNLABELED": 9} |
| incorrect-equality | 10 | {"UNLABELED": 8, "VALIDATED_FP": 2} |
| locked-ether | 1 | {"UNLABELED": 1} |
| low-level-calls | 20 | {"UNLABELED": 20} |
| missing-inheritance | 1 | {"UNLABELED": 1} |
| missing-zero-check | 16 | {"UNLABELED": 16} |
| naming-convention | 129 | {"UNLABELED": 129} |
| pragma | 2 | {"UNLABELED": 2} |
| redundant-statements | 5 | {"UNLABELED": 5} |
| reentrancy-benign | 10 | {"UNLABELED": 10} |
| reentrancy-eth | 5 | {"UNLABELED": 3, "KNOWN_TP": 2} |
| reentrancy-events | 20 | {"UNLABELED": 20} |
| reentrancy-no-eth | 11 | {"UNLABELED": 11} |
| return-bomb | 1 | {"UNLABELED": 1} |
| shadowing-local | 10 | {"UNLABELED": 10} |
| solc-version | 15 | {"UNLABELED": 15} |
| timestamp | 3 | {"UNLABELED": 3} |
| unchecked-lowlevel | 2 | {"UNLABELED": 2} |
| unchecked-transfer | 17 | {"UNLABELED": 17} |
| unindexed-event-address | 9 | {"UNLABELED": 9} |
| unused-return | 20 | {"UNLABELED": 20} |

## Cohort readiness

Only **2 independently validated FPs** and **2 exact known TPs** are available. The approximate 10-FP and 5–10-TP target is not met. The two disputed SpankChain findings remain excluded. No final LLM cohort or verification targets are created. The validated SpankChain equality labels retain their narrow warning-level limitations; actual LLM rejections are not independent labels.

## Best 20 candidates

| Rank | Case | Detector | Target | Finding ID |
|---:|---|---|---|---|
| 1 | spartan | unchecked-transfer | Pool.swapTo(address,address) | e0b32bd732a1c264102776aaadff912380062745caa2eef526f7ad911b9e44f5 |
| 2 | visor-finance | arbitrary-send-erc20 | RewardsHypervisor.deposit(uint256,address,address) | 5d3eca2555a2051ff6412cb4a9bffb2027fe752f63b717bf319dc6d7c96cb1cb |
| 3 | spankchain | reentrancy-eth | LedgerChannel.byzantineCloseChannel(bytes32) | a03eb32cf0cb25b5d913b9890d1e238c647156d1da44ca03a9c1c3676916782f |
| 4 | bearn | unused-return | BvaultsBank.emergencyWithdraw(uint256) | 29e22b3a9cb0d2b5102fd039174b1b903cdf962a1f80edfd60a7b520bf0d47cc |
| 5 | xsurge | incorrect-equality | SurgeToken.purchase(address,uint256) | 0d1056a6b05f35c0661820fd228845121f557c692860dd5fbbf953fb28675bea |
| 6 | eleven | divide-before-multiply | ElevenNeverSellVault.pendingNerve(address) | 259a3a4cd3d251a7b1fbfc8b02d3112f69a6958925ee805487f78233aba35d25 |
| 7 | burgerswap | unused-return | DemaxPlatform.migrateLiquidity(address,address,address,address[]) | de6520f714d63694f73f233c8dde8ce42741bcd4d921f6cc4900c6c33d68deb8 |
| 8 | spartan | arbitrary-send-eth | Router._handleTransferOut(address,uint256,address) | 3426dee9e8ef729ea3be1f7398d4d28fb04cd4158f433644d7058e127a547d3b |
| 9 | bearn | reentrancy-no-eth | BvaultsBank.migrateStrategy(uint256,address) | 705ce4acff1a3216ca1c5cc0a7d9cd1120988c4f3fd5c0bf811364ef1865435f |
| 10 | spankchain | constant-function-asm | ECTools.uintToBytes32(uint256) | f994fab55d8647cd6e028b5811ad9d9e120155326faf4eca1d48fc670807ceaa |
| 11 | eleven | unchecked-transfer | ElevenNeverSellVault.chargeFees() | 71a916f70433320f294d6256d4cb9d11f2ba1715e9c80fef76541df2d78446ac |
| 12 | xsurge | divide-before-multiply | SurgeToken.purchase(address,uint256) | c52e2859d9d1e3de2c8cd8b04fc807338298075b3928224d4acd5d73740c477f |
| 13 | burgerswap | unused-return | DemaxPlatform.swapPrecondition(address) | 40750c41d2e69ce2f681004ed403a7bd57f9b162a0d6c3b834760a79f4592478 |
| 14 | spartan | unchecked-lowlevel | Router._handleTransferIn(address,uint256,address) | b88645d859573e7cd79ccb9443b3405342bedfe577d59ac77dd91a970a3ea6aa |
| 15 | spankchain | incorrect-equality | LedgerChannel._isContained(bytes32,bytes,bytes32) | 555479cc96ea35b4affe7a8500f50e27fa63fc965a2d8947e485baa85f11f08c |
| 16 | eleven | reentrancy-no-eth | ElevenNeverSellVault.claimRewards() | b560cc3081584d2ee310e177077fe5398803858478b18a49faa0142284663824 |
| 17 | bearn | unchecked-transfer | BvaultsBank.migrateStrategy(uint256,address) | 62e7b3ba7e49dfb99841e2603e650dff6bc6782f4e9ee8c52c9d8656800f6dff |
| 18 | xsurge | divide-before-multiply | SurgeToken.sell(uint256) | 9fb62fea1ce3dc5432b21e883cbe16f925a50ca3d210c0f619a84ddbceb91869 |
| 19 | burgerswap | unused-return | DemaxPlatform.swapPrecondition(address) | 92f3e299e4e000f89bb0130a7aa47f367305bf9e4b285d6d30ef81f619a48c0c |
| 20 | spartan | locked-ether | Pool.constructor(address,address) | e8fd05569b88b694d2f90f4cb31d7238e3a16b4bfe1ab3c0143012345d08c63b |

Full analyzer descriptions, source lines, current labels and review rationale appear in finding_adjudication_candidates.md.

## Workflow

1. Recover the missing full SpankChain JSON if available; do not manufacture finding rows.
2. Independently adjudicate diverse candidates by exact finding ID; record evidence and label scope. Leave uncertainty unlabeled/disputed.
3. Freeze a finding-level cohort only after sufficient independent FP/TP labels exist. Keep labels separate from production model inputs.
4. Later compare before-LLM labeled TP/FP precision with retained TP, filtered FP, inconclusive outcomes, after-LLM precision, TP retention and FP reduction. State treatment of inconclusive outcomes explicitly. Exclude disputed/unlabeled findings from binary metrics.
5. Incident-level Slither misses remain upstream misses, not LLM failures. Supplemental cases retain their roles; this finding-level experiment never rewrites incident-level classifications.

No LLM call, verify_request invocation, source analysis, target change or incident reclassification occurred. Existing files are hash checked.

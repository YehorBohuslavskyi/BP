# Authoritative finding-level adjudications

Consolidated by (case, finding_id). Original inventory labels and historical incident classifications are preserved in their original files. VALIDATED_TP means a demonstrated code-level property, not necessarily the historical root cause. Labels from prior manual reviews remain attributed to their original evidence.

## Unique counts

| Label | Count |
|---|---:|
| KNOWN_TP | 2 |
| VALIDATED_TP | 3 |
| VALIDATED_FP | 10 |
| DISPUTED | 5 |
| UNLABELED | 401 |

Usable TP: **5**. Usable FP: **10**. Minimum **5 TP + 10 FP reached**. This count does not itself freeze a cohort, establish detector/case diversity, or trigger inference.

## New selected validations

- **A / Spartan:** original Router helper calls a rejecting local recipient after successful mock wrapped-native withdrawal. The trace shows the recipient revert; adapter execution continues, recipient balance stays 0 and Router retains 1 native unit (10^18 base units). This is helper-level code evidence, not a historical exploit or a complete public-entrypoint reachability proof.
- **B / Eleven:** original claimRewards path attempts a 50-token payment with a 100-token vault balance. Token returns false without moving balances; claim succeeds and reward debt advances 0 → 50, while claimable reward falls 50 → 0. Harvest and token dependencies are explicitly local fixtures. The successful-transfer control pays 50 and then advances debt.
- **C / SpankChain:** complete local source confirms _isContained returns bool and the line-1055 comparison with true is precisely a proof-acceptance guard. This receives manual_source_adjudication only. No new regression exercises that exact guard.

Regression command:

```bash
.venv/bin/python test/defihacklabs/finding_regressions/run.py
```

Observed: **9 passed, 0 failed, 0 skipped**, including four new A/B tests, five retained tests and 64 existing fuzz cases. Evidence and observations: `test/defihacklabs/finding_regressions/evidence/selected-adjudications.json`. Original source hashes remain unchanged. No network, live contracts, wallets, fork, attack payload or LLM is involved.

## Adjudicated findings

| Case | Detector | Function | Finding ID | Final label | Provenance |
|---|---|---|---|---|---|
| spankchain | reentrancy-eth | byzantineCloseChannel(bytes32) | a03eb32cf0cb25b5d913b9890d1e238c647156d1da44ca03a9c1c3676916782f | DISPUTED | manual_source_adjudication |
| spankchain | reentrancy-eth | LCOpenTimeout(bytes32) | da49c1a96621ac0ec579d1887de3a8ce6ffd1be3d610c7819b78645f05e0e19f | KNOWN_TP | historical_ground_truth |
| spankchain | incorrect-equality | LCOpenTimeout(bytes32) | 3f327db1af5b9c5fb9e5718c5815b582ddfe4919e36215440cc0f62b12122388 | VALIDATED_FP | manual_source_adjudication, regression_test |
| spankchain | incorrect-equality | _isContained(bytes32,bytes,bytes32) | 555479cc96ea35b4affe7a8500f50e27fa63fc965a2d8947e485baa85f11f08c | VALIDATED_FP | manual_source_adjudication, regression_test |
| spankchain | incorrect-equality | initVCstate(bytes32,bytes32,bytes,address,address,uint256[2],uint256[4],string) | 7ba937136995fd888e3da4dfece9bf0e6fd752d81e5c7530e2dd743b93615f71 | VALIDATED_FP | manual_source_adjudication |
| spankchain | incorrect-equality | consensusCloseChannel(bytes32,uint256,uint256[4],string,string) | cc4904ecb52d01e681860b4ca265fd72afbcc804e7cb2dbd7ea05169e15b57d8 | VALIDATED_FP | manual_source_adjudication, regression_test |
| spankchain | constant-function-asm | recoverSigner(bytes32,string) | 20e97a75d64e3cd6b6d815803e10fb50ecf7f4a6238c4a4957f2045f6cdb7efb | DISPUTED | manual_source_adjudication, regression_test |
| spankchain | constant-function-asm | uintToBytes32(uint256) | f994fab55d8647cd6e028b5811ad9d9e120155326faf4eca1d48fc670807ceaa | VALIDATED_FP | manual_source_adjudication |
| spankchain | arbitrary-send-eth | consensusCloseChannel(bytes32,uint256,uint256[4],string,string) | 2aea17d89905a4065d3beb5f7cbd39e1a6f5a90900fa882b9707ee9a04eb6909 | DISPUTED | manual_source_adjudication, regression_test |
| xsurge | reentrancy-eth | sell(uint256) | 283e78f92682b97003c79c283ba78a6a978eb958c5d03c0c58416f345bf2ebc5 | KNOWN_TP | historical_ground_truth |
| xsurge | incorrect-equality | purchase(address,uint256) | 0d1056a6b05f35c0661820fd228845121f557c692860dd5fbbf953fb28675bea | VALIDATED_FP | manual_source_adjudication |
| burgerswap | unused-return | swapPrecondition(address) | 40750c41d2e69ce2f681004ed403a7bd57f9b162a0d6c3b834760a79f4592478 | VALIDATED_FP | manual_source_adjudication |
| burgerswap | unused-return | swapPrecondition(address) | 92f3e299e4e000f89bb0130a7aa47f367305bf9e4b285d6d30ef81f619a48c0c | VALIDATED_FP | manual_source_adjudication |
| visor-finance | arbitrary-send-erc20 | deposit(uint256,address,address) | 5d3eca2555a2051ff6412cb4a9bffb2027fe752f63b717bf319dc6d7c96cb1cb | VALIDATED_FP | manual_source_adjudication |
| eleven | unchecked-transfer | safeTokenTransfer(address,address,uint256) | 3b17fa7df6d46dd6f38e672c759cc3862bd948b157686032c03d60efb271a8f5 | VALIDATED_TP | regression_test |
| eleven | reentrancy-no-eth | claimRewards() | b560cc3081584d2ee310e177077fe5398803858478b18a49faa0142284663824 | DISPUTED | manual_source_adjudication |
| bearn | reentrancy-no-eth | migrateStrategy(uint256,address) | 705ce4acff1a3216ca1c5cc0a7d9cd1120988c4f3fd5c0bf811364ef1865435f | DISPUTED | manual_source_adjudication |
| spartan | arbitrary-send-eth | _handleTransferOut(address,uint256,address) | 3426dee9e8ef729ea3be1f7398d4d28fb04cd4158f433644d7058e127a547d3b | VALIDATED_FP | manual_source_adjudication |
| spartan | locked-ether | constructor(address,address) | e8fd05569b88b694d2f90f4cb31d7238e3a16b4bfe1ab3c0143012345d08c63b | VALIDATED_TP | manual_source_adjudication, regression_test |
| spartan | unchecked-lowlevel | _handleTransferOut(address,uint256,address) | b9cbd4da367d63c678d1e691cd43d6293494bc6363eca3dd96a5cb6468417c3a | VALIDATED_TP | regression_test |

## Evidence and scope

### spankchain — reentrancy-eth — a03eb32cf0cb25b5d913b9890d1e238c647156d1da44ca03a9c1c3676916782f

Label: **DISPUTED**.

External transfers precede state update, so the warning cannot be dismissed, but this exact finding is not independently matched to the documented historical exploit.
Evidence: `user_supplied_manual_review_this_consolidation`.
Scope: Exact reported property only; no blanket contract/function safety assertion.
### spankchain — reentrancy-eth — da49c1a96621ac0ec579d1887de3a8ce6ffd1be3d610c7819b78645f05e0e19f

Label: **KNOWN_TP**.

Existing exact finding-level mapping to the independently documented historical vulnerability. No other findings inherit this label.
Evidence: `examples/defihacklabs/evaluation/slither_baseline.json`.
### spankchain — incorrect-equality — 3f327db1af5b9c5fb9e5718c5815b582ddfe4919e36215440cc0f62b12122388

Label: **VALIDATED_FP**.

Existing independent SpankChain adjudication B; source/test reasoning and limitations retained in the cited validation record and report.
Evidence: `test/defihacklabs/evidence/validation-record.json`.
Scope: Creator/unopened equality guards only; not timeout function safety.
### spankchain — incorrect-equality — 555479cc96ea35b4affe7a8500f50e27fa63fc965a2d8947e485baa85f11f08c

Label: **VALIDATED_FP**.

The comparison cursor == _root checks exact equality of the reconstructed Merkle hash and expected root. It is a proof/hash invariant, not a numerical balance threshold. Original inherited routine accepts matching reconstructed roots and rejects changed roots/siblings.
Evidence: `examples/defihacklabs/evaluation/final20/finding_regression_adjudications.json`.
Scope: Exact comparison only; no assertion that the full proof encoding, channel state machine, or library is secure.

The equality cursor == _root is the required final Merkle-proof predicate. Exact reconstructed-root equality is intentional.
Evidence: `user_supplied_manual_review_this_consolidation`.
Scope: Exact reported property only; no blanket contract/function safety assertion.
### spankchain — incorrect-equality — 7ba937136995fd888e3da4dfece9bf0e6fd752d81e5c7530e2dd743b93615f71

Label: **VALIDATED_FP**.

The exact flagged comparison requires acceptance of a boolean Merkle-proof predicate. For a bool x, x == true has the same truth value as x. It is not a balance, timestamp or numeric threshold equality.
Evidence: `test/defihacklabs/finding_regressions/evidence/selected-adjudications.json`.
Scope: Boolean proof-acceptance comparison only; not a full initVCstate safety label.
### spankchain — incorrect-equality — cc4904ecb52d01e681860b4ca265fd72afbcc804e7cb2dbd7ea05169e15b57d8

Label: **VALIDATED_FP**.

Existing independent SpankChain adjudication C; source/test reasoning and limitations retained in the cited validation record and report.
Evidence: `test/defihacklabs/evidence/validation-record.json`.
Scope: Comparison-level invariant only; excludes separate unchecked arithmetic and malicious token concerns.
### spankchain — constant-function-asm — 20e97a75d64e3cd6b6d815803e10fb50ecf7f4a6238c4a4957f2045f6cdb7efb

Label: **DISPUTED**.

Existing independent SpankChain adjudication D; source/test reasoning and limitations retained in the cited validation record and report.
Evidence: `test/defihacklabs/evidence/validation-record.json`.
Scope: Applicable conservative historical assembly review flag versus actual mutability defect remains disputed.
### spankchain — constant-function-asm — f994fab55d8647cd6e028b5811ad9d9e120155326faf4eca1d48fc670807ceaa

Label: **VALIDATED_FP**.

The assembly performs mstore only into newly allocated memory. It does not read or modify contract state or external environment and is compatible with the declared pure/view semantics relevant to the warning.
Evidence: `user_supplied_manual_review_this_consolidation`.
Scope: Exact reported property only; no blanket contract/function safety assertion.
### spankchain — arbitrary-send-eth — 2aea17d89905a4065d3beb5f7cbd39e1a6f5a90900fa882b9707ee9a04eb6909

Label: **DISPUTED**.

Existing independent SpankChain adjudication A; source/test reasoning and limitations retained in the cited validation record and report.
Evidence: `test/defihacklabs/evidence/validation-record.json`.
Scope: Fixed-recipient claim versus separate reopen/replay payout issue remains disputed.
### xsurge — reentrancy-eth — 283e78f92682b97003c79c283ba78a6a978eb958c5d03c0c58416f345bf2ebc5

Label: **KNOWN_TP**.

Existing exact finding-level mapping to the independently documented historical vulnerability. No other findings inherit this label.
Evidence: `examples/defihacklabs/evaluation/final20/slither_baseline.json`.
### xsurge — incorrect-equality — 0d1056a6b05f35c0661820fd228845121f557c692860dd5fbbf953fb28675bea

Label: **VALIDATED_FP**.

prevBNBAmount == 0 intentionally handles the initial-purchase special case before price calculation. The strict equality is not being used as a fragile authorization/accounting invariant.
Evidence: `user_supplied_manual_review_this_consolidation`.
Scope: Exact reported property only; no blanket contract/function safety assertion.
### burgerswap — unused-return — 40750c41d2e69ce2f681004ed403a7bd57f9b162a0d6c3b834760a79f4592478

Label: **VALIDATED_FP**.

The second component of getReserves() is intentionally discarded through tuple destructuring. The function uses the first reserve value required by the subsequent calculation. This is not a discarded success/failure signal.
Evidence: `user_supplied_manual_review_this_consolidation`.
Scope: Exact reported property only; no blanket contract/function safety assertion.
### burgerswap — unused-return — 92f3e299e4e000f89bb0130a7aa47f367305bf9e4b285d6d30ef81f619a48c0c

Label: **VALIDATED_FP**.

For this separate reserve query, only the required first returned reserve is used and the second tuple value is intentionally discarded.
Evidence: `user_supplied_manual_review_this_consolidation`.
Scope: Exact reported property only; no blanket contract/function safety assertion.
### visor-finance — arbitrary-send-erc20 — 5d3eca2555a2051ff6412cb4a9bffb2027fe752f63b717bf319dc6d7c96cb1cb

Label: **VALIDATED_FP**.

The exact Slither finding concerns the EOA safeTransferFrom(from, address(this), amount) branch. Transfer requires allowance from from; the caller cannot spend arbitrary third-party tokens without approval. The historical Visor exploit used the separate contract branch and therefore does not validate this exact warning.
Evidence: `user_supplied_manual_review_this_consolidation`.
Scope: User-supplied manual adjudication of the EOA branch; recorded as supplied, not a new test of allowance ownership or caller binding. Historical contract-branch vulnerability is distinct.
### eleven — unchecked-transfer — 3b17fa7df6d46dd6f38e672c759cc3862bd948b157686032c03d60efb271a8f5

Label: **VALIDATED_TP**.

Original claimRewards, claim, harvest, safeTokenTransfer and updateDebt execute without override. Sufficient balance 100 versus payment 50 selects exact line-1065 else branch; local token records transfer sender/recipient/amount/result. Debt advances despite no token movement.
Evidence: `test/defihacklabs/finding_regressions/evidence/selected-adjudications.json`.
Scope: Exact reported property in local fixtures; no historical incident reclassification.
### eleven — reentrancy-no-eth — b560cc3081584d2ee310e177077fe5398803858478b18a49faa0142284663824

Label: **DISPUTED**.

External calls precede reward-debt state updates and cross-function state exposure exists, but the available evidence does not independently demonstrate exploitability.
Evidence: `user_supplied_manual_review_this_consolidation`.
Scope: Exact reported property only; no blanket contract/function safety assertion.
### bearn — reentrancy-no-eth — 705ce4acff1a3216ca1c5cc0a7d9cd1120988c4f3fd5c0bf811364ef1865435f

Label: **DISPUTED**.

Multiple external calls occur before the strategy pointer update. Operator restriction alone does not prove safety, but exploitability has not been independently demonstrated.
Evidence: `user_supplied_manual_review_this_consolidation`.
Scope: Exact reported property only; no blanket contract/function safety assertion.
### spartan — arbitrary-send-eth — 3426dee9e8ef729ea3be1f7398d4d28fb04cd4158f433644d7058e127a547d3b

Label: **VALIDATED_FP**.

In the adjudicated reachable payout path, _recipient is constrained to msg.sender and the amount is the output of that caller's liquidity operation. The reported arbitrary ETH recipient is therefore an intended user payout rather than unauthorized arbitrary-value transfer.
Evidence: `user_supplied_manual_review_this_consolidation`.
Scope: Only the manually adjudicated reachable liquidity-payout path; not every hypothetical use of the internal helper.
### spartan — locked-ether — e8fd05569b88b694d2f90f4cb31d7238e3a16b4bfe1ab3c0143012345d08c63b

Label: **VALIDATED_TP**.

Pool constructor and swapTo accept native value. Complete Pool implementation (source lines 85–344) contains no native-value transfer, send, value-bearing call, selfdestruct, delegatecall, or inherited implementation that can provide an exit. Its outgoing transfers are typed ERC20 calls with zero native value. Native value accepted at deployment remains without an exit.
Evidence: `examples/defihacklabs/evaluation/final20/finding_regression_adjudications.json`.
Scope: Code-level locked-native-value finding; not the known historical Spartan exploit, not a new incident-level detection, and not evidence that this path was used in production.
### spartan — unchecked-lowlevel — b9cbd4da367d63c678d1e691cd43d6293494bc6363eca3dd96a5cb6468417c3a

Label: **VALIDATED_TP**.

Expected value-bearing call reached always-reverting RejectNative.receive (trace records LocalPaymentRejected); therefore native CALL returned false. Original helper returned and adapter continuation marker became true. Wrapped-native withdrawal counter and balances confirmed prior success.
Evidence: `test/defihacklabs/finding_regressions/evidence/selected-adjudications.json`.
Scope: Exact reported property in local fixtures; no historical incident reclassification.

## Preservation and limitations

Historical reentrancy mappings remain KNOWN_TP. Spartan locked-ether remains VALIDATED_TP, not the historical Spartan exploit. Its original regression record is preserved. Merkle-root equality is counted once with both prior manual and regression evidence. Previously disputed findings remain disputed.

The authoritative inventory covers 421 case/finding observations, with 417 distinct Slither IDs because of shared dependency warnings. SpankChain full-run evidence remains incomplete. No rows or labels are inferred for unavailable findings. Unlabeled/disputed rows remain excluded from binary metrics.

Prior manually supplied Visor and Spartan payout rationales remain attributed and scoped; this update does not re-test those decisions. Case-level/provisional-cohort separation remains unchanged. No targets, LLM results, raw source or incident-level baseline records were edited.

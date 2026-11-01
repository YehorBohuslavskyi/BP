# Independent validation of SpankChain LLM rejections

Validation date: 2026-11-01. These labels come from manual source/detector
inspection and local EVM execution, not the model's verdict. The four model
verdicts/reasons and the earlier `LCOpenTimeout` CONFIRMED result are supplied by
the user; this work neither reruns inference nor edits those exported results.

## Findings and ground-truth policy

| Finding | Detector | Function | LLM verdict | Independent label | Evidence / thesis use |
| --- | --- | --- | --- | --- | --- |
| A | `arbitrary-send-eth` | `LedgerChannel.consensusCloseChannel(bytes32,uint256,uint256[4],string,string)` | `false_positive` | **DISPUTED** | Recipient substitution fails, but reopening and replaying signatures drains another channel. Do not count as an unqualified FP or as proof of arbitrary-recipient theft. |
| B | `incorrect-equality` | `LedgerChannel.LCOpenTimeout(bytes32)` | `false_positive` | **VALIDATED_FP** | Creator/unopened checks behave as authorization/state guards. Suitable as narrowly scoped, manually validated warning-level ground truth. |
| C | `incorrect-equality` | `LedgerChannel.consensusCloseChannel(bytes32,uint256,uint256[4],string,string)` | `false_positive` | **VALIDATED_FP** | The token equality is an appropriate recorded-balance invariant, not the detector's attacker-perturbable live-balance threshold. Suitable only for this exact comparison; not a claim of universal arithmetic/token safety. |
| D | `constant-function-asm` | `ECTools.recoverSigner(bytes32,string)` | `false_positive` | **DISPUTED** | Correct conservative detector trigger; actual helper shows no mutability violation. The model's view-versus-pure rejection is invalid. Exclude from unqualified binary FP ground truth. |

`VALIDATED_FP` applies to the exact reported warning under the documented scope,
not to the safety of the whole function or contract. `DISPUTED` records a material
mismatch between a broad safety assertion, the detector's actual claim, and the
available evidence. A different bug in the same function is not automatically a
true positive for the selected detector. No precision, recall, or FP-reduction
percentage is calculated here.

## Reproducible execution and compatibility

New suite: [`../../test/defihacklabs/SpankChainValidation.t.sol`](../../test/defihacklabs/SpankChainValidation.t.sol).
Run from the repository root:

```bash
.venv/bin/python test/defihacklabs/run_validation.py
```

The runner invokes installed native solc 0.4.25 with standard JSON, then:

```bash
forge test --root test/defihacklabs \
  --use "$PWD/.venv/.solc-select/artifacts/solc-0.8.24/solc-0.8.24" \
  --offline -vv
```

Run the Python command first: it creates the required bytecode artifacts in
`test/defihacklabs/.generated/`. To inspect the counterexample trace:

```bash
.venv/bin/python test/defihacklabs/run_validation.py \
  --match-test test_A_reopenAndReplayOldSignaturesDrainsOtherChannel -vvvv
```

To reproduce the detector claims separately, without overwriting saved evidence:

```bash
SOLC_VERSION=0.4.25 .venv/bin/slither examples/defihacklabs/SpankChain.sol \
  --detect arbitrary-send-eth,incorrect-equality,constant-function-asm \
  --json - --fail-none > /tmp/spankchain-fp-validation-slither.json
```

Local versions: Foundry 1.8.3 (`cae51ad458f6abb64852b7709eb784352429825d`),
Slither 0.11.6, solc 0.4.25 for the victim and solc 0.8.24 for tests. Both compilers
and Foundry use the Byzantium EVM target. Victim compilation enables the optimizer
with 200 runs, producing 16,874 bytes of creation code and permitting deployment
under the normal EVM code-size limit. The modern test harness uses the default
disabled optimizer. No fork/RPC, downloads,
forge-std dependency, deployment to a network, or model/API call is required.

Compatibility measures, exhaustively:

1. The exact original file is passed as source content to solc 0.4.25. No source
   rewrite, pragma change, arithmetic upgrade, or added guard is performed.
   Optimization is an explicit compiler setting, not a source compatibility edit;
   the historical deployment's exact compiler settings are not claimed to match.
2. `ECTools` is deployed with its original creation bytecode. The runner records
   solc's 20-byte library link offsets; the test inserts the deployed library
   address at those offsets before deploying `LedgerChannel`. This is ordinary
   library linking, not instruction modification.
3. Solidity 0.8.24 test interfaces supply ABI calls to the original 0.4.25 bytecode.
   Original `HumanStandardToken` bytecode is used for normal token tests.
4. A separate `PermissiveToken` fixture tests untrusted token behavior. It is used
   only by the explicit overflow-boundary test, never as the ordinary token.
5. A separate old-compiler `HistoricalMutabilityControl.sol.txt` fixture tests
   an intentionally mislabeled view function with `sstore`. The `.txt` suffix
   keeps Foundry from recompiling it as modern source; the runner compiles it
   with 0.4.25. It is not part of the victim.
6. Foundry cheatcodes supply identities, valid cryptographic signatures, initial
   EOA funds and time. No victim storage or balance is forged. Deposits and
   replay payouts go through real contract calls. A test-only guard truth table
   does not replace or mutate executable victim logic.

The runner checks the original source SHA-256 before and after execution:
`501119bb522ddd4fe4fd7b08f4f9591d2197991b53aba06f9bb50ac4362f56a0`.
The previous [source provenance and incident record](SpankChain_ground_truth.md)
remains unchanged, including its archived-source/deployed-bytecode limitations.

Observed output:

```text
Ran 29 tests for SpankChainValidation.t.sol:SpankChainValidation
Suite result: ok. 29 passed; 0 failed; 0 skipped
29 tests passed, 0 failed, 0 skipped (29 total tests)
```

Two of those tests each execute 64 seeded fuzz cases (`seed = 0x1234`). Complete
output: [`forge-output.txt`](../../test/defihacklabs/evidence/forge-output.txt).
Versions, hashes, exact Slither claims/IDs, and independent labels:
[`validation-record.json`](../../test/defihacklabs/evidence/validation-record.json).
A PASS in the replay/overflow tests means the counterexample was reproduced;
it does not mean the contract was safe.

## A — arbitrary ETH sends in consensusCloseChannel

**Slither claim:** the function sends ETH to an arbitrary user; it lists the two
`partyAddresses[0/1].transfer(_balances[0/1])` calls at lines 872–873.
**LLM verdict:** false_positive, based on fixed participants and two signatures.

**Manual analysis:** no recipient argument exists in this ABI. The recipients
are the recorded participants. The signed hash includes channel ID, close flag,
sequence, both participants, and all four payout amounts. Both recovered signers
must match. Consequently, being the transaction sender does not grant payout
rights, and changing the signed participant/balance data invalidates authorization.

However, successful close only sets `isOpen=false`; it does not delete the channel
or invalidate its signatures. `joinChannel` accepts any not-open channel from
party I, including a previously closed channel, and permits zero deposits. The
sequence comparison in `consensusCloseChannel` is commented out, and close does
not store a consumed sequence. This creates a replay path.

**Dynamic tests/results:** all eight `test_A_*` cases passed:

- A third-party relayer using valid signatures pays only recorded A/I, not itself.
- Empty signatures fail; replacing I's signature with an attacker's fails.
- Signing a substituted recipient fails, even when the real participants sign
  that substituted message. Recreating the existing channel cannot replace them.
- Changing the payout split while preserving its sum invalidates old signatures.
- Immediate replay without reopening fails, isolating the state check.
- **Counterexample:** deposit 1 ETH from A and I; another depositor funds a separate
  2 ETH channel. Close the original channel with valid signatures. I then rejoins
  with `[0,0]` and reuses exactly the same signatures, sequence and balances.
  Another 1 ETH is paid to each A/I, exhausting the other channel's 2 ETH.
  Its depositor's subsequent timeout refund reverts. Real token liquidity is
  explicitly donated to satisfy the test channel's second token payout;
  the ETH loss uses the other depositor's actual deposit, not `vm.deal` on the victim.

**Independent label: DISPUTED.** Narrow arbitrary-recipient substitution is not
demonstrated. But the question also asks whether an unauthorized payout is
possible, and reusable authorization permits repeated settlement without new
consent. Calling this function generally safe because it checks two signatures
would be false. Conversely, calling Slither's arbitrary-recipient warning a
validated TP solely because of a separate replay mechanism would conflate bugs.

**Limitations / thesis use:** this counterexample requires a malicious recorded
party I and signatures from a previous valid close (publicly revealed at close).
It is a local replay finding, not a claim that this was the historical SpankChain
attack. Exclude A from clean binary FP/TP statistics; use it to demonstrate why
independent validation and explicit warning scope matter.

## B — equality guards in LCOpenTimeout

**Slither claim:** line 694 is a dangerous strict equality:
`msg.sender == Channels[_lcID].partyAddresses[0] && Channels[_lcID].isOpen == false`.
**LLM verdict:** false_positive, intentional authorization and state guards.

**Manual analysis:** address identity requires exact equality. The boolean test
means the channel has not been joined. These are not equality thresholds over
an account balance or timestamp; the subsequent timeout test uses `now > deadline`.
Slither 0.11.6's detector actually excludes direct address-only comparisons, but
reports the compound node containing the state-boolean comparison. Its source
uses dependency taints from timestamps and balances; the source comments also
acknowledge field-sensitivity limitations. The exact taint path is not itself
proven by these EVM tests and is not required for the predicate-level conclusion.

**Dynamic tests/results:** all six `test_B_*` cases passed. The creator of an
unopened channel can refund after expiry. Non-creator, party I, creator after
join, and creator before expiry all revert. Tests use the original deployed
code. An additional predicate truth table shows that replacing conjunction with
OR would admit both non-creators of unopened channels and creators of joined
channels. Using `!isOpen` instead of `isOpen == false` is equivalent, not weaker.

**Independent label: VALIDATED_FP**, for this equality warning. It correctly
implements the stated authorization/state checks.

**Limitations / thesis use:** six cases plus source reasoning are not an exhaustive
proof. The real token-callback reentrancy in this same function remains a separate
true vulnerability. Successful guard tests do not establish that timeouts are
safe overall, nor cure the closed-versus-never-joined lifecycle issue. Safe as
warning-level FP ground truth with this scope; never as a function-safety label.

## C — payout-sum equality in consensusCloseChannel

**Slither claim:** line 833 is a dangerous strict equality:
`totalTokenDeposit == _balances[2] + _balances[3]`.
**LLM verdict:** false_positive, conservation of balance.

**Manual analysis:** the left side is the recorded initial token deposit plus
recorded additional deposits, not the token's externally perturbable live balance.
The requested split must account for that total exactly. Permitting a smaller
sum would leave part of the channel's accounted entitlement unpaid; permitting
a larger sum could spend shared liquidity. The ETH check at line 831 has the
same purpose. Exact comparison is appropriate. Nevertheless the old compiler's
addition is modulo 2**256: equality alone is not a full mathematical conservation
proof, and successful token calls do not establish that an untrusted token
really delivered the claimed amounts.

**Dynamic tests/results:** all nine C tests passed (one has 64 fuzz cases):

- With valid signatures, an exact split pays both participants and empties the
  channel's corresponding ETH/token deposits.
- Token sum below/above the recorded total each reverts. The same ETH cases
  revert. Signatures are valid for the mismatched values, isolating the invariant.
- Conserving token splits pass across seeded inputs.
- Extra real token transfers and ETH belonging to a different channel do not
  block an otherwise valid close; these external balances are not the threshold.
- `[MAX_UINT256, 201]` has a mathematical sum of `2**256 + 200` but a wrapped sum
  of 200. This passes the equality with a permissive token returning true.
  No real token theft or creation is established by that fixture.
- The same wrapped token amounts with the original ordinary token revert and
  roll back the prior ETH transfers, leaving both assets unchanged.

**Independent label: VALIDATED_FP for the strict-equality warning.** Neither
arithmetic wrapping nor a lying token makes exact equality the wrong comparison;
these are separate unchecked-arithmetic/token-trust concerns. Do not generalize
the LLM explanation to “this check guarantees conservation for every uint256
input and every token.” The boundary test explicitly refutes that statement.

**Limitations / thesis use:** safe only as comparison-level FP ground truth with
recorded accounting, ordinary-token behavior and non-overflowing sums stated.
Not evidence that `consensusCloseChannel` is financially safe, nor evidence that
all sums greater than the total revert for every adversarial token. If the thesis
uses function-level exploitability instead of detector-claim labels, C must be
re-adjudicated rather than silently importing this narrower FP label.

## D — pure declaration and inline assembly in recoverSigner

**Slither claim:** line 87–134 `ECTools.recoverSigner(bytes32,string)` “is declared
view but contains assembly code.” **LLM verdict:** false_positive because the
source says `pure` rather than `view`.

**Exact declaration:** `function recoverSigner(bytes32 _hashedMsg, string _sig)
public pure returns (address)`.

**Detector behavior:** installed Slither 0.11.6's
`slither/detectors/attributes/const_functions_asm.py` explicitly tests
`f.view or f.pure`, then `f.contains_assembly`, and is restricted to Solidity
0.4.x. Its documentation covers constant, pure, and view. The parser in
`slither/solc_parsing/declarations/function.py::_analyze_attributes` sets **both**
`pure=True` and `view=True` for a pure declaration. The detector chooses the word
`view` whenever `f.view` is true. Inspection of the parsed actual function
confirmed `view=True`, `pure=True`, `contains_assembly=True`. Thus the wording is
explained by the implementation; it does not invalidate the finding.

**Manual code analysis:** this assembly uses `mload`, `add`, and `byte` to decode
r/s/v from memory. The called hex-decoding helpers operate on memory as well
(including `mstore` in `uintToBytes32`). Hashing and the `ecrecover` precompile do
not write storage. There is no storage write, event emission, value transfer,
selfdestruct, or external user-selected call in this helper. Reverts for bad
input are different from reverts caused by violating static-call restrictions.

Historical mutability annotations did not always impose EVM-level write
protection. Solidity 0.4.25's documentation warns about view enforcement and
explains that pure behavior cannot be fully enforced at the EVM level. Slither's
warning is meaningful as a request to review old annotated assembly, not proof
that every such function modifies state. See the
[0.4.25 language documentation](https://docs.soliditylang.org/en/v0.4.25/contracts.html#view-functions)
and [detector documentation](https://github.com/crytic/slither/wiki/Detector-Documentation#constant-functions-using-assembly-code).

**Dynamic tests/results:** all six D tests passed (one has 64 fuzz cases):

- Original library bytecode returns the expected signer under both CALL and
  STATICCALL. Recorded library storage reads and writes are both empty.
- Short signatures and an invalid v return zero under STATICCALL.
- A zero hash reverts as expected from explicit input validation.
- Seeded messages remain compatible with STATICCALL and recover the signer.
- **Positive control:** a separately compiled 0.4.25 view function containing
  `sstore` emits a compiler warning, writes storage under CALL, and fails under
  STATICCALL. This shows the harness can detect the historical hazard.

**Independent label: DISPUTED.** This is a valid conservative detector trigger,
but no mutability exploit is established in the inspected helper. Under a
strict “actual state mutation” vulnerability definition, the local analysis
supports harmless assembly; under Slither's review-rule definition, the alert
is applicable. These are different label semantics. The LLM's supplied reason
is invalid regardless: a pure/view wording difference is not an exclusion.

**Limitations / thesis use:** storage traces and finite signatures do not prove
all behavior for all inputs; the manual call-chain review supplies additional
evidence. This is not a complete signature-scheme audit. Exclude D from clean
binary FP reduction claims unless the thesis first specifies which detector
semantics it scores and obtains a separate adjudication under that definition.

## Overall research conclusion

B and narrowly scoped C have independent support as false positives of the
specific equality detector. A and D are not clean examples of model FP removal.
A exposes an omitted authorization-lifecycle problem; D exposes a faulty
wording-based rejection. Preserve these distinctions and the passing
counterexample tests in any thesis discussion. Do not infer labels for any
other Slither warnings from these results.

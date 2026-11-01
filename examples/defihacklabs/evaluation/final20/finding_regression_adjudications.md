# Additional independent finding adjudications

Two exact finding IDs have new source/test-backed adjudications. This separate
overlay leaves every existing inventory/packet label, incident-level baseline,
target and LLM result unchanged. No model verdict was used.

| Case | Finding | New independent label | Scope |
|---|---|---|---|
| SpankChain | `incorrect-equality` / `555479cc96ea35b4affe7a8500f50e27fa63fc965a2d8947e485baa85f11f08c` | VALIDATED_FP | Exact reconstructed Merkle hash equals expected root |
| Spartan | `locked-ether` / `e8fd05569b88b694d2f90f4cb31d7238e3a16b4bfe1ab3c0143012345d08c63b` | KNOWN_TP | Native value accepted by Pool has no native-value exit in the implementation |

## FP evidence

`LedgerChannel._isContained(bytes32,bytes,bytes32)` reconstructs a sorted Merkle
hash, then compares it with `_root`. Exact hash equality is required for this
proof predicate. It does not compare an externally perturbable numerical balance.
Tests execute the original inherited 0.4.25 routine through a minimal test-only
public adapter. Empty and single-sibling proofs succeed for their reconstructed
root; altered roots/siblings fail. The seeded fuzz test checks 64 leaf/sibling
pairs. This validates only the flagged equality, not every property of the proof
format or channel implementation.

## TP evidence

The complete `Pool` implementation, lines 85–344 of Spartan's `Victim.sol`,
was reviewed separately from the following `Router` contract. Pool inherits only
an interface and uses internal arithmetic routines. Its payable constructor
and `swapTo` accept native value. Outgoing asset operations are typed ERC20
transfers; Pool has no native-value transfer/send/value-bearing call,
selfdestruct or delegation exit. Router's native-transfer helpers do not provide
an exit for Pool's balance because they execute in a separate contract context.

A deterministic test deploys unchanged compiled Pool code with native value and
a constructor dependency providing only token metadata. The balance remains;
ordinary getters work, while conventional withdrawal/rescue selectors and the
fallback fail. These selector tests alone do not prove the absence of every exit:
that conclusion also depends on reviewing the entire Pool implementation. No
victim storage or native-value behavior is replaced. The fixture supplies only
constructor name/symbol responses.

This TP concerns a valid code-level locked-value warning, not the historical
Spartan liquidity-share exploit. Do not convert the incident-level MISSED record
to DETECTED. No historical loss or use of this native-value path is claimed.

## Reproduction

```bash
.venv/bin/python test/defihacklabs/finding_regressions/run.py
```

Observed: **5 passed, 0 failed, 0 skipped**, including 64 seeded fuzz cases.
Original LedgerChannel uses solc 0.4.25; original Spartan source uses solc 0.6.8;
the test harness uses solc 0.8.24. Original-source optimizer settings for these
regressions are enabled, 200 runs. Sources are compiled unchanged via standard
JSON; the adapter is a separate source unit. Original ECTools is deployed and
linked normally using compiler-reported offsets. Source hashes are checked
before and after execution. No fork, public chain, exploit replay or LLM is used.
Detailed output: `test/defihacklabs/finding_regressions/evidence/forge-output.txt`.

## Label availability and limits

Only two validated FPs and two known TPs were present in the local inventory.
This overlay adds one of each, yielding **3 FP and 3 TP labels backed by the
available local records** if this overlay is adopted. If seven further independent
FP adjudications exist elsewhere, they must be supplied with finding IDs and
evidence before they can be counted; the approximate user-reported nine were not
silently treated as local ground truth.

Only one additional TP was promoted. Other unchecked-transfer/callback candidates
need stronger deployed-dependency or independently justified reachability evidence;
mocking an arbitrary token failure alone is not used to declare them deployment-
level TPs. No FP-reduction/precision metrics or new LLM cohort are created.

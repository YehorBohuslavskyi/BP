# SpankChain: one real-world selective-context verification demo

This is a single known-incident demonstration, not a DeFiHackLabs benchmark.
The analyzed Solidity is the victim's archived payment-channel source, **not**
DeFiHackLabs' exploit PoC. No live LLM verification was run during preparation.

## 1. Known incident ground truth

| Field | Record |
| --- | --- |
| Incident | SpankChain payment-channel reentrancy |
| DeFiHackLabs PoC | [`src/test/2018-10/SpankChain_exp.sol`](https://github.com/SunWeb3Sec/DeFiHackLabs/blob/main/src/test/2018-10/SpankChain_exp.sol) — documentation only, not the analyzed source |
| Vulnerable protocol | SpankChain |
| Vulnerable contract | `LedgerChannel`, payment-channel contract |
| Chain | Ethereum mainnet |
| Vulnerable contract address | `0xf91546835f756DA0c10cFa0CDA95b15577b84aA7` |
| Attack transaction | [`0x21e9d20b57f6ae60dac23466c8395d47f42dc24628e5a31f224567a2b4effa88`](https://etherscan.io/tx/0x21e9d20b57f6ae60dac23466c8395d47f42dc24628e5a31f224567a2b4effa88), as referenced by the PoC |
| Date | 2018-10-07, the DeFiHackLabs incident date; the protocol report describes Saturday evening in its US-local timezone |
| Known root cause | An attacker-selected token's `transfer` executes before the channel is deleted; its callback can re-enter the timeout refund using the still-existing balance |
| Affected function | `LedgerChannel.LCOpenTimeout(bytes32)` |
| Expected vulnerability class | Reentrancy allowing repeated ETH refunds through a malicious ERC20 callback |
| Expected Slither detector | `reentrancy-eth` |
| Expected prototype verdict | **CONFIRMED**, a ground-truth expectation, not an observed LLM result |
| Evidence/source | DeFiHackLabs PoC, protocol incident report, and archived victim source linked below |

The protocol's [incident report](https://medium.com/spankchain/we-got-spanked-what-we-know-so-far-d5ed3a0f38fe)
identifies the same victim address and explains the token callback and delayed
deletion. Its [technical follow-up](https://medium.com/connext/transparency-report-64c9e58e0a19)
also discusses this attack. The
[DeFiHackLabs incident index](https://github.com/SunWeb3Sec/DeFiHackLabs/blob/main/past/2021/README.md#20181007-spankchain---reentrancy)
provides the dataset linkage.

This is suitable for static analysis because the external call and later state
deletion are visible in one function. `createChannel` shows that the caller can
choose the token address. The PoC's simulated funding does not make the root
cause an oracle, price-manipulation, or flash-loan-only vulnerability.

## 2. Actual source and preparation

- Original victim explorer reference:
  [Etherscan contract source](https://etherscan.io/address/0xf91546835f756da0c10cfa0cda95b15577b84aa7#code).
- Retrieved source:
  [Trail of Bits / crytic's archived `SpankChain_Payment.sol`](https://github.com/crytic/not-so-smart-contracts/blob/master/reentrancy/SpankChain_source_code/SpankChain_Payment.sol).
  Its first line explicitly identifies the same victim address. The archive's
  [reentrancy documentation](https://github.com/crytic/not-so-smart-contracts/blob/master/reentrancy/README.md)
  links the SpankChain incident report.
- Local file: [`SpankChain.sol`](SpankChain.sol).
- Source SHA-256:
  `501119bb522ddd4fe4fd7b08f4f9591d2197991b53aba06f9bb50ac4362f56a0`.
- License: upstream Apache 2.0 notice retained; full license in
  [`LICENSE-SpankChain.txt`](LICENSE-SpankChain.txt).

The upstream source was already flattened. This copy retains all five original
units: `Token`, `ECTools`, `StandardToken`, `HumanStandardToken`, and
`LedgerChannel`. No imports, interface stubs, replacement implementations, or
new Solidity dependencies were added. No function, check, storage declaration,
or call ordering was removed or rewritten. Keeping the existing flattened
bundle avoids changing the meaning of the original contract.

Retrieval used GitHub's rendered source view because shell network/DNS access
was unavailable and Etherscan returned HTTP 403. Indentation and blank-line
formatting were normalized by that view; the file was renamed and a trailing
copy/provenance comment was added. Thus the local checksum pins **this prepared
copy**, not the original upstream byte sequence. Solidity statements and the
vulnerable logic were retained. This is an archived-source reproduction, **not
a fresh source-to-deployed-bytecode verification**. No immutable upstream commit
hash was recovered; the exact retrieval path and local checksum are provided.

## 3. Observed compilation and Slither output

Tested compiler: **0.4.25+commit.59dbf8f1.Linux.g++**.
The retained source pragma is `^0.4.23`. Use the tested 0.4.25 compiler for the
demo; the deployment's original exact compiler/optimizer settings were not
independently established. Slither version used: **0.11.6**.

Run from the repository root:

```bash
SOLC_VERSION=0.4.25 .venv/bin/solc --bin --abi examples/defihacklabs/SpankChain.sol > /tmp/spankchain-compiled.txt

SOLC_VERSION=0.4.25 .venv/bin/slither examples/defihacklabs/SpankChain.sol --detect reentrancy-eth --json - --fail-none > /tmp/spankchain-reentrancy.json
```

Compilation passed. `--fail-none` lets Slither return success when it finds
warnings; it does not suppress those warnings. The targeted command reports
**two** `reentrancy-eth` candidates. Select only:

| Slither field | Observed result |
| --- | --- |
| Detector | `reentrancy-eth` |
| Contract / function | `LedgerChannel.LCOpenTimeout(bytes32)` |
| Impact / confidence | High / Medium |
| Target range | Local source lines 692–715 |
| ETH transfer | Line 699 |
| External token call | Line 705 |
| State deletion after external call | `delete Channels[_lcID]`, line 713 |

The ETH `.transfer` is not the callback entry: the later **token** `transfer`
executes attacker-controlled code while the channel balance remains recorded.
The creator check does not exclude an attacker who created their own channel.

Saved raw detector-scoped evidence:
[`SpankChain_slither.json`](SpankChain_slither.json).
A separate full-default-detector run, matching the GUI's analysis scope,
produced **126 warnings**. Per-detector counts are in
[`SpankChain_preflight.json`](SpankChain_preflight.json). Other warnings,
including the second `reentrancy-eth` candidate, are **not assessed here**;
none is automatically labeled false positive.

To reproduce the full GUI-equivalent detector scope:

```bash
SOLC_VERSION=0.4.25 .venv/bin/slither examples/defihacklabs/SpankChain.sol --json - --fail-none > /tmp/spankchain-all-findings.json
```

## 4. Prototype status — separate from ground truth

**Actual LLM verifier status: NOT RUN. Actual verdict: null. API calls: 0.**

Local checks passed for compilation, finding parsing, exact target resolution,
GUI upload/static-analysis eligibility, and initial selective-context payload
construction. The upload check used the worker's normal upload-directory cwd.
The preflight artifact records the actual payload and these checks, not a
fabricated inference transcript.

The initial source is just `LCOpenTimeout(bytes32)` (706 characters versus
29,787 characters in the full file). Eight context fragments are requestable,
including the `Channels` mapping declaration and direct writers such as
`createChannel`. Dependency source is not automatically included initially.
These are source character counts, not measured API tokens or final context
savings. The existing catalog does not separately supply the `Channel` struct
as an independent fragment; relevant field usage is visible in the target and
writer functions. No verifier changes were made to accommodate this case.

A model can still return `inconclusive` or disagree. Record the actual outcome
and explanation honestly; do not replace it with the expected label or repeat
runs until a favorable response appears. No historical fork exploit replay
or transaction trace verification was performed during this preparation.

## 5. Exact GUI demonstration steps

1. Launch from the repository root:

   ```bash
   .venv/bin/streamlit run streamlit_app.py
   ```

2. Open **Analyze Contract**, choose **Contract source → Upload**, and upload
   `examples/defihacklabs/SpankChain.sol`. This example is not added to the GUI's
   built-in Demo registry. Do not upload `SpankChain_exp.sol`.
3. Select **Installed compatible compiler → 0.4.25**, then **Run Slither**.
   This is local static analysis and does not call OpenAI.
4. Open **Inspect a finding · source, evidence, and optional single verification**.
   In **Finding to inspect**, select **reentrancy-eth · LCOpenTimeout(bytes32)**.
   Confirm `LedgerChannel`, High impact, and the token-call/state-deletion claim.
5. Ensure the server has your existing `OPENAI_API_KEY` configuration and select
   your intended **OpenAI model**. Start with **Maximum verification rounds = 4**;
   record the chosen model and round budget with the demonstration.
6. Click **Verify selected finding** exactly once. This step makes paid API calls
   for that one candidate. Do not click **Verify all eligible findings**.
7. Show the actual verdict and explanation, then **Evidence and requested
   context** and **Context efficiency**. Compare the result with the independently
   documented expected **CONFIRMED** label. Explain that requests are selective
   and need not include every available fragment.
8. Use **Export full analysis** to save the demo result separately from existing
   research results. Preserve pending/unreviewed statuses for all other findings.

The scope is one historical real-world case. It does not establish precision,
recall, or generalization across DeFiHackLabs. Existing SmartBugs, CGT,
scalability artifacts, detector mappings, GUI, and verifier code are untouched.

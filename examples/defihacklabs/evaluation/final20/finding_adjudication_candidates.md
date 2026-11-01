# Manual adjudication candidates

These are 20 unlabeled findings selected for review, not a final LLM cohort. Ranking rotates cases and detector classes, then favors High impact and compact reported line spans. Available source is checked; dependency completeness and testability must be confirmed by a human. A short reported span is not proof of small semantic scope. No inferred FP/TP labels.

## 1. spartan — unchecked-transfer

- Finding ID: `e0b32bd732a1c264102776aaadff912380062745caa2eef526f7ad911b9e44f5`
- Target: `Pool.swapTo(address,address)`
- Impact/confidence: High / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`
- Reported source lines: [265]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
Pool.swapTo(address,address) (Victim.sol#252-267) ignores return value by iBEP20(token).transfer(member,outputAmount) (Victim.sol#265)
```

## 2. visor-finance — arbitrary-send-erc20

- Finding ID: `5d3eca2555a2051ff6412cb4a9bffb2027fe752f63b717bf319dc6d7c96cb1cb`
- Target: `RewardsHypervisor.deposit(uint256,address,address)`
- Impact/confidence: High / High
- Source: `examples/defihacklabs/evaluation/final20/contracts/visor-finance/analysis/RewardsHypervisor.sol`
- Reported source lines: [61]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
RewardsHypervisor.deposit(uint256,address,address) (RewardsHypervisor.sol#41-65) uses arbitrary from in transferFrom: visr.safeTransferFrom(from,address(this),visrDeposit) (RewardsHypervisor.sol#61)
```

## 3. spankchain — reentrancy-eth

- Finding ID: `a03eb32cf0cb25b5d913b9890d1e238c647156d1da44ca03a9c1c3676916782f`
- Target: `LedgerChannel.byzantineCloseChannel(bytes32)`
- Impact/confidence: High / Medium
- Source: `examples/defihacklabs/SpankChain.sol`
- Reported source lines: [1306, 1307, 1313, 1314, 1315, 1316, 1317, 1318, 1319, 1321, 1322, 1323, 1324, 1325, 1326, 1327, 1331]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
Reentrancy in LedgerChannel.byzantineCloseChannel(bytes32) (examples/defihacklabs/SpankChain.sol#1241-1337):
	External calls:
	- require(bool,string)(channel.token.transfer(channel.partyAddresses[0],tokenbalanceA),byzantineCloseChannel: token transfer failure) (examples/defihacklabs/SpankChain.sol#1313-1319)
	- require(bool,string)(channel.token.transfer(channel.partyAddresses[1],tokenbalanceI),byzantineCloseChannel: token transfer failure) (examples/defihacklabs/SpankChain.sol#1321-1327)
	External calls sending eth:
	- channel.partyAddresses[0].transfer(ethbalanceA) (examples/defihacklabs/SpankChain.sol#1306)
	- channel.partyAddresses[1].transfer(ethbalanceI) (examples/defihacklabs/SpankChain.sol#1307)
	State variables written after the call(s):
	- channel.isOpen = false (examples/defihacklabs/SpankChain.sol#1331)
	LedgerChannel.Channels (examples/defihacklabs/SpankChain.sol#622) can be used in cross function reentrancies:
	- LedgerChannel.Channels (examples/defihacklabs/SpankChain.sol#622)
	- LedgerChannel.LCOpenTimeout(bytes32) (examples/defihacklabs/SpankChain.sol#692-715)
	- LedgerChannel.byzantineCloseChannel(bytes32) (examples/defihacklabs/SpankChain.sol#1241-1337)
	- LedgerChannel.closeVirtualChannel(bytes32,bytes32) (examples/defihacklabs/SpankChain.sol#1192-1237)
	- LedgerChannel.consensusCloseChannel(bytes32,uint256,uint256[4],string,string) (examples/defihacklabs/SpankChain.sol#804-889)
	- LedgerChannel.createChannel(bytes32,address,uint256,address,uint256[2]) (examples/defihacklabs/SpankChain.sol#623-690)
	- LedgerChannel.deposit(bytes32,address,uint256,bool) (examples/defihacklabs/SpankChain.sol#757-800)
	- LedgerChannel.getChannel(bytes32) (examples/defihacklabs/SpankChain.sol#1366-1423)
	- LedgerChannel.initVCstate(bytes32,bytes32,bytes,address,address,uint256[2],uint256[4],string) (examples/defihacklabs/SpankChain.sol#1005-1077)
	- LedgerChannel.joinChannel(bytes32,uint256[2]) (examples/defihacklabs/SpankChain.sol#716-751)
	- LedgerChannel.settleVC(bytes32,bytes32,uint256,address,address,uint256[4],string) (examples/defihacklabs/SpankChain.sol#1085-1191)
	- LedgerChannel.updateLCstate(bytes32,uint256[6],bytes32,string,string) (examples/defihacklabs/SpankChain.sol#892-1001)
```

## 4. bearn — unused-return

- Finding ID: `29e22b3a9cb0d2b5102fd039174b1b903cdf962a1f80edfd60a7b520bf0d47cc`
- Target: `BvaultsBank.emergencyWithdraw(uint256)`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/bearn/raw/Implementation.sol`
- Reported source lines: [1101]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
BvaultsBank.emergencyWithdraw(uint256) (Implementation.sol#1090-1110) ignores return value by IStrategy(poolInfo[_pid].strategy).withdraw(msg.sender,amount) (Implementation.sol#1101)
```

## 5. xsurge — incorrect-equality

- Finding ID: `0d1056a6b05f35c0661820fd228845121f557c692860dd5fbbf953fb28675bea`
- Target: `SurgeToken.purchase(address,uint256)`
- Impact/confidence: Medium / High
- Source: `examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol`
- Reported source lines: [560]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
SurgeToken.purchase(address,uint256) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#554-574) uses a dangerous strict equality:
	- prevBNBAmount == 0 (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#560)
```

## 6. eleven — divide-before-multiply

- Finding ID: `259a3a4cd3d251a7b1fbfc8b02d3112f69a6958925ee805487f78233aba35d25`
- Target: `ElevenNeverSellVault.pendingNerve(address)`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`
- Reported source lines: [1028]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
ElevenNeverSellVault.pendingNerve(address) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1026-1031) performs a multiplication on the result of a division:
	- harvested11nrvPerShare_ = harvested11nrvPerShare.add(IMasterMind(mastermind).pendingNerve(nrvPid,address(this)).mul(1e18).div(pps).mul(1e12).div(totalSupply())) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1028)
```

## 7. burgerswap — unused-return

- Finding ID: `de6520f714d63694f73f233c8dde8ce42741bcd4d921f6cc4900c6c33d68deb8`
- Target: `DemaxPlatform.migrateLiquidity(address,address,address,address[])`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol`
- Reported source lines: [1027]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
DemaxPlatform.migrateLiquidity(address,address,address,address[]) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#1018-1034) ignores return value by IDemaxPair(newPair).mint(users[i]) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#1027)
```

## 8. spartan — arbitrary-send-eth

- Finding ID: `3426dee9e8ef729ea3be1f7398d4d28fb04cd4158f433644d7058e127a547d3b`
- Target: `Router._handleTransferOut(address,uint256,address)`
- Impact/confidence: High / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`
- Reported source lines: [586]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
Router._handleTransferOut(address,uint256,address) (Victim.sol#581-591) sends eth to arbitrary user
	Dangerous calls:
	- address(_recipient).call{value: _amount}() (Victim.sol#586)
```

## 9. bearn — reentrancy-no-eth

- Finding ID: `705ce4acff1a3216ca1c5cc0a7d9cd1120988c4f3fd5c0bf811364ef1865435f`
- Target: `BvaultsBank.migrateStrategy(uint256,address)`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/bearn/raw/Implementation.sol`
- Reported source lines: [879, 880, 881, 882]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
Reentrancy in BvaultsBank.migrateStrategy(uint256,address) (Implementation.sol#873-883):
	External calls:
	- IStrategy(_oldStrategy).withdraw(address(this),_oldWantAmt) (Implementation.sol#879)
	- pool.want.transfer(_newStrategy,_oldWantAmt) (Implementation.sol#880)
	- IStrategy(_newStrategy).migrateFrom(_oldStrategy,_oldWantAmt,_oldSharesTotal) (Implementation.sol#881)
	State variables written after the call(s):
	- pool.strategy = _newStrategy (Implementation.sol#882)
	BvaultsBank.poolInfo (Implementation.sol#776) can be used in cross function reentrancies:
	- BvaultsBank._getReward(uint256) (Implementation.sol#989-1005)
	- BvaultsBank.add(uint256,IERC20,bool,address) (Implementation.sol#841-854)
	- BvaultsBank.massUpdatePools() (Implementation.sol#958-963)
	- BvaultsBank.migrateStrategy(uint256,address) (Implementation.sol#873-883)
	- BvaultsBank.pendingReward(uint256,uint256,address) (Implementation.sol#926-942)
	- BvaultsBank.poolInfo (Implementation.sol#776)
	- BvaultsBank.poolLength() (Implementation.sol#830-832)
	- BvaultsBank.resetStrategy(uint256,address) (Implementation.sol#863-867)
	- BvaultsBank.set(uint256,uint256) (Implementation.sol#857-861)
	- BvaultsBank.shutdownStrategy(uint256) (Implementation.sol#869-871)
	- BvaultsBank.stakedWantTokens(uint256,address) (Implementation.sol#945-955)
	- BvaultsBank.updatePool(uint256) (Implementation.sol#966-987)
	- BvaultsBank.withdraw(uint256,uint256) (Implementation.sol#1038-1083)
```

## 10. spankchain — constant-function-asm

- Finding ID: `f994fab55d8647cd6e028b5811ad9d9e120155326faf4eca1d48fc670807ceaa`
- Target: `ECTools.uintToBytes32(uint256)`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/SpankChain.sol`
- Reported source lines: [207, 208, 209, 210, 211, 212, 213]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
ECTools.uintToBytes32(uint256) (examples/defihacklabs/SpankChain.sol#207-213) is declared view but contains assembly code
```

## 11. eleven — unchecked-transfer

- Finding ID: `71a916f70433320f294d6256d4cb9d11f2ba1715e9c80fef76541df2d78446ac`
- Target: `ElevenNeverSellVault.chargeFees()`
- Impact/confidence: High / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`
- Reported source lines: [1000]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
ElevenNeverSellVault.chargeFees() (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#995-1002) ignores return value by IERC20(nrv).transfer(buybackstrat,toSell) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1000)
```

## 12. xsurge — divide-before-multiply

- Finding ID: `c52e2859d9d1e3de2c8cd8b04fc807338298075b3928224d4acd5d73740c477f`
- Target: `SurgeToken.purchase(address,uint256)`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol`
- Reported source lines: [562, 564]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
SurgeToken.purchase(address,uint256) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#554-574) performs a multiplication on the result of a division:
	- tokensToSend = nShouldPurchase.mul(spreadDivisor).div(10 ** 2) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#564)
	- nShouldPurchase = _totalSupply.mul(bnbAmount).div(prevBNBAmount) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#562)
```

## 13. burgerswap — unused-return

- Finding ID: `40750c41d2e69ce2f681004ed403a7bd57f9b162a0d6c3b834760a79f4592478`
- Target: `DemaxPlatform.swapPrecondition(address)`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol`
- Reported source lines: [736]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
DemaxPlatform.swapPrecondition(address) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#728-742) ignores return value by (reserveDGAS,None) = DemaxSwapLibrary.getReserves(FACTORY,DGAS,token) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#736)
```

## 14. spartan — unchecked-lowlevel

- Finding ID: `b88645d859573e7cd79ccb9443b3405342bedfe577d59ac77dd91a970a3ea6aa`
- Target: `Router._handleTransferIn(address,uint256,address)`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`
- Reported source lines: [570]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
Router._handleTransferIn(address,uint256,address) (Victim.sol#565-579) ignores return value by address(WBNB).call{value: _amount}() (Victim.sol#570)
```

## 15. spankchain — incorrect-equality

- Finding ID: `555479cc96ea35b4affe7a8500f50e27fa63fc965a2d8947e485baa85f11f08c`
- Target: `LedgerChannel._isContained(bytes32,bytes,bytes32)`
- Impact/confidence: Medium / High
- Source: `examples/defihacklabs/SpankChain.sol`
- Reported source lines: [1360]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
LedgerChannel._isContained(bytes32,bytes,bytes32) (examples/defihacklabs/SpankChain.sol#1338-1362) uses a dangerous strict equality:
	- cursor == _root (examples/defihacklabs/SpankChain.sol#1360)
```

## 16. eleven — reentrancy-no-eth

- Finding ID: `b560cc3081584d2ee310e177077fe5398803858478b18a49faa0142284663824`
- Target: `ElevenNeverSellVault.claimRewards()`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`
- Reported source lines: [1000, 1001, 1006, 1007, 1012, 1018, 1063, 1065, 1080, 1081, 1085, 1086]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
Reentrancy in ElevenNeverSellVault.claimRewards() (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1079-1082):
	External calls:
	- claim(msg.sender) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1080)
		- IMasterMind(mastermind).deposit(nrvPid,0) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1018)
		- IMasterMind(elechef).deposit(elePid,0) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1012)
		- IERC20(nrv).transfer(convertTo11nrvStrat,toStake) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1006)
		- ConvertTo11NrvStrat(convertTo11nrvStrat).convert(nrv) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1007)
		- IERC20(_token).transfer(_to,sushiBal) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1063)
		- IERC20(_token).transfer(_to,_amount) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1065)
		- IERC20(nrv).transfer(buybackstrat,toSell) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1000)
		- Buybackstrat(buybackstrat).chargeFees(nrv,receiveFee) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1001)
	State variables written after the call(s):
	- updateDebt(msg.sender) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1081)
		- harvested11nrvPerUser[_add] = balanceOf(_add).mul(harvested11nrvPerShare).div(1e12) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1086)
	ElevenNeverSellVault.harvested11nrvPerUser (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#926) can be used in cross function reentrancies:
	- ElevenNeverSellVault.claim(address) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1069-1077)
	- ElevenNeverSellVault.harvested11nrvPerUser (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#926)
	- ElevenNeverSellVault.pendingNerve(address) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1026-1031)
	- ElevenNeverSellVault.updateDebt(address) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1084-1087)
	- updateDebt(msg.sender) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1081)
		- harvestedElePerUser[_add] = balanceOf(_add).mul(harvestedElePerShare).div(1e12) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1085)
	ElevenNeverSellVault.harvestedElePerUser (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#928) can be used in cross function reentrancies:
	- ElevenNeverSellVault.claim(address) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1069-1077)
	- ElevenNeverSellVault.harvestedElePerUser (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#928)
	- ElevenNeverSellVault.pendingEleven(address) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1033-1037)
	- ElevenNeverSellVault.updateDebt(address) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1084-1087)
```

## 17. bearn — unchecked-transfer

- Finding ID: `62e7b3ba7e49dfb99841e2603e650dff6bc6782f4e9ee8c52c9d8656800f6dff`
- Target: `BvaultsBank.migrateStrategy(uint256,address)`
- Impact/confidence: High / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/bearn/raw/Implementation.sol`
- Reported source lines: [880]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
BvaultsBank.migrateStrategy(uint256,address) (Implementation.sol#873-883) ignores return value by pool.want.transfer(_newStrategy,_oldWantAmt) (Implementation.sol#880)
```

## 18. xsurge — divide-before-multiply

- Finding ID: `9fb62fea1ce3dc5432b21e883cbe16f925a50ca3d210c0f619a84ddbceb91869`
- Target: `SurgeToken.sell(uint256)`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol`
- Reported source lines: [585, 588]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
SurgeToken.sell(uint256) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#577-602) performs a multiplication on the result of a division:
	- tokensToSwap = tokenAmount.mul(sellFee).div(10 ** 2) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#585)
	- amountBNB = tokensToSwap.mul(calculatePrice()) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#588)
```

## 19. burgerswap — unused-return

- Finding ID: `92f3e299e4e000f89bb0130a7aa47f367305bf9e4b285d6d30ef81f619a48c0c`
- Target: `DemaxPlatform.swapPrecondition(address)`
- Impact/confidence: Medium / Medium
- Source: `examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol`
- Reported source lines: [737]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
DemaxPlatform.swapPrecondition(address) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#728-742) ignores return value by (reserveWETH,None) = DemaxSwapLibrary.getReserves(FACTORY,WETH,token) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#737)
```

## 20. spartan — locked-ether

- Finding ID: `e8fd05569b88b694d2f90f4cb31d7238e3a16b4bfe1ab3c0143012345d08c63b`
- Target: `Pool.constructor(address,address)`
- Impact/confidence: Medium / High
- Source: `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`
- Reported source lines: [117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267]
- Current label: **UNLABELED**
- Review rationale: High/Medium warning with resolvable target source; compare the exact analyzer claim against guards, state transitions and call behavior. Prioritized for case/detector diversity and reported line-span locality. No exploit execution or presumption of label is requested.

Slither description:

```text
Contract locking ether found:
	Contract Pool (Victim.sol#85-344) has payable functions:
	 - Pool.constructor(address,address) (Victim.sol#117-128)
	 - Pool.swapTo(address,address) (Victim.sol#252-267)
	But does not have a function to withdraw the ether
```

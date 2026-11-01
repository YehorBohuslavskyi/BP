# Manual adjudication packet

Twenty candidates in the existing rank order. Current labels are copied unchanged. Questions are intentionally unanswered. Record independent evidence before entering a final label; a historical incident or LLM verdict does not validate an unrelated warning. This packet supplies excerpts, not complete contracts or proof of safety. A KNOWN_TP decision needs evidence matching the exact finding.

## 1. spartan — unchecked-transfer

Finding ID: `e0b32bd732a1c264102776aaadff912380062745caa2eef526f7ad911b9e44f5`  
Impact / confidence: High / Medium  
Contract / function: `Pool.swapTo(address,address)`  
Reported lines: [265]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
Pool.swapTo(address,address) (Victim.sol#252-267) ignores return value by iBEP20(token).transfer(member,outputAmount) (Victim.sol#265)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 252–268

```text
  252 |     function swapTo(address token, address member) public payable returns (uint outputAmount, uint fee) {
  253 |         require((token == BASE || token == TOKEN), "Must be BASE or TOKEN");
  254 |         address _fromToken; uint _amount;
  255 |         if(token == BASE){
  256 |             _fromToken = TOKEN;
  257 |             _amount = _getAddedTokenAmount();
  258 |             (outputAmount, fee) = _swapTokenToBase(_amount);
  259 |         } else {
  260 |             _fromToken = BASE;
  261 |             _amount = _getAddedBaseAmount();
  262 |             (outputAmount, fee) = _swapBaseToToken(_amount);
  263 |         }
  264 |         emit Swapped(_fromToken, token, _amount, outputAmount, fee, member);
  265 |         iBEP20(token).transfer(member, outputAmount);
  266 |         return (outputAmount, fee);
  267 |     }
  268 | 
```

local_function: _getAddedBaseAmount — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 269–277

```text
  269 |     function _getAddedBaseAmount() internal view returns(uint256 _actual){
  270 |         uint _baseBalance = iBEP20(BASE).balanceOf(address(this)); 
  271 |         if(_baseBalance > baseAmount){
  272 |             _actual = _baseBalance.sub(baseAmount);
  273 |         } else {
  274 |             _actual = 0;
  275 |         }
  276 |         return _actual;
  277 |     }
```

local_function: _getAddedTokenAmount — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 278–286

```text
  278 |     function _getAddedTokenAmount() internal view returns(uint256 _actual){
  279 |         uint _tokenBalance = iBEP20(TOKEN).balanceOf(address(this)); 
  280 |         if(_tokenBalance > tokenAmount){
  281 |             _actual = _tokenBalance.sub(tokenAmount);
  282 |         } else {
  283 |             _actual = 0;
  284 |         }
  285 |         return _actual;
  286 |     }
```

local_function: _swapBaseToToken — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 288–296

```text
  288 |     function _swapBaseToToken(uint256 _x) internal returns (uint256 _y, uint256 _fee){
  289 |         uint256 _X = baseAmount;
  290 |         uint256 _Y = tokenAmount;
  291 |         _y =  _DAO().UTILS().calcSwapOutput(_x, _X, _Y);
  292 |         _fee = _DAO().UTILS().calcSwapFee(_x, _X, _Y);
  293 |         _setPoolAmounts(_X.add(_x), _Y.sub(_y));
  294 |         _addPoolMetrics(_y+_fee, _fee, false);
  295 |         return (_y, _fee);
  296 |     }
```

### Neutral adjudication question

Can the referenced token transfer fail or return false while execution proceeds with an inconsistent asset/accounting state, or is successful transfer established by the shown call semantics and guards?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label. Additional local context omitted: _swapTokenToBase, swapTo

## 2. visor-finance — arbitrary-send-erc20

Finding ID: `5d3eca2555a2051ff6412cb4a9bffb2027fe752f63b717bf319dc6d7c96cb1cb`  
Impact / confidence: High / High  
Contract / function: `RewardsHypervisor.deposit(uint256,address,address)`  
Reported lines: [61]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
RewardsHypervisor.deposit(uint256,address,address) (RewardsHypervisor.sol#41-65) uses arbitrary from in transferFrom: visr.safeTransferFrom(from,address(this),visrDeposit) (RewardsHypervisor.sol#61)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/visor-finance/analysis/RewardsHypervisor.sol`; lines 41–65

```text
   41 |     function deposit(
   42 |         uint256 visrDeposit,
   43 |         address payable from,
   44 |         address to
   45 |     ) external returns (uint256 shares) {
   46 |         require(visrDeposit > 0, "deposits must be nonzero");
   47 |         require(to != address(0) && to != address(this), "to");
   48 |         require(from != address(0) && from != address(this), "from");
   49 | 
   50 |         shares = visrDeposit;
   51 |         if (vvisr.totalSupply() != 0) {
   52 |           uint256 visrBalance = visr.balanceOf(address(this));
   53 |           shares = shares.mul(vvisr.totalSupply()).div(visrBalance);
   54 |         }
   55 | 
   56 |         if(isContract(from)) {
   57 |           require(IVisor(from).owner() == msg.sender); 
   58 |           IVisor(from).delegatedTransferERC20(address(visr), address(this), visrDeposit);
   59 |         }
   60 |         else {
   61 |           visr.safeTransferFrom(from, address(this), visrDeposit);
   62 |         }
   63 | 
   64 |         vvisr.mint(to, shares);
   65 |     }
```

local_function: isContract — `examples/defihacklabs/evaluation/final20/contracts/visor-finance/analysis/RewardsHypervisor.sol`; lines 99–105

```text
   99 |     function isContract(address _addr) private returns (bool isContract){
  100 | 				uint32 size;
  101 | 				assembly {
  102 | 					size := extcodesize(_addr)
  103 | 				}
  104 | 				return (size > 0);
  105 | 		}
```

### Neutral adjudication question

For the exact reported transferFrom sink and its branch, can an unauthorized caller choose a different owner as from and spend that owner’s approved tokens, or do the shown checks bind the caller to the owner?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 3. spankchain — reentrancy-eth

Finding ID: `a03eb32cf0cb25b5d913b9890d1e238c647156d1da44ca03a9c1c3676916782f`  
Impact / confidence: High / Medium  
Contract / function: `LedgerChannel.byzantineCloseChannel(bytes32)`  
Reported lines: [1306, 1307, 1313, 1314, 1315, 1316, 1317, 1318, 1319, 1321, 1322, 1323, 1324, 1325, 1326, 1327, 1331]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

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

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/SpankChain.sol`; lines 1241–1257

```text
 1241 | function byzantineCloseChannel(bytes32 _lcID) public {
 1242 | 
 1243 | Channel storage channel = Channels[_lcID];
 1244 | 
 1245 | // check settlement flag
 1246 | 
 1247 | require(channel.isOpen, "Channel is not open");
 1248 | 
 1249 | require(channel.isUpdateLCSettling == true);
 1250 | 
 1251 | require(channel.numOpenVC == 0);
 1252 | require(channel.updateLCtimeout < now, "LC timeout over.");
 1253 | 
 1254 | // if off chain state update didnt reblance deposits, just return to deposit owner
 1255 | 
 1256 | uint256 totalEthDeposit = channel.initialDeposit[0] + channel.ethBalances[2] + channel.ethBalances[3];
 1257 | 
```

target_and_reported_lines_with_surroundings — `examples/defihacklabs/SpankChain.sol`; lines 1303–1337

```text
 1303 | 
 1304 | if(ethbalanceA != 0 || ethbalanceI != 0) {
 1305 | 
 1306 | channel.partyAddresses[0].transfer(ethbalanceA);
 1307 | channel.partyAddresses[1].transfer(ethbalanceI);
 1308 | 
 1309 | }
 1310 | 
 1311 | if(tokenbalanceA != 0 || tokenbalanceI != 0) {
 1312 | 
 1313 | require(
 1314 | 
 1315 | channel.token.transfer(channel.partyAddresses[0], tokenbalanceA),
 1316 | 
 1317 | "byzantineCloseChannel: token transfer failure"
 1318 | 
 1319 | );
 1320 | 
 1321 | require(
 1322 | 
 1323 | channel.token.transfer(channel.partyAddresses[1], tokenbalanceI),
 1324 | 
 1325 | "byzantineCloseChannel: token transfer failure"
 1326 | 
 1327 | );
 1328 | 
 1329 | }
 1330 | 
 1331 | channel.isOpen = false;
 1332 | 
 1333 | numChannels--;
 1334 | 
 1335 | emit DidLCClose(_lcID, channel.sequence, ethbalanceA, ethbalanceI, tokenbalanceA, tokenbalanceI);
 1336 | 
 1337 | }
```

### Neutral adjudication question

Does the external call permit attacker-controlled re-entry that can violate a relevant state invariant, or is the reported path harmless under the shown guards and state transitions?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 4. bearn — unused-return

Finding ID: `29e22b3a9cb0d2b5102fd039174b1b903cdf962a1f80edfd60a7b520bf0d47cc`  
Impact / confidence: Medium / Medium  
Contract / function: `BvaultsBank.emergencyWithdraw(uint256)`  
Reported lines: [1101]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
BvaultsBank.emergencyWithdraw(uint256) (Implementation.sol#1090-1110) ignores return value by IStrategy(poolInfo[_pid].strategy).withdraw(msg.sender,amount) (Implementation.sol#1101)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/bearn/raw/Implementation.sol`; lines 1090–1110

```text
 1090 |     function emergencyWithdraw(uint256 _pid) public nonReentrant {
 1091 |         require(!pausePool[_pid], "paused");
 1092 |         require(!blacklistAccount[msg.sender], "blacklisted");
 1093 | 
 1094 |         PoolInfo storage pool = poolInfo[_pid];
 1095 |         UserInfo storage user = userInfo[_pid][msg.sender];
 1096 | 
 1097 |         uint256 wantLockedTotal = IStrategy(poolInfo[_pid].strategy).wantLockedTotal();
 1098 |         uint256 sharesTotal = IStrategy(poolInfo[_pid].strategy).sharesTotal();
 1099 |         uint256 amount = user.shares.mul(wantLockedTotal).div(sharesTotal);
 1100 | 
 1101 |         IStrategy(poolInfo[_pid].strategy).withdraw(msg.sender, amount);
 1102 | 
 1103 |         pool.want.safeTransfer(address(msg.sender), amount);
 1104 |         emit EmergencyWithdraw(msg.sender, _pid, amount);
 1105 |         user.shares = 0;
 1106 |         uint256 _rewardPoolLength = rewardPoolInfo.length;
 1107 |         for (uint256 _rewardPid = 0; _rewardPid < _rewardPoolLength; ++_rewardPid) {
 1108 |             user.rewardDebt[_rewardPid] = 0;
 1109 |         }
 1110 |     }
```

local_modifier: nonReentrant — `examples/defihacklabs/evaluation/final20/contracts/bearn/raw/Implementation.sol`; lines 672–684

```text
  672 |     modifier nonReentrant() {
  673 |         // On the first call to nonReentrant, _notEntered will be true
  674 |         require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
  675 | 
  676 |         // Any calls to nonReentrant after this point will fail
  677 |         _status = _ENTERED;
  678 | 
  679 |         _;
  680 | 
  681 |         // By storing the original value once again, a refund is triggered (see
  682 |         // https://eips.ethereum.org/EIPS/eip-2200)
  683 |         _status = _NOT_ENTERED;
  684 |     }
```

### Neutral adjudication question

What does each discarded return value signify, and can ignoring it allow an unsuccessful or materially different operation to be treated as successful by this caller?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 5. xsurge — incorrect-equality

Finding ID: `0d1056a6b05f35c0661820fd228845121f557c692860dd5fbbf953fb28675bea`  
Impact / confidence: Medium / High  
Contract / function: `SurgeToken.purchase(address,uint256)`  
Reported lines: [560]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
SurgeToken.purchase(address,uint256) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#554-574) uses a dangerous strict equality:
	- prevBNBAmount == 0 (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#560)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol`; lines 554–574

```text
  554 |     function purchase(address buyer, uint256 bnbAmount) internal returns (bool) {
  555 |         // make sure we don't buy more than the bnb in this contract
  556 |         require(bnbAmount <= address(this).balance, 'purchase not included in balance');
  557 |         // previous amount of BNB before we received any        
  558 |         uint256 prevBNBAmount = (address(this).balance).sub(bnbAmount);
  559 |         // if this is the first purchase, use current balance
  560 |         prevBNBAmount = prevBNBAmount == 0 ? address(this).balance : prevBNBAmount;
  561 |         // find the number of tokens we should mint to keep up with the current price
  562 |         uint256 nShouldPurchase = hyperInflatePrice ? _totalSupply.mul(bnbAmount).div(address(this).balance) : _totalSupply.mul(bnbAmount).div(prevBNBAmount);
  563 |         // apply our spread to tokens to inflate price relative to total supply
  564 |         uint256 tokensToSend = nShouldPurchase.mul(spreadDivisor).div(10**2);
  565 |         // revert if under 1
  566 |         if (tokensToSend < 1) {
  567 |             revert('Must Buy More Than One Surge');
  568 |         }
  569 |         
  570 |         // mint the tokens we need to the buyer
  571 |         mint(buyer, tokensToSend);
  572 |         emit Transfer(address(this), buyer, tokensToSend);
  573 |         return true;
  574 |     }
```

local_function: mint — `examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol`; lines 610–613

```text
  610 |     function mint(address receiver, uint amount) internal {
  611 |         _balances[receiver] = _balances[receiver].add(amount);
  612 |         _totalSupply = _totalSupply.add(amount);
  613 |     }
```

### Neutral adjudication question

Is this exact equality required by the intended authorization, state, proof or accounting invariant, or can an independently changeable value make it unsafe or prevent a valid operation?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 6. eleven — divide-before-multiply

Finding ID: `259a3a4cd3d251a7b1fbfc8b02d3112f69a6958925ee805487f78233aba35d25`  
Impact / confidence: Medium / Medium  
Contract / function: `ElevenNeverSellVault.pendingNerve(address)`  
Reported lines: [1028]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
ElevenNeverSellVault.pendingNerve(address) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1026-1031) performs a multiplication on the result of a division:
	- harvested11nrvPerShare_ = harvested11nrvPerShare.add(IMasterMind(mastermind).pendingNerve(nrvPid,address(this)).mul(1e18).div(pps).mul(1e12).div(totalSupply())) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1028)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`; lines 1025–1031

```text
 1025 | 
 1026 |     function pendingNerve(address _user) public view returns (uint){
 1027 |         uint pps = Pps(nrv11).getPricePerFullShare();
 1028 |         uint harvested11nrvPerShare_ = harvested11nrvPerShare.add(IMasterMind(mastermind).pendingNerve(nrvPid, address(this)).mul(1e18).div(pps).mul(1e12).div(totalSupply()));
 1029 |         uint nrv11ToPay_ = harvested11nrvPerShare_.mul(balanceOf(_user)).div(1e12).sub(harvested11nrvPerUser[_user]);
 1030 |         return nrv11ToPay_;
 1031 |     }
```

local_function: balanceOf — `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`; lines 507–509

```text
  507 |     function balanceOf(address account) public view override returns (uint256) {
  508 |         return _balances[account];
  509 |     }
```

local_function: totalSupply — `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`; lines 500–502

```text
  500 |     function totalSupply() public view override returns (uint256) {
  501 |         return _totalSupply;
  502 |     }
```

### Neutral adjudication question

Can the shown division-before-multiplication rounding materially violate the intended calculation for reachable inputs, or is the truncation acceptable under the relevant units and bounds?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 7. burgerswap — unused-return

Finding ID: `de6520f714d63694f73f233c8dde8ce42741bcd4d921f6cc4900c6c33d68deb8`  
Impact / confidence: Medium / Medium  
Contract / function: `DemaxPlatform.migrateLiquidity(address,address,address,address[])`  
Reported lines: [1027]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
DemaxPlatform.migrateLiquidity(address,address,address,address[]) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#1018-1034) ignores return value by IDemaxPair(newPair).mint(users[i]) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#1027)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol`; lines 1018–1034

```text
 1018 |     function migrateLiquidity(address pair, address tokenA, address tokenB, address[] calldata users) external onlyOwner {
 1019 |         if (IDemaxFactory(FACTORY).getPair(tokenA, tokenB) == address(0)) {
 1020 |             IDemaxFactory(FACTORY).createPair(tokenA, tokenB);
 1021 |         }
 1022 |         address newPair = IDemaxFactory(FACTORY).getPair(tokenA, tokenB);
 1023 |         for(uint i = 0; i < users.length; i++) {
 1024 |             uint liquidity = IDemaxPair(pair).balanceOf(users[i]);
 1025 |             if(liquidity > 0) {
 1026 |                 IDemaxPair(pair).burn(users[i], newPair, liquidity);
 1027 |                 IDemaxPair(newPair).mint(users[i]);
 1028 |                 IDemaxFactory(FACTORY).addPlayerPair(users[i], newPair);
 1029 |             }
 1030 |         }
 1031 | 
 1032 |         IDemaxTransferListener(TRANSFER_LISTENER).upgradeProdutivity(pair, newPair);
 1033 |         
 1034 |     }
```

local_modifier: onlyOwner — `examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol`; lines 22–25

```text
   22 |     modifier onlyOwner() {
   23 |         require(msg.sender == owner, 'Ownable: FORBIDDEN');
   24 |         _;
   25 |     }
```

### Neutral adjudication question

What does each discarded return value signify, and can ignoring it allow an unsuccessful or materially different operation to be treated as successful by this caller?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 8. spartan — arbitrary-send-eth

Finding ID: `3426dee9e8ef729ea3be1f7398d4d28fb04cd4158f433644d7058e127a547d3b`  
Impact / confidence: High / Medium  
Contract / function: `Router._handleTransferOut(address,uint256,address)`  
Reported lines: [586]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
Router._handleTransferOut(address,uint256,address) (Victim.sol#581-591) sends eth to arbitrary user
	Dangerous calls:
	- address(_recipient).call{value: _amount}() (Victim.sol#586)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 581–591

```text
  581 |     function _handleTransferOut(address _token, uint256 _amount, address _recipient) internal {
  582 |         if(_amount > 0) {
  583 |             if (_token == address(0)) {
  584 |                 // If BNB, then withdraw to BNB, then forward BNB to recipient
  585 |                 iWBNB(WBNB).withdraw(_amount);
  586 |                 payable(_recipient).call{value:_amount}(""); 
  587 |             } else {
  588 |                 iBEP20(_token).transfer(_recipient, _amount);
  589 |             }
  590 |         }
  591 |     }
```

local_caller: removeLiquidityExactAndSwap — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 478–501

```text
  478 |     function removeLiquidityExactAndSwap(uint units, bool toBase, address token) public returns (uint outputAmount){
  479 |         address _pool = getPool(token);
  480 |         require(units < iBEP20(_pool).totalSupply(), "InputErr");
  481 |         Pool(_pool).transferTo(_pool, units);
  482 |         (uint _outputBase, uint _outputToken) = Pool(_pool).removeLiquidity();
  483 |         totalPooled = totalPooled.sub(_outputBase);
  484 |         removeLiquidityTx += 1;
  485 |         if(toBase){
  486 |             // sell to BASE
  487 |             iBEP20(token).transfer(_pool, _outputToken);
  488 |             (uint _baseBought, uint _fee) = Pool(_pool).swap(token);
  489 |             totalFees += _fee;
  490 |             outputAmount = _baseBought.add(_outputBase);
  491 |             _handleTransferOut(BASE, outputAmount, msg.sender);
  492 |         } else {
  493 |             // buy to TOKEN
  494 |             iBEP20(BASE).transfer(_pool, _outputToken);
  495 |             (uint _tokenBought, uint _fee) = Pool(_pool).swap(BASE);
  496 |             totalFees += _DAO().UTILS().calcValueInBase(token, _fee);
  497 |             outputAmount = _tokenBought.add(_outputToken);
  498 |             _handleTransferOut(token, outputAmount, msg.sender);
  499 |         }
  500 |         return outputAmount;
  501 |     }
```

### Neutral adjudication question

Can an unauthorized caller influence the reported ETH recipient or payout, or do reachable callers and their authorization checks constrain the transfer to an authorized recipient and amount?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 9. bearn — reentrancy-no-eth

Finding ID: `705ce4acff1a3216ca1c5cc0a7d9cd1120988c4f3fd5c0bf811364ef1865435f`  
Impact / confidence: Medium / Medium  
Contract / function: `BvaultsBank.migrateStrategy(uint256,address)`  
Reported lines: [879, 880, 881, 882]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

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

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/bearn/raw/Implementation.sol`; lines 873–885

```text
  873 |     function migrateStrategy(uint256 _pid, address _newStrategy) public onlyOperator {
  874 |         require(IStrategy(_newStrategy).wantLockedTotal() == 0 && IStrategy(_newStrategy).sharesTotal() == 0, "new strategy not empty");
  875 |         PoolInfo storage pool = poolInfo[_pid];
  876 |         address _oldStrategy = pool.strategy;
  877 |         uint256 _oldSharesTotal = IStrategy(_oldStrategy).sharesTotal();
  878 |         uint256 _oldWantAmt = IStrategy(_oldStrategy).wantLockedTotal();
  879 |         IStrategy(_oldStrategy).withdraw(address(this), _oldWantAmt);
  880 |         pool.want.transfer(_newStrategy, _oldWantAmt);
  881 |         IStrategy(_newStrategy).migrateFrom(_oldStrategy, _oldWantAmt, _oldSharesTotal);
  882 |         pool.strategy = _newStrategy;
  883 |     }
  884 | 
  885 |     function rewardPoolLength() external view returns (uint256) {
```

local_modifier: onlyOperator — `examples/defihacklabs/evaluation/final20/contracts/bearn/raw/Implementation.sol`; lines 815–818

```text
  815 |     modifier onlyOperator() {
  816 |         require(operator == msg.sender, "BvaultsBank: caller is not the operator");
  817 |         _;
  818 |     }
```

### Neutral adjudication question

Can a callback through the reported external call observe or change stale state in a way that violates an invariant, considering access restrictions, modifiers, and callable paths?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 10. spankchain — constant-function-asm

Finding ID: `f994fab55d8647cd6e028b5811ad9d9e120155326faf4eca1d48fc670807ceaa`  
Impact / confidence: Medium / Medium  
Contract / function: `ECTools.uintToBytes32(uint256)`  
Reported lines: [207, 208, 209, 210, 211, 212, 213]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
ECTools.uintToBytes32(uint256) (examples/defihacklabs/SpankChain.sol#207-213) is declared view but contains assembly code
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/SpankChain.sol`; lines 204–216

```text
  204 | 
  205 | // @thanks https://ethereum.stackexchange.com/questions/4170/how-to-convert-a-uint-to-bytes-in-solidity
  206 | 
  207 | function uintToBytes32(uint _uint) public pure returns (bytes b) {
  208 | 
  209 | b = new bytes(32);
  210 | 
  211 | assembly {mstore(add(b, 32), _uint)}
  212 | 
  213 | }
  214 | 
  215 | // @dev Hashes the signed message
  216 | 
```

### Neutral adjudication question

Does this assembly or its reachable call chain violate the declared mutability or compatibility guarantees for the relevant compiler, or does it only perform operations permitted by that declaration?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 11. eleven — unchecked-transfer

Finding ID: `71a916f70433320f294d6256d4cb9d11f2ba1715e9c80fef76541df2d78446ac`  
Impact / confidence: High / Medium  
Contract / function: `ElevenNeverSellVault.chargeFees()`  
Reported lines: [1000]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
ElevenNeverSellVault.chargeFees() (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#995-1002) ignores return value by IERC20(nrv).transfer(buybackstrat,toSell) (examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol#1000)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`; lines 995–1003

```text
  995 |     function chargeFees() internal {
  996 |         address receiveFee;
  997 |         if(harvesters[msg.sender]) receiveFee = msg.sender;
  998 |         else receiveFee = 0x6B3C201575aCe5Ed6B67df5c91E40B98c0D2BE36;
  999 |         uint toSell = IERC20(nrv).balanceOf(address(this)).mul(bpsFee).div(10000);
 1000 |         IERC20(nrv).transfer(buybackstrat, toSell);
 1001 |         Buybackstrat(buybackstrat).chargeFees(nrv, receiveFee);
 1002 |     }
 1003 | 
```

### Neutral adjudication question

Can the referenced token transfer fail or return false while execution proceeds with an inconsistent asset/accounting state, or is successful transfer established by the shown call semantics and guards?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 12. xsurge — divide-before-multiply

Finding ID: `c52e2859d9d1e3de2c8cd8b04fc807338298075b3928224d4acd5d73740c477f`  
Impact / confidence: Medium / Medium  
Contract / function: `SurgeToken.purchase(address,uint256)`  
Reported lines: [562, 564]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
SurgeToken.purchase(address,uint256) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#554-574) performs a multiplication on the result of a division:
	- tokensToSend = nShouldPurchase.mul(spreadDivisor).div(10 ** 2) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#564)
	- nShouldPurchase = _totalSupply.mul(bnbAmount).div(prevBNBAmount) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#562)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol`; lines 554–574

```text
  554 |     function purchase(address buyer, uint256 bnbAmount) internal returns (bool) {
  555 |         // make sure we don't buy more than the bnb in this contract
  556 |         require(bnbAmount <= address(this).balance, 'purchase not included in balance');
  557 |         // previous amount of BNB before we received any        
  558 |         uint256 prevBNBAmount = (address(this).balance).sub(bnbAmount);
  559 |         // if this is the first purchase, use current balance
  560 |         prevBNBAmount = prevBNBAmount == 0 ? address(this).balance : prevBNBAmount;
  561 |         // find the number of tokens we should mint to keep up with the current price
  562 |         uint256 nShouldPurchase = hyperInflatePrice ? _totalSupply.mul(bnbAmount).div(address(this).balance) : _totalSupply.mul(bnbAmount).div(prevBNBAmount);
  563 |         // apply our spread to tokens to inflate price relative to total supply
  564 |         uint256 tokensToSend = nShouldPurchase.mul(spreadDivisor).div(10**2);
  565 |         // revert if under 1
  566 |         if (tokensToSend < 1) {
  567 |             revert('Must Buy More Than One Surge');
  568 |         }
  569 |         
  570 |         // mint the tokens we need to the buyer
  571 |         mint(buyer, tokensToSend);
  572 |         emit Transfer(address(this), buyer, tokensToSend);
  573 |         return true;
  574 |     }
```

local_function: mint — `examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol`; lines 610–613

```text
  610 |     function mint(address receiver, uint amount) internal {
  611 |         _balances[receiver] = _balances[receiver].add(amount);
  612 |         _totalSupply = _totalSupply.add(amount);
  613 |     }
```

### Neutral adjudication question

Can the shown division-before-multiplication rounding materially violate the intended calculation for reachable inputs, or is the truncation acceptable under the relevant units and bounds?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 13. burgerswap — unused-return

Finding ID: `40750c41d2e69ce2f681004ed403a7bd57f9b162a0d6c3b834760a79f4592478`  
Impact / confidence: Medium / Medium  
Contract / function: `DemaxPlatform.swapPrecondition(address)`  
Reported lines: [736]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
DemaxPlatform.swapPrecondition(address) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#728-742) ignores return value by (reserveDGAS,None) = DemaxSwapLibrary.getReserves(FACTORY,DGAS,token) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#736)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol`; lines 728–742

```text
  728 |     function swapPrecondition(address token) public view returns (bool) {
  729 |         if (token == DGAS || token == WETH) return true;
  730 |         uint256 percent = IDemaxConfig(CONFIG).getConfigValue(ConfigNames.TOKEN_TO_DGAS_PAIR_MIN_PERCENT);
  731 |         if (!existPair(WETH, DGAS)) return false;
  732 |         if (!existPair(DGAS, token)) return false;
  733 |         if (!(IDemaxConfig(CONFIG).checkPair(DGAS, token) && IDemaxConfig(CONFIG).checkPair(WETH, token))) return false;
  734 |         if (!existPair(WETH, token)) return true;
  735 |         if (percent == 0) return true;
  736 |         (uint256 reserveDGAS, ) = DemaxSwapLibrary.getReserves(FACTORY, DGAS, token);
  737 |         (uint256 reserveWETH, ) = DemaxSwapLibrary.getReserves(FACTORY, WETH, token);
  738 |         (uint256 reserveWETH2, uint256 reserveDGAS2) = DemaxSwapLibrary.getReserves(FACTORY, WETH, DGAS);
  739 |         uint256 dgasValue = SafeMath.mul(reserveDGAS, reserveWETH2) / reserveDGAS2;
  740 |         uint256 limitValue = SafeMath.mul(SafeMath.add(dgasValue, reserveWETH), percent) / PERCENT_DENOMINATOR;
  741 |         return dgasValue >= limitValue;
  742 |     }
```

local_function: existPair — `examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol`; lines 976–978

```text
  976 |     function existPair(address tokenA, address tokenB) public view returns (bool) {
  977 |         return IDemaxFactory(FACTORY).getPair(tokenA, tokenB) != address(0);
  978 |     }
```

### Neutral adjudication question

What does each discarded return value signify, and can ignoring it allow an unsuccessful or materially different operation to be treated as successful by this caller?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 14. spartan — unchecked-lowlevel

Finding ID: `b88645d859573e7cd79ccb9443b3405342bedfe577d59ac77dd91a970a3ea6aa`  
Impact / confidence: Medium / Medium  
Contract / function: `Router._handleTransferIn(address,uint256,address)`  
Reported lines: [570]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
Router._handleTransferIn(address,uint256,address) (Victim.sol#565-579) ignores return value by address(WBNB).call{value: _amount}() (Victim.sol#570)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 565–579

```text
  565 |     function _handleTransferIn(address _token, uint256 _amount, address _pool) internal returns(uint256 actual){
  566 |         if(_amount > 0) {
  567 |             if(_token == address(0)){
  568 |                 // If BNB, then send to WBNB contract, then forward WBNB to pool
  569 |                 require((_amount == msg.value), "InputErr");
  570 |                 payable(WBNB).call{value:_amount}(""); 
  571 |                 iBEP20(WBNB).transfer(_pool, _amount); 
  572 |                 actual = _amount;
  573 |             } else {
  574 |                 uint startBal = iBEP20(_token).balanceOf(_pool); 
  575 |                 iBEP20(_token).transferFrom(msg.sender, _pool, _amount); 
  576 |                 actual = iBEP20(_token).balanceOf(_pool).sub(startBal);
  577 |             }
  578 |         }
  579 |     }
```

local_caller: createPool — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 413–431

```text
  413 |     function createPool(uint256 inputBase, uint256 inputToken, address token) public payable returns(address pool){
  414 |         require(getPool(token) == address(0), "CreateErr");
  415 |         require(token != BASE, "Must not be Base");
  416 |         require((inputToken > 0 && inputBase > 0), "Must get tokens for both");
  417 |         Pool newPool; address _token = token;
  418 |         if(token == address(0)){_token = WBNB;} // Handle BNB
  419 |         newPool = new Pool(BASE, _token); 
  420 |         pool = address(newPool);
  421 |         mapToken_Pool[_token] = pool;
  422 |         uint256 _actualInputBase = _handleTransferIn(BASE, inputBase, pool);
  423 |         _handleTransferIn(token, inputToken, pool);
  424 |         arrayTokens.push(_token);
  425 |         isPool[pool] = true;
  426 |         totalPooled += _actualInputBase;
  427 |         addLiquidityTx += 1;
  428 |         Pool(pool).addLiquidityForMember(msg.sender);
  429 |         emit NewPool(token, pool, now);
  430 |         return pool;
  431 |     }
```

### Neutral adjudication question

Can the reported low-level call fail or return unexpected data while the caller continues in an inconsistent state, or is success guaranteed or independently checked?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 15. spankchain — incorrect-equality

Finding ID: `555479cc96ea35b4affe7a8500f50e27fa63fc965a2d8947e485baa85f11f08c`  
Impact / confidence: Medium / High  
Contract / function: `LedgerChannel._isContained(bytes32,bytes,bytes32)`  
Reported lines: [1360]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
LedgerChannel._isContained(bytes32,bytes,bytes32) (examples/defihacklabs/SpankChain.sol#1338-1362) uses a dangerous strict equality:
	- cursor == _root (examples/defihacklabs/SpankChain.sol#1360)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/SpankChain.sol`; lines 1338–1363

```text
 1338 | function _isContained(bytes32 _hash, bytes _proof, bytes32 _root) internal pure returns (bool) {
 1339 | 
 1340 | bytes32 cursor = _hash;
 1341 | 
 1342 | bytes32 proofElem;
 1343 | 
 1344 | for (uint256 i = 64; i <= _proof.length; i += 32) {
 1345 | 
 1346 | assembly { proofElem := mload(add(_proof, i)) }
 1347 | 
 1348 | if (cursor < proofElem) {
 1349 | 
 1350 | cursor = keccak256(abi.encodePacked(cursor, proofElem));
 1351 | 
 1352 | } else {
 1353 | 
 1354 | cursor = keccak256(abi.encodePacked(proofElem, cursor));
 1355 | 
 1356 | }
 1357 | 
 1358 | }
 1359 | 
 1360 | return cursor == _root;
 1361 | 
 1362 | }
 1363 | 
```

### Neutral adjudication question

Is this exact equality required by the intended authorization, state, proof or accounting invariant, or can an independently changeable value make it unsafe or prevent a valid operation?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 16. eleven — reentrancy-no-eth

Finding ID: `b560cc3081584d2ee310e177077fe5398803858478b18a49faa0142284663824`  
Impact / confidence: Medium / Medium  
Contract / function: `ElevenNeverSellVault.claimRewards()`  
Reported lines: [1000, 1001, 1006, 1007, 1012, 1018, 1063, 1065, 1080, 1081, 1085, 1086]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

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

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`; lines 997–1021

```text
  997 |         if(harvesters[msg.sender]) receiveFee = msg.sender;
  998 |         else receiveFee = 0x6B3C201575aCe5Ed6B67df5c91E40B98c0D2BE36;
  999 |         uint toSell = IERC20(nrv).balanceOf(address(this)).mul(bpsFee).div(10000);
 1000 |         IERC20(nrv).transfer(buybackstrat, toSell);
 1001 |         Buybackstrat(buybackstrat).chargeFees(nrv, receiveFee);
 1002 |     }
 1003 | 
 1004 |     function addLiquidity() internal{
 1005 |         uint toStake = IERC20(nrv).balanceOf(address(this));
 1006 |         IERC20(nrv).transfer(convertTo11nrvStrat, toStake);
 1007 |         ConvertTo11NrvStrat(convertTo11nrvStrat).convert(nrv);
 1008 |     }
 1009 |     
 1010 |     function updateEle() public{
 1011 |         uint eleBfr = IERC20(ele).balanceOf(address(this));
 1012 |         IMasterMind(elechef).deposit(elePid, 0);
 1013 |         uint eleAftr = IERC20(ele).balanceOf(address(this));
 1014 |         harvestedElePerShare = harvestedElePerShare.add(eleAftr.sub(eleBfr).mul(1e12).div(totalSupply()));
 1015 |     }
 1016 | 
 1017 |     function update11Nrv() public{
 1018 |         IMasterMind(mastermind).deposit(nrvPid, 0);//claim
 1019 |         chargeFees();
 1020 |         uint nrv11Bfr = IERC20(nrv11).balanceOf(address(this));
 1021 |         addLiquidity();
```

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`; lines 1060–1068

```text
 1060 |     function safeTokenTransfer(address _token, address _to, uint256 _amount) internal {
 1061 |         uint256 sushiBal = IERC20(_token).balanceOf(address(this));
 1062 |         if (_amount > sushiBal) {
 1063 |             IERC20(_token).transfer(_to, sushiBal);
 1064 |         } else {
 1065 |             IERC20(_token).transfer(_to, _amount);
 1066 |         }
 1067 |     }
 1068 | 
```

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`; lines 1077–1089

```text
 1077 |     }
 1078 |     
 1079 |     function claimRewards() public{
 1080 |         claim(msg.sender);
 1081 |         updateDebt(msg.sender);
 1082 |     }
 1083 |     
 1084 |     function updateDebt(address _add) internal{
 1085 |         harvestedElePerUser[_add] = balanceOf(_add).mul(harvestedElePerShare).div(1e12);
 1086 |         harvested11nrvPerUser[_add] = balanceOf(_add).mul(harvested11nrvPerShare).div(1e12);
 1087 |     }
 1088 | 
 1089 |     /**
```

local_function: updateDebt — `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`; lines 1084–1087

```text
 1084 |     function updateDebt(address _add) internal{
 1085 |         harvestedElePerUser[_add] = balanceOf(_add).mul(harvestedElePerShare).div(1e12);
 1086 |         harvested11nrvPerUser[_add] = balanceOf(_add).mul(harvested11nrvPerShare).div(1e12);
 1087 |     }
```

local_function: claim — `examples/defihacklabs/evaluation/final20/contracts/eleven/raw/ElevenNeverSellVault.sol`; lines 1069–1077

```text
 1069 |     function claim(address _add) internal{
 1070 |         if(totalSupply() != 0) harvest();
 1071 |         if(balanceOf(_add) != 0){
 1072 |             uint eleToPay = balanceOf(_add).mul(harvestedElePerShare).div(1e12).sub(harvestedElePerUser[_add]);
 1073 |             uint nrv11ToPay = balanceOf(_add).mul(harvested11nrvPerShare).div(1e12).sub(harvested11nrvPerUser[_add]);
 1074 |             safeTokenTransfer(ele, _add, eleToPay);
 1075 |             safeTokenTransfer(nrv11, _add, nrv11ToPay);
 1076 |         }
 1077 |     }
```

### Neutral adjudication question

Can a callback through the reported external call observe or change stale state in a way that violates an invariant, considering access restrictions, modifiers, and callable paths?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 17. bearn — unchecked-transfer

Finding ID: `62e7b3ba7e49dfb99841e2603e650dff6bc6782f4e9ee8c52c9d8656800f6dff`  
Impact / confidence: High / Medium  
Contract / function: `BvaultsBank.migrateStrategy(uint256,address)`  
Reported lines: [880]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
BvaultsBank.migrateStrategy(uint256,address) (Implementation.sol#873-883) ignores return value by pool.want.transfer(_newStrategy,_oldWantAmt) (Implementation.sol#880)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/bearn/raw/Implementation.sol`; lines 873–883

```text
  873 |     function migrateStrategy(uint256 _pid, address _newStrategy) public onlyOperator {
  874 |         require(IStrategy(_newStrategy).wantLockedTotal() == 0 && IStrategy(_newStrategy).sharesTotal() == 0, "new strategy not empty");
  875 |         PoolInfo storage pool = poolInfo[_pid];
  876 |         address _oldStrategy = pool.strategy;
  877 |         uint256 _oldSharesTotal = IStrategy(_oldStrategy).sharesTotal();
  878 |         uint256 _oldWantAmt = IStrategy(_oldStrategy).wantLockedTotal();
  879 |         IStrategy(_oldStrategy).withdraw(address(this), _oldWantAmt);
  880 |         pool.want.transfer(_newStrategy, _oldWantAmt);
  881 |         IStrategy(_newStrategy).migrateFrom(_oldStrategy, _oldWantAmt, _oldSharesTotal);
  882 |         pool.strategy = _newStrategy;
  883 |     }
```

local_modifier: onlyOperator — `examples/defihacklabs/evaluation/final20/contracts/bearn/raw/Implementation.sol`; lines 815–818

```text
  815 |     modifier onlyOperator() {
  816 |         require(operator == msg.sender, "BvaultsBank: caller is not the operator");
  817 |         _;
  818 |     }
```

### Neutral adjudication question

Can the referenced token transfer fail or return false while execution proceeds with an inconsistent asset/accounting state, or is successful transfer established by the shown call semantics and guards?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 18. xsurge — divide-before-multiply

Finding ID: `9fb62fea1ce3dc5432b21e883cbe16f925a50ca3d210c0f619a84ddbceb91869`  
Impact / confidence: Medium / Medium  
Contract / function: `SurgeToken.sell(uint256)`  
Reported lines: [585, 588]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
SurgeToken.sell(uint256) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#577-602) performs a multiplication on the result of a division:
	- tokensToSwap = tokenAmount.mul(sellFee).div(10 ** 2) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#585)
	- amountBNB = tokensToSwap.mul(calculatePrice()) (examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol#588)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol`; lines 577–602

```text
  577 |     function sell(uint256 tokenAmount) public nonReentrant returns (bool) {
  578 |         
  579 |         address seller = msg.sender;
  580 |         
  581 |         // make sure seller has this balance
  582 |         require(_balances[seller] >= tokenAmount, 'cannot sell above token amount');
  583 |         
  584 |         // calculate the sell fee from this transaction
  585 |         uint256 tokensToSwap = tokenAmount.mul(sellFee).div(10**2);
  586 |         
  587 |         // how much BNB are these tokens worth?
  588 |         uint256 amountBNB = tokensToSwap.mul(calculatePrice());
  589 |         
  590 |         // send BNB to Seller
  591 |         (bool successful,) = payable(seller).call{value: amountBNB, gas: 40000}(""); 
  592 |         if (successful) {
  593 |             // subtract full amount from sender
  594 |             _balances[seller] = _balances[seller].sub(tokenAmount, 'sender does not have this amount to sell');
  595 |             // if successful, remove tokens from supply
  596 |             _totalSupply = _totalSupply.sub(tokenAmount);
  597 |         } else {
  598 |             revert();
  599 |         }
  600 |         emit Transfer(seller, address(this), tokenAmount);
  601 |         return true;
  602 |     }
```

local_modifier: nonReentrant — `examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol`; lines 20–25

```text
   20 |     modifier nonReentrant() {
   21 |         require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
   22 |         _status = _ENTERED;
   23 |         _;
   24 |         _status = _NOT_ENTERED;
   25 |     }
```

local_function: calculatePrice — `examples/defihacklabs/evaluation/final20/contracts/xsurge/raw/SurgeToken.sol`; lines 605–607

```text
  605 |     function calculatePrice() public view returns (uint256) {
  606 |         return ((address(this).balance).div(_totalSupply));
  607 |     }
```

### Neutral adjudication question

Can the shown division-before-multiplication rounding materially violate the intended calculation for reachable inputs, or is the truncation acceptable under the relevant units and bounds?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 19. burgerswap — unused-return

Finding ID: `92f3e299e4e000f89bb0130a7aa47f367305bf9e4b285d6d30ef81f619a48c0c`  
Impact / confidence: Medium / Medium  
Contract / function: `DemaxPlatform.swapPrecondition(address)`  
Reported lines: [737]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
DemaxPlatform.swapPrecondition(address) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#728-742) ignores return value by (reserveWETH,None) = DemaxSwapLibrary.getReserves(FACTORY,WETH,token) (examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol#737)
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol`; lines 728–742

```text
  728 |     function swapPrecondition(address token) public view returns (bool) {
  729 |         if (token == DGAS || token == WETH) return true;
  730 |         uint256 percent = IDemaxConfig(CONFIG).getConfigValue(ConfigNames.TOKEN_TO_DGAS_PAIR_MIN_PERCENT);
  731 |         if (!existPair(WETH, DGAS)) return false;
  732 |         if (!existPair(DGAS, token)) return false;
  733 |         if (!(IDemaxConfig(CONFIG).checkPair(DGAS, token) && IDemaxConfig(CONFIG).checkPair(WETH, token))) return false;
  734 |         if (!existPair(WETH, token)) return true;
  735 |         if (percent == 0) return true;
  736 |         (uint256 reserveDGAS, ) = DemaxSwapLibrary.getReserves(FACTORY, DGAS, token);
  737 |         (uint256 reserveWETH, ) = DemaxSwapLibrary.getReserves(FACTORY, WETH, token);
  738 |         (uint256 reserveWETH2, uint256 reserveDGAS2) = DemaxSwapLibrary.getReserves(FACTORY, WETH, DGAS);
  739 |         uint256 dgasValue = SafeMath.mul(reserveDGAS, reserveWETH2) / reserveDGAS2;
  740 |         uint256 limitValue = SafeMath.mul(SafeMath.add(dgasValue, reserveWETH), percent) / PERCENT_DENOMINATOR;
  741 |         return dgasValue >= limitValue;
  742 |     }
```

local_function: existPair — `examples/defihacklabs/evaluation/final20/contracts/burgerswap/raw/DemaxPlatform.sol`; lines 976–978

```text
  976 |     function existPair(address tokenA, address tokenB) public view returns (bool) {
  977 |         return IDemaxFactory(FACTORY).getPair(tokenA, tokenB) != address(0);
  978 |     }
```

### Neutral adjudication question

What does each discarded return value signify, and can ignoring it allow an unsuccessful or materially different operation to be treated as successful by this caller?

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.

## 20. spartan — locked-ether

Finding ID: `e8fd05569b88b694d2f90f4cb31d7238e3a16b4bfe1ab3c0143012345d08c63b`  
Impact / confidence: Medium / High  
Contract / function: `Pool.constructor(address,address)`  
Reported lines: [117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267]  
Current label: **UNLABELED**  
Adjudication notes: _not entered_  
Final label: _not assigned_

### Exact Slither claim

```text
Contract locking ether found:
	Contract Pool (Victim.sol#85-344) has payable functions:
	 - Pool.constructor(address,address) (Victim.sol#117-128)
	 - Pool.swapTo(address,address) (Victim.sol#252-267)
	But does not have a function to withdraw the ether
```

### Source evidence

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 114–131

```text
  114 |         return iBASE(BASE).DAO();
  115 |     }
  116 | 
  117 |     constructor (address _base, address _token) public payable {
  118 |         BASE = _base;
  119 |         TOKEN = _token;
  120 | 
  121 |         string memory poolName = "SpartanPoolV1-";
  122 |         string memory poolSymbol = "SPT1-";
  123 |         _name = string(abi.encodePacked(poolName, iBEP20(_token).name()));
  124 |         _symbol = string(abi.encodePacked(poolSymbol, iBEP20(_token).symbol()));
  125 |         
  126 |         decimals = 18;
  127 |         genesis = now;
  128 |     }
  129 | 
  130 |     //========================================iBEP20=========================================//
  131 |     function name() public view override returns (string memory) {
```

target_and_reported_lines_with_surroundings — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 249–270

```text
  249 |         return (outputAmount, fee);
  250 |     }
  251 | 
  252 |     function swapTo(address token, address member) public payable returns (uint outputAmount, uint fee) {
  253 |         require((token == BASE || token == TOKEN), "Must be BASE or TOKEN");
  254 |         address _fromToken; uint _amount;
  255 |         if(token == BASE){
  256 |             _fromToken = TOKEN;
  257 |             _amount = _getAddedTokenAmount();
  258 |             (outputAmount, fee) = _swapTokenToBase(_amount);
  259 |         } else {
  260 |             _fromToken = BASE;
  261 |             _amount = _getAddedBaseAmount();
  262 |             (outputAmount, fee) = _swapBaseToToken(_amount);
  263 |         }
  264 |         emit Swapped(_fromToken, token, _amount, outputAmount, fee, member);
  265 |         iBEP20(token).transfer(member, outputAmount);
  266 |         return (outputAmount, fee);
  267 |     }
  268 | 
  269 |     function _getAddedBaseAmount() internal view returns(uint256 _actual){
  270 |         uint _baseBalance = iBEP20(BASE).balanceOf(address(this)); 
```

local_function: constructor — `examples/defihacklabs/evaluation/final20/contracts/spartan/raw/Victim.sol`; lines 376–380

```text
  376 |     constructor () public payable {
  377 |         BASE = 0xE4Ae305ebE1AbE663f261Bc00534067C80ad677C;
  378 |         WBNB = 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c;
  379 |         DEPLOYER = msg.sender;
  380 |     }
```

### Neutral adjudication question

Can this contract retain ETH received through reachable payable entry points without an authorized usable exit, or do its transfer paths permit the intended funds to leave? Consider the actual contract, not just the constructor.

Context limits: Excerpts are bounded and may be discontinuous; omitted ranges are not evidence of absence. External implementation behavior, reachable inputs and complete cross-function paths must be checked independently before assigning a label.


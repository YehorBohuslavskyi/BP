// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

// Test-only ABI adapters. The victim and token execute their original 0.4.25 bytecode.
interface Vm {
    function readFile(string calldata) external view returns (string memory);
    function parseJsonBytes(string calldata, string calldata) external pure returns (bytes memory);
    function parseJsonUintArray(string calldata, string calldata) external pure returns (uint256[] memory);
    function addr(uint256) external pure returns (address);
    function sign(uint256, bytes32) external pure returns (uint8, bytes32, bytes32);
    function toString(bytes calldata) external pure returns (string memory);
    function prank(address) external;
    function deal(address, uint256) external;
    function warp(uint256) external;
    function expectRevert() external;
    function record() external;
    function accesses(address) external returns (bytes32[] memory, bytes32[] memory);
}
interface Ledger {
    function createChannel(bytes32,address,uint256,address,uint256[2] calldata) external payable;
    function joinChannel(bytes32,uint256[2] calldata) external payable;
    function LCOpenTimeout(bytes32) external;
    function consensusCloseChannel(bytes32,uint256,uint256[4] calldata,string calldata,string calldata) external;
}
interface Token {
    function transfer(address,uint256) external returns (bool);
    function approve(address,uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

// Adversarial external token: documents what a bool-returning token can claim.
// This is NOT a replacement for the victim or for the ordinary-token test paths.
contract PermissiveToken {
    uint256 public calls;
    uint256 public first;
    uint256 public second;
    function transferFrom(address,address,uint256) external pure returns (bool) { return true; }
    function transfer(address,uint256 amount) external returns (bool) {
        if (calls == 0) first = amount; else second = amount;
        calls++;
        return true;
    }
}

contract SpankChainValidation {
    Vm constant vm = Vm(address(uint160(uint256(keccak256('hevm cheat code')))));
    Ledger ledger;
    Token token;
    address libraryAddress;
    address partyA;
    address partyI;
    address attacker;
    uint256 constant KEY_A = 0xA11CE;
    uint256 constant KEY_I = 0xB0B;
    uint256 constant KEY_X = 0xBAD;
    bytes memoryControlCreation;
    bytes32 constant ID = keccak256('validation-channel');

    function deploy(bytes memory creation) internal returns (address deployed) {
        assembly { deployed := create(0, add(creation,32), mload(creation)) }
        require(deployed != address(0), 'deployment failed');
    }

    function setUp() public {
        vm.warp(1_000_000);
        partyA = vm.addr(KEY_A); partyI = vm.addr(KEY_I); attacker = vm.addr(KEY_X);
        vm.deal(partyA, 100 ether); vm.deal(partyI, 100 ether); vm.deal(attacker, 100 ether);
        string memory artifact = vm.readFile('.generated/legacy.json');
        libraryAddress = deploy(vm.parseJsonBytes(artifact, '.libraryCreation'));
        memoryControlCreation = vm.parseJsonBytes(artifact, '.mutabilityControlCreation');
        bytes memory creation = vm.parseJsonBytes(artifact, '.ledgerCreation');
        uint256[] memory offsets = vm.parseJsonUintArray(artifact, '.libraryLinkOffsets');
        bytes20 lib = bytes20(libraryAddress);
        for (uint256 n; n < offsets.length; n++) {
            for (uint256 i; i < 20; i++) creation[offsets[n]+i] = lib[i];
        }
        ledger = Ledger(deploy(creation));
        token = Token(deploy(bytes.concat(vm.parseJsonBytes(artifact, '.tokenCreation'),
            abi.encode(uint256(1_000_000), 'Test', uint8(18), 'TST'))));
        require(token.transfer(partyA, 1000)); require(token.transfer(partyI, 1000));
        vm.prank(partyA); require(token.approve(address(ledger), type(uint256).max));
        vm.prank(partyI); require(token.approve(address(ledger), type(uint256).max));
    }

    function open(bool joined) internal {
        vm.prank(partyA);
        ledger.createChannel{value: 1 ether}(ID, partyI, 10, address(token), [uint256(1 ether),uint256(100)]);
        if (joined) {
            vm.prank(partyI);
            ledger.joinChannel{value: 1 ether}(ID, [uint256(1 ether),uint256(100)]);
        }
    }
    function payouts() internal pure returns (uint256[4] memory) {
        return [uint256(1 ether),uint256(1 ether),uint256(100),uint256(100)];
    }
    function stateHash(uint256[4] memory amounts, address a, address i) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(ID, true, uint256(1), uint256(0), bytes32(0),
            a, i, amounts[0],amounts[1],amounts[2],amounts[3]));
    }
    function signature(uint256 key, bytes32 hash) internal returns (string memory) {
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(key, keccak256(abi.encodePacked('\x19Ethereum Signed Message:\n32',hash)));
        return vm.toString(abi.encodePacked(r,s,v));
    }
    function close(uint256[4] memory amounts) internal {
        bytes32 hash = stateHash(amounts,partyA,partyI);
        ledger.consensusCloseChannel(ID,1,amounts,signature(KEY_A,hash),signature(KEY_I,hash));
    }

    function test_A_validSignaturesAllowRelayerButOnlyPayRecordedParties() public {
        open(true);
        uint256 a = partyA.balance; uint256 i = partyI.balance; uint256 x = attacker.balance;
        uint256[4] memory amounts = payouts(); bytes32 hash = stateHash(amounts,partyA,partyI);
        string memory sigA = signature(KEY_A,hash); string memory sigI = signature(KEY_I,hash);
        vm.prank(attacker); ledger.consensusCloseChannel(ID,1,amounts,sigA,sigI);
        require(partyA.balance == a + 1 ether && partyI.balance == i + 1 ether);
        require(attacker.balance == x && address(ledger).balance == 0);
    }
    function test_A_noSignaturesCannotPay() public {
        open(true); vm.expectRevert();
        ledger.consensusCloseChannel(ID,1,payouts(),'','');
        require(address(ledger).balance == 2 ether);
    }
    function test_A_attackerSignatureCannotReplacePartyI() public {
        open(true); uint256[4] memory amounts = payouts(); bytes32 hash = stateHash(amounts,partyA,partyI);
        string memory a = signature(KEY_A,hash); string memory x = signature(KEY_X,hash);
        vm.expectRevert(); ledger.consensusCloseChannel(ID,1,amounts,a,x);
        require(address(ledger).balance == 2 ether);
    }
    function test_A_substitutedRecipientInSignedMessageFails() public {
        open(true); uint256[4] memory amounts = payouts(); bytes32 hash = stateHash(amounts,partyA,attacker);
        string memory a = signature(KEY_A,hash); string memory i = signature(KEY_I,hash);
        vm.expectRevert(); ledger.consensusCloseChannel(ID,1,amounts,a,i);
        require(address(ledger).balance == 2 ether);
    }
    function test_A_recreateCannotSubstituteRecordedParticipants() public {
        open(true); vm.prank(attacker); vm.expectRevert();
        ledger.createChannel(ID,attacker,0,address(token),[uint256(0),uint256(0)]);
    }
    function test_A_changedConservingBalancesInvalidateSignatures() public {
        open(true); uint256[4] memory amounts = payouts(); bytes32 hash = stateHash(amounts,partyA,partyI);
        string memory a = signature(KEY_A,hash); string memory i = signature(KEY_I,hash);
        amounts[0] = 0; amounts[1] = 2 ether;
        vm.expectRevert(); ledger.consensusCloseChannel(ID,1,amounts,a,i);
        require(address(ledger).balance == 2 ether);
    }
    function test_A_reopenAndReplayOldSignaturesDrainsOtherChannel() public {
        open(true);
        // Another user funds a separate channel; no forced balance/storage edits.
        address victim = vm.addr(0xCAFE); vm.deal(victim, 10 ether);
        vm.prank(victim);
        ledger.createChannel{value:2 ether}(keccak256('other'),partyI,10,address(token),[uint256(2 ether),uint256(0)]);
        // Only ETH is relevant; sufficient real tokens for both payouts are donated.
        require(token.transfer(address(ledger),200));
        uint256[4] memory amounts = payouts(); bytes32 hash = stateHash(amounts,partyA,partyI);
        string memory a = signature(KEY_A,hash); string memory i = signature(KEY_I,hash);
        ledger.consensusCloseChannel(ID,1,amounts,a,i);
        require(address(ledger).balance == 2 ether);
        vm.prank(partyI); ledger.joinChannel(ID,[uint256(0),uint256(0)]);
        uint256 beforeA = partyA.balance; uint256 beforeI = partyI.balance;
        // Same signatures, sequence and balances; no new authorization from A.
        vm.prank(partyI); ledger.consensusCloseChannel(ID,1,amounts,a,i);
        require(address(ledger).balance == 0);
        require(partyA.balance == beforeA + 1 ether && partyI.balance == beforeI + 1 ether);
        vm.warp(block.timestamp + 11);
        vm.prank(victim); vm.expectRevert(); ledger.LCOpenTimeout(keccak256('other'));
    }

    function test_A_immediateReplayWithoutReopeningFails() public {
        open(true); uint256[4] memory amounts = payouts(); bytes32 hash = stateHash(amounts,partyA,partyI);
        string memory a=signature(KEY_A,hash); string memory i=signature(KEY_I,hash);
        ledger.consensusCloseChannel(ID,1,amounts,a,i);
        vm.expectRevert(); ledger.consensusCloseChannel(ID,1,amounts,a,i);
    }

    function test_B_creatorUnopenedAfterDeadlineSucceeds() public {
        open(false); vm.warp(block.timestamp+11); uint256 beforeA=partyA.balance;
        vm.prank(partyA); ledger.LCOpenTimeout(ID);
        require(partyA.balance == beforeA+1 ether && address(ledger).balance == 0);
    }
    function test_B_nonCreatorRejected() public {
        open(false); vm.warp(block.timestamp+11); vm.prank(attacker); vm.expectRevert();
        ledger.LCOpenTimeout(ID); require(address(ledger).balance == 1 ether);
    }
    function test_B_partyIRejected() public {
        open(false); vm.warp(block.timestamp+11); vm.prank(partyI); vm.expectRevert(); ledger.LCOpenTimeout(ID);
    }
    function test_B_creatorJoinedRejected() public {
        open(true); vm.warp(block.timestamp+11); vm.prank(partyA); vm.expectRevert(); ledger.LCOpenTimeout(ID);
    }
    function test_B_beforeDeadlineRejected() public {
        open(false); vm.prank(partyA); vm.expectRevert(); ledger.LCOpenTimeout(ID);
    }
    function test_B_relaxedGuardTruthTable() public pure {
        // Predicate analysis only; never used as substitute victim code.
        for (uint256 creator; creator<2; creator++) for (uint256 opened; opened<2; opened++) {
            bool original = creator==1 && opened==0;
            bool relaxed = creator==1 || opened==0;
            if (creator==0 && opened==0) require(!original && relaxed);
            if (creator==1 && opened==1) require(!original && relaxed);
            require(original == (creator==1 && !(opened==1)));
        }
    }

    function test_C_equalPayoutsConserveActualEthAndTokens() public {
        open(true); uint256 a=token.balanceOf(partyA); uint256 i=token.balanceOf(partyI);
        uint256 ethA=partyA.balance; uint256 ethI=partyI.balance;
        close(payouts());
        require(token.balanceOf(partyA)==a+100 && token.balanceOf(partyI)==i+100);
        require(token.balanceOf(address(ledger))==0 && address(ledger).balance==0);
        require(partyA.balance==ethA+1 ether && partyI.balance==ethI+1 ether);
    }
    function mismatch(uint256 index, bool greater) internal {
        open(true); uint256[4] memory amounts=payouts();
        if(greater) amounts[index]++; else amounts[index]--;
        // Sign the mismatched values correctly, isolating the conservation check.
        bytes32 hash=stateHash(amounts,partyA,partyI);
        string memory a=signature(KEY_A,hash); string memory i=signature(KEY_I,hash);
        vm.expectRevert(); ledger.consensusCloseChannel(ID,1,amounts,a,i);
        require(address(ledger).balance==2 ether && token.balanceOf(address(ledger))==200);
    }
    function test_C_tokenSumBelowRejectedWithValidSignatures() public { mismatch(2,false); }
    function test_C_tokenSumAboveRejectedWithValidSignatures() public { mismatch(2,true); }
    function test_C_ethSumBelowRejectedWithValidSignatures() public { mismatch(0,false); }
    function test_C_ethSumAboveRejectedWithValidSignatures() public { mismatch(0,true); }
    function testFuzz_C_ordinaryTokenConservingSplits(uint8 split) public {
        open(true); uint256 n=uint256(split)%201; uint256[4] memory amounts=payouts();
        amounts[2]=n; amounts[3]=200-n; close(amounts);
        require(token.balanceOf(partyA)==900+n && token.balanceOf(partyI)==900+200-n);
    }
    function test_C_unrelatedFundsDoNotBlockAccountedEquality() public {
        open(true);
        vm.prank(attacker);
        ledger.createChannel{value:2 ether}(keccak256('other'),partyI,10,address(token),[uint256(2 ether),uint256(0)]);
        require(token.transfer(address(ledger),17));
        close(payouts());
        require(address(ledger).balance==2 ether && token.balanceOf(address(ledger))==17);
    }

    function test_C_uint256WrapCannotDrainOrdinaryToken() public {
        open(true);
        uint256[4] memory amounts=[uint256(1 ether),uint256(1 ether),type(uint256).max,uint256(201)];
        bytes32 hash=stateHash(amounts,partyA,partyI);
        string memory a=signature(KEY_A,hash); string memory i=signature(KEY_I,hash);
        vm.expectRevert(); ledger.consensusCloseChannel(ID,1,amounts,a,i);
        require(token.balanceOf(address(ledger))==200 && address(ledger).balance==2 ether);
    }

    function test_C_uint256WrapPassesEqualityWithPermissiveToken() public {
        PermissiveToken mock=new PermissiveToken();
        vm.prank(partyA); ledger.createChannel(ID,partyI,10,address(mock),[uint256(0),uint256(100)]);
        vm.prank(partyI); ledger.joinChannel(ID,[uint256(0),uint256(100)]);
        uint256[4] memory amounts=[uint256(0),uint256(0),type(uint256).max,uint256(201)];
        close(amounts);
        require(mock.first()==type(uint256).max && mock.second()==201);
        // Mathematical sum is 2**256+200; old compiler's uint256 sum is 200.
    }

    function recover(bytes32 hash,string memory sig,bool staticMode) internal returns(address) {
        bytes memory data=abi.encodeWithSignature('recoverSigner(bytes32,string)',hash,sig);
        bool ok; bytes memory out;
        if(staticMode) (ok,out)=libraryAddress.staticcall(data); else (ok,out)=libraryAddress.call(data);
        require(ok,'recover reverted'); return abi.decode(out,(address));
    }
    function test_D_validSignatureStaticcallAndCallAgreeWithoutStorageAccess() public {
        bytes32 hash=keccak256('message'); string memory sig=signature(KEY_A,hash);
        vm.record(); require(recover(hash,sig,true)==partyA); require(recover(hash,sig,false)==partyA);
        (bytes32[] memory reads,bytes32[] memory writes)=vm.accesses(libraryAddress);
        require(reads.length==0 && writes.length==0);
    }
    function test_D_shortSignatureReturnsZeroUnderStaticcall() public {
        require(recover(keccak256('message'),'0x1234',true)==address(0));
    }
    function test_D_invalidVReturnsZeroUnderStaticcall() public {
        bytes32 hash=keccak256('message'); bytes memory sig=bytes(signature(KEY_A,hash));
        sig[130]='f'; sig[131]='f'; require(recover(hash,string(sig),true)==address(0));
    }
    function test_D_zeroHashRevertsForInputValidation() public {
        bytes memory data=abi.encodeWithSignature('recoverSigner(bytes32,string)',bytes32(0),'');
        (bool ok,)=libraryAddress.staticcall(data); require(!ok);
    }
    function test_D_historicalUnsafeViewControlWritesOnCallButFailsStaticcall() public {
        address control=deploy(memoryControlCreation);
        bytes memory data=abi.encodeWithSignature('mislabeled()');
        (bool staticOk,)=control.staticcall{gas:100_000}(data); require(!staticOk);
        vm.record(); (bool callOk,)=control.call(data); require(callOk);
        (,bytes32[] memory writes)=vm.accesses(control); require(writes.length>0);
    }

    function testFuzz_D_recoveryRemainsStaticCompatible(bytes32 hash) public {
        if(hash==bytes32(0)) return;
        require(recover(hash,signature(KEY_A,hash),true)==partyA);
    }
}

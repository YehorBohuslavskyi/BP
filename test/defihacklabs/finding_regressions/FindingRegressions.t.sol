// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
interface VmEvidence {
    function readFile(string calldata) external view returns(string memory);
    function parseJsonBytes(string calldata,string calldata) external pure returns(bytes memory);
    function parseJsonUintArray(string calldata,string calldata) external pure returns(uint256[] memory);
    function deal(address,uint256) external;
}
interface ProofProbe { function check(bytes32,bytes calldata,bytes32) external pure returns(bool); }
// Constructor dependency supplies metadata only. No victim call behavior is mocked.
contract MetadataToken {
    function name() external pure returns(string memory) {return 'Metadata';}
    function symbol() external pure returns(string memory) {return 'META';}
}
contract FindingRegressions {
    VmEvidence constant vm=VmEvidence(address(uint160(uint256(keccak256('hevm cheat code')))));
    ProofProbe proof;
    bytes poolCreation;
    function deploy(bytes memory code,uint256 value) internal returns(address deployed) {
        assembly {deployed:=create(value,add(code,32),mload(code))}
        require(deployed!=address(0),'deployment failed');
    }
    function setUp() public {
        string memory data=vm.readFile('.generated/contracts.json');
        address lib=deploy(vm.parseJsonBytes(data,'.library'),0);
        bytes memory code=vm.parseJsonBytes(data,'.proof');
        uint256[] memory offsets=vm.parseJsonUintArray(data,'.offsets');
        for(uint256 j;j<offsets.length;j++) for(uint256 k;k<20;k++) code[offsets[j]+k]=bytes20(lib)[k];
        proof=ProofProbe(deploy(code,0));poolCreation=vm.parseJsonBytes(data,'.pool');
        vm.deal(address(this),10 ether);
    }
    function test_FP_emptyProofRequiresExactRoot() public view {
        bytes32 leaf=keccak256('leaf');
        require(proof.check(leaf,'',leaf));
        require(!proof.check(leaf,'',bytes32(uint256(leaf)^1)));
    }
    function rootFor(bytes32 a,bytes32 b) internal pure returns(bytes32) {
        return a<b ? keccak256(abi.encodePacked(a,b)):keccak256(abi.encodePacked(b,a));
    }
    function test_FP_sortedSiblingProofAcceptsOnlyReconstructedRoot() public view {
        bytes32 leaf=keccak256('leaf');bytes32 sibling=keccak256('sibling');bytes32 root=rootFor(leaf,sibling);
        // Existing proof format reserves the first 32 data bytes before sibling entries.
        bytes memory evidence=abi.encodePacked(bytes32(0),sibling);
        require(proof.check(leaf,evidence,root));
        require(!proof.check(leaf,evidence,bytes32(uint256(root)^1)));
        require(!proof.check(leaf,abi.encodePacked(bytes32(0),bytes32(uint256(sibling)^1)),root));
    }
    function testFuzz_FP_exactHashRootIsRequired(bytes32 leaf,bytes32 sibling) public view {
        bytes32 root=rootFor(leaf,sibling);bytes memory evidence=abi.encodePacked(bytes32(0),sibling);
        require(proof.check(leaf,evidence,root));
        require(!proof.check(leaf,evidence,bytes32(uint256(root)^1)));
    }
    function test_TP_poolAcceptsNativeValueDespiteTokenAccounting() public {
        address metadata=address(new MetadataToken());
        address pool=deploy(bytes.concat(poolCreation,abi.encode(metadata,metadata)),1 ether);
        require(pool.balance==1 ether,'payable constructor must accept value');
        // Getter remains usable; it does not expose a native-value exit.
        (bool ok,bytes memory out)=pool.staticcall(abi.encodeWithSignature('BASE()'));
        require(ok && abi.decode(out,(address))==metadata);
        require(pool.balance==1 ether);
    }
    function test_TP_poolDoesNotHaveConventionalNativeExitOrFallback() public {
        address metadata=address(new MetadataToken());
        address pool=deploy(bytes.concat(poolCreation,abi.encode(metadata,metadata)),1 ether);
        (bool withdrawOk,)=pool.call(abi.encodeWithSignature('withdraw()'));
        (bool rescueOk,)=pool.call(abi.encodeWithSignature('rescueETH(address)',address(this)));
        (bool fallbackOk,)=pool.call('');
        require(!withdrawOk && !rescueOk && !fallbackOk);
        require(pool.balance==1 ether);
        // The all-path conclusion also requires manual source review; selector tests alone are not a proof.
    }
}

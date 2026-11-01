// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;
interface VmLocal {
    function readFile(string calldata) external view returns(string memory);
    function parseJsonBytes(string calldata,string calldata) external pure returns(bytes memory);
    function deal(address,uint256) external;
    function etch(address,bytes calldata) external;
    function prank(address) external;
    function expectCall(address,uint256,bytes calldata) external;
}
interface PaymentProbeABI {
    function configureWrapped(address) external;
    function pay(address,uint256) external;
    function continued() external view returns(bool);
}
interface RewardProbeABI {
    function seed(address,uint256,uint256,address,address) external;
    function claimRewards() external;
    function pendingEleven(address) external view returns(uint256);
    function harvestedElePerUser(address) external view returns(uint256);
}
contract LocalWrappedNative {
    uint256 public withdrawals;
    function withdraw(uint256 amount) external {
        withdrawals++;
        (bool sent,)=payable(msg.sender).call{value:amount}("");
        require(sent,'fixture withdrawal delivery failed');
    }
    receive() external payable {}
}
contract RejectNative {
    error LocalPaymentRejected();
    receive() external payable { revert LocalPaymentRejected(); }
}
contract AcceptNative { receive() external payable {} }
contract LocalERC20 {
    mapping(address=>uint256) public balanceOf;
    bool public returnsFalse;
    uint256 public transferCalls;
    uint256 public lastAmount;
    address public lastRecipient;
    address public lastSender;
    bool public lastReturn;
    function setFailure(bool fail) external { returnsFalse=fail; }
    function mint(address who,uint256 amount) external { balanceOf[who]+=amount; }
    function allowance(address,address) external pure returns(uint256) {return 0;}
    function approve(address,uint256) external pure returns(bool) {return true;}
    function transfer(address to,uint256 amount) external returns(bool) {
        transferCalls++;lastAmount=amount;lastRecipient=to;lastSender=msg.sender;
        if(returnsFalse) { lastReturn=false;return false; }
        require(balanceOf[msg.sender]>=amount,'fixture insufficient balance');
        balanceOf[msg.sender]-=amount;balanceOf[to]+=amount;
        lastReturn=true;return true;
    }
}
contract LocalHarvestDependencies {
    function deposit(uint256,uint256) external {}
    function chargeFees(address,address) external {}
    function convert(address) external {}
    function pendingEleven(uint256,address) external pure returns(uint256) { return 0; }
}
contract PaymentAndRewardRegressions {
    VmLocal constant vm=VmLocal(address(uint160(uint256(keccak256('hevm cheat code')))));
    address constant UNDERLYING=0x401479091d0F7b8AE437Ee8B054575cd33ea72Bd;
    address constant ELE=0xAcD7B3D9c10e97d0efA418903C0c7669E702E4C0;
    address constant NRV=0x42F6f551ae042cBe50C739158b4f0CAC0Edb9096;
    address constant NRV11=0x54f4D5dd6164B99603E77C8E13FFC3B239F63147;
    address constant CHEF=0x2EBe8CDbCB5fB8564bC45999DAb8DA264E31f24E;
    address constant ELECHEF=0x1ac6C0B955B6D7ACb61c9Bdf3EE98E0689e07B8A;
    address constant USER=address(0xA11CE);
    PaymentProbeABI router;
    RewardProbeABI vault;
    LocalWrappedNative wrapped;
    function deploy(bytes memory code) internal returns(address deployed) {
        assembly {deployed:=create(0,add(code,32),mload(code))}
        require(deployed!=address(0),'fixture deployment failed');
    }
    function setUp() public {
        string memory data=vm.readFile('.generated/contracts.json');
        router=PaymentProbeABI(deploy(vm.parseJsonBytes(data,'.payment')));
        wrapped=new LocalWrappedNative();vm.deal(address(wrapped),10 ether);
        router.configureWrapped(address(wrapped));
        LocalERC20 tokenTemplate=new LocalERC20();
        vm.etch(UNDERLYING,address(tokenTemplate).code);
        vm.etch(ELE,address(tokenTemplate).code);
        vm.etch(NRV,address(tokenTemplate).code);
        vm.etch(NRV11,address(tokenTemplate).code);
        LocalHarvestDependencies dependency=new LocalHarvestDependencies();
        vm.etch(CHEF,address(dependency).code);vm.etch(ELECHEF,address(dependency).code);
        vault=RewardProbeABI(deploy(vm.parseJsonBytes(data,'.reward')));
        vault.seed(USER,10,5e12,address(dependency),address(dependency));
        LocalERC20(ELE).mint(address(vault),100);
    }
    function test_A_rejectedPayoutContinuesAndLeavesValueInRouter() public {
        RejectNative recipient=new RejectNative();
        uint256 beforeRecipient=address(recipient).balance;
        uint256 beforeRouter=address(router).balance;
        vm.expectCall(address(recipient),1 ether,bytes(''));
        router.pay(address(recipient),1 ether);
        require(wrapped.withdrawals()==1,'withdrawal did not occur');
        require(address(wrapped).balance==9 ether,'wrapped withdrawal did not succeed');
        require(router.continued(),'execution did not continue after rejected call');
        require(address(recipient).balance==beforeRecipient,'recipient was paid');
        require(address(router).balance==beforeRouter+1 ether,'undelivered value not retained');
        // The expected call reached immutable receive() code that always reverts;
        // therefore the original low-level CALL returned false (also visible in the trace).
    }
    function test_A_successfulPayoutControlDeliversValue() public {
        AcceptNative recipient=new AcceptNative();
        router.pay(address(recipient),1 ether);
        require(wrapped.withdrawals()==1 && router.continued());
        require(address(recipient).balance==1 ether && address(router).balance==0);
    }
    function test_B_falseTransferAdvancesDebtWithoutPayment() public {
        LocalERC20 reward=LocalERC20(ELE);reward.setFailure(true);
        uint256 pendingBefore=vault.pendingEleven(USER);
        uint256 debtBefore=vault.harvestedElePerUser(USER);
        uint256 balanceBefore=reward.balanceOf(USER);
        require(pendingBefore==50 && debtBefore==0,'no nonzero initial entitlement');
        require(reward.balanceOf(address(vault))==100,'exact else branch not funded');
        vm.prank(USER);vault.claimRewards();
        require(reward.transferCalls()==1 && !reward.lastReturn(),'false transfer not executed');
        require(reward.lastSender()==address(vault) && reward.lastRecipient()==USER && reward.lastAmount()==50);
        require(reward.balanceOf(USER)==balanceBefore && reward.balanceOf(address(vault))==100,'balances moved');
        require(vault.harvestedElePerUser(USER)==50,'debt not updated');
        require(vault.pendingEleven(USER)==0,'unpaid entitlement not eliminated');
        // Successful return here establishes that original claimRewards did not revert.
    }
    function test_B_successfulTransferControlPaysBeforeDebtUpdate() public {
        LocalERC20 reward=LocalERC20(ELE);require(vault.pendingEleven(USER)==50);
        vm.prank(USER);vault.claimRewards();
        require(reward.lastReturn() && reward.lastAmount()==50);
        require(reward.balanceOf(USER)==50 && reward.balanceOf(address(vault))==50);
        require(vault.harvestedElePerUser(USER)==50 && vault.pendingEleven(USER)==0);
    }
}

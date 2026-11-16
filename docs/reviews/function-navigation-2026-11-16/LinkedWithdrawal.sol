pragma solidity 0.8.24;

contract LinkedWithdrawal {
    mapping(address => uint256) private balances;
    bool private entered;

    modifier guarded() {
        require(!entered, "busy");
        entered = true;
        _;
        entered = false;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        withdrawFor(payable(msg.sender));
    }

    function guardedWithdraw() external guarded {
        withdrawFor(payable(msg.sender));
    }

    function withdrawFor(address payable account) internal {
        uint256 amount = balances[account];
        require(amount > 0, "empty");
        sendFunds(account, amount);
        balances[account] = 0;
    }

    function sendFunds(address payable account, uint256 amount) internal {
        (bool success,) = account.call{value: amount}("");
        require(success, "transfer failed");
    }
}

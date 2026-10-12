pragma solidity 0.8.24;

contract AccessDemo {
    address public owner;
    uint public value;

    constructor(){
        owner = msg.sender;
    }

    modifier onlyOwner(){
        require(msg.sender == owner, "Not Owner");
        _;
    }

    function setValue(uint256 newValue) external onlyOwner {
        value = newValue;
    }

    function getValue() external view returns(uint256){
        return value;
    }
}
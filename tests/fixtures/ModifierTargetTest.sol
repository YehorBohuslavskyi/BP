pragma solidity ^0.8.24;

contract ModifierTargetTest {
    address public owner;
    enum Role { None, Member, Manager }
    mapping(address => Role) public roles;

    modifier onlyManager() {
        require(
            roles[msg.sender] == Role.Manager || msg.sender == owner,
            "not manager"
        );
        _;
    }

    function privilegedAction() external onlyManager {}

    function setRole(address member, Role role) external {
        require(msg.sender == owner);
        roles[member] = role;
    }

    constructor() { owner = msg.sender; }
}

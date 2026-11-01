// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title LargeTreasury
 * @notice Large treasury and organization-management contract used for
 *         scalability experiments with static analysis and selective-context
 *         LLM verification.
 *
 * The contract intentionally contains a mixture of ordinary business logic,
 * defensive patterns, legacy compatibility code, and risky patterns.
 * Nothing in the source labels a particular function as vulnerable.
 */
contract LargeTreasury {
    // =====================================================================
    // Types
    // =====================================================================

    enum ProposalState {
        Pending,
        Approved,
        Executed,
        Cancelled,
        Expired
    }

    enum PaymentState {
        Scheduled,
        Claimed,
        Cancelled
    }

    enum BudgetState {
        Active,
        Frozen,
        Closed
    }

    enum Role {
        None,
        Member,
        Manager,
        Auditor
    }

    struct Member {
        bool active;
        Role role;
        uint96 spendingLimit;
        uint64 joinedAt;
        uint64 lastActivityAt;
        uint256 totalDeposited;
        uint256 totalReimbursed;
        uint256 totalSpent;
    }

    struct Proposal {
        address proposer;
        address payable recipient;
        uint256 amount;
        bytes data;
        string description;
        uint64 createdAt;
        uint64 executeAfter;
        uint64 expiresAt;
        uint32 approvals;
        ProposalState state;
    }

    struct ScheduledPayment {
        address payable recipient;
        uint256 amount;
        uint64 releaseTime;
        PaymentState state;
        string memo;
    }

    struct RecurringPayment {
        address payable recipient;
        uint256 amount;
        uint64 interval;
        uint64 nextExecution;
        uint32 remainingExecutions;
        bool active;
        string memo;
    }

    struct Budget {
        string name;
        uint256 limit;
        uint256 spent;
        uint64 periodStart;
        uint64 periodEnd;
        BudgetState state;
    }

    struct Invoice {
        address vendor;
        uint256 amount;
        bytes32 documentHash;
        uint64 submittedAt;
        uint64 dueAt;
        bool approved;
        bool paid;
        string invoiceReference;
    }

    struct AuditEntry {
        bytes32 action;
        address actor;
        address target;
        uint256 amount;
        uint64 timestamp;
        bytes32 metadataHash;
    }

    struct Allowance {
        uint256 limit;
        uint256 spent;
        uint64 periodStart;
        uint64 periodEnd;
    }

    // =====================================================================
    // State
    // =====================================================================

    address public owner;
    address public pendingOwner;
    address public guardian;
    address public auditor;

    bool public paused;
    bool public emergencyMode;

    uint256 public proposalCount;
    uint256 public scheduledPaymentCount;
    uint256 public recurringPaymentCount;
    uint256 public budgetCount;
    uint256 public invoiceCount;
    uint256 public auditEntryCount;

    uint256 public totalManaged;
    uint256 public totalDeposits;
    uint256 public totalWithdrawals;
    uint256 public totalExternalValue;
    uint256 public dailySpent;
    uint256 public lastSpendDay;

    uint256 public constant MIN_DELAY = 1 hours;
    uint256 public constant MAX_PROPOSAL_DELAY = 30 days;
    uint256 public constant MAX_BATCH_SIZE = 40;
    uint256 public constant MAX_DESCRIPTION_LENGTH = 512;
    uint256 public constant DEFAULT_INVOICE_PERIOD = 14 days;

    mapping(address => Member) public members;
    mapping(uint256 => Proposal) private proposals;
    mapping(uint256 => ScheduledPayment) private scheduledPayments;
    mapping(uint256 => RecurringPayment) private recurringPayments;
    mapping(uint256 => Budget) private budgets;
    mapping(uint256 => Invoice) private invoices;
    mapping(uint256 => AuditEntry) private auditEntries;

    mapping(uint256 => mapping(address => bool)) public proposalApprovedBy;
    mapping(address => uint256) public credits;
    mapping(address => uint256) public lastWithdrawal;
    mapping(address => Allowance) private allowances;
    mapping(address => mapping(bytes32 => bool)) public permissions;
    mapping(bytes32 => bool) public processedOperations;
    mapping(bytes32 => uint256) public accountingTotals;
    mapping(address => uint256) public vendorPaidTotal;
    mapping(address => uint256) public departmentSpent;
    mapping(address => uint256) public departmentLimits;

    address[] private memberList;
    address[] private vendorList;
    bytes32[] private accountingKeys;

    // =====================================================================
    // Events
    // =====================================================================

    event OwnershipTransferStarted(address indexed currentOwner, address indexed pendingOwner);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event GuardianChanged(address indexed previousGuardian, address indexed newGuardian);
    event AuditorChanged(address indexed previousAuditor, address indexed newAuditor);
    event Paused(address indexed account);
    event Unpaused(address indexed account);
    event EmergencyModeChanged(bool enabled);

    event MemberAdded(address indexed member, Role role, uint256 spendingLimit);
    event MemberRemoved(address indexed member);
    event MemberRoleUpdated(address indexed member, Role previousRole, Role newRole);
    event SpendingLimitUpdated(address indexed member, uint256 oldLimit, uint256 newLimit);
    event PermissionUpdated(address indexed account, bytes32 indexed permission, bool allowed);

    event Deposit(address indexed sender, address indexed beneficiary, uint256 amount);
    event CreditAdded(address indexed account, uint256 amount, string reason);
    event CreditWithdrawn(address indexed account, uint256 amount);

    event ProposalCreated(
        uint256 indexed proposalId,
        address indexed proposer,
        address indexed recipient,
        uint256 amount,
        uint256 executeAfter
    );
    event ProposalApproved(uint256 indexed proposalId, address indexed approver);
    event ProposalCancelled(uint256 indexed proposalId);
    event ProposalExecuted(uint256 indexed proposalId, address indexed recipient, uint256 amount);

    event ScheduledPaymentCreated(
        uint256 indexed paymentId,
        address indexed recipient,
        uint256 amount,
        uint256 releaseTime
    );
    event ScheduledPaymentClaimed(uint256 indexed paymentId, address indexed recipient, uint256 amount);
    event ScheduledPaymentCancelled(uint256 indexed paymentId);

    event RecurringPaymentCreated(
        uint256 indexed paymentId,
        address indexed recipient,
        uint256 amount,
        uint256 interval,
        uint256 executions
    );
    event RecurringPaymentExecuted(uint256 indexed paymentId, uint256 amount, uint256 nextExecution);
    event RecurringPaymentCancelled(uint256 indexed paymentId);

    event BudgetCreated(uint256 indexed budgetId, string name, uint256 limit);
    event BudgetSpent(uint256 indexed budgetId, address indexed recipient, uint256 amount);
    event BudgetStateChanged(uint256 indexed budgetId, BudgetState state);

    event InvoiceSubmitted(uint256 indexed invoiceId, address indexed vendor, uint256 amount);
    event InvoiceApproved(uint256 indexed invoiceId);
    event InvoicePaid(uint256 indexed invoiceId, address indexed vendor, uint256 amount);

    event ExternalCall(address indexed target, uint256 value, bytes data);
    event EmergencyWithdrawal(address indexed recipient, uint256 amount);
    event AllowanceConfigured(address indexed account, uint256 limit, uint256 periodStart, uint256 periodEnd);
    event AllowanceSpent(address indexed account, address indexed recipient, uint256 amount);
    event AccountingRecorded(bytes32 indexed key, uint256 amount);
    event AuditLogged(uint256 indexed entryId, bytes32 indexed action, address indexed actor);

    // =====================================================================
    // Modifiers
    // =====================================================================

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyGuardian() {
        require(msg.sender == guardian, "not guardian");
        _;
    }

    modifier onlyAuditor() {
        require(msg.sender == auditor, "not auditor");
        _;
    }

    modifier onlyMember() {
        require(members[msg.sender].active, "not member");
        _;
    }

    modifier onlyManager() {
        require(
            members[msg.sender].active &&
                (members[msg.sender].role == Role.Manager || msg.sender == owner),
            "not manager"
        );
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "paused");
        _;
    }

    modifier proposalExists(uint256 proposalId) {
        require(proposalId > 0 && proposalId <= proposalCount, "unknown proposal");
        _;
    }

    modifier budgetExists(uint256 budgetId) {
        require(budgetId > 0 && budgetId <= budgetCount, "unknown budget");
        _;
    }

    modifier invoiceExists(uint256 invoiceId) {
        require(invoiceId > 0 && invoiceId <= invoiceCount, "unknown invoice");
        _;
    }

    // =====================================================================
    // Constructor / receive
    // =====================================================================

    constructor(address initialGuardian, address initialAuditor) payable {
        require(initialGuardian != address(0), "zero guardian");
        require(initialAuditor != address(0), "zero auditor");

        owner = msg.sender;
        guardian = initialGuardian;
        auditor = initialAuditor;

        members[msg.sender] = Member({
            active: true,
            role: Role.Manager,
            spendingLimit: type(uint96).max,
            joinedAt: uint64(block.timestamp),
            lastActivityAt: uint64(block.timestamp),
            totalDeposited: msg.value,
            totalReimbursed: 0,
            totalSpent: 0
        });

        memberList.push(msg.sender);

        if (msg.value > 0) {
            totalManaged = msg.value;
            totalDeposits = msg.value;
            emit Deposit(msg.sender, msg.sender, msg.value);
        }
    }

    receive() external payable {
        _recordDeposit(msg.sender, msg.sender, msg.value);
    }

    fallback() external payable {
        if (msg.value > 0) {
            _recordDeposit(msg.sender, msg.sender, msg.value);
        }
    }

    // =====================================================================
    // Ownership and administration
    // =====================================================================

    function startOwnershipTransfer(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero owner");
        pendingOwner = newOwner;
        emit OwnershipTransferStarted(owner, newOwner);
    }

    function acceptOwnership() external {
        require(msg.sender == pendingOwner, "not pending owner");

        address previousOwner = owner;
        owner = msg.sender;
        pendingOwner = address(0);

        if (!members[msg.sender].active) {
            members[msg.sender] = Member({
                active: true,
                role: Role.Manager,
                spendingLimit: type(uint96).max,
                joinedAt: uint64(block.timestamp),
                lastActivityAt: uint64(block.timestamp),
                totalDeposited: 0,
                totalReimbursed: 0,
                totalSpent: 0
            });
            memberList.push(msg.sender);
        }

        emit OwnershipTransferred(previousOwner, msg.sender);
    }

    function setGuardian(address newGuardian) external onlyOwner {
        require(newGuardian != address(0), "zero guardian");
        address previousGuardian = guardian;
        guardian = newGuardian;
        emit GuardianChanged(previousGuardian, newGuardian);
    }

    function setAuditor(address newAuditor) external onlyOwner {
        require(newAuditor != address(0), "zero auditor");
        address previousAuditor = auditor;
        auditor = newAuditor;
        emit AuditorChanged(previousAuditor, newAuditor);
    }

    function pause() external onlyGuardian {
        paused = true;
        emit Paused(msg.sender);
    }

    function unpause() external onlyOwner {
        paused = false;
        emit Unpaused(msg.sender);
    }

    function setEmergencyMode(bool enabled) external {
        require(msg.sender == owner || msg.sender == guardian, "not authorized");
        emergencyMode = enabled;
        emit EmergencyModeChanged(enabled);
    }

    function legacySetGuardian(address newGuardian) external {
        require(tx.origin == owner, "not authorized");
        require(newGuardian != address(0), "zero guardian");

        address previousGuardian = guardian;
        guardian = newGuardian;

        emit GuardianChanged(previousGuardian, newGuardian);
    }

    // =====================================================================
    // Member and role management
    // =====================================================================

    function addMember(address account, Role role, uint96 spendingLimit) external onlyOwner {
        require(account != address(0), "zero member");
        require(!members[account].active, "already member");
        require(role != Role.None, "invalid role");

        members[account] = Member({
            active: true,
            role: role,
            spendingLimit: spendingLimit,
            joinedAt: uint64(block.timestamp),
            lastActivityAt: uint64(block.timestamp),
            totalDeposited: 0,
            totalReimbursed: 0,
            totalSpent: 0
        });

        memberList.push(account);
        emit MemberAdded(account, role, spendingLimit);
    }

    function removeMember(address account) external onlyOwner {
        require(members[account].active, "not active");
        require(account != owner, "owner");
        members[account].active = false;
        members[account].role = Role.None;
        emit MemberRemoved(account);
    }

    function updateMemberRole(address account, Role newRole) external onlyOwner {
        require(members[account].active, "not active");
        require(newRole != Role.None, "invalid role");

        Role previousRole = members[account].role;
        members[account].role = newRole;
        members[account].lastActivityAt = uint64(block.timestamp);

        emit MemberRoleUpdated(account, previousRole, newRole);
    }

    function setSpendingLimit(address account, uint96 newLimit) external onlyOwner {
        require(members[account].active, "not active");

        uint256 oldLimit = members[account].spendingLimit;
        members[account].spendingLimit = newLimit;

        emit SpendingLimitUpdated(account, oldLimit, newLimit);
    }

    function setPermission(
        address account,
        bytes32 permission,
        bool allowed
    ) external onlyOwner {
        require(account != address(0), "zero account");
        permissions[account][permission] = allowed;
        emit PermissionUpdated(account, permission, allowed);
    }

    function hasPermission(address account, bytes32 permission) external view returns (bool) {
        return permissions[account][permission];
    }

    function getMemberCount() external view returns (uint256) {
        return memberList.length;
    }

    function getMemberAt(uint256 index) external view returns (address) {
        require(index < memberList.length, "index");
        return memberList[index];
    }

    function getMemberSummary(
        address account
    )
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 totalDeposited_,
            uint256 totalReimbursed_,
            uint256 totalSpent_
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    // =====================================================================
    // Deposits and credits
    // =====================================================================

    function deposit() external payable whenNotPaused {
        _recordDeposit(msg.sender, msg.sender, msg.value);
    }

    function depositFor(address beneficiary) external payable whenNotPaused {
        require(beneficiary != address(0), "zero beneficiary");
        _recordDeposit(msg.sender, beneficiary, msg.value);
    }

    function managerDepositFor(address beneficiary) external payable onlyManager whenNotPaused {
        require(beneficiary != address(0), "zero beneficiary");
        _recordDeposit(msg.sender, beneficiary, msg.value);
    }

    function addCredit(
        address account,
        uint256 amount,
        string calldata reason
    ) external onlyManager {
        require(account != address(0), "zero account");
        require(amount > 0, "zero amount");

        credits[account] += amount;
        emit CreditAdded(account, amount, reason);
    }

    function reduceCredit(address account, uint256 amount) external onlyOwner {
        require(amount > 0, "zero amount");
        require(credits[account] >= amount, "insufficient credit");
        credits[account] -= amount;
    }

    function withdrawCredit(uint256 amount) external whenNotPaused {
        require(amount > 0, "zero amount");
        require(credits[msg.sender] >= amount, "insufficient credit");
        require(address(this).balance >= amount, "insufficient treasury");

        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "transfer failed");

        credits[msg.sender] -= amount;
        totalManaged -= amount;
        totalWithdrawals += amount;
        lastWithdrawal[msg.sender] = block.timestamp;

        emit CreditWithdrawn(msg.sender, amount);
    }

    function withdrawCreditSafe(uint256 amount) external whenNotPaused {
        require(amount > 0, "zero amount");
        require(credits[msg.sender] >= amount, "insufficient credit");
        require(address(this).balance >= amount, "insufficient treasury");

        credits[msg.sender] -= amount;
        totalManaged -= amount;
        totalWithdrawals += amount;
        lastWithdrawal[msg.sender] = block.timestamp;

        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "transfer failed");

        emit CreditWithdrawn(msg.sender, amount);
    }

    function transferCredit(address recipient, uint256 amount) external whenNotPaused {
        require(recipient != address(0), "zero recipient");
        require(amount > 0, "zero amount");
        require(credits[msg.sender] >= amount, "insufficient credit");

        credits[msg.sender] -= amount;
        credits[recipient] += amount;
    }

    function availableCredit(address account) external view returns (uint256) {
        return credits[account];
    }

    // =====================================================================
    // Proposal system
    // =====================================================================

    function createProposal(
        address payable recipient,
        uint256 amount,
        bytes calldata data,
        string calldata description,
        uint64 delay,
        uint64 lifetime
    ) external onlyMember whenNotPaused returns (uint256 proposalId) {
        require(recipient != address(0), "zero recipient");
        require(amount > 0 || data.length > 0, "empty proposal");
        require(delay >= MIN_DELAY && delay <= MAX_PROPOSAL_DELAY, "invalid delay");
        require(lifetime >= delay, "invalid lifetime");
        require(bytes(description).length <= MAX_DESCRIPTION_LENGTH, "description too long");

        proposalId = ++proposalCount;

        proposals[proposalId] = Proposal({
            proposer: msg.sender,
            recipient: recipient,
            amount: amount,
            data: data,
            description: description,
            createdAt: uint64(block.timestamp),
            executeAfter: uint64(block.timestamp + delay),
            expiresAt: uint64(block.timestamp + lifetime),
            approvals: 1,
            state: ProposalState.Pending
        });

        proposalApprovedBy[proposalId][msg.sender] = true;
        members[msg.sender].lastActivityAt = uint64(block.timestamp);

        emit ProposalCreated(proposalId, msg.sender, recipient, amount, block.timestamp + delay);
    }

    function approveProposal(uint256 proposalId) external onlyMember proposalExists(proposalId) {
        Proposal storage proposal = proposals[proposalId];

        require(proposal.state == ProposalState.Pending, "not pending");
        require(block.timestamp <= proposal.expiresAt, "expired");
        require(!proposalApprovedBy[proposalId][msg.sender], "already approved");

        proposalApprovedBy[proposalId][msg.sender] = true;
        proposal.approvals += 1;
        members[msg.sender].lastActivityAt = uint64(block.timestamp);

        if (proposal.approvals >= 2) {
            proposal.state = ProposalState.Approved;
        }

        emit ProposalApproved(proposalId, msg.sender);
    }

    function cancelProposal(uint256 proposalId) external proposalExists(proposalId) {
        Proposal storage proposal = proposals[proposalId];

        require(
            proposal.state == ProposalState.Pending ||
                proposal.state == ProposalState.Approved,
            "not cancellable"
        );
        require(
            msg.sender == proposal.proposer || msg.sender == owner,
            "not authorized"
        );

        proposal.state = ProposalState.Cancelled;
        emit ProposalCancelled(proposalId);
    }

    function expireProposal(uint256 proposalId) external proposalExists(proposalId) {
        Proposal storage proposal = proposals[proposalId];
        require(
            proposal.state == ProposalState.Pending ||
                proposal.state == ProposalState.Approved,
            "not active"
        );
        require(block.timestamp > proposal.expiresAt, "not expired");

        proposal.state = ProposalState.Expired;
    }

    function executeProposal(
        uint256 proposalId
    ) external proposalExists(proposalId) whenNotPaused {
        Proposal storage proposal = proposals[proposalId];

        require(proposal.state == ProposalState.Approved, "not approved");
        require(block.timestamp >= proposal.executeAfter, "timelocked");
        require(block.timestamp <= proposal.expiresAt, "expired");
        require(proposal.approvals >= 2, "not enough approvals");
        require(address(this).balance >= proposal.amount, "insufficient treasury");

        proposal.state = ProposalState.Executed;

        (bool success, ) = proposal.recipient.call{value: proposal.amount}(proposal.data);
        require(success, "proposal call failed");

        if (proposal.amount > 0) {
            totalManaged -= proposal.amount;
            totalWithdrawals += proposal.amount;
        }

        emit ProposalExecuted(proposalId, proposal.recipient, proposal.amount);
    }

    function getProposal(
        uint256 proposalId
    )
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint64 createdAt,
            uint64 executeAfter,
            uint64 expiresAt,
            uint32 approvals,
            ProposalState state,
            string memory description
        )
    {
        Proposal storage proposal = proposals[proposalId];

        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.createdAt,
            proposal.executeAfter,
            proposal.expiresAt,
            proposal.approvals,
            proposal.state,
            proposal.description
        );
    }

    // =====================================================================
    // Scheduled payments
    // =====================================================================

    function schedulePayment(
        address payable recipient,
        uint256 amount,
        uint64 releaseTime,
        string calldata memo
    ) external onlyManager returns (uint256 paymentId) {
        require(recipient != address(0), "zero recipient");
        require(amount > 0, "zero amount");
        require(releaseTime > block.timestamp, "release in past");

        paymentId = ++scheduledPaymentCount;

        scheduledPayments[paymentId] = ScheduledPayment({
            recipient: recipient,
            amount: amount,
            releaseTime: releaseTime,
            state: PaymentState.Scheduled,
            memo: memo
        });

        emit ScheduledPaymentCreated(paymentId, recipient, amount, releaseTime);
    }

    function cancelScheduledPayment(uint256 paymentId) external onlyManager {
        ScheduledPayment storage payment = scheduledPayments[paymentId];
        require(payment.recipient != address(0), "unknown payment");
        require(payment.state == PaymentState.Scheduled, "not scheduled");

        payment.state = PaymentState.Cancelled;
        emit ScheduledPaymentCancelled(paymentId);
    }

    function claimScheduledPayment(uint256 paymentId) external whenNotPaused {
        ScheduledPayment storage payment = scheduledPayments[paymentId];

        require(payment.recipient != address(0), "unknown payment");
        require(msg.sender == payment.recipient, "not recipient");
        require(payment.state == PaymentState.Scheduled, "not scheduled");
        require(block.timestamp >= payment.releaseTime, "not released");
        require(address(this).balance >= payment.amount, "insufficient treasury");

        payment.state = PaymentState.Claimed;
        totalManaged -= payment.amount;
        totalWithdrawals += payment.amount;

        (bool success, ) = payment.recipient.call{value: payment.amount}("");
        require(success, "transfer failed");

        emit ScheduledPaymentClaimed(paymentId, payment.recipient, payment.amount);
    }

    function getScheduledPayment(
        uint256 paymentId
    )
        external
        view
        returns (
            address recipient,
            uint256 amount,
            uint64 releaseTime,
            PaymentState state,
            string memory memo
        )
    {
        ScheduledPayment storage payment = scheduledPayments[paymentId];
        return (
            payment.recipient,
            payment.amount,
            payment.releaseTime,
            payment.state,
            payment.memo
        );
    }

    // =====================================================================
    // Recurring payments
    // =====================================================================

    function createRecurringPayment(
        address payable recipient,
        uint256 amount,
        uint64 interval,
        uint32 executions,
        string calldata memo
    ) external onlyOwner returns (uint256 paymentId) {
        require(recipient != address(0), "zero recipient");
        require(amount > 0, "zero amount");
        require(interval >= 1 hours, "interval too short");
        require(executions > 0, "zero executions");

        paymentId = ++recurringPaymentCount;

        recurringPayments[paymentId] = RecurringPayment({
            recipient: recipient,
            amount: amount,
            interval: interval,
            nextExecution: uint64(block.timestamp + interval),
            remainingExecutions: executions,
            active: true,
            memo: memo
        });

        emit RecurringPaymentCreated(paymentId, recipient, amount, interval, executions);
    }

    function executeRecurringPayment(uint256 paymentId) external whenNotPaused {
        RecurringPayment storage payment = recurringPayments[paymentId];

        require(payment.active, "inactive");
        require(payment.recipient != address(0), "unknown payment");
        require(block.timestamp >= payment.nextExecution, "too early");
        require(payment.remainingExecutions > 0, "finished");
        require(address(this).balance >= payment.amount, "insufficient treasury");

        payment.remainingExecutions -= 1;
        payment.nextExecution = uint64(block.timestamp + payment.interval);

        if (payment.remainingExecutions == 0) {
            payment.active = false;
        }

        totalManaged -= payment.amount;
        totalWithdrawals += payment.amount;

        (bool success, ) = payment.recipient.call{value: payment.amount}("");
        require(success, "recurring payment failed");

        emit RecurringPaymentExecuted(paymentId, payment.amount, payment.nextExecution);
    }

    function cancelRecurringPayment(uint256 paymentId) external onlyOwner {
        RecurringPayment storage payment = recurringPayments[paymentId];
        require(payment.active, "inactive");
        payment.active = false;
        emit RecurringPaymentCancelled(paymentId);
    }

    function getRecurringPayment(
        uint256 paymentId
    )
        external
        view
        returns (
            address recipient,
            uint256 amount,
            uint64 interval,
            uint64 nextExecution,
            uint32 remainingExecutions,
            bool active,
            string memory memo
        )
    {
        RecurringPayment storage payment = recurringPayments[paymentId];
        return (
            payment.recipient,
            payment.amount,
            payment.interval,
            payment.nextExecution,
            payment.remainingExecutions,
            payment.active,
            payment.memo
        );
    }

    // =====================================================================
    // Budgets
    // =====================================================================

    function createBudget(
        string calldata name,
        uint256 limit,
        uint64 periodStart,
        uint64 periodEnd
    ) external onlyOwner returns (uint256 budgetId) {
        require(bytes(name).length > 0, "empty name");
        require(limit > 0, "zero limit");
        require(periodEnd > periodStart, "invalid period");

        budgetId = ++budgetCount;

        budgets[budgetId] = Budget({
            name: name,
            limit: limit,
            spent: 0,
            periodStart: periodStart,
            periodEnd: periodEnd,
            state: BudgetState.Active
        });

        emit BudgetCreated(budgetId, name, limit);
    }

    function spendBudget(
        uint256 budgetId,
        address payable recipient,
        uint256 amount
    ) external onlyManager budgetExists(budgetId) whenNotPaused {
        Budget storage budget = budgets[budgetId];

        require(budget.state == BudgetState.Active, "budget inactive");
        require(block.timestamp >= budget.periodStart, "period not started");
        require(block.timestamp <= budget.periodEnd, "period ended");
        require(recipient != address(0), "zero recipient");
        require(amount > 0, "zero amount");
        require(budget.spent + amount <= budget.limit, "budget exceeded");
        require(address(this).balance >= amount, "insufficient treasury");

        budget.spent += amount;
        totalManaged -= amount;
        totalWithdrawals += amount;

        (bool success, ) = recipient.call{value: amount}("");
        require(success, "budget payment failed");

        emit BudgetSpent(budgetId, recipient, amount);
    }

    function setBudgetState(
        uint256 budgetId,
        BudgetState state
    ) external onlyOwner budgetExists(budgetId) {
        budgets[budgetId].state = state;
        emit BudgetStateChanged(budgetId, state);
    }

    function increaseBudgetLimit(
        uint256 budgetId,
        uint256 additionalLimit
    ) external onlyOwner budgetExists(budgetId) {
        require(additionalLimit > 0, "zero increase");
        budgets[budgetId].limit += additionalLimit;
    }

    function getBudget(
        uint256 budgetId
    )
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint64 periodStart,
            uint64 periodEnd,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        return (
            budget.name,
            budget.limit,
            budget.spent,
            budget.periodStart,
            budget.periodEnd,
            budget.state
        );
    }

    // =====================================================================
    // Department limits
    // =====================================================================

    function setDepartmentLimit(address department, uint256 limit) external onlyOwner {
        require(department != address(0), "zero department");
        departmentLimits[department] = limit;
    }

    function departmentPayment(
        address payable recipient,
        uint256 amount
    ) external onlyManager whenNotPaused {
        uint256 limit = departmentLimits[msg.sender];

        require(limit > 0, "department not configured");
        require(amount > 0, "zero amount");
        require(departmentSpent[msg.sender] + amount <= limit, "department limit");
        require(address(this).balance >= amount, "insufficient treasury");

        departmentSpent[msg.sender] += amount;
        members[msg.sender].totalSpent += amount;
        totalManaged -= amount;
        totalWithdrawals += amount;

        (bool success, ) = recipient.call{value: amount}("");
        require(success, "department payment failed");
    }

    function resetDepartmentSpent(address department) external onlyOwner {
        departmentSpent[department] = 0;
    }

    // =====================================================================
    // Allowances
    // =====================================================================

    function configureAllowance(
        address account,
        uint256 limit,
        uint64 periodStart,
        uint64 periodEnd
    ) external onlyOwner {
        require(account != address(0), "zero account");
        require(periodEnd > periodStart, "invalid period");

        allowances[account] = Allowance({
            limit: limit,
            spent: 0,
            periodStart: periodStart,
            periodEnd: periodEnd
        });

        emit AllowanceConfigured(account, limit, periodStart, periodEnd);
    }

    function spendAllowance(
        address payable recipient,
        uint256 amount
    ) external onlyMember whenNotPaused {
        Allowance storage allowance = allowances[msg.sender];

        require(recipient != address(0), "zero recipient");
        require(block.timestamp >= allowance.periodStart, "period not started");
        require(block.timestamp <= allowance.periodEnd, "period ended");
        require(amount > 0, "zero amount");
        require(allowance.spent + amount <= allowance.limit, "allowance exceeded");
        require(address(this).balance >= amount, "insufficient treasury");

        allowance.spent += amount;
        members[msg.sender].totalSpent += amount;
        totalManaged -= amount;
        totalWithdrawals += amount;

        (bool success, ) = recipient.call{value: amount}("");
        require(success, "allowance payment failed");

        emit AllowanceSpent(msg.sender, recipient, amount);
    }

    function getAllowance(
        address account
    ) external view returns (uint256 limit, uint256 spent, uint64 periodStart, uint64 periodEnd) {
        Allowance storage allowance = allowances[account];
        return (
            allowance.limit,
            allowance.spent,
            allowance.periodStart,
            allowance.periodEnd
        );
    }

    // =====================================================================
    // Invoices
    // =====================================================================

    function submitInvoice(
        address vendor,
        uint256 amount,
        bytes32 documentHash,
        string calldata invoiceReference
    ) external onlyManager returns (uint256 invoiceId) {
        require(vendor != address(0), "zero vendor");
        require(amount > 0, "zero amount");
        require(documentHash != bytes32(0), "zero hash");

        invoiceId = ++invoiceCount;

        invoices[invoiceId] = Invoice({
            vendor: vendor,
            amount: amount,
            documentHash: documentHash,
            submittedAt: uint64(block.timestamp),
            dueAt: uint64(block.timestamp + DEFAULT_INVOICE_PERIOD),
            approved: false,
            paid: false,
            invoiceReference: invoiceReference
        });

        emit InvoiceSubmitted(invoiceId, vendor, amount);
    }

    function approveInvoice(uint256 invoiceId) external onlyOwner invoiceExists(invoiceId) {
        Invoice storage invoice = invoices[invoiceId];

        require(!invoice.paid, "already paid");
        require(!invoice.approved, "already approved");

        invoice.approved = true;
        emit InvoiceApproved(invoiceId);
    }

    function payInvoice(uint256 invoiceId) external invoiceExists(invoiceId) whenNotPaused {
        Invoice storage invoice = invoices[invoiceId];

        require(invoice.approved, "not approved");
        require(!invoice.paid, "already paid");
        require(address(this).balance >= invoice.amount, "insufficient treasury");

        invoice.paid = true;
        vendorPaidTotal[invoice.vendor] += invoice.amount;
        totalManaged -= invoice.amount;
        totalWithdrawals += invoice.amount;

        (bool success, ) = payable(invoice.vendor).call{value: invoice.amount}("");
        require(success, "invoice payment failed");

        emit InvoicePaid(invoiceId, invoice.vendor, invoice.amount);
    }

    function updateInvoiceDueDate(
        uint256 invoiceId,
        uint64 newDueAt
    ) external onlyManager invoiceExists(invoiceId) {
        Invoice storage invoice = invoices[invoiceId];
        require(!invoice.paid, "already paid");
        require(newDueAt > block.timestamp, "past due date");
        invoice.dueAt = newDueAt;
    }

    function getInvoice(
        uint256 invoiceId
    )
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            bytes32 documentHash,
            uint64 submittedAt,
            uint64 dueAt,
            bool approved,
            bool paid,
            string memory invoiceReference
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.documentHash,
            invoice.submittedAt,
            invoice.dueAt,
            invoice.approved,
            invoice.paid,
            invoice.invoiceReference
        );
    }

    // =====================================================================
    // Reimbursements and batch payments
    // =====================================================================

    function reimburseMember(
        address payable member,
        uint256 amount,
        string calldata reason
    ) external onlyManager whenNotPaused {
        require(members[member].active, "not member");
        require(amount > 0, "zero amount");
        require(address(this).balance >= amount, "insufficient treasury");

        members[member].totalReimbursed += amount;
        totalManaged -= amount;
        totalWithdrawals += amount;

        (bool success, ) = member.call{value: amount}("");
        require(success, "reimbursement failed");

        emit CreditAdded(member, amount, reason);
    }

    function batchReimburse(
        address payable[] calldata recipients,
        uint256[] calldata amounts
    ) external onlyOwner whenNotPaused {
        require(recipients.length == amounts.length, "length mismatch");
        require(recipients.length <= MAX_BATCH_SIZE, "batch too large");

        for (uint256 i = 0; i < recipients.length; i++) {
            address payable recipient = recipients[i];
            uint256 amount = amounts[i];

            if (recipient == address(0) || amount == 0) {
                continue;
            }

            require(address(this).balance >= amount, "insufficient treasury");

            totalManaged -= amount;
            totalWithdrawals += amount;

            (bool success, ) = recipient.call{value: amount}("");
            require(success, "batch payment failed");
        }
    }

    function batchCredit(
        address[] calldata accounts,
        uint256[] calldata amounts
    ) external onlyManager {
        require(accounts.length == amounts.length, "length mismatch");
        require(accounts.length <= MAX_BATCH_SIZE, "batch too large");

        for (uint256 i = 0; i < accounts.length; i++) {
            if (accounts[i] == address(0) || amounts[i] == 0) {
                continue;
            }
            credits[accounts[i]] += amounts[i];
        }
    }

    function batchSetSpendingLimits(
        address[] calldata accounts,
        uint96[] calldata limits
    ) external onlyOwner {
        require(accounts.length == limits.length, "length mismatch");
        require(accounts.length <= MAX_BATCH_SIZE, "batch too large");

        for (uint256 i = 0; i < accounts.length; i++) {
            if (!members[accounts[i]].active) {
                continue;
            }
            members[accounts[i]].spendingLimit = limits[i];
        }
    }

    // =====================================================================
    // Daily member spending
    // =====================================================================

    function spendFromMemberLimit(
        address payable recipient,
        uint256 amount
    ) external onlyMember whenNotPaused {
        require(recipient != address(0), "zero recipient");
        require(amount > 0, "zero amount");
        require(amount <= members[msg.sender].spendingLimit, "over member limit");

        uint256 currentDay = block.timestamp / 1 days;

        if (currentDay != lastSpendDay) {
            lastSpendDay = currentDay;
            dailySpent = 0;
        }

        dailySpent += amount;
        members[msg.sender].totalSpent += amount;
        members[msg.sender].lastActivityAt = uint64(block.timestamp);

        require(address(this).balance >= amount, "insufficient treasury");

        totalManaged -= amount;
        totalWithdrawals += amount;

        (bool success, ) = recipient.call{value: amount}("");
        require(success, "payment failed");
    }

    // =====================================================================
    // External integrations
    // =====================================================================

    function callIntegration(
        address target,
        uint256 value,
        bytes calldata data
    ) external onlyOwner returns (bytes memory returnData) {
        require(target != address(0), "zero target");
        require(address(this).balance >= value, "insufficient treasury");

        (bool success, bytes memory result) = target.call{value: value}(data);
        require(success, "integration failed");

        if (value > 0) {
            totalManaged -= value;
            totalWithdrawals += value;
            totalExternalValue += value;
        }

        emit ExternalCall(target, value, data);
        return result;
    }

    function staticIntegrationCall(
        address target,
        bytes calldata data
    ) external view returns (bytes memory returnData) {
        require(target != address(0), "zero target");
        (bool success, bytes memory result) = target.staticcall(data);
        require(success, "static integration failed");
        return result;
    }

    function legacyBatchCall(
        address[] calldata targets,
        bytes[] calldata payloads
    ) external onlyOwner {
        require(targets.length == payloads.length, "length mismatch");
        require(targets.length <= MAX_BATCH_SIZE, "batch too large");

        for (uint256 i = 0; i < targets.length; i++) {
            if (targets[i] == address(0)) {
                continue;
            }

            targets[i].call(payloads[i]);
            emit ExternalCall(targets[i], 0, payloads[i]);
        }
    }

    function safeBatchCall(
        address[] calldata targets,
        bytes[] calldata payloads
    ) external onlyOwner returns (bool[] memory successes) {
        require(targets.length == payloads.length, "length mismatch");
        require(targets.length <= MAX_BATCH_SIZE, "batch too large");

        successes = new bool[](targets.length);

        for (uint256 i = 0; i < targets.length; i++) {
            require(targets[i] != address(0), "zero target");
            (bool success, ) = targets[i].call(payloads[i]);
            successes[i] = success;
        }
    }

    // =====================================================================
    // Accounting
    // =====================================================================

    function recordAccounting(
        bytes32 key,
        uint256 amount
    ) external onlyAuditor {
        require(key != bytes32(0), "zero key");

        if (accountingTotals[key] == 0) {
            accountingKeys.push(key);
        }

        accountingTotals[key] += amount;
        emit AccountingRecorded(key, amount);
    }

    function correctAccounting(
        bytes32 key,
        uint256 newTotal
    ) external onlyOwner {
        require(key != bytes32(0), "zero key");
        accountingTotals[key] = newTotal;
    }

    function getAccountingKeyCount() external view returns (uint256) {
        return accountingKeys.length;
    }

    function getAccountingKey(uint256 index) external view returns (bytes32) {
        require(index < accountingKeys.length, "index");
        return accountingKeys[index];
    }

    function getAccountingTotal(bytes32 key) external view returns (uint256) {
        return accountingTotals[key];
    }

    // =====================================================================
    // Vendor management
    // =====================================================================

    function registerVendor(address vendor) external onlyManager {
        require(vendor != address(0), "zero vendor");

        bool exists = false;
        for (uint256 i = 0; i < vendorList.length; i++) {
            if (vendorList[i] == vendor) {
                exists = true;
                break;
            }
        }

        if (!exists) {
            vendorList.push(vendor);
        }
    }

    function getVendorCount() external view returns (uint256) {
        return vendorList.length;
    }

    function getVendorAt(uint256 index) external view returns (address) {
        require(index < vendorList.length, "index");
        return vendorList[index];
    }

    // =====================================================================
    // Audit log
    // =====================================================================

    function writeAuditEntry(
        bytes32 action,
        address target,
        uint256 amount,
        bytes32 metadataHash
    ) external {
        require(
            msg.sender == owner ||
                msg.sender == auditor ||
                members[msg.sender].role == Role.Manager,
            "not authorized"
        );

        uint256 entryId = ++auditEntryCount;

        auditEntries[entryId] = AuditEntry({
            action: action,
            actor: msg.sender,
            target: target,
            amount: amount,
            timestamp: uint64(block.timestamp),
            metadataHash: metadataHash
        });

        emit AuditLogged(entryId, action, msg.sender);
    }

    function getAuditEntry(
        uint256 entryId
    )
        external
        view
        returns (
            bytes32 action,
            address actor,
            address target,
            uint256 amount,
            uint64 timestamp,
            bytes32 metadataHash
        )
    {
        require(entryId > 0 && entryId <= auditEntryCount, "unknown entry");
        AuditEntry storage entry = auditEntries[entryId];

        return (
            entry.action,
            entry.actor,
            entry.target,
            entry.amount,
            entry.timestamp,
            entry.metadataHash
        );
    }

    // =====================================================================
    // Operation tracking
    // =====================================================================

    function markOperationProcessed(bytes32 operationId) external onlyManager {
        require(operationId != bytes32(0), "zero operation");
        require(!processedOperations[operationId], "already processed");

        processedOperations[operationId] = true;
    }

    function operationWasProcessed(bytes32 operationId) external view returns (bool) {
        return processedOperations[operationId];
    }

    // =====================================================================
    // Emergency actions
    // =====================================================================

    function emergencyWithdraw(
        address payable recipient,
        uint256 amount
    ) external onlyGuardian {
        require(paused || emergencyMode, "not emergency");
        require(recipient != address(0), "zero recipient");
        require(amount <= address(this).balance, "insufficient treasury");

        totalManaged -= amount;
        totalWithdrawals += amount;

        (bool success, ) = recipient.call{value: amount}("");
        require(success, "emergency transfer failed");

        emit EmergencyWithdrawal(recipient, amount);
    }

    function recoverTo(
        address payable recipient,
        uint256 amount
    ) external {
        require(msg.sender == guardian || tx.origin == owner, "not authorized");
        require(recipient != address(0), "zero recipient");
        require(amount <= address(this).balance, "insufficient treasury");

        (bool success, ) = recipient.call{value: amount}("");
        require(success, "recovery failed");

        totalManaged -= amount;
        totalWithdrawals += amount;

        emit EmergencyWithdrawal(recipient, amount);
    }

    function emergencyDisableMember(address account) external onlyGuardian {
        require(emergencyMode, "not emergency");
        require(members[account].active, "not active");
        require(account != owner, "owner");

        members[account].active = false;
        members[account].role = Role.None;
        emit MemberRemoved(account);
    }

    // =====================================================================
    // Reporting and statistics
    // =====================================================================

    function treasuryBalance() external view returns (uint256) {
        return address(this).balance;
    }

    function isMember(address account) external view returns (bool) {
        return members[account].active;
    }

    function proposalState(
        uint256 proposalId
    ) external view proposalExists(proposalId) returns (ProposalState) {
        return proposals[proposalId].state;
    }

    function totalOutstandingCredits(
        address[] calldata accounts
    ) external view returns (uint256 total) {
        for (uint256 i = 0; i < accounts.length; i++) {
            total += credits[accounts[i]];
        }
    }

    function totalVendorPayments(
        address[] calldata vendors
    ) external view returns (uint256 total) {
        for (uint256 i = 0; i < vendors.length; i++) {
            total += vendorPaidTotal[vendors[i]];
        }
    }

    function summarizeBudgetUsage(
        uint256[] calldata budgetIds
    ) external view returns (uint256 totalLimits, uint256 totalSpent_) {
        for (uint256 i = 0; i < budgetIds.length; i++) {
            require(budgetIds[i] > 0 && budgetIds[i] <= budgetCount, "unknown budget");
            Budget storage budget = budgets[budgetIds[i]];
            totalLimits += budget.limit;
            totalSpent_ += budget.spent;
        }
    }

    function summarizeMembers(
        address[] calldata accounts
    )
        external
        view
        returns (
            uint256 activeCount,
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        for (uint256 i = 0; i < accounts.length; i++) {
            Member storage member = members[accounts[i]];
            if (member.active) {
                activeCount += 1;
            }
            deposited += member.totalDeposited;
            reimbursed += member.totalReimbursed;
            spent += member.totalSpent;
        }
    }

    // =====================================================================
    // Maintenance utilities
    // =====================================================================

    function touchMember(address account) external onlyManager {
        require(members[account].active, "not active");
        members[account].lastActivityAt = uint64(block.timestamp);
    }

    function normalizeMemberLimits(
        address[] calldata accounts,
        uint96 maximum
    ) external onlyOwner {
        require(accounts.length <= MAX_BATCH_SIZE, "batch too large");

        for (uint256 i = 0; i < accounts.length; i++) {
            if (
                members[accounts[i]].active &&
                members[accounts[i]].spendingLimit > maximum
            ) {
                members[accounts[i]].spendingLimit = maximum;
            }
        }
    }

    function closeExpiredBudgets(
        uint256[] calldata budgetIds
    ) external onlyManager {
        require(budgetIds.length <= MAX_BATCH_SIZE, "batch too large");

        for (uint256 i = 0; i < budgetIds.length; i++) {
            uint256 budgetId = budgetIds[i];

            if (budgetId == 0 || budgetId > budgetCount) {
                continue;
            }

            Budget storage budget = budgets[budgetId];

            if (
                budget.state == BudgetState.Active &&
                block.timestamp > budget.periodEnd
            ) {
                budget.state = BudgetState.Closed;
                emit BudgetStateChanged(budgetId, BudgetState.Closed);
            }
        }
    }

    function cancelExpiredScheduledPayments(
        uint256[] calldata paymentIds
    ) external onlyManager {
        require(paymentIds.length <= MAX_BATCH_SIZE, "batch too large");

        for (uint256 i = 0; i < paymentIds.length; i++) {
            uint256 paymentId = paymentIds[i];

            if (paymentId == 0 || paymentId > scheduledPaymentCount) {
                continue;
            }

            ScheduledPayment storage payment = scheduledPayments[paymentId];

            if (
                payment.state == PaymentState.Scheduled &&
                block.timestamp > payment.releaseTime + 30 days
            ) {
                payment.state = PaymentState.Cancelled;
                emit ScheduledPaymentCancelled(paymentId);
            }
        }
    }

    function deactivateFinishedRecurringPayments(
        uint256[] calldata paymentIds
    ) external onlyManager {
        require(paymentIds.length <= MAX_BATCH_SIZE, "batch too large");

        for (uint256 i = 0; i < paymentIds.length; i++) {
            uint256 paymentId = paymentIds[i];

            if (paymentId == 0 || paymentId > recurringPaymentCount) {
                continue;
            }

            RecurringPayment storage payment = recurringPayments[paymentId];

            if (payment.active && payment.remainingExecutions == 0) {
                payment.active = false;
                emit RecurringPaymentCancelled(paymentId);
            }
        }
    }

    // =====================================================================
    // Internal helpers
    // =====================================================================

    function _recordDeposit(
        address sender,
        address beneficiary,
        uint256 amount
    ) internal {
        require(amount > 0, "zero deposit");

        totalManaged += amount;
        totalDeposits += amount;

        if (members[beneficiary].active) {
            members[beneficiary].totalDeposited += amount;
            members[beneficiary].lastActivityAt = uint64(block.timestamp);
        }

        emit Deposit(sender, beneficiary, amount);
    }

    // =====================================================================
    // Extended reporting and policy helpers for scalability experiments
    // =====================================================================

    function getTreasuryTotals()
        external
        view
        returns (
            uint256 managed,
            uint256 deposits,
            uint256 withdrawals,
            uint256 externalValue,
            uint256 balance
        )
    {
        return (
            totalManaged,
            totalDeposits,
            totalWithdrawals,
            totalExternalValue,
            address(this).balance
        );
    }

    function getSystemActors()
        external
        view
        returns (
            address owner_,
            address pendingOwner_,
            address guardian_,
            address auditor_
        )
    {
        return (owner, pendingOwner, guardian, auditor);
    }

    function getSystemFlags()
        external
        view
        returns (
            bool paused_,
            bool emergencyMode_
        )
    {
        return (paused, emergencyMode);
    }

    function getSystemCounters()
        external
        view
        returns (
            uint256 proposals_,
            uint256 scheduled_,
            uint256 recurring_,
            uint256 budgets_,
            uint256 invoices_,
            uint256 audits_
        )
    {
        return (
            proposalCount,
            scheduledPaymentCount,
            recurringPaymentCount,
            budgetCount,
            invoiceCount,
            auditEntryCount
        );
    }

    function getMemberActivity(address account)
        external
        view
        returns (
            uint64 joinedAt,
            uint64 lastActivityAt,
            uint256 lastWithdrawalAt
        )
    {
        Member storage member = members[account];
        return (
            member.joinedAt,
            member.lastActivityAt,
            lastWithdrawal[account]
        );
    }

    function getMemberFinancials(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent,
            credits[account]
        );
    }

    function getDepartmentStatus(address department)
        external
        view
        returns (
            uint256 limit,
            uint256 spent,
            uint256 remaining
        )
    {
        limit = departmentLimits[department];
        spent = departmentSpent[department];
        remaining = limit > spent ? limit - spent : 0;
    }

    function getBudgetRemaining(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (uint256)
    {
        Budget storage budget = budgets[budgetId];
        return budget.limit > budget.spent ? budget.limit - budget.spent : 0;
    }

    function getBudgetUtilization(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (uint256 basisPoints)
    {
        Budget storage budget = budgets[budgetId];
        if (budget.limit == 0) {
            return 0;
        }
        return (budget.spent * 10_000) / budget.limit;
    }

    function getInvoiceStatus(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            bool approved,
            bool paid,
            bool overdue
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        approved = invoice.approved;
        paid = invoice.paid;
        overdue = !invoice.paid && block.timestamp > invoice.dueAt;
    }


    function memberSnapshot1(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot1(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot2(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot2(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot3(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot3(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot4(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot4(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot5(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot5(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot6(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot6(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot7(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot7(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot8(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot8(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot9(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot9(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot10(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot10(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot11(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot11(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot12(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot12(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot13(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot13(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot14(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot14(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot15(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot15(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot16(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot16(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot17(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot17(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot18(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot18(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot19(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot19(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot20(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot20(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot21(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot21(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot22(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot22(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot23(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot23(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot24(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot24(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot25(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot25(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot26(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot26(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot27(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot27(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot28(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot28(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot29(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot29(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }

    function memberSnapshot30(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot30(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function budgetSnapshot1(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot2(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot3(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot4(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot5(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot6(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot7(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot8(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot9(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot10(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot11(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot12(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot13(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot14(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot15(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function proposalSnapshot1(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot2(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot3(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot4(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot5(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot6(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot7(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot8(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot9(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot10(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function invoiceSnapshot1(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot2(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot3(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot4(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot5(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot6(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot7(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot8(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function computePolicyValue1(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue2(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue3(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue4(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue5(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue6(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue7(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue8(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue9(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue10(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }

    function memberSnapshot61(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot61(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot62(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot62(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot63(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot63(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot64(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot64(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot65(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot65(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot66(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot66(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot67(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot67(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot68(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot68(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot69(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot69(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot70(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot70(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot71(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot71(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot72(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot72(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot73(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot73(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot74(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot74(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot75(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot75(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot76(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot76(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot77(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot77(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot78(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot78(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot79(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot79(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot80(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot80(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot81(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot81(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot82(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot82(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot83(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot83(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot84(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot84(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot85(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot85(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot86(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot86(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot87(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot87(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot88(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot88(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot89(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot89(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot90(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot90(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot91(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot91(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot92(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot92(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot93(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot93(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot94(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot94(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot95(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot95(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot96(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot96(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot97(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot97(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot98(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot98(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot99(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot99(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot100(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot100(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot101(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot101(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot102(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot102(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot103(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot103(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot104(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot104(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot105(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot105(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot106(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot106(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot107(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot107(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot108(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot108(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot109(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot109(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot110(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot110(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot111(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot111(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot112(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot112(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot113(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot113(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot114(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot114(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot115(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot115(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot116(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot116(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot117(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot117(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot118(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot118(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot119(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot119(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function memberSnapshot120(address account)
        external
        view
        returns (
            bool active,
            Role role,
            uint256 spendingLimit,
            uint256 credit
        )
    {
        Member storage member = members[account];
        return (
            member.active,
            member.role,
            member.spendingLimit,
            credits[account]
        );
    }

    function memberFinancialSnapshot120(address account)
        external
        view
        returns (
            uint256 deposited,
            uint256 reimbursed,
            uint256 spent
        )
    {
        Member storage member = members[account];
        return (
            member.totalDeposited,
            member.totalReimbursed,
            member.totalSpent
        );
    }


    function budgetSnapshot31(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot32(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot33(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot34(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot35(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot36(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot37(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot38(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot39(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot40(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot41(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot42(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot43(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot44(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot45(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot46(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot47(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot48(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot49(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot50(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot51(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot52(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot53(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot54(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot55(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot56(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot57(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot58(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot59(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function budgetSnapshot60(uint256 budgetId)
        external
        view
        budgetExists(budgetId)
        returns (
            string memory name,
            uint256 limit,
            uint256 spent,
            uint256 remaining,
            BudgetState state
        )
    {
        Budget storage budget = budgets[budgetId];
        uint256 remainingAmount =
            budget.limit > budget.spent ? budget.limit - budget.spent : 0;

        return (
            budget.name,
            budget.limit,
            budget.spent,
            remainingAmount,
            budget.state
        );
    }


    function proposalSnapshot21(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot22(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot23(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot24(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot25(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot26(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot27(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot28(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot29(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot30(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot31(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot32(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot33(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot34(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot35(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot36(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot37(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot38(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot39(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function proposalSnapshot40(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (
            address proposer,
            address recipient,
            uint256 amount,
            uint32 approvals,
            ProposalState state
        )
    {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.recipient,
            proposal.amount,
            proposal.approvals,
            proposal.state
        );
    }


    function invoiceSnapshot16(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot17(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot18(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot19(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot20(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot21(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot22(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot23(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot24(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot25(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot26(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot27(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot28(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot29(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function invoiceSnapshot30(uint256 invoiceId)
        external
        view
        invoiceExists(invoiceId)
        returns (
            address vendor,
            uint256 amount,
            uint64 dueAt,
            bool approved,
            bool paid
        )
    {
        Invoice storage invoice = invoices[invoiceId];
        return (
            invoice.vendor,
            invoice.amount,
            invoice.dueAt,
            invoice.approved,
            invoice.paid
        );
    }


    function computePolicyValue21(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue22(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue23(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue24(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue25(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue26(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue27(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue28(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue29(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue30(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue31(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue32(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue33(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue34(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue35(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue36(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue37(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue38(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue39(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue40(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue41(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue42(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue43(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue44(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue45(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue46(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue47(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue48(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue49(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }


    function computePolicyValue50(
        uint256 baseAmount,
        uint256 basisPoints,
        uint256 cap
    ) external pure returns (uint256) {
        if (baseAmount == 0 || basisPoints == 0) {
            return 0;
        }

        uint256 calculated = (baseAmount * basisPoints) / 10_000;
        return calculated > cap ? cap : calculated;
    }

}

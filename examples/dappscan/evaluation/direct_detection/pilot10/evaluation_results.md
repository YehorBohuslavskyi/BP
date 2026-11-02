# DAppSCAN direct detection

## Metrics

- detected: 0
- missed: 3
- inconclusive: 18
- labeled_vulnerabilities: 21
- additional_unlabeled_findings: 16
- recall: 0.0
- type_accuracy_among_detected: None
- type_accuracy_note: SWC compatibility is required by the matching rule; not an independent classifier metric.
- location_match_rate: 0.0
- total_api_calls: 149
- total_tokens: 610343
- average_rounds: 2.0694444444444446
- average_requested_fragments: 4.222222222222222
- context_reduction: 0.8889378018348433

## Ground-truth classifications

| SWC | Ground-truth function | Lines | Relevant sessions | Classification |
| --- | --- | --- | --- | --- |
| SWC-107 | deposit | 53–61 | deposit(address,uint256) | MISSED |
| SWC-107 | deposit | 65–73 | deposit(address) | MISSED |
| SWC-114 | deposit | 65–73 | deposit(address) | MISSED |
| SWC-112 | ownerOf | 491–493 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-104 | safeTransferFrom | 675–697 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-107 | withdraw | 1097–1104 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-111 | assert | 23–23 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-111 | create | 121–121 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-135 | Unavailable | 157–157 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-135 | Unavailable | 161–161 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-107 | withdraw | 224–224 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-104 | transfer | 76–76 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-104 | liquidate | 692–692 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-135 | Unavailable | 64–64 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-135 | Unavailable | 71–71 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-105 | apeWithdrawSimpleToken | 133–135 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-105 | distribute | 35–35 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-105 | transfer | Unavailable | transfer(address,uint256), transfer(address,uint256) | INCONCLUSIVE |
| SWC-115 | leverage | 160–160 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-115 | exchange | 172–172 | not_analyzed_or_unresolved | INCONCLUSIVE |
| SWC-115 | create | 129–129 | not_analyzed_or_unresolved | INCONCLUSIVE |

## Additional unlabeled findings

- constructor(address,uint256,uint256): Unvalidated zero ratio parameter causes division-by-zero denial of service (No SWC). ADDITIONAL_UNLABELED_FINDING
- deposit(address,uint256): Unvalidated exchange ratio enables free minting (No SWC). ADDITIONAL_UNLABELED_FINDING
- deposit(address,uint256): Fee-on-transfer underlying causes undercollateralized minting (No SWC). ADDITIONAL_UNLABELED_FINDING
- deposit(address): Unauthorized claim of unsolicited underlying-token transfers (No SWC). ADDITIONAL_UNLABELED_FINDING
- deposit(address): Precision-loss accounting can strand underlying tokens (No SWC). ADDITIONAL_UNLABELED_FINDING
- withdraw(address,uint256): Reentrancy causing stale accounting and excess token issuance (SWC-107). ADDITIONAL_UNLABELED_FINDING
- approve(address,uint256): ERC20 approval race condition (SWC-114). ADDITIONAL_UNLABELED_FINDING
- transferFrom(address,address,uint256): Integer overflow in token balance accounting (SWC-101). ADDITIONAL_UNLABELED_FINDING
- transfer(address,uint256): Blacklist enforcement bypass via transferFrom (No SWC). ADDITIONAL_UNLABELED_FINDING
- ban(address): Blacklist bypass / improper authorization enforcement (No SWC). ADDITIONAL_UNLABELED_FINDING
- approve(address,uint256): ERC-20 approval race condition / transaction-order dependence (SWC-114). ADDITIONAL_UNLABELED_FINDING
- approveAndCall(address,uint256,bytes): ERC-20 allowance race condition / transaction-order dependence (SWC-114). ADDITIONAL_UNLABELED_FINDING
- approve(address,uint256): ERC-20 approval race (transaction-order dependence) (SWC-114). ADDITIONAL_UNLABELED_FINDING
- unlockedTokens(address): Locked-token transfer bypass (No SWC). ADDITIONAL_UNLABELED_FINDING
- unlockedTokens(address): Stale-lock accounting causes revert / denial of service (SWC-101). ADDITIONAL_UNLABELED_FINDING
- tokensToEth(uint256): Division by zero / denial of service (SWC-101). ADDITIONAL_UNLABELED_FINDING

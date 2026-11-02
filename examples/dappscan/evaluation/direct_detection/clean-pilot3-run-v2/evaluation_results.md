# DAppSCAN direct detection

## Metrics

- detected: 0
- missed: 4
- inconclusive: 2
- unevaluable: 0
- labeled_vulnerabilities: 6
- additional_unlabeled_findings: 14
- selected_files: 3
- ready_files: 3
- analyzed_files: 3
- preparation_failures: 0
- evaluable_labels: 6
- unevaluable_labels: 0
- evaluation_coverage: 1.0
- recall: 0.0
- type_accuracy_among_detected: None
- type_accuracy_note: SWC compatibility is required by the matching rule; not an independent classifier metric.
- location_match_rate: 0.0
- total_api_calls: 90
- total_tokens: 342564
- average_rounds: 2.0
- average_requested_fragments: 4.4
- context_reduction: 0.9243374417268024

## Ground-truth classifications

| SWC | Ground-truth function | Lines | Relevant sessions | Classification |
| --- | --- | --- | --- | --- |
| SWC-107 | deposit | 53–61 | deposit(address,uint256) | MISSED |
| SWC-107 | deposit | 65–73 | deposit(address) | MISSED |
| SWC-114 | deposit | 65–73 | deposit(address) | MISSED |
| SWC-115 | leverage | 160–160 | leverage(uint256,uint256,uint256) | MISSED |
| SWC-115 | exchange | 172–172 | exchange(uint256,uint256) | INCONCLUSIVE |
| SWC-115 | create | 129–129 | create() | INCONCLUSIVE |

## Additional unlabeled findings

- constructor(address,uint256,uint256): Division by zero / denial of service from unchecked ratioNum (SWC-113). ADDITIONAL_UNLABELED_FINDING
- constructor(address,uint256,uint256): Unchecked zero conversion ratio causing unbacked wrapped tokens (No SWC). ADDITIONAL_UNLABELED_FINDING
- deposit(address,uint256): Rounding-induced zero-cost minting (SWC-101). ADDITIONAL_UNLABELED_FINDING
- _withdraw(address,uint256): Precision-loss inflation / free minting (No SWC). ADDITIONAL_UNLABELED_FINDING
- amtToUnderlyingAmt(uint256): Missing validation of division denominator / denial of service (SWC-123). ADDITIONAL_UNLABELED_FINDING
- amtToUnderlyingAmt(uint256): Arithmetic overflow denial of service (SWC-101). ADDITIONAL_UNLABELED_FINDING
- approve(address,uint256): ERC-20 approval race condition (SWC-114). ADDITIONAL_UNLABELED_FINDING
- transfer(address,uint256): Integer overflow in recipient balance during transfer (SWC-101). ADDITIONAL_UNLABELED_FINDING
- transferFrom(address,address,uint256): Integer overflow in recipient balance accounting (SWC-101). ADDITIONAL_UNLABELED_FINDING
- changeOwner(uint256,uint256,uint256,uint256): Unintended ETH retention / accidental fund loss (SWC-105). ADDITIONAL_UNLABELED_FINDING
- changeDeposit(uint256,uint256): Improper handling of excess ETH / locked funds (SWC-105). ADDITIONAL_UNLABELED_FINDING
- changeYearFee(uint256,uint256): Incorrect state-field comparison causing fee update bypass / denial of intended update (No SWC). ADDITIONAL_UNLABELED_FINDING
- reclaimERC20(address,address): Unchecked ERC-20 transfer return value (SWC-104). ADDITIONAL_UNLABELED_FINDING
- reclaimERC20(address,address): Unchecked ERC-20 transfer return value (SWC-104). ADDITIONAL_UNLABELED_FINDING

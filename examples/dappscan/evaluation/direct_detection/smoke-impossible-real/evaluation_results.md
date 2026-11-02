# DAppSCAN direct detection

## Metrics

- detected: 1
- missed: 2
- inconclusive: 0
- labeled_vulnerabilities: 3
- additional_unlabeled_findings: 4
- recall: 0.3333333333333333
- type_accuracy_among_detected: 1.0
- type_accuracy_note: SWC compatibility is required by the matching rule; not an independent classifier metric.
- location_match_rate: 0.3333333333333333
- total_api_calls: 31
- total_tokens: 95419
- average_rounds: 2.8181818181818183
- average_requested_fragments: 7.545454545454546
- context_reduction: 0.9466744984637628

## Ground-truth classifications

| SWC | Ground-truth function | Lines | Relevant sessions | Classification |
| --- | --- | --- | --- | --- |
| SWC-107 | deposit | 53–61 | deposit(address,uint256) | MISSED |
| SWC-107 | deposit | 65–73 | deposit(address) | MISSED |
| SWC-114 | deposit | 65–73 | deposit(address) | DETECTED |

## Additional unlabeled findings

- constructor(address,uint256,uint256): Missing input validation / invalid initialization (No SWC). ADDITIONAL_UNLABELED_FINDING
- deposit(address,uint256): Zero-cost minting from unchecked conversion ratio (No SWC). ADDITIONAL_UNLABELED_FINDING
- deposit(address,uint256): Rounding-to-zero deposit conversion (No SWC). ADDITIONAL_UNLABELED_FINDING
- approve(address,uint256): ERC-20 approval race condition / transaction-order dependence (SWC-114). ADDITIONAL_UNLABELED_FINDING

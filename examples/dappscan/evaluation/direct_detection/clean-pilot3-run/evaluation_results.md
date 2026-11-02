# DAppSCAN direct detection

## Metrics

- detected: 0
- missed: 1
- inconclusive: 0
- unevaluable: 2
- labeled_vulnerabilities: 3
- additional_unlabeled_findings: 3
- selected_files: 1
- ready_files: 1
- analyzed_files: 1
- preparation_failures: 0
- evaluable_labels: 1
- unevaluable_labels: 2
- evaluation_coverage: 0.3333333333333333
- recall: 0.0
- type_accuracy_among_detected: None
- type_accuracy_note: SWC compatibility is required by the matching rule; not an independent classifier metric.
- location_match_rate: 0.0
- total_api_calls: 25
- total_tokens: 74967
- average_rounds: 2.272727272727273
- average_requested_fragments: 5.2727272727272725
- context_reduction: 0.9584944876197361

## Ground-truth classifications

| SWC | Ground-truth function | Lines | Relevant sessions | Classification |
| --- | --- | --- | --- | --- |
| SWC-107 | deposit | 53–61 | deposit(address,uint256) | MISSED |
| SWC-107 | deposit | 65–73 | not_analyzed_or_unresolved | UNEVALUABLE |
| SWC-114 | deposit | 65–73 | not_analyzed_or_unresolved | UNEVALUABLE |

## Additional unlabeled findings

- constructor(address,uint256,uint256): Improper input validation allowing unbacked token minting (SWC-132). ADDITIONAL_UNLABELED_FINDING
- constructor(address,uint256,uint256): Invalid ratio configuration causing permanent denial of service (SWC-128). ADDITIONAL_UNLABELED_FINDING
- approve(address,uint256): ERC-20 approval race condition (SWC-114). ADDITIONAL_UNLABELED_FINDING

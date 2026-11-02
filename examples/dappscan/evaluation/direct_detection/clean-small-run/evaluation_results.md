# DAppSCAN direct detection

## Metrics

- detected: 0
- missed: 3
- inconclusive: 0
- unevaluable: 0
- labeled_vulnerabilities: 3
- additional_unlabeled_findings: 5
- selected_files: 1
- ready_files: 1
- analyzed_files: 1
- preparation_failures: 0
- evaluable_labels: 3
- unevaluable_labels: 0
- evaluation_coverage: 1.0
- recall: 0.0
- type_accuracy_among_detected: None
- type_accuracy_note: SWC compatibility is required by the matching rule; not an independent classifier metric.
- location_match_rate: 0.0
- total_api_calls: 23
- total_tokens: 68970
- average_rounds: 2.090909090909091
- average_requested_fragments: 5.2727272727272725
- context_reduction: 0.961313934574372

## Ground-truth classifications

| SWC | Ground-truth function | Lines | Relevant sessions | Classification |
| --- | --- | --- | --- | --- |
| SWC-107 | deposit | 53–61 | deposit(address,uint256) | MISSED |
| SWC-107 | deposit | 65–73 | deposit(address) | MISSED |
| SWC-114 | deposit | 65–73 | deposit(address) | MISSED |

## Additional unlabeled findings

- deposit(address,uint256): Incorrect accounting for fee-on-transfer/deflationary underlying tokens (No SWC). ADDITIONAL_UNLABELED_FINDING
- deposit(address): Unpermissioned deposit front-running / theft of transferred funds (No SWC). ADDITIONAL_UNLABELED_FINDING
- _withdraw(address,uint256): Improper input validation causing withdrawal denial of service (No SWC). ADDITIONAL_UNLABELED_FINDING
- _withdraw(address,uint256): Improper input validation enabling free minting (No SWC). ADDITIONAL_UNLABELED_FINDING
- approve(address,uint256): ERC-20 approval race condition (SWC-114). ADDITIONAL_UNLABELED_FINDING

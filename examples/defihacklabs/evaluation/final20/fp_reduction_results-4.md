# Frozen finding-level FP-reduction evaluation

Status: **COMPLETED**. Configuration ready: True.

Frozen baseline: TP 5, FP 10, candidate-level FN 0; precision 5/15 = 33.33%; candidate retention 100%.

## LLM outcomes

```json
{
  "tp_retained": 4,
  "tp_lost": 0,
  "tp_inconclusive": 1,
  "fp_filtered": 7,
  "fp_retained": 2,
  "fp_inconclusive": 1,
  "errors": 0,
  "not_run": 0,
  "tp_retention": 0.8,
  "fp_reduction": 0.7,
  "precision_after_llm_binary": 0.6666666666666666,
  "conservative_precision": 0.625,
  "inconclusive_rate": 0.13333333333333333,
  "total_api_calls_attempted": 22,
  "total_tokens": 54480,
  "average_rounds": 1.4666666666666666,
  "average_requested_fragments": 1.5333333333333334,
  "usage_may_be_incomplete": false
}
```

NOT_RUN is not an LLM error, false negative, or abstention. Null rates mean the experiment has not completed; zero observed calls/tokens is not zero retention. No earlier pilot results are substituted for this frozen run.

| Case | Detector | Finding ID | Ground truth | LLM verdict/status | Correct? | Rounds | Requested fragments | Total tokens |
|---|---|---|---|---|---|---:|---:|---:|
| spankchain | reentrancy-eth | da49c1a96621ac0ec579d1887de3a8ce6ffd1be3d610c7819b78645f05e0e19f | TP | confirmed | yes | 2 | 6 | 8423 |
| spankchain | incorrect-equality | 3f327db1af5b9c5fb9e5718c5815b582ddfe4919e36215440cc0f62b12122388 | FP | false_positive | yes | 2 | 5 | 5970 |
| spankchain | incorrect-equality | 555479cc96ea35b4affe7a8500f50e27fa63fc965a2d8947e485baa85f11f08c | FP | false_positive | yes | 1 | 0 | 1186 |
| spankchain | incorrect-equality | 7ba937136995fd888e3da4dfece9bf0e6fd752d81e5c7530e2dd743b93615f71 | FP | false_positive | yes | 1 | 0 | 2632 |
| spankchain | incorrect-equality | cc4904ecb52d01e681860b4ca265fd72afbcc804e7cb2dbd7ea05169e15b57d8 | FP | false_positive | yes | 3 | 6 | 11176 |
| spankchain | constant-function-asm | f994fab55d8647cd6e028b5811ad9d9e120155326faf4eca1d48fc670807ceaa | FP | false_positive | yes | 1 | 0 | 954 |
| xsurge | reentrancy-eth | 283e78f92682b97003c79c283ba78a6a978eb958c5d03c0c58416f345bf2ebc5 | TP | confirmed | yes | 3 | 4 | 10150 |
| xsurge | incorrect-equality | 0d1056a6b05f35c0661820fd228845121f557c692860dd5fbbf953fb28675bea | FP | false_positive | yes | 1 | 0 | 1831 |
| burgerswap | unused-return | 40750c41d2e69ce2f681004ed403a7bd57f9b162a0d6c3b834760a79f4592478 | FP | false_positive | yes | 1 | 0 | 2112 |
| burgerswap | unused-return | 92f3e299e4e000f89bb0130a7aa47f367305bf9e4b285d6d30ef81f619a48c0c | FP | confirmed | no | 1 | 0 | 2014 |
| visor-finance | arbitrary-send-erc20 | 5d3eca2555a2051ff6412cb4a9bffb2027fe752f63b717bf319dc6d7c96cb1cb | FP | confirmed | no | 1 | 0 | 1558 |
| eleven | unchecked-transfer | 3b17fa7df6d46dd6f38e672c759cc3862bd948b157686032c03d60efb271a8f5 | TP | confirmed | yes | 1 | 0 | 1105 |
| spartan | arbitrary-send-eth | 3426dee9e8ef729ea3be1f7398d4d28fb04cd4158f433644d7058e127a547d3b | FP | inconclusive | abstain | 2 | 2 | 2698 |
| spartan | locked-ether | e8fd05569b88b694d2f90f4cb31d7238e3a16b4bfe1ab3c0143012345d08c63b | TP | inconclusive | abstain | 1 | 0 | 1522 |
| spartan | unchecked-lowlevel | b9cbd4da367d63c678d1e691cd43d6293494bc6363eca3dd96a5cb6468417c3a | TP | confirmed | yes | 1 | 0 | 1149 |

## Methodology

Candidate-level evaluation only: denominator 15; unrelated incident misses/421 findings excluded.
Errors and NOT_RUN are not fabricated inconclusive verdicts; performance rates withheld until all 15 final results exist.
Binary precision = retained TP / (retained TP + retained FP).
Conservative precision = (retained TP + inconclusive TP) / (retained TP + retained FP + inconclusive TP + inconclusive FP).
Four-round production protocol; no selective retries. Prompt journals contain production messages only.

Ground truth is stored only in the frozen cohort and post-inference reports. Technical targets contain production findings/payload/catalog only; workers do not read adjudication or ground-truth files. Source and finding names/comments remain normal production data. No expected outcome, regression result or historical explanation is appended to prompts. Per-call prompt journals enable audit after a real run.

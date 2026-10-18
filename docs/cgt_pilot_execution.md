# Authorized CGT pilot attempt

The frozen 10-finding cohort (5 positive, all 5 negative) was attempted using the configured model `gpt-5.6-luna`. The prompt and selective-context policy were unchanged; ground-truth labels remained on the evaluation side. The remaining 17 findings were not attempted.

All ten source/function preparations succeeded. All ten first API attempts raised `APIConnectionError`. A credential-free diagnostic confirmed that `api.openai.com` DNS resolution fails in this environment. No completed rounds, context requests, explanations, evidence IDs, or verdicts were returned. These are 10 runtime errors, not 10 inconclusive assessments. The empty decided-case confusion matrix is TP=FP=TN=FN=0 and supports no performance conclusion.

Actual billed input/output/total token usage is unknown: all ten attempts lack usage responses. The zero accumulated token counters in raw exports represent no reported usage, not evidence of zero billing. Average completed rounds across attempted findings is zero; an average for successful assessments is undefined.

The supplied temporary credential file was deleted after execution. No credentials were included in artifacts. Network access must be restored before another attempt; existing attempt evidence must be preserved. Authorization remains limited to these ten findings.

Evidence: `results/cgt_authorized_pilot/execution_report.json`, `connectivity.json`, `frozen.json`, and `pilot/{config.json,findings.json,findings.csv,summary.json,errors.json}`.

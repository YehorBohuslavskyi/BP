# Real DAppSCAN scan: ForTube Oracle.sol

Scanned the actual **ForTube 2.0 Oracle.sol** from the local teacher-provided
DAppSCAN checkout, using compiler **0.6.12** and the current two-stage direct LLM
scanner. The model input is byte-for-byte identical to the original source.

## Results

| Measure | Result |
| --- | --- |
| Function coverage | **9/9 rows examined**, including the IACL interface |
| Local static warnings | **8**: four low and four informational |
| High / medium static warnings | **0 / 0** |
| Discovery candidates | **1**, for setACL(address) |
| Accepted confirmed / rejected / inconclusive verdicts | **0 / 0 / 0** |
| Processing outcome | **Partial: one semantic-consistency failure** |
| Provider requests | **3**: two discovery, one verification |
| Actual tokens | **7,243 input + 869 output = 8,112** |
| Paid retries / token-count requests | **0 / 0** |

The local warnings concern two missing zero-address checks, an access-control
change event, a timestamp comparison, two naming conventions and two compiler
version rules. They are warnings, not independently confirmed vulnerabilities.

## Why the LLM result is partial

Discovery suspected an access-control issue in `setACL(address)`. The original
model response returned **rejected**, explaining that only the current ACL
address can reach the assignment. The supplied source contains:

```solidity
require(msg.sender == ACL, "require ACL");
ACL = _ACL;
```

Its structured fields say the mechanism is contradicted and the mitigation is
effective, with no unresolved conditions. It labels the `require` quote as
`protection`, but also labels `ACL = _ACL;` as `dangerous_behavior`. The current
protocol disallows this affirmative dangerous-behavior role alongside a rejection.
The exact failed rule is **REJECTION_UNRESOLVED_OR_DANGEROUS_CLAIM**.

This is a conflict in evidence labeling, not a compiler or API crash. The
explanation and visible caller check support the rejection rationale, but that
does not repair the inconsistent structured response. The original rejection
was therefore **not accepted as a security verdict**. The final result remains
partial; it is neither a confirmed vulnerability nor a claim that the contract
is safe. No model response, field, quote or verdict was rewritten.

A generic prompt/schema clarification could distinguish a guarded sensitive
operation from a reachable dangerous path in future development. This scan did
not weaken the validator or rerun the contract to obtain a preferred outcome.

## Integrity and limits

- Source selected for manageable structure/size from an already exposed
  development project, without consulting Oracle's GT labels or expected outcome.
- Separate user-requested demonstration; no frozen cohort advanced or was rescored.
- Original DAppSCAN source and all files under runs/ and experiments/ unchanged.
- Saved model responses, supplied source, manifests, checksums and prompt/schema
  snapshots preserved separately under raw-artifacts/.
- Offline revalidation checked source identity, request/candidate/evidence
  provenance and the same consistency failure without any new API call.
- Scan stopped after this contract: three requests within the eleven-request
  cap. No uncertain request or paid stage was retried.
- The temporary session key was cleared after the scan and is not in reports.

## Files

- [Readable LLM report](llm-report.html)
- [Detailed LLM report](llm-report.json)
- [Readable local static report](static-report.html)
- [Original contract source](Oracle.sol)
- [Offline consistency review](offline-consistency-review.json)
- [Completion and usage record](scan-completion.json)

This is one real-contract demonstration, not a benchmark accuracy estimate.
Unselected functions and the absence of accepted findings do not establish safety.

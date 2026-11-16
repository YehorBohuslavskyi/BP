# Working scanner — final verification

The scanner is implemented in BP and verified end to end. It is available at
http://127.0.0.1:8501 while the local server is running.

## Genuine fresh LLM demonstration

- Method: Mode B v2 structural discovery, then source verification.
- Source: `examples/scanner/VulnerableVault.sol`, solc **0.8.24**.
- Model: `gpt-5.4-mini-2026-03-17`.
- Coverage: **2/2 function rows examined**.
- Discovery: **one candidate**.
- Verification: **confirmed, high-severity reentrancy in withdraw()**.
- The explanation identifies the external call before the balance update and
  the resulting opportunity to reenter while the balance is still nonzero.
- Consistency validation: **passed**, with supplied source evidence and no
  unresolved evidence, processing failures, skipped or pending candidates.
- Requests: **2 total** (one discovery, one verification), within the approved
  maximum of four. No token-count requests, automatic retries or second run.
- Actual reported usage: **4,478 input + 660 output = 5,138 tokens**.
- No extra context retrieval was necessary for this example. Reported estimated
  verification source-context reduction: **45.3%**, which is not billing savings.
- The temporary session key was cleared after the run and is absent from all
  exported reports and artifacts. The provider credential itself was not changed.

## Verification evidence

| Requirement | Authoritative evidence | Result |
| --- | --- | --- |
| Real local source scanning | Fresh vulnerable and guarded Slither reports | Passed |
| Concrete before/after demonstration | High reentrancy warning in VulnerableVault; absent in GuardedVault; informational call warning retained | Passed |
| Example/upload/paste workflow and source invalidation | Real scanner services and Streamlit integration tests | Passed |
| Current two-stage LLM scanner | Genuine new discovery and verification provider responses with distinct response IDs | Passed |
| Candidate identity, supplied evidence and source quotes | Fresh preparation plus offline manifest/checksum/result revalidation | Passed |
| Selective context requests and conservative failures | Real compiler plus mocked multi-round integration and contradiction tests | Passed offline; this live example did not need retrieval |
| Reviewable reports | Fresh JSON, self-contained HTML and browser screenshot | Passed |
| Request gating and credential isolation | Explicit Run/cost controls; tests of child-only key injection and Forget behavior | Passed |
| Existing modes and research safeguards | Full offline suite: **498 tests passed** | Passed |
| Historical preservation | SHA-256 comparison of **2,386 files** under runs/ and experiments/ | Unchanged |

The raw discovery response, verification session, manifests, supplied source,
prompt/schema snapshots and file hashes are preserved separately in
`scanner-live-artifacts/` and `scanner-live-artifact-hashes.json`. A subsequent
offline audit blocked all model clients/network connections, recompiled the
exact source and revalidated the saved run without another API call.

The original malformed historical report was not repaired or ignored in the
real reuse audit. Scope unit tests use private fixtures, and a separate test
asserts the real audit still refuses malformed input. No frozen experiment was
rerun, no GT scoring or label tuning occurred, and no commit or push was made.

## Teacher walkthrough

1. Open the scanner to inspect the completed direct LLM result and its evidence.
2. Use Local static scan to compare the vulnerable and guarded vault examples.
3. Open or download `scanner-live-report.html` for a readable record of the real
   LLM run; JSON and the raw evidence bundle provide the detailed audit trail.

This demonstrates a working scanner, not comprehensive security coverage or
general benchmark accuracy. LLM confirmation is not an executed exploit proof.
Additional model scans remain explicit user actions and may incur charges.

No required implementation or demonstration-validation work remains.

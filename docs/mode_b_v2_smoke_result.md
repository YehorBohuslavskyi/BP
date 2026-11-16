# Phase 3A live smoke — partial result

The user approved and executed the reviewed plan in their terminal. Run:
`runs/mode-b-v2-smoke-2026-11-09-01/`. Model: `gpt-5.4-mini-2026-03-17`.
This is development engineering evidence, not a held-out benchmark.

## Observed result

- Source: `examples/AccessDemoUnrestricted.sol`, Solidity 0.8.24, 4 FULL_INDEX functions.
- Discovery: 4/4 examined, 2 selected, 2 not selected, one unique candidate.
- Candidate: `batch-0001:C1`, access control / authorization in `changeOwner(address)`.
- Verification: first attempt failed; 0 completed verdicts, 1 processing failure.
- Confirmed/rejected/inconclusive: 0/0/0. Skipped candidates: 0.
- Selectively retrieved fragments: 0. The retrieval branch was not exercised live.
- Actual endpoint attempts: 2 input-count requests and 2 generation requests.
- Discovery usage: 1,494 input + 363 output = 1,857 tokens.
- Verification input was counted as 1,016 tokens before the generation attempt;
  provider usage for that attempt is unknown, not zero.
- Shared reservations: 13,010 tokens. Reservations are not billed usage.
- Reported verification context reduction: 84.73% (20 selected-source estimate /
  131 full-source estimate). This describes the initial selection of a failed session,
  not successful selective verification or detection accuracy.

The budget ledger recorded `GENERATION_FAILED_OR_INTERRUPTED` and the session
recorded `API_CALL_ERROR`. The original exception class/status were discarded.
Consequently this artifact cannot establish whether the cause was a timeout,
API rejection, interruption, or local structured-response validation failure.
Do not claim the failure was caused by missing API credentials: discovery succeeded.

## Source review and isolation

The only supplied source fragment was `changeOwner(address)` (lines 24–26):

```solidity
function changeOwner(address newOwner) external {
    owner = newOwner;
}
```

Manual inspection of the existing source shows that `onlyOwner()` uses this same
`owner` variable to protect `setValue(uint256)`. The unrestricted assignment supports
the discovery hypothesis of unauthorized ownership changes, but the live verifier
returned no verdict or evidence IDs. No exploit was executed or dynamically confirmed.
The modifier was advertised/requested by discovery, not retrieved during verification.

The saved model-input source fields contain no matches for the existing ground-truth
annotation markers. The selected demo has no benchmark annotation comments. No GT
labels or expected answers were added to model input. This is a targeted inspection,
not a universal guarantee that arbitrary labels could never enter another dataset.

## Offline diagnostic correction

`v2_smoke.exception_metadata` now records exception class, HTTP status if available,
interruption flag and Pydantic validation-error count. It excludes raw messages,
response bodies, headers and validation inputs. No inference prompt, schema, budget,
Mode A/B v1/C behavior or saved live artifact was changed. No further API calls occurred.

Full offline regression: **242 passed, 0 failures, 0 errors, 0 skips**. All 1,282
files under the historical artifact roots, now including the eight live-run files,
retained their hashes during the suite; the live-run hash snapshot also matches.

The code change deliberately invalidates the old executable plan's implementation
hash. Do not rerun the old command or edit its manifest. A future diagnostic retry
needs a fresh reviewed plan/output and explicit approval; it is not automatic.
The smoke milestone remains incomplete until verification and selective retrieval
are observed successfully. No accuracy improvement is claimed.

# UNSEEN_EVIDENCE_ID diagnosis and bounded continuation — offline only

The two failures are **confirmed model protocol violations**. Both returned a final
confirmation citing real catalog IDs whose source had not been delivered. The existing
validator correctly refused them. Pydantic/schema parsing succeeded. No request_context
response occurred, so the context resolver was never invoked. No catalog identity or
source-provenance mismatch was found. Primary-only initial source was the intended
methodology, not an accidental retrieval omission.

The old prompt already said that available_context is a menu and only target and
provided_context contain seen source. It did not explicitly distinguish the nested
Phase 1 requested_context_ids from delivered source or enumerate a per-request evidence
allowlist. That presentation may have contributed, but the model's internal reason
cannot be established. No claim that a resolver repair caused better live reliability
is made; this fix has only been tested offline.

## Exact mismatch

| Candidate | Primary source actually supplied | Returned evidence IDs | Unseen evidence |
|---|---|---|---|
| setAuthoriser(address) | fragment-e68e7f5f180ed6cbf7e5 | primary + fragment-15fd53ee88bf2a9b4fd2 + fragment-91517c7c74cd1cf140af + fragment-9837f46d928e8d36b510 | onlyOwner(), onlyAuthoriser(), authoriser state variable |
| transfer(address,address,uint256) | fragment-29920ba34bff663be35e | primary + fragment-91517c7c74cd1cf140af | onlyAuthoriser() |

For both failed candidates, provided_context=[] and there were **zero source requests**.
All unseen IDs were valid catalog entries present only in available_context. Discovery
requested onlyOwner for setAuthoriser and onlyAuthoriser for transfer; those deferred
requirements had not been executed. The setAuthoriser response additionally cited the
unrequested onlyAuthoriser and authoriser state variable.

The complete per-candidate menu-only ID/name lists, returned IDs, primary/source IDs,
Phase 1 requests, usage, session/request paths and hashes are in
[`diagnosis.json`](../experiments/mode-b-v2-unseen-evidence-2026-11-09/diagnosis.json).
Every request-record checksum and response was matched to its saved session. The exact
wire request hash was reproduced against the ledger using the unchanged response schema.
Source/catalog provenance and original prompt hashes were checked from parent artifacts.

The third candidate, _transferOwnership(address), cited only its supplied primary
fragment (fragment-e7e34ed536fda9f66b18). Its completed rejection remains valid for that
specific hypothesis and remains associated with the original prompt/model. It does not
prove the entire access-control path or contract secure.

## Protocol/presentation changes

`direct_verification.py` now explicitly distinguishes four sets:

- target: actual primary source, valid evidence;
- provided_context: actual retrieved source, valid evidence;
- available_context: names/IDs only, not evidence;
- candidate requested_context_ids/related_fragment_ids: discovery planning metadata,
  not evidence unless source has subsequently been delivered.

Every request contains `evidence_policy.allowed_evidence_ids`, primary/provided source
IDs, and still-unsupplied discovery requirements. Already delivered IDs are removed
from the retrieval menu. The model must return request_context first and await a later
source-bearing request before citing an unsupplied ID. Missing source requires requests
or abstention, not an unsupported final confirmation.

No response schema, verdict/evidence acceptance rule or source-delivery policy was
relaxed. Available IDs do not become evidence by appearing in a candidate or example.
The validator still computes its own seen set from actual target/provided source,
independent of model claims. Failed evidence checks now preserve candidate, stage,
round, supplied IDs, unsupplied known catalog IDs and count of unknown IDs. Arbitrary
unknown values are not printed in those safe diagnostics.

## Automatic initial context: considered, not implemented

Automatically supplying bounded Phase 1 requests could reduce requests/rounds and give
attached guards earlier. It increases initial source selection and tokens, can supply
unnecessary source, and changes discovery's role in choosing context. It therefore
needs a separately declared methodology/version and coverage/cost analysis.

It would not by itself repair setAuthoriser's original response: its discovery request
included onlyOwner, but the model also cited onlyAuthoriser and authoriser. Supplying
all IDs cited by an invalid response afterward would not retroactively establish what
the model saw. This task retains primary-only initial source, followed by bounded
request_context retrieval. Only prompt/presentation and diagnostics changed.

## Offline recovery feasibility

The complete structured responses are available and were reprocessed in mocked tests.
Both still correctly fail UNSEEN_EVIDENCE_ID. They cannot be safely accepted by deleting
citations, changing final to request_context, automatically loading missing source after
the fact, or inventing an inconclusive/confirmed verdict. A manual source assessment
would be a different provenance-bearing analysis, not recovery of these LLM verdicts.
The two candidate hypotheses remain usable for a newly approved verification attempt;
no discovery call is necessary. The original failed sessions remain unchanged with null
accepted verdicts, and do not become GT detections.

## Actual consumed usage

| Session | Input | Output | Total |
|---|---:|---:|---:|
| setAuthoriser | 1,972 | 261 | 2,233 |
| transfer | 2,001 | 184 | 2,185 |
| _transferOwnership | 2,002 | 161 | 2,163 |
| Verification total | **5,975** | **606** | **6,581** |

Three generation requests plus three count requests = **six API endpoints**, zero new
discovery calls, and no unknown usage. The ledger reserved 17,975 tokens; reservations
are not actual consumption. Including the previously paid discovery once gives 9,526
actual tokens. This offline diagnosis made zero API calls.

## Proposed continuation — not executed, new approval required

[`continuation-plan.json`](../experiments/mode-b-v2-unseen-evidence-2026-11-09/continuation-plan.json)
binds the new prompt/code to the original dataset manifest, finalized report/session
checksums, source/catalog, recovered import and parent ledger. No original frozen plan
or inference artifact was edited. Only failed candidates batch-0001:cand-1 and
batch-0001:cand-2 are scheduled. The third completed rejection is retained separately
with its old prompt/provenance, not silently relabelled as a new-prompt response.

The narrow continuation runner uses the existing verifier, resolver, deduplication,
aggregation and journaled counted transport. Original candidate IDs and issue groups
remain stable. Superseded failed attempts remain in the parent run. Standard issue
metrics describe retained/current results; `actual_all_attempts_usage_including_history`
adds all parent pipeline attempts and new consumed usage without double counting the
retained rejection. Unknown new usage remains explicitly recorded.

- Model: gpt-5.4-mini-2026-03-17; ProjectWalletAuthoriser only.
- Source/version/catalog: unchanged, checked against original manifest.
- New output: `runs/mode-b-v2-unseen-evidence-continuation-2026-11-09/` (unused).
- Discovery calls: **0**; at most **6 verification generations + 6 count endpoints**.
- New reservation cap: **40,000 tokens**. Parent + continuation reservations <=57,975,
  within the original case's 60,000 cap. Parent 3 + new maximum 6 generation/count calls
  also remain within its original 9+9 caps. No refunds of failed attempts.
- Two candidates, maximum three rounds each; input cap 12,000/call, output cap 4,000,
  eight retrieved fragments/candidate and 8,000 estimated source tokens/candidate.
- Expected 2–6 generations depending on context requests; actual token cost unknown,
  bounded by reservation gates. The larger prompt adds some input overhead.
- max_retries=0; explicit resume validates checkpoints and retains spent budgets.
  Pending/uncertain calls cannot automatically replay. No other contract is included.

Only after approval of this new configuration:

```bash
OPENAI_MODEL=gpt-5.4-mini-2026-03-17 \
.venv/bin/python scripts/run_v2_candidate_continuation.py execute \
  --plan experiments/mode-b-v2-unseen-evidence-2026-11-09/continuation-plan.json \
  --approved-plan-sha256 c272509ebd998cac0d90a244dca0116c02493abba40308dd27c88ef34e4cc45f \
  --run
```

Artifacts: new continuation manifest, request journal, budget ledger/checkpoint,
per-candidate sessions and combined JSON/Markdown report with explicit retained history.
The original dataset manifest now intentionally fails current implementation identity
checks because the verifier prompt changed. Do not bypass that guard to run CoreVoting,
LeverageService or held-out cases; those need a freshly frozen protocol plan and approval.
This is a development protocol fix, not prompt tuning on held-out outcomes.

## Validation and changed files

Modified `src/context_audit/direct_verification.py`. Added
`src/context_audit/v2_candidate_continuation.py`,
`scripts/run_v2_candidate_continuation.py`, `tests/test_unseen_evidence.py`, this report,
and the separate diagnosis/continuation-plan artifacts.

Nine new tests cover the actual two failed responses, primary-only initial evidence,
legitimate multi-round source requests, zero retrieval budget, fabricated IDs, retained
rejection, remaining-budget calculation, mocked continuation/resume and parent checksum
failure. Full offline suite: **343 passed, 0 failures, 0 errors, 0 skips**, with real
OpenAI client construction blocked. All historical artifact hashes are checked separately.
No real API calls, experimental reruns, commits or pushes occurred.

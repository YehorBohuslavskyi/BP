# PRA semantic-consistency diagnosis — 16 November 2026

BP repository: `/home/coca-cola/projects/BP` (Ubuntu-24.04).
The repository already contained substantial uncommitted development work. No commit or push was made.

## Findings

| Function | Original verdict | Original consistency failure | Offline v2 result |
| --- | --- | --- | --- |
| `unlock()` | confirmed | `MECHANISM_NOT_IN_EXPLANATION` | Still blocked: `EXPLICIT_CORE_UNCERTAINTY` |
| `lock()` | inconclusive | `MECHANISM_NOT_IN_EXPLANATION` | Passes as the original inconclusive assessment, in a separate review only |
| `set(address,bool)` | rejected | `MECHANISM_NOT_IN_EXPLANATION`; `REJECTION_UNRESOLVED_OR_DANGEROUS_CLAIM` | Still blocked by the structured dangerous-claim conflict |
| `setACL(address)` | none | Skipped due to candidate budget | Unchanged; no replayed verdict |

All three original failures included an exact normalized-substring check between
`verdict_basis.mechanism` and `explanation`. All three model responses paraphrased
their mechanism. The prompt did require a verbatim statement, so these were real
format violations under v1, but that requirement was an unnecessarily brittle
proxy for semantic consistency. None of the three failures established a genuine
contradiction merely through the phrase mismatch. The validator never required
the candidate vulnerability name verbatim; it required the basis text verbatim.

`unlock()` nevertheless contains a substantive contradiction: it says the core
conditions are established and the mechanism supported, but its explanation admits
the snippet does not establish a concrete theft path beyond authorized
self-withdrawal. Its execution flow establishes an ordinary operation and call
ordering, not a supported harmful consequence. This assessment must not become an
accepted confirmation. The new generic explicit-uncertainty check catches that
admission; it is not a verdict about the contract's actual security.

`lock()` is internally consistent: unknown mechanism, unknown conditions, unknown
mitigation, uncertainty-role source quotes, and explicit missing state/accounting
evidence all support abstention. Its original phrase-match failure was a false
semantic rejection. It can pass offline as the model's original `inconclusive`;
that provides no confirmed or rejected security result.

`set(address,bool)` is ambiguous/internally conflicting at the structured level:
it declares a contradicted mechanism and effective protection but labels the
state-write excerpt `dangerous_behavior`. That is an affirmative structured role,
not simply prose mentioning an attack hypothesis. The conservative mixed-role
failure remains. Moreover, only the function body was supplied; the `auth`
modifier implementation was not. Its name alone cannot establish effective
authorization, and a deposit threshold does not prove caller authorization.
Even relaxing the mixed-role check would not justify accepting this rejection.
No modifier source was retrieved for this diagnosis.

## Code and protocol changes

- `src/context_audit/verdict_consistency.py`: version becomes
  `verdict-consistency-v2`; removes exact explanation-substring membership;
  retains nonblank mechanism, structured status, unresolved-condition, evidence
  ID, source-quote and contradiction checks. Adds a generic check for an explicit
  admission that no harmful path has been established. Explicitly attributed
  hypothetical clauses are excluded from affirmative-danger matching, ending
  at a sentence/contrast boundary so a later residual dangerous assertion still
  fails. The rejection structured-role rule is unchanged.
- `src/context_audit/direct_verification.py`: clarifies that the mechanism may
  paraphrase the same candidate. Adds `review_saved_response()`, a separate audit
  interface for completed and semantic-only failed final responses. It checks
  recorded usage, candidate identity, final-response structure, supplied source,
  request source and evidence before the current consistency gate. For failed
  responses it validates a temporary copy; it never changes the original result.
  Its output records checksums, the original verdict, eligibility, and
  `authorizes_resume=false`. Artifact-envelope checksums remain the caller's
  responsibility and were verified in this replay.
- `tests/test_verdict_consistency.py`: replaces the obsolete verbatim-match test
  with a blank-mechanism guard test.
- `tests/test_pra_consistency_review.py`: 17 new tests covering paraphrases,
  hypothetical rejection discussion, unresolved confirmation, structured
  contradictions, the three saved PRA fixtures, unchanged inputs, and tampering
  with usage, candidate, request source, evidence, original verdict and quotes.

No response-schema change was necessary: the existing structured fields suffice.
The prompt and implementation hashes change, and the consistency version is
explicitly bumped. Frozen plans and prior approvals remain frozen; they do not
authorize execution under v2. Budgets, discovery, candidate selection, scorer and
Solidity source files are unchanged.

Removing substring membership does not add a semantic entailment proof. A
nonempty but unrelated paraphrase may escape deterministic checks; the validator
still cannot prove arbitrary English entailment or Solidity exploitability. No
token-overlap threshold, vulnerability-specific synonym list or extra model call
was substituted for the old phrase match.

## Historical replay

| Case / function | Original verdict | v1 consistency result | v2 consistency result |
| --- | --- | --- | --- |
| wallet / `setAuthoriser(address)` | inconclusive | pass | pass |
| wallet / `transfer(address,address,uint256)` | confirmed | pass | pass |
| wallet / `_transferOwnership(address)` | rejected | pass | pass |
| voting / `execute(uint256,address[],bytes[])` | confirmed | pass | pass |
| voting / `vote(address[],bytes[],uint256,CoreVoting.Ballot)` | rejected | pass | pass |
| owner / `removeOwner(address,address,uint256)` | rejected | pass | pass |
| owner / `addOwnerWithThreshold(address,uint256)` | confirmed | blocked | blocked (same rules) |
| owner / `setupOwners(address[],uint256)` | rejected | pass | pass |
| transfers / `safeTransfer(IERC20,address,uint256)` | confirmed | blocked | blocked (same rules) |

All nine historical replay outcomes and their rule codes are unchanged. Legacy
passes remain `historical_limited`; they are not proof of compliance with the
new source-claim protocol. The existing successful smoke confirmation also passes
its regression test. This replay does not revise historical inference or accuracy.

## Validation and preservation

- Focused suite: **72 tests passed**, including all 17 new tests.
- Full offline suite: **467 tests ran, no test failures; one class-setup error**.
  The same error existed before the changes (baseline: 450 tests ran).
  `test_development_pilot.FrozenPilotTests.setUpClass` cannot parse
  `runs/mode-b-v2-verification-retry-2026-11-09-01/analysis/report.json`:
  `Extra data: line 390 column 1 (char 21204)`. Tests in that class were not run.
  This historical file was not repaired or truncated.
- The offline suite and replay blocked OpenAI client construction and Python
  socket connections. Existing installed compilers were used; no downloads.
- Frozen PRA source identity matches freshly prepared source.
- All three PRA session envelope checksums match their saved results.
- SHA-256 comparison: **2,386 historical files unchanged** under `runs/` and
  `experiments/`, with no added or removed files in those trees.
- No inference or token-count requests; no new case execution; no GT label
  inspection for diagnosis/tuning; no scoring, budget or benchmark changes.
- Original finalized PRA counters, finalization seal, manifests, journals and
  skipped candidate remain unchanged. No accepted security verdict was inserted.

## Recommended next step

Retain PRA as its original finalized partial development run. Preserve the
separate v2 offline review, where only `lock()` is eligible as inconclusive.
Neither the saved `unlock()` confirmation nor the saved `set(...)` rejection can
be safely accepted from this evidence; do not rerun PRA automatically. Freeze and
review v2 before preparing any separately authorized continuation. Address the
malformed historical report through a separately recorded integrity diagnosis
before claiming a fully passing suite; never silently rewrite it.

The detailed JSON contains original PRA assessment fields, execution flows,
incomplete evidence, evidence IDs, exact supplied fragments and old/new rule
results. It is a separate audit record, not a replacement inference report.

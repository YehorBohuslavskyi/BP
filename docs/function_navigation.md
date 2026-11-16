# Source-linked function navigation and investigation limits

The existing source catalog now carries `function-index-v1`, a compiler-backed
navigation index for each available function and modifier. It links exact source
fragment IDs instead of resolving calls by name. Overloads, inherited source,
same-name functions in different contracts, libraries, modifiers, state
declarations and direct writers retain their source identities.

Each node records outgoing calls, incoming callers, attached modifiers and state
reads/writes. Reverse links are built from the forward links. Failed IR and
unavailable source are explicit unknowns. Dynamic function pointers and low-level
calls remain unresolved. A high-level external call points to its compiler-known
declaration and explicitly leaves the runtime implementation unknown. Caller
completeness is scoped to indexed source and is false if the index contains
unresolved paths; it never proves runtime reachability or authorization.

Discovery sees whitelisted relationship metadata. Verification receives the
relationships of functions whose source has actually been delivered, plus a
menu prioritized by shortest graph distance from delivered fragments. This
reveals relevant callers, callees, guards and state dependencies without
automatically delivering extra source. Cycles are bounded by visited IDs.
All existing round, fragment, source, input and total-token guards still apply.
An ID in the relationship graph or menu is not evidence until source is supplied.

The discovery instructions also ask for a specific condition and harmful
consequence to test. Sensitive operations alone are not vulnerability evidence.
The consistency rules remain `verdict-consistency-v4`; their logic was not relaxed.

## Provenance

The full index is serialized with discovery artifacts, bound by
`function_index_sha256`, and included in preparation/discovery/verification code
identities. Reconstructed prepared catalogs validate it. Changes require fresh
preparation and a fresh execution plan. Old manifests, finalized cases and
approvals are not rewritten or silently migrated. Historical responses remain
available through the separate read-only review interface.

## Explicit fresh-run limit profiles

`investigation-limits-v1` provides the following development configurations:

| Profile | Candidates | Rounds/candidate | Extra fragments | Verification tokens |
| --- | ---: | ---: | ---: | ---: |
| baseline | 2 | 3 | 8 | 200,000 |
| rounds | 2 | 5 | 8 | 200,000 |
| context | 2 | 3 | 12 | 200,000 |
| coverage | 6 | 3 | 8 | 200,000 |
| expanded | 6 | 5 | 12 | 400,000 |

These profiles retain an 8,000-token source limit, 12,000-token input limit and
4,000-token verification output limit. They do not promise every candidate can
finish: total usage can stop processing sooner. Baseline subscription preparation
continues preserving the parent's existing round/source limits and its original
two-candidate cap. Non-baseline subscription profiles require an explicit small
development pilot and a fresh source-prepared proposal; they cannot silently
change validation/held-out evaluation settings.

The scanner exposes these options under **Review depth**. **Current settings**
preserves the previous scanner defaults. Fragment and source-token limits are
also editable. Changing settings or preparing code never starts inference.

For a future explicitly authorized standalone scan:

```bash
.venv/bin/python scripts/scanner.py scan source.sol --method direct --provider codex --limit-profile expanded --live --output NEW_DIRECTORY
```

For offline preparation of a fresh development plan:

```bash
.venv/bin/python scripts/run_subscription_evaluation.py prepare --proposal FRESH_SOURCE_PROPOSAL --output NEW_PLAN --development-pilot-size 1 --limit-profile rounds
```

The standalone command above starts real model requests and requires separate
authorization. It was not executed during implementation. Old source-preparation
bundles correctly fail current identity checks and must not be patched in place.

The scanner's actual Codex transport cap now includes the selected verification
budget and discovery allowance, rather than retaining an unrelated fixed
200,000-token default. Fresh subscription plans enforce both individual case
and overall ceilings. Inconsistent case call/verification caps fail before
transport construction. Observed-token thresholds are stop conditions before
the next request; the last response can exceed them. Reports retain that usage.

## Validation and limits of the claim

Offline compiler tests cover exact forward/reverse pointers, overloads,
inheritance, distinct contracts, modifiers, libraries, dynamic calls, missing IR,
recursive traversal, serialization/hashes, menu source isolation and a mocked
multi-round caller/guard investigation. Profile tests show additional rounds
deliver additional source, a larger fragment cap admits more source, and a
larger candidate cap reduces synthetic skips. They do not invent confirmations.

Two previously analyzed development sources still include all 65 function rows
under the same 24,000-character batch bound. Their richer metadata requires
seven discovery batches instead of five; fresh plan budgets must account for
this increase. All 12 separate historical response review outcomes are unchanged.

These checks establish index and budget behavior, not improved real-model
precision/recall. Dynamic behavior, external implementations and unspecified
security requirements can still require abstention. A separately approved
development check is needed before claiming an observed model improvement.


## Source-only refresh and completed development check

`scripts/reindex_source_proposal.py` rebuilds one to three explicitly named
development cases into a fresh preparation directory. It verifies unchanged
source, sanitized dependencies and installed compiler, retains case order,
splits and frozen budgets, excludes label payloads and never starts inference.
Existing parent and historical output directories cannot be modified.

```bash
.venv/bin/python scripts/reindex_source_proposal.py --parent-proposal OLD_PROPOSAL --output FRESH_SOURCE_PROPOSAL --case-id EXACT_DEVELOPMENT_CASE
```

The final full offline suite passes all 575 tests. Source-only reconstruction
was also validated on one previously exposed real development source.

After separate explicit approval, one handcrafted LinkedWithdrawal development
control completed with five Codex turns and 73,863 reported tokens. The model
requested seven source fragments across four verification rounds and confirmed
high-severity reentrancy through an unguarded caller path. Current consistency
and saved source/evidence checks pass; processing failures and budget skips are
zero. No dynamic exploit or precision/recall evaluation was performed. This is
an end-to-end navigation check, not an independent accuracy improvement claim.
The one-time authorization is consumed; no automatic repeat is authorized.

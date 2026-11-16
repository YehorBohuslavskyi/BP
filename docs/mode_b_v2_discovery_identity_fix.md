# Discovery identity validation — offline repair

The first ProjectWalletAuthoriser response used a contract-qualified function name
in **contract** for all three hypotheses. The primary_function and primary_fragment_id
fields were already correct. Exact original values:

- `ProjectWalletAuthoriser.setAuthoriser(address)`
- `ProjectWalletAuthoriser.transfer(address,address,uint256)`
- `Ownable._transferOwnership(address)`

The old Pydantic schema accepted these nonempty strings, then semantic validation
required contract == `ProjectWalletAuthoriser`, raising `Candidate primary function
mismatch`. The last entry is an inherited function, declared in Ownable but analyzed
in ProjectWalletAuthoriser. This is a confirmed protocol failure, not a security
verdict. Historical accounting remains 2,945 tokens and zero verification sessions.

## Validation changes

`direct_discovery.py` now explicitly instructs the model to keep the canonical batch
contract, full signature and opaque fragment ID in three separate fields. Inherited
functions use the analyzed batch contract. The response schema and API format are
unchanged.

`normalize_identity` requires a unique primary row in the supplied batch and a real
catalog function fragment. It accepts canonical fields unchanged. A qualified alias
is accepted only if it is exactly `batch_contract.signature` or
`compiler_recorded_declaring_contract.signature` for that same primary fragment and
resolves uniquely among the supplied rows. The same conservative rule handles an
alias in primary_function. There is no suffix matching, dotted-string splitting,
bare-name overload selection or inference of missing identities. A declaring contract
name alone does not substitute for the analyzed contract.

Examples rejected: `Unknown.withdraw(uint256)`, bare `Unknown`, bare `Base` when
analyzing Vault, `Vault.withdraw()` paired with the withdraw(uint256) fragment,
fabricated IDs, qualified aliases resolving to multiple rows, and unknown/unadvertised
related or requested references. Existing source provenance, annotation sanitization,
opaque ID, source-access and verifier evidence checks are unchanged.

After complete response-schema and examined-function validation, semantic validation
can isolate invalid candidates in a mixed batch. Accepted candidates proceed;
per-candidate protocol errors are recorded in discovery errors and original identities
are retained with normalized identities in the round's candidate_validation list.
These diagnostics do not represent rejected security hypotheses. Ambiguous duplicate
IDs/claims remain rejected together, preserving existing strict duplicate behavior.
A batch with no valid candidates despite nonempty proposals still fails. Invalid
schema/types or incomplete examined-function coverage still fail the entire batch;
there is no automatic JSON repair or silent acceptance of malformed candidates.

The raw saved model assessment is never mutated. Verification receives canonical
candidate fields only; original identity strings remain provenance/diagnostic data.

## Offline reprocessing

[`offline_reprocessing.json`](../experiments/mode-b-v2-identity-fix-2026-11-09/offline_reprocessing.json)
records the original artifact hash/manifest, matched current source/catalog identity,
normalizer hash, original and normalized identities, six examined rows and three
accepted hypotheses. Reprocessing used zero calls/tokens. No verification verdicts
were generated and the historical run/report remain unchanged.

The derivative is explicitly **not** an executed discovery manifest under the new
prompt. Ordinary pipeline resume must not silently treat it as one. Safe offline
identity recovery is established; using recovered candidates for live verification
would require an explicit provenance-aware import/review step. No discovery API call
is necessary merely to recover these three candidates.

## Tests and integrity

Added 14 tests in `tests/test_discovery_identity.py`: canonical identity; qualified
contract and function fields; overload mismatch; inherited declarations; unknown
contracts; mismatched/fabricated primary IDs; ambiguous aliases; inaccessible context;
mixed valid/invalid candidates and coverage; duplicate IDs; exact saved real response;
and explicit prompt field rules. The real-response test also checks source/catalog
identity and that the original response is unchanged.

Full offline regression: **306 passed, 0 failures, 0 errors, 0 skips**. Real OpenAI
client construction was blocked during the suite. An initial regression exposed
first-wins duplicate handling; the implementation was corrected to reject ambiguous
duplicates together and all original tests now pass without changes. Python compile
checks and git diff checks passed. All 1,334 pre-existing artifact files checked,
including the failed run, previous experiments and frozen pilots, retained hashes.
No real API calls, experimental reruns, commits or pushes occurred.

## Optional fresh bounded run — not executed or approved

No paid retry is needed for offline recovery. If a full new inference run is desired,
[`fresh-run-plan.json`](../experiments/mode-b-v2-identity-fix-2026-11-09/fresh-run-plan.json)
binds the corrected prompt/implementation to the same source and model. It deliberately
runs fresh discovery, rather than disguising old output as a new-prompt response.
This optional plan is separate from the offline derivative and needs new approval.
A future verification-only importer would avoid the repeat discovery call; it was
not added to this protocol-fix task.

- Model: `gpt-5.4-mini-2026-03-17`; ProjectWalletAuthoriser only, B v2.
- Output: `runs/mode-b-v2-identity-fix-2026-11-09/ixo-authoriser/b2/` (unused).
- Maximum 12 generation + 12 count requests, 40,000 reserved tokens; stage limits
  allow 1 discovery + 3 candidates × 3 verification rounds = 10 generations.
- Input cap 12,000/call; discovery output 8,000; verification output 4,000;
  at most 8 retrieved fragments and 8,000 estimated source tokens per candidate.
- No automatic retry; uncertain or interrupted requests retain reservations and
  cannot be silently replayed. No other contract or B v1 run is included.

Only after separate approval:

```bash
OPENAI_MODEL=gpt-5.4-mini-2026-03-17 \
.venv/bin/python scripts/run_development_experiment.py execute \
  --plan experiments/mode-b-v2-identity-fix-2026-11-09/fresh-run-plan.json \
  --approved-plan-sha256 23c817ca10bd4ed59245dc3e2b53c19c04faca5f2401696868e0b420dcba8785 \
  --run
```

Changed implementation: `src/context_audit/direct_discovery.py`. Created tests, this
audit, the offline derivative and optional plan. Historical plans now fail the
implementation identity check; do not update their checksums or bypass that guard.

# Mode B v2 verifier consistency

`verdict-consistency-v1` is a development protocol revision. Discovery, candidate
selection, source retrieval, budgets and GT scoring are unchanged. No additional
model call or automatic paid retry is used. The verifier prompt/schema and
implementation hashes change, so previous execution approvals cannot authorize
new runs automatically.

The original verifier accepted a structurally valid final response once evidence
IDs belonged to supplied source. It did not check whether the explanation
contradicted the verdict. A model could confirm the existence of a normal path
while denying the vulnerability.

New live responses retain the original eight fields and require `verdict_basis`.
For `request_context` it must be null. For final responses it contains:

- `mechanism_status`: `supported`, `contradicted`, `unknown`, relative to this candidate.
- `core_conditions`: `established`, `not_established`, `unknown`.
- `mitigation_status`: `none_identified`, `effective`, `ineffective`, `unknown`.
- `mechanism`: a statement taken from the explanation.
- `mitigation_reason`: the protection/contradiction or residual-path explanation.
- `unresolved_conditions`: remaining conditions that affect the conclusion.
- `evidence_claims`: `{fragment_id, source_quote, role}` entries, with role
  `dangerous_behavior`, `protection`, or `uncertainty`.

The strict OpenAI schema and prompt expose these definitions. Evidence IDs must
still be actually supplied. Claims must cite those IDs and quote supplied code;
comment-only excerpts and fabricated quotes fail. Quote comparison ignores code
whitespace/comments but preserves string-literal contents. This is bounded to
the existing source context, with no retrieval during validation.

A confirmation requires a supported mechanism, established core conditions,
no effective/unknown core mitigation, no unresolved conditions, and dangerous
source claims. A claimed mitigation bypass requires its source and a residual
dangerous source claim. A rejection requires a contradicted mechanism and a
source-grounded protection/contradiction. An abstention requires unknown mechanism
status and meaningful missing conditions. Narrow relational prose checks detect
explicit unsupported hypotheses, prevention, unreachable/core-unknown paths and
verdict/explanation/flow conflicts. They handle negation and do not reject the
word `checked` alone. Mixed risks and protections require a grounded resolution.

Failure produces processing status `processing_failed`, error code
`SEMANTIC_CONSISTENCY_FAILED`, and **null accepted verdict/severity**. The original
model verdict, failed rule codes, safe candidate/evidence IDs and round are
recorded. The original response remains unchanged in the saved round; API usage
is counted once. The system never substitutes another security verdict. Existing
aggregation counts this as a processing failure and separately reports
`semantic_consistency_failures`. The unchanged GT scorer handles unmatched labels
conservatively. Reports show validation diagnostics without putting source quotes
or arbitrary model prose into ordinary error diagnostics.

Historical eight-field artifacts retain their original schema and provenance.
`LegacyVerificationResponse` and `replay_consistency()` provide an explicit
offline review copy. Replay checks candidate/source/evidence/location/usage and
the recorded request; it flags detectable prose contradictions without inventing
new model fields. A legacy pass is marked `historical_limited`: it is not proof
that the response meets the new source-claim protocol. Historical artifacts and
their previous adjudications are never rewritten. Default live/resume paths do
not downgrade to this parser, and changed manifests require a new output/approval.
The existing explicit candidate-continuation path rechecks retained legacy results
before allowing them to remain historical inputs.

Replay results for the completed development cases are recorded separately in
`experiments/mode-b-v2-consistency-hardening-2026-11-10/`. Both the Transfers and
OwnerManager add-owner confirmations are flagged: their explanations describe
protections and/or admit unresolved core evidence. The ProjectWalletAuthoriser
transfer confirmation, ownership rejection and abstention, both CoreVoting
outcomes, the OwnerManager rejections and the successful smoke confirmation pass
the limited historical checks. These are consistency reviews, not new inference
or revised accuracy claims.

Pre-fix and post-fix results must not be pooled as one unchanged protocol. Apply
the same replay layer to pre-fix artifacts and disclose its limited coverage;
fully matched live comparisons require separately approved runs under one
protocol revision. No old stages should be rerun merely to manufacture comparability.

The proposed continuation contains only the five remaining frozen development
cases. Its single-case commands stop after each contract, use the same model and
per-case limits, and require separate execution authorization. Existing results,
validation cases and held-out cases are excluded. No continuation is executed by
preparation or tests.

Limit: deterministic field/quote/relational checks do not prove arbitrary English
entailment, Solidity reachability or exploitability. A model can still make a
consistent but factually wrong claim, omit a mitigation, or quote code that does
not substantively prove its assigned role. The new gate is protocol validation,
not an independent detector, theorem prover or exploit validator. Unrecognized
paraphrases can evade prose checks, and ambiguous valid statements may be flagged.
Manual review and controlled evaluation remain necessary.


## Offline v2 correction — 2026-11-16

The frozen runs described above retain v1 provenance. Current code now uses
`verdict-consistency-v2`: mechanism paraphrases are permitted, explicitly
attributed hypotheses are not treated as affirmative risk assertions, and an
explicit admission of an unestablished harmful path prevents confirmation.
The existing schema, structured-role rules and source/evidence guards remain.
`review_saved_response()` emits a separate offline audit and never authorizes
resume or replaces a finalized result. See
[the PRA diagnosis](mode_b_v2_pra_offline_diagnosis.md) and
[the separate review record](reviews/pra-consistency-v2-2026-11-16.json).
Only the saved PRA lock abstention passes this review; the unlock confirmation
and set rejection remain blocked. No API requests or historical changes occurred.

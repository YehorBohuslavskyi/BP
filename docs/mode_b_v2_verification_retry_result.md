# Verification-only retry: observed response-validation failure

Run: `runs/mode-b-v2-verification-retry-2026-11-09-01/`.
The user executed the prepared verification-only command. No additional API requests
were made while inspecting this result.

Confirmed observations:

- Saved discovery was reused; zero discovery calls in this retry.
- One input-count request and one generation request.
- Generation returned response ID `resp_0273a81357f9cb62016af1bf79dc7487d29f62d9be653684c7`.
- Usage: 1,016 input + 183 output = **1,199 tokens**, with zero reported reasoning tokens.
- Generation duration recorded: approximately **2.174 seconds**.
- Local response parsing raised **Pydantic ValidationError**, one validation error.
- Candidate `batch-0001:C1` remains a processing failure with null verdict.
- No additional context fragments were retrieved.

The response/accounting preservation change worked: this is now a known local
validation failure after receipt of an API response, rather than an unknown transport
outcome. It does not prove the original run failed for the same reason. The retry's
specific failed field/rule and raw model response were not recorded, so they cannot
be recovered from these files. No particular protocol violation is asserted.

The remaining logging gap was corrected offline in `v2_errors.py`: validation
errors now include allowlisted Pydantic error types, safe field locations and stable
codes for the verifier's six cross-field rules. Arbitrary field names are replaced;
raw messages, response text, values, inputs and contexts are never emitted. No
acceptance rule, prompt or model configuration was relaxed or tuned.

New tests exercise all six rule mappings and demonstrate that bad field values and
unknown field names cannot leak through diagnostics. Full regression result:
**261 passed, 0 failures, 0 errors, 0 skips**. All **1,290 historical artifact files**
checked, including both live runs, retained their hashes. No commits or pushes.

No further retry was executed or prepared. Both previous executable plans now also
fail their implementation-identity checks after the diagnostic update, and their
existing output directories cannot be reused. Keep these runs unchanged. This remains
an incomplete engineering smoke test, not a verified vulnerability or accuracy result.

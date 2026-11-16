# Results and next development step — 16 November 2026

The scanner can use the installed Codex CLI signed in with ChatGPT. No API
credits were purchased, no API-key requests were made and no paid API fallback
was used. This consumes the existing Codex allowance and remains subject to
its limits; it is not unlimited free inference or API-token transfer.

## Actual evaluation

- Planned: 73 fresh source files from 58 projects, preserving project/duplicate
  splits: 37 development, 9 validation and 27 held-out files.
- Free Slither comparison: all 73 compiled/scanned successfully. There are 1,508
  warnings associated with target files (81 High and 156 Medium). These overlap,
  include informational warnings and are not validated vulnerability counts.
- Codex: 10 development files attempted, 3 complete and 7 partial; 63 unrun.
  All validation and held-out files remain unrun by the model.
- 40 attempted turns: 39 with reported usage and one failed/unknown turn.
  Recorded usage: 682,827 tokens, including 110,592 cached input tokens.
  Total usage is a lower bound because the failed turn has unknown usage.
- 266 of 289 structural rows in attempted files examined; 23 unevaluable after
  the last discovery failure. Discovery produced 29 hypotheses. Verification
  accepted one rejection, seven processing failures and 21 skipped candidates.
  There were zero accepted confirmations and zero accepted inconclusive verdicts.
- No GT labels were loaded. Precision and recall are undefined here; unlabelled
  static warnings and model hypotheses cannot be treated as false positives.

The final turn produced `CODEX_TURN_FAILED_OR_LIMIT_REACHED`. The old adapter
did not retain its public error message when the CLI exited with status zero.
The saved data cannot distinguish quota, connectivity or another client failure.
The runner stopped automatically without retrying or falling back to the API.
No further model requests were made.

## Safe fixes and verification

After the run stopped, diagnostics were fixed to preserve redacted public error
events for future zero-exit failed turns, while excluding hidden reasoning and
credentials. One regression covers the error, redaction and no-retry behavior.
An existing UI smoke test now has the same 30-second startup allowance as other
scanner UI tests, after a transient three-second timeout; its assertions remain.
The complete offline suite then passed 515 tests. Three additional focused
exposure-registry tests passed after that suite. No tests used model allowance.

Only the ten actual attempts are recorded in a separate exposure registry, so
future fresh plans exclude them, including the unknown last outcome. Unrun
preparation files are not marked exposed. The registry fails closed on corrupt
records. The evaluated implementation is retained in `protocol-snapshot/` before
these diagnostic/exposure changes. The frozen plan must not be reused with the
changed implementation. Any continuation requires a fresh, reviewed plan.

All 2,386 historical files under runs/ and experiments/ are byte-identical, with
no added or removed files in those trees. Raw responses, failures, seals and
journals in this separate evaluation have not been revised or accepted offline.

## Next stage

The subscription connection is working; model-protocol reliability needs more
development before claiming scanner accuracy or moving to attacker emulation.
Address repeated/invalid source-ID requests and account for Codex context overhead
in verification budgeting, using development cases only. Freeze the revised
protocol before a separately authorized fresh run. Keep validation/held-out
labels isolated and never relax consistency checks to force confirmations.

Attack emulation should later use isolated local test chains. A successful
exploit can provide concrete evidence under stated assumptions; a failed attempt
alone does not establish that a finding is a false positive.

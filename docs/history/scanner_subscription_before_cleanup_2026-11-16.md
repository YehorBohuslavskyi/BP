# Scanner through the included Codex allowance

The scanner supports the installed official Codex CLI with ChatGPT sign-in.
This route uses the account's existing plan allowance. It does not transfer chat
tokens into API credits. It removes API-key environment variables, forces ChatGPT
authentication and has no paid API fallback or credit purchase step.

## Use

1. Check `codex login status` in the environment containing the installed CLI.
   It must report ChatGPT sign-in; API-key login is rejected by this backend.
2. Start the local scanner, select Direct LLM scan (v2), and prepare the source.
3. Keep **Codex subscription** selected. The default model is `gpt-6-luna`.
4. Confirm use of the existing Codex allowance and explicitly click Run.

For the command line:

```bash
.venv/bin/python scripts/scanner.py scan /path/to/Contract.sol \
  --method direct --provider codex --live --model gpt-6-luna
```

No account-security settings are changed. Individual Daybreak enrollment is a
separate access program with its own requirements. Ordinary subscription sign-in
was already active for the scanner checks; this does not grant Daybreak access.

## Limits and isolation

Subscription limits still apply. Reported allowance, authentication or transport
errors stop the scan; no automatic application retry is made. The CLI may perform
its builtin connection retries. Output-token limits are prompt guidance on this
backend, not a hard provider cap. Observed-token thresholds are checked before
the next turn, so the last turn may exceed them. CLI context overhead is included
in reported usage and is not the same as source-context size or API cost.

Each request uses a temporary source-only prompt and strict response schema.
Shell, browsing, apps, plugins, delegation and project instructions are disabled.
Unexpected tool events invalidate the response. Authentication files are never
read or copied by the scanner. Public results and usage are retained; hidden
reasoning is not exported. Unknown usage and partial outcomes remain visible.

## Separate research protocol

This is a separate backend/model condition from the historical API experiments.
Do not pool these results as if they used the same model. Consistency protocol
`verdict-consistency-v3` clarifies neutral `context` evidence versus observed
`protection` and established `dangerous_behavior`. Guarded assignments can be
context in a rejection; context alone cannot confirm or reject a candidate.
Existing contradiction, quote and supplied-evidence checks remain enforced.

Before fresh evaluation, 514 offline tests passed. A development subscription
control made three real Codex turns with zero API-key calls and recorded 37,264
tokens. Its model confirmation failed the mitigation-evidence consistency rule;
that partial result remains unchanged. It is not an accepted security finding.

The frozen DAppSCAN evaluation contains 73 fresh sources from 58 projects:
37 development, 9 validation and 27 held-out sources. Five prior sources are
excluded. Existing project and duplicate splits are preserved. Source/provenance
hashes are checked before execution, and code identity stays frozen during it.
Global limits are 300 Codex turns and 5 million observed tokens, with no API-key
billing. Evaluation labels are not loaded during inference. The same source set
also receives a free local Slither baseline. Raw warning counts can include
dependency findings and duplicates; they are not precision or recall.

The evaluation output is separate from historical runs and experiments. Every
case retains its original response, usage, consistency outcome and completion
seal. Finalized cases cannot be replayed automatically. Partial and unrun cases
must be disclosed. Independent post-inference review is needed for detection
quality; source-consistent model confirmation is not an executed exploit.

Automated attack emulation remains a later stage, restricted to isolated local
test chains. A failed exploit attempt alone does not prove a false positive.


## Source-request hardening follow-up — 2026-11-16

Context-bound Codex schemas, explicit retrieval capacity and CLI-overhead budgeting
passed a fresh two-file development pilot: seven turns, 133,450 reported tokens,
zero API-key calls, zero source-ID failures or budget skips. One inconclusive
verdict was accepted; one original abstention remains a saved v3 consistency
failure. Its separate v4 review is inconclusive only. The v4 correction is tested
offline (535 full tests passed), with no new live check after that rule change.
GT labels and validation/held-out files remain isolated. See
reviews/scanner-source-request-hardening-2026-11-16/report.md for limits and evidence.

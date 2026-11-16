# Source-request and budget hardening — 16 November 2026

The request and budget fixes were tested offline and through a fresh two-file
DAppSCAN development pilot using the existing ChatGPT-authenticated Codex CLI.
No API-key calls, credit purchases or paid API fallback occurred. Ground-truth
labels stayed unread. Validation and held-out files were not used.

## Changes

The Codex wire schema now allows only unseen menu IDs in context requests and
only delivered source IDs in evidence/claims. It limits request counts to the
remaining fragment capacity. Menu entries show estimated source size, exclude
individually oversized fragments, and state remaining rounds and capacity.
The last round requires a final assessment; missing evidence still permits
inconclusive. The local validator independently rejects bad IDs and combined
source-budget overruns; no fuzzy ID correction, automatic retry or verdict
substitution was added.

Preflight budgeting includes a 32,000-token reserve for CLI/schema overhead,
above the 26,335 maximum observed in saved verification calls. The reserve can
increase from actual reported usage. Estimates are not hard provider caps.
Actual usage, including cached input tokens, is retained without subtracting
overhead. A schema-invalid completed response now retains known usage and its
original public output. Actual constrained prompts/schemas are saved with hashes.
The UI and CLI expose the verification budget; Codex worker timeout allowance
now matches the longer backend timeout. The API backend keeps its existing path.

The separate pilot preserved original API preparation budgets as provenance and
declared actual Codex budgets separately: two candidates and three rounds per
file, 200,000 verification tokens and 400,000 observed total tokens per file.
Global limits were 20 turns / 750,000 observed tokens; the two files' individual
call bounds allowed at most 14 turns in total. The last turn can exceed an
observed-token threshold. No application retries or count-token calls occurred.

## Real pilot result

Sources: OVM_SequencerEntrypoint.sol (openzeppelin-Optimism) and
BaseParaSwapAdapter.sol (QuillAudits-AAVE-ParaSwap Adapter). Both were fresh
development files from the existing frozen project splits.

- Both files attempted; one complete, one partial.
- Seven Codex turns, 133,450 reported tokens, zero unknown-usage turns.
- All 18 structural function rows examined; two candidates generated.
- Zero repeated/invalid source-ID failures and zero budget skips.
- One accepted inconclusive verdict; one semantic-consistency failure.
- Zero accepted confirmations or rejections. No exploits were executed.

This small live result establishes that the CLI accepted the constrained wire
schema and completed the retrieval flow. It does not measure dataset accuracy
or establish that the scanner's general reliability has improved.

## Separate consistency review

The partial response was originally inconclusive. It observed an ignored return
value, but explicitly left signature authorization and harmful consequences
unresolved. The v3 prose check treated the word "ignored" as a dangerous path
without recognizing the distinction between a source fact and exploitability.

Consistency v4 separates a neutral operation-risk observation from an asserted
harmful path for structured abstentions. Unknown mechanism and explicit missing
evidence remain required; an affirmative dangerous_behavior claim still blocks
abstention. Confirmed/rejected and legacy prose checks remain unchanged. Existing
source-quote, evidence-ID and contradiction checks remain enforced. Six new
regressions cover this distinction and the retained safeguards.

The separate offline review finds the original response eligible only as
inconclusive under v4. Its saved failure, original counters, response and seal
remain unchanged. It is not a confirmation, rejection or authorization to resume.
The evaluated v3 code is saved in the pilot's protocol-snapshot directory.
The current v4 change has not received a fresh live check.

## Validation and next stage

All 535 offline tests pass. The original 2,620 protected files (2,386 historical
files plus the prior subscription evaluation) and every sealed pilot artifact
remain byte-identical. No commits or pushes were made. Only actual attempted
sources enter the new exposure registry, preventing future fresh-plan replay.

The next stage is a fresh development check of consistency v4, followed by a
frozen larger evaluation with independent post-inference adjudication. Precision
and recall are not reported from this pilot. Attacker emulation remains later:
isolated local test chains, explicit assumptions, and failed exploitation treated
as inconclusive rather than automatic proof of a false positive.

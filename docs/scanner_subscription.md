# Scanner through the Codex allowance

The default direct backend uses an installed Codex CLI signed in with ChatGPT.
It uses existing account allowance, removes API-key environment variables and has
no paid API fallback. Source preparation is local; model requests need an explicit
Run action and consent. The separately billed API backend remains optional.

## Setup and use

1. Run `codex login status` in the environment containing the CLI. This backend
   requires ChatGPT sign-in and rejects API-key login.
2. Start `.venv/bin/python scripts/scanner.py serve` and open the local interface.
3. Choose Direct LLM scan, prepare the source and select Codex subscription.
4. Review model, investigation limits and usage thresholds, then explicitly Run.

The configured default model is `gpt-6-luna`. Availability and account allowance
must be checked in the execution environment; the application makes no promise
that a subscription is unlimited or equivalent to API credits.

For an independently authorized command-line scan:

```bash
.venv/bin/python scripts/scanner.py scan Contract.sol --method direct \
  --provider codex --model gpt-6-luna --limit-profile expanded --live --output NEW_OUTPUT
```

## Limits and isolation

See [function navigation and profiles](function_navigation.md) for individual
round, context and candidate experiments. The interface exposes the actual
transport ceiling, including discovery overhead. Allowance, authentication or
transport errors stop execution. There are no application retries or paid
fallbacks. CLI connection retries may still occur.

Reported tokens include CLI context overhead. Observed-token thresholds stop
the next request, so the last response may exceed the threshold. Output-token
guidance is not a hard provider cap. Unknown usage and partial outcomes remain
visible; selected source estimates are not billing savings or detection accuracy.

Requests use a temporary source-only prompt and strict response schema. Shell,
browsing, apps, plugins, delegation and project instructions are disabled for
model execution. Unexpected tool events invalidate a response. Authentication
files are never read or copied; hidden reasoning is not exported.

## Research status

Current consistency checks use v4. A handcrafted navigation check completed with
five turns and 73,863 reported tokens; its confirmed reentrancy assessment passes
source/evidence and consistency checks. It is development evidence, not a frozen
accuracy evaluation or an exploit proof. See the
[compact review](reviews/function-navigation-2026-11-16/summary.json).

Larger earlier subscription studies, all partial outcomes and actual exposure
registries remain preserved. Old source sets are not automatically fresh: previous
model attempts, including failed or uncertain attempts, count as exposure.
Backend/model changes define separate study conditions from historical API runs.
Frozen studies cannot be resumed or pooled merely because their source still exists.

The next real-contract pilot requires a fresh source-only proposal, current code
identity, explicit per-case/global ceilings and new execution approval. Evaluation
labels remain separate until a frozen, separately authorized evaluation stage.

Earlier chronological backend notes are preserved in
[the pre-cleanup version](history/scanner_subscription_before_cleanup_2026-11-16.md).

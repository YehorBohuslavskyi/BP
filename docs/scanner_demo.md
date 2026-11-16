# Demonstrating the scanner

The scanner runs locally at **http://127.0.0.1:8501**. It can scan self-contained
Solidity files, display warnings and source evidence, and export JSON and a
readable HTML report. It also exposes Mode B v2 discovery plus selective source
verification. The older analysis screens and frozen research results are retained.

## Start

In Ubuntu, from `/home/coca-cola/projects/BP`:

```bash
.venv/bin/python scripts/scanner.py doctor
.venv/bin/python scripts/scanner.py serve
```

The launcher sets up the existing virtual environment's compiler paths. Manual
shell activation is not required. Open the local URL printed by the launcher.
Stop the server with Ctrl+C in its terminal. No compiler or package downloads
occur when starting or scanning. A compatible locally installed compiler is required.

## A five-minute teacher demonstration with no API charges

1. Open **Scanner** and keep **Local static scan (no API)** selected.
2. Choose **Vulnerable vault**, then click **Run local scan**.
   The real Slither scan reports `reentrancy-eth` at high severity. Expand the
   finding to show the external call and the subsequent balance update.
3. Choose **Guarded vault**. The old results disappear. Scan again: the
   reentrancy warning is absent. An informational low-level-call warning remains.
   Show the updated source: it clears the balance before transferring and adds
   a reentry guard. The absence of this warning is not a proof of security.
4. Download the JSON and readable reports. The report identifies the source hash,
   compiler, method, warning, location and actual usage (zero model requests).
5. Select **Saved LLM evidence** in the sidebar. Show the original confirmed,
   rejected and inconclusive model assessments from the preserved 9 November
   development run. Explain that these are genuine historical responses, not
   new scans of the displayed vault. The page verifies the saved report checksum
   and uses limited legacy consistency checks; it does not claim new accuracy.
6. Return to **Scanner**, choose **Direct LLM scan (v2)** and **Prepare contract**.
   Show the real compiler-backed function catalog and discovery batch count.
   Preparation is local. Choose **Codex subscription** for included allowance,
   confirm its use, and click Run. The optional API route has separate billing.
   See [subscription scanning](scanner_subscription.md).

The two vault sources are demonstration examples, separate from the frozen
benchmark. They do not influence benchmark selection, labels, scoring or tuning.
The local before/after detection result is one real example, not a general recall
or precision claim. Original findings are not rewritten or relabeled.

## Scan another file

Use **Upload** or **Paste** in the Scanner workspace. This simple interface accepts
one UTF-8 `.sol` file up to 1 MiB, without imports. Syntax/compiler failures are
shown separately from scan results. Source changes clear previous preparation
and results. A scan starts only on an explicit Run click; rerendering, navigation
and report downloads do not call a model.

For projects with imports, retain the existing advanced v2 command:

```bash
.venv/bin/python scripts/run_direct_discovery.py /path/to/Contract.sol --stage prepare --output /new/empty/prepared
```

It resolves installed local dependencies. It does not download missing libraries.

## Command-line scans and export

```bash
# Real local scans; no model requests
.venv/bin/python scripts/scanner.py scan --example vulnerable
.venv/bin/python scripts/scanner.py scan --example guarded
.venv/bin/python scripts/scanner.py scan /path/to/Contract.sol --output /new/report/directory

# Compiler-backed Mode B v2 preparation only
.venv/bin/python scripts/scanner.py scan --example vulnerable --method prepare
```

Default outputs go into a new, uniquely named directory under `scanner-output/`.
Existing output directories are rejected rather than overwritten. Interactive
scans use owned temporary directories, separate from all research outputs.

## Fresh direct LLM scanning

The default **Codex subscription** backend needs an installed Codex CLI signed
in with ChatGPT, not an API key. It uses the existing plan allowance and stops
on a reported allowance or transport error. It never falls back to the paid API.
See [subscription setup and evaluation](scanner_subscription.md).

For the optional **OpenAI API (separate billing)** backend, enter the key in **OpenAI API key (session only)** in the local scanner, or set
`OPENAI_API_KEY` in the environment used to start the app. Session keys remain in
memory, are passed only to the isolated worker environment, and can be cleared
with **Forget session key**. Never place keys in source files, reports or chat. Set `OPENAI_MODEL`, or enter a model ID in
the scanner. Credentials are not accepted through source upload or exported.
The worker isolates the model setting from other sessions.

```bash
# This command makes paid requests. Run only when you intend to authorize them.
.venv/bin/python scripts/scanner.py scan /path/to/Contract.sol \
  --method direct --provider openai --live --model YOUR_MODEL_ID --max-candidates 3 --max-rounds 3
```

Mode B v2 supplies structural metadata to discovery without Slither warnings,
then verifies candidate source with bounded context requests. Only actually
supplied fragment IDs and matching source quotes can support verdicts. A
contradictory model response becomes a processing failure, not a manufactured
security verdict. Coverage, abstentions, errors and skipped candidates are visible.

Default limits: six discovery batches, three candidates, three rounds per
candidate, 60,000 reported verification tokens and 2,000 output tokens per
verification response. Discovery tokens are additional; the discovery backend
allows up to 8,000 output tokens per response. The request ceiling is discovery
batches plus candidates times rounds. Token estimates are not a price quote or
a guaranteed whole-scan billing ceiling. Provider failures may leave unknown usage.
The API SDK has no automatic retries. The Codex route has no application
retries, but its CLI can use builtin connection retries. A new click starts a new scan, never an implicit
resume or a replay of an uncertain request.

The new live adapter has been verified with real compiler preparation and
mocked provider responses, including retrieval, confirmation, guard-based
rejection, and consistency failure. The final authorized provider check also succeeded: 2/2 function rows examined,
one high-severity reentrancy confirmation, no processing or consistency failures,
and two requests using 5,138 tokens. The real result is preserved separately in
`docs/reviews/scanner-live-2026-11-16/` and the user-facing live report.

## Tests and historical integrity

The full offline unittest suite includes real local compiler/static scans and
mocked inference. Existing pilot scope tests use a private reuse fixture so that
an unrelated malformed historical report cannot prevent their assertions from
running. A separate test confirms that the real reuse audit still refuses
malformed JSON. The original malformed report is not repaired or silently skipped.

`runs/`, `experiments/`, frozen plans, GT labels, budgets and score definitions
remain unchanged. Saved LLM evidence remains explicitly historical. Do not use
this demonstration to claim a held-out evaluation or whole-dataset accuracy.


## Completed provider-check configuration

The user authorized one small demonstration contract using
`gpt-5.4-mini-2026-03-17`, at most **four model requests**, with no retries.
The prepared VulnerableVault source uses one discovery batch. Set maximum
candidates to **1** and maximum verification rounds to **3** (1 + 1 × 3 = 4).
The one-time check has completed successfully. These limits document that run;
they do not authorize another paid scan. Entering a key alone never starts inference.


## Final provider check completed

The authorized live check completed successfully with **two** requests, below
the approved four-request cap, and **5,138** tokens. It confirmed the reentrancy
issue in `withdraw()` with valid source evidence and no processing failures.
The session key was cleared afterwards. No repeat check is needed.
See [final verification](scanner_final_verification.md) in the repository,
or the separate user-facing `scanner-live-report.html`.

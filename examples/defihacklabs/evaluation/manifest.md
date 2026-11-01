# Local DeFiHackLabs evaluation integration

Status: **INCOMPLETE_LOCAL_MATERIALS**. Requested: 20 incidents. Available: **1 pilot**.
The 20-case primary subset is **not frozen**. No prospective Slither evaluation began.
The pilot integration manifest is immutable for this snapshot; SHA-256 is recorded
in the baseline and targets. Selection bias from the already-known pilot is explicit.

| ID | Project | Date | Category | Function | Source | Compiler |
|---|---|---|---|---|---|---|
| spankchain | SpankChain | 2018-10-07 | reentrancy | LedgerChannel.LCOpenTimeout(bytes32) | local archived victim source | 0.4.25 |

The local search found the existing SpankChain source, ground-truth documentation,
preflight, detector-scoped Slither JSON, and independent validation. No local
DeFiHackLabs checkout/catalog or additional incident PoCs were located under
`/home/coca-cola/projects` or `/tmp`. The PoC path referenced in the documentation
is an upstream reference, not an available local file. Missing metadata stays null.
SmartBugs and CGT sources cannot establish new DeFiHackLabs incident provenance
and were not substituted. There are no fabricated excluded incidents or 19 placeholder
cases. No candidate replacements were possible from the local evidence.

## Imported baseline

| ID | Known category/function | Detector | Result |
|---|---|---|---|
| spankchain | reentrancy / LCOpenTimeout(bytes32) | reentrancy-eth | DETECTED |

Selected 1; previously compiled 1; previously analyzable 1; detected 1; missed 0;
ambiguous 0; not analyzable 0. Pilot-only recall = 1/1 = 100%; this is not a
20-case real-world recall estimate. No new compilation, Slither run or inference
was needed for integration. The original outputs are not overwritten.

The full-default run's 126 findings are supported by preflight counts, but its
complete raw output is not in the pilot directory. Available raw output has two
reentrancy-eth findings. The other raw finding is retained as
UNLABELED_ADDITIONAL_FINDING. Do not interpret missing full-run records as zero
additional warnings. Existing equality FP and disputed labels stay in their
original independent-validation document and are not merged into binary metrics.

## Reproduction and next step

Check all integration hashes without inference:

```bash
.venv/bin/python examples/defihacklabs/evaluation/check_integrity.py
```

`build_local_evaluation.py` creates this integration once and refuses overwrites.
19 additional locally documented incidents with faithful victim sources are needed
before a prospective 20-case manifest can be frozen and the remaining baseline run.
There are **zero new unpaid/completed-pilot-excluded LLM targets**. No new batch
verification command is applicable yet. To open the existing production workflow:

```bash
.venv/bin/streamlit run streamlit_app.py
```

The one technical target is retained for integration, marked already-completed.
Do not rerun it as a new cohort observation. Ground truth is stored in the manifest,
separate from the production payload. No batch inference runner is introduced in
this incomplete cohort. Do not send manifest, labels, incident notes or this report
to the model. Local sources may retain original names/comments as production source
data; no root-cause annotations were added to victim code.

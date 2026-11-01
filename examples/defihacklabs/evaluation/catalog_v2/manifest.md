# Local catalog screening, version 2

Catalog commit: `d4bd931e758a375ed7fcecf52322dfeab54f8c0d`. Metadata entries screened: **907**.
Screening decisions: `{"CATEGORY_REVIEW_REQUIRED": 454, "EXCLUDED_CATEGORY": 175, "SOURCE_UNAVAILABLE": 277, "SELECTED_EXISTING_PILOT": 1}`.

**20-case cohort not frozen: 1 source-backed pilot, 19 cases missing.**
PoCs were used only as documentation. No exploit execution or new Slither/LLM run occurred.
The checkout is primarily a reproduction catalog, not a verified victim-source archive.
`source_role_audit.json` records the local Solidity file-role screen. Non-test support
and unresolved file roles are not silently certified as faithful vulnerable contracts.
Victim sources still require incident/address/version provenance and their dependencies.

The source-backed case remains SpankChain: reentrancy, LedgerChannel.LCOpenTimeout(bytes32),
solc 0.4.25. The local official PoC linkage is now recorded in manifest.json.
The unchanged source snapshot remains in `../contracts/spankchain/SpankChain.sol`.
Imported baseline: compiled 1; analyzable 1; DETECTED 1; MISSED 0; AMBIGUOUS 0;
NOT_ANALYZABLE 0. Pilot-only recall 1/1; new LLM-ready targets 0. Additional available
warnings retain their previous unlabeled status. Raw full-default baseline limitations
remain as recorded in the original integration.

No 20 cases are selected solely to fill slots, and no source-unavailable candidate is
counted as MISSED or NOT_ANALYZABLE in a selected cohort. SOURCE_UNAVAILABLE applies
locally, not globally. Deterministic category matching is preliminary screening;
mixed categories and unknown metadata require manual review before future selection.

The original six integration files and their integrity hashes are preserved. This
versioned directory holds the extended inventory and metadata. Check both with:

```bash
.venv/bin/python examples/defihacklabs/evaluation/check_integrity.py
.venv/bin/python examples/defihacklabs/evaluation/check_catalog_v2.py
```

A new paid verification command is not applicable: the sole technical target is the
already-completed pilot. Obtain faithful victim sources locally, then select and freeze
a prospective cohort before running new default Slither analyses or preparing new
inference jobs. No ground-truth manifest is to be passed as an LLM payload.

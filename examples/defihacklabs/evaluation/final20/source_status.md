# Nominated 20-case source readiness

Frozen: **NO**. Counts: `{"SOURCE_READY": 4, "SOURCE_NEEDS_REVIEW": 4, "SOURCE_UNAVAILABLE": 9, "PROXY_HISTORY_UNRESOLVED": 3, "WRONG_SOURCE_VERSION": 0}`.

SpankChain, Visor, XSURGE and BurgerSwap have SOURCE_READY status. Remaining nominated cases prevent cohort freeze. Original pilot artifacts remain unchanged.

| Incident | Status | Victim | Implementation reference (unvalidated) | Compiler | Main reason |
|---|---|---|---|---|---|
| SpankChain | SOURCE_READY | 0xf91546835f756DA0c10cFa0CDA95b15577b84aA7 | Unavailable | 0.4.25 | Reuse previously accepted complete pilot unchanged; byte-identical local archived source and license copied. Archived-source/deployed-bytecode limitations retained. |
| SQTokenStaking | SOURCE_UNAVAILABLE | 0x404404A845FFF0201f3a4D419B4839fC419c99F7 | Unavailable | Unavailable | No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors. |
| SubQuery Settings | SOURCE_UNAVAILABLE | 0xf282737992Da4217bf5f8B6AE621181e84d7d3b9 | Unavailable | Unavailable | No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors. |
| GiddyVaultV3 | SOURCE_UNAVAILABLE | 0x5f0ad32c00641d1d2bb628ff341e0d4bb4494318 | Unavailable | Unavailable | No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors. |
| JoeAgent | PROXY_HISTORY_UNRESOLVED | 0xef0f12d08d66e76E1866e60F30a0DaA578e00c04 | ['0xb12ce0a21f67a9fc3c8ad1c7dbc4b017b7e67319'] | Unavailable | Documented proxy/delegate architecture; no incident-time logic snapshot or independently validated historical implementation linkage available locally. |
| MureDistribution | SOURCE_UNAVAILABLE | 0x365083717efb17f3895290ba38f20f568c7a4d8a | Unavailable | Unavailable | No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors. |
| XSURGE | SOURCE_READY | 0xE1E1Aa58983F6b8eE8E4eCD206ceA6578F036c21 | Unavailable | 0.8.5; pragma ^0.8.0 | Complete import-free victim source; successful solc 0.8.5 compilation and standard-json Slither evidence (21 findings). |
| MAPProtocol / Butter | SOURCE_UNAVAILABLE | 0x0000317bec33af037b5fab2028f52d14658f6a56 | Unavailable | Unavailable | No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors. |
| Grim Finance | SOURCE_UNAVAILABLE | 0x660184CE8AF80e0B1e5A1172A16168b15f4136bF | Unavailable | Unavailable | No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors. |
| Parity WalletLibrary | SOURCE_NEEDS_REVIEW | 0x863DF6BFa4469f3ead0bE8f9F2AAE51c91A907b4 | Unavailable | Unavailable | Local SmartBugs parity_wallet_bug_2.sol is an annotated archive lead; exact equivalence to this library deployment/version not established. Not certified or copied as ready. |
| BiFi | PROXY_HISTORY_UNRESOLVED | 0x808c3ba97268dbf9695b1ec10729e09c7e67a9e3 | ['0x47be3d1def039bd85e7570864bb5148e7491a65f'] | 0.6.12 | Documented proxy/delegate architecture; no incident-time logic snapshot or independently validated historical implementation linkage available locally. |
| NewMarketTrading / SquidRouterModule | SOURCE_NEEDS_REVIEW | 0x1f1d37a3Bf840e35c6a860c7C2dA71Fe555123ca | Unavailable | Unavailable | Ethereum incident documents verified source at the same address on Base; cross-chain deployed-code equivalence is not established and no raw verified snapshot is local. |
| ATM | SOURCE_NEEDS_REVIEW | Unavailable | Unavailable | Unavailable | Multiple distinct local incidents match this project name; exact incident must be resolved before assigning a victim/source. Alternate PoC references retained. |
| BurgerSwap | SOURCE_READY | 0xBf6527834dBB89cdC97A79FCD62E6c08B19F8ec0 | Unavailable | 0.6.6 | Flattened import-free DemaxPlatform source successfully compiled with solc 0.6.6; completed Slither output contains 96 findings. |
| Hundred Finance | SOURCE_NEEDS_REVIEW | Unavailable | Unavailable | Unavailable | Multiple distinct local incidents match this project name; exact incident must be resolved before assigning a victim/source. Alternate PoC references retained. |
| Rari Capital Fuse | PROXY_HISTORY_UNRESOLVED | 0x26267e41CeCa7C8E0f143554Af707336f27Fa051 | Unavailable | Unavailable | Documented proxy/delegate architecture; no incident-time logic snapshot or independently validated historical implementation linkage available locally. |
| Visor Finance | SOURCE_READY | 0xC9f27A50f82571C1C8423A42970613b8dBDA14ef | Unavailable | 0.7.6 | Complete local dependencies and unchanged self-contained analysis copy compile with solc 0.7.6; standard-json Slither succeeded with 41 findings. |
| Revest Finance | SOURCE_UNAVAILABLE | 0x2320A28f52334d62622cc2EaFa15DE55F9987eD9 | Unavailable | Unavailable | No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors. |
| LendfMe | SOURCE_UNAVAILABLE | 0x0eEe3E3828A45f7601D5F54bF49bB01d1A9dF5ea | Unavailable | Unavailable | No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors. |
| Popsicle Finance | SOURCE_UNAVAILABLE | 0xc4ff55a4329f84f9Bf0F5619998aB570481EBB48 | Unavailable | Unavailable | No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors. |

## Cases preventing freeze

- SQTokenStaking: No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors.
- SubQuery Settings: No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors.
- GiddyVaultV3: No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors.
- JoeAgent: Documented proxy/delegate architecture; no incident-time logic snapshot or independently validated historical implementation linkage available locally.
- MureDistribution: No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors.
- MAPProtocol / Butter: No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors.
- Grim Finance: No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors.
- Parity WalletLibrary: Local SmartBugs parity_wallet_bug_2.sol is an annotated archive lead; exact equivalence to this library deployment/version not established. Not certified or copied as ready.
- BiFi: Documented proxy/delegate architecture; no incident-time logic snapshot or independently validated historical implementation linkage available locally.
- NewMarketTrading / SquidRouterModule: Ethereum incident documents verified source at the same address on Base; cross-chain deployed-code equivalence is not established and no raw verified snapshot is local.
- ATM: Multiple distinct local incidents match this project name; exact incident must be resolved before assigning a victim/source. Alternate PoC references retained.
- Hundred Finance: Multiple distinct local incidents match this project name; exact incident must be resolved before assigning a victim/source. Alternate PoC references retained.
- Rari Capital Fuse: Documented proxy/delegate architecture; no incident-time logic snapshot or independently validated historical implementation linkage available locally.
- Revest Finance: No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors.
- LendfMe: No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors.
- Popsicle Finance: No faithful raw victim source located locally; interfaces and PoC helpers are not victim source. Prior provider acquisition was blocked by DNS/transport errors.

Source-provider links are documentary references, not evidence of successful retrieval. PoC source pragmas are deliberately excluded from victim compiler identification. BiFi compiler 0.6.12 is explicitly reported by its documentation; it is not locally compiled or independently verified here. For multi-contract cases, a single victim address may be only an entrypoint; the complete vulnerable implementation/dependency set remains to be established.

Parity archive lead: `datasets/smartbugs-curated/dataset/access_control/parity_wallet_bug_2.sol`. It is not copied into the ready pool without deployment equivalence. ATM retains 2024-04, 2026-06 token and 2026-06 LP-burn references; Hundred retains both 2022-03 and 2023-04 references. The cohort nomination has not silently selected among these incidents.

No new source was certified from a different-chain deployment or current proxy implementation. Existing evaluation, source-acquisition and research files were read only. No final metrics are computed.


## Visor completed local evidence

Complete local dependencies and unchanged self-contained analysis copy compile with solc 0.7.6; standard-json Slither succeeded with 41 findings.

Known-vulnerability baseline: **MISSED**. Caller-controlled from contract supplies owner/delegatedTransferERC20 behavior; deposit does not verify receipt before mint. Reported arbitrary-send-erc20 sink is the ELSE/non-contract safeTransferFrom branch, not this documented path.

The arbitrary-send-erc20 warning and all other 40 warnings are retained as UNLABELED_ADDITIONAL_FINDING. No FP/TP adjudication or LLM job is created. Raw/analysis source and historical provenance remain unchanged. Current evidence is in contracts/visor-finance/evidence/integration.json. No final metrics are calculated.

## XSURGE completed evidence integration

SOURCE_READY; known historical sell cross-function reentrancy: DETECTED by reentrancy-eth. Evidence is preserved under contracts/xsurge/evidence/. A technical target is recorded in verification_targets.json; historical ground truth stays in the baseline and evidence integration record. No inference or aggregate metrics computed.

## BurgerSwap completed evidence integration

SOURCE_READY; known vulnerability baseline: **MISSED**. Known root cause is cross-function reentrancy invalidating precomputed swap amounts before _swap reuses them. The related reentrancy-events finding reports calls followed by SwapToken emission and does not establish stale-amount/reserve-state reuse. It is not a corresponding ground-truth detection.

The platform address supplied for DemaxPlatform is distinct from the pool address previously extracted from the PoC; both roles are retained in JSON. All 96 findings remain UNLABELED_ADDITIONAL_FINDING. No BurgerSwap LLM target is created. Evidence files and their hashes are preserved in contracts/burgerswap/evidence/. No aggregate metrics computed.

## Supplemental Eleven Finance evidence

Eleven Finance is SOURCE_READY; known emergencyBurn missing-share-burn vulnerability is MISSED. This supplemental case does not replace any of the nominated 20; nominated status counts remain unchanged. The appended CSV row and JSON supplemental_records identify its additional status. Compiler: 0.6.12. Raw flattened source is unchanged; existing compilation and all 58 Slither findings are preserved under contracts/eleven/evidence/. All findings are UNLABELED_ADDITIONAL_FINDING. No LLM target or cohort freeze.

## Supplemental bEarn evidence

bEarn / BvaultsBank: SOURCE_READY, solc 0.6.12; known withdrawal denomination mismatch: MISSED. All 115 findings remain UNLABELED_ADDITIONAL_FINDING; no verification target. Existing proxy/implementation sources, technical integration, compilation and Slither outputs are preserved. Manual adjudication is in contracts/bearn/evidence/adjudication.json. This supplemental case does not replace a nominated cohort member or change nominated counts.

## Supplemental Spartan Protocol evidence

Spartan Protocol: SOURCE_READY; solc 0.6.8; known liquidity-share calculation flaw: MISSED. All 76 findings remain UNLABELED_ADDITIONAL_FINDING. No LLM target. Source and original technical evidence retained unchanged; manual mapping is in contracts/spartan/evidence/adjudication.json. External UTILS calculation/deployment completeness is not independently reverified. Supplemental case; nominated counts and cohort membership unchanged.

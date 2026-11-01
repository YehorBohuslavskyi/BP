# Source acquisition attempt

Candidates attempted (metadata and archive screening): 277.
Sourcify candidate requests: 164 (171 HTTP GETs).
Explorer candidate requests: 101.
Sourcify outcomes: {"METADATA_INSUFFICIENT": 113, "TRANSPORT_ERROR": 164}.

New verified source-backed snapshots: **0**. Sourcify successes: 0;
explorer-source successes: 0; exact archive-source successes: 0.
Unverified-bytecode failures: **0 established**. Proxy-only failures: **not established**.
Ambiguous implementation failures: not independently established; documented references
are retained for review in source_acquisition_evidence.json. Do not conflate unreachable
providers with absent/unverified sources. All final SOURCE_UNAVAILABLE statuses are
local acquisition outcomes, not statements about public verification availability.

No successful incident list, compiler versions or certified proxy/implementation pairs
can be reported. Existing SpankChain remains the sole previous source-backed pilot,
not a new acquisition and not included in the 277-candidate denominator.
At least 25 strong source-backed candidates: **NO**.

Main bottleneck: provider connectivity and incomplete/unambiguous chain/address metadata.
Shell HTTPS requests fail DNS in this environment; the web-tool Sourcify contract
lookup was also inaccessible. No source bytes were reconstructed from rendered pages,
bytecode or PoCs. Local archive address references are leads only; no exact deployment
identity has been established. Proxy lookup, if later reachable, must be checked against
the incident-time implementation, not merely the current proxy implementation.

This run does not freeze a cohort, compile, run Slither, invoke a verifier or compute
any detection metrics. Existing research files are preserved and hash checked.
The acquisition script refuses overwrites; a retry must use a fresh directory:

```bash
.venv/bin/python examples/defihacklabs/evaluation/acquire_sources.py --output-dir /tmp/bp-source-acquisition-retry
```

The script records downloaded provider responses as pending review; a successful HTTP
response alone never earns SOURCE_VERIFIED_AND_SNAPSHOTTED. Review must establish a
verified match, complete source content, root unit, compiler/settings and historical
proxy linkage before certifying an immutable raw snapshot. No guessed ABI or victim
function is used to certify identity.

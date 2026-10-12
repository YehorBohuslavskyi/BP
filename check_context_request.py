import json
from pathlib import Path

from slither.slither import Slither

from context_audit.catalog import FragmentCatalog
from context_audit.context import build_function_context
from context_audit.payload import (
    build_initial_payload,
    resolve_context_request,
)


source_path = Path(
    "examples/AccessDemoUnrestricted.sol"
).resolve()

slither = Slither(str(source_path))
catalog = FragmentCatalog(source_path.parent)

target = next(
    function
    for contract in slither.contracts
    for function in contract.functions
    if contract.name == "AccessDemoUnrestricted"
    and function.full_name == "setValue(uint256)"
)

context = build_function_context(target, catalog)
initial_payload = build_initial_payload(context, catalog)

modifier_id = context["modifiers"][0]["fragment_id"]

result = resolve_context_request(
    requested_ids=[
        modifier_id,
        modifier_id,
        "unknown-fragment",
    ],
    initial_payload=initial_payload,
    catalog=catalog,
)

print(json.dumps(result, indent=2, ensure_ascii=False))
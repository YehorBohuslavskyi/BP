import json
from pathlib import Path

from slither.slither import Slither
from context_audit.llm import analyze

from context_audit.catalog import FragmentCatalog
from context_audit.context import build_function_context
from context_audit.payload import (
    build_initial_payload,
    resolve_context_request,
)


source_path = Path(
    "examples/AccessDemoRestricted.sol"
).resolve()

slither = Slither(str(source_path))
catalog = FragmentCatalog(source_path.parent)

target = next(
    function
    for contract in slither.contracts
    for function in contract.functions
    if contract.name == "AccessDemoRestricted"
    and function.full_name == "setValue(uint256)"
)

context = build_function_context(target, catalog)
initial_payload = build_initial_payload(context, catalog)

provided_context = []
max_rounds = 4
total_tokens = 0

for round_number in range(1, max_rounds + 1):
    print(f"\n--- Round {round_number}/{max_rounds} ---")

    result = analyze(initial_payload, provided_context)
    total_tokens += (result.get("usage") or {}).get("total_tokens", 0)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    assessment = result["assessment"]

    if assessment["action"] == "final":
        print(f"\nFinal verdict: {assessment['verdict']}")
        break

    if round_number == max_rounds:
        print("\nStopped: round limit reached. Outcome: inconclusive.")
        break

    resolved = resolve_context_request(
        requested_ids=assessment["requested_ids"],
        initial_payload=initial_payload,
        catalog=catalog,
    )

    if resolved["errors"]:
        print(json.dumps(resolved["errors"], indent=2))
        raise RuntimeError("Context resolution failed.")

    existing_ids = {fragment["id"] for fragment in provided_context}

    new_fragments = [
        fragment
        for fragment in resolved["fragments"]
        if fragment["id"] not in existing_ids
    ]

    if not new_fragments:
        print("\nStopped: no new context. Outcome: inconclusive.")
        break

    provided_context.extend(new_fragments)

    print("\nAdded context:")
    for fragment in new_fragments:
        print(f"  {fragment['kind']}: {fragment['name']}")

print(f"\nTotal tokens across calls: {total_tokens}")
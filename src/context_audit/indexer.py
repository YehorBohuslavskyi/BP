import argparse 
from pathlib import Path
from slither.slither import Slither
import json
from context_audit.context import build_function_context
from context_audit.catalog import FragmentCatalog
from context_audit.payload import build_initial_payload

def inspect_contract(source_path: Path, function_signature: str | None = None) -> dict:
    slither = Slither(str(source_path))
    catalog = FragmentCatalog(source_path.parent)
    found = False
    initial_payloads = []
    contexts = []

    for contract in slither.contracts:
        for function in contract.functions:
            if(function_signature is not None and function.full_name != function_signature):
                continue
            found = True

            context = build_function_context(function, catalog)
            context["contract"] = contract.name
            contexts.append(context)
            initial_payloads.append(build_initial_payload(context, catalog))

    if function_signature is not None and not found:
        raise ValueError(f"Function  not found: {function_signature}")

    return {"source": str(source_path), "functions": contexts, "catalog": catalog.to_dict(), "initial_payloads": initial_payloads}

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect the structure of a Solidity contract"
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Path to the Solidity source file"
    )
    parser.add_argument(
        '--function',
        dest="function_signature",
        help="Function signature, for example setValue(uint256)"
    )
    parser.add_argument(
        '--output',
        type=Path,
        help="Save the report to a JSON file"
    )

    args = parser.parse_args()

    source_path = args.source.resolve()
    if not source_path.is_file():
        parser.error(f"File not found: {source_path}")

    try:
        report = inspect_contract(source_path, args.function_signature)
    except ValueError as err:
        parser.error(str(err))

    json_text = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output is not None:
        output_path = args.output.resolve()

        if output_path == source_path:
            parser.error(f"Output file cannot be the same as the source file")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json_text + "\n", encoding="utf-8")
        except OSError as err:
            parser.error(f"Cannot save report: {err}")

        print(f"Report saved to {output_path}")
    else:
        print(json_text)

if __name__ == "__main__":
    main()
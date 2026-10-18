"""Resolve Solidity functions and inspect their selective-context catalogs."""
import argparse 
from pathlib import Path
from slither.slither import Slither
from slither.core.declarations import Function
import json
from context_audit.context import build_function_context
from context_audit.catalog import FragmentCatalog

def find_function(
    slither: Slither,
    contract_name: str,
    function_signature: str,
    file: str | None = None,
) -> Function | None:
    """Resolve the exact contract and signature, optionally requiring file identity."""
    for contract in slither.contracts:
        if contract.name != contract_name:
            continue

        for function in contract.functions:
            if function.full_name != function_signature:
                continue

            if file is not None:
                function_file = Path(
                    function.source_mapping.filename.relative
                ).as_posix()

                finding_file = Path(file).as_posix()

                if function_file != finding_file:
                    continue

            return function

    return None

def inspect_contract(
    source_path: Path,
    function_signature: str | None = None,
    project_root: Path | None = None,
) -> dict:
    """Compile a source and collect contexts for matching functions."""
    slither = Slither(str(source_path))

    if project_root is None:
        project_root = source_path.parent

    catalog = FragmentCatalog(project_root)

    found = False
    contexts = []

    for contract in slither.contracts:
        for function in contract.functions:
            if(function_signature is not None and function.full_name != function_signature):
                continue
            found = True

            context = build_function_context(function, catalog)
            context["contract"] = contract.name
            contexts.append(context)

    if function_signature is not None and not found:
        raise ValueError(f"Function  not found: {function_signature}")

    return {"source": str(source_path), "functions": contexts, "catalog": catalog.to_dict()}

def main() -> None:
    """Parse command-line arguments and invoke the module entry point."""
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

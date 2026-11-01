"""Selective context for function/modifier targets and their direct state dependencies."""
from itertools import chain

from slither.core.declarations import Function, Modifier
from context_audit.catalog import FragmentCatalog

def build_function_context(function: Function, catalog: FragmentCatalog) -> dict:
    """Backward-compatible entry point for function context consumers."""
    return build_target_context(function, catalog)


def build_target_context(target: Function, catalog: FragmentCatalog) -> dict:
    """Build modifier, state-declaration, and direct-writer metadata for either target kind."""
    kind = "modifier" if isinstance(target, Modifier) else "function"
    target_id = catalog.add(target, kind, target.full_name)
    modifiers = []
    related_variables ={}

    for variable in (
        target.state_variables_read
        + target.state_variables_written
    ):
        related_variables[variable.canonical_name] = variable

    for modifier in target.modifiers:
        modifier_id = catalog.add(modifier, "modifier", modifier.full_name)
        modifiers.append({
            "fragment_id": modifier_id,
            "name": modifier.name,
            "state_reads": [
                variable.name for variable in modifier.state_variables_read
            ],
            "state_writes": [
                variable.name for variable in modifier.state_variables_written
            ]
        })
        for variable in (
            modifier.state_variables_read 
            + modifier.state_variables_written
        ):
            related_variables[variable.canonical_name] = variable

    dependencies = []

    for variable_id, variable in sorted(related_variables.items()):
        declaration_id = catalog.add(variable, "state_variable", variable.canonical_name)

        direct_writers = []

        # Functions and modifiers can both write a dependency. Keep the original
        # functions-first order because catalog order controls request metadata.
        candidates = chain(
            ((candidate, "function") for candidate in target.contract.functions),
            ((modifier, "modifier") for modifier in target.contract.modifiers),
        )
        for writer, writer_kind in candidates:
            if variable in writer.state_variables_written:
                direct_writers.append({
                    "fragment_id": catalog.add(writer, writer_kind, writer.full_name),
                    "signature": writer.full_name,
                    "kind": writer_kind,
                })

        dependencies.append({
            "id": variable_id,
            "name": variable.name,
            "declaration_id": declaration_id,
            "direct_writers": direct_writers
        })


    return {
        "fragment_id": target_id,
        "kind": kind,
        "contract": target.contract.name,
        "signature": target.full_name,
        "visibility": target.visibility,
        "state_reads": [
            variable.name for variable in target.state_variables_read
        ],
        "state_writes": [
            variable.name for variable in target.state_variables_written
        ],
        "modifiers": modifiers,
        "state_dependencies": dependencies
    }

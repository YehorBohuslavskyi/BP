"""Dependency-aware metadata for a target function and its direct state dependencies."""
from itertools import chain

from slither.core.declarations import Function
from context_audit.catalog import FragmentCatalog

def build_function_context(function: Function, catalog: FragmentCatalog) -> dict:
    """Build modifier, state-declaration, and direct-writer metadata for a function."""
    function_id = catalog.add(function, "function", function.full_name)
    modifiers = []
    related_variables ={}

    for variable in (
        function.state_variables_read 
        + function.state_variables_written
    ):
        related_variables[variable.canonical_name] = variable

    for modifier in function.modifiers:
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
            ((candidate, "function") for candidate in function.contract.functions),
            ((modifier, "modifier") for modifier in function.contract.modifiers),
        )
        for writer, kind in candidates:
            if variable in writer.state_variables_written:
                direct_writers.append({
                    "fragment_id": catalog.add(writer, kind, writer.full_name),
                    "signature": writer.full_name,
                    "kind": kind,
                })

        dependencies.append({
            "id": variable_id,
            "name": variable.name,
            "declaration_id": declaration_id,
            "direct_writers": direct_writers
        })


    return {
        "fragment_id": function_id,
        "signature": function.full_name,
        "visibility": function.visibility,
        "state_reads": [
            variable.name for variable in function.state_variables_read
        ],
        "state_writes": [
            variable.name for variable in function.state_variables_written
        ],
        "modifiers": modifiers,
        "state_dependencies": dependencies
    }

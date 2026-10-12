from context_audit.catalog import FragmentCatalog

def build_initial_payload (
        context: dict,
        catalog: FragmentCatalog,
) -> dict :
    target_id = context["fragment_id"]
    target = catalog.get(target_id)

    available = {}

    def add_available(fragment_id: str, reason: str) -> None:
        if  fragment_id == target_id:
            return
        fragment = catalog.get(fragment_id)

        if fragment_id not in available:
            available[fragment_id] = {
                "id": fragment["id"],
                "kind": fragment["kind"],
                "name": fragment["name"],
                "reasons": []
            }

        if reason not in available[fragment_id]["reasons"]:
            available[fragment_id]["reasons"].append(reason)

    for modifier in context["modifiers"]:
        add_available(modifier["fragment_id"], "modifier")

    for dependency in context["state_dependencies"]:
        variable_name = dependency["name"]

        add_available(dependency["declaration_id"], f"state variable declaration: {variable_name}")

        for writer in dependency["direct_writers"]:
            add_available(writer["fragment_id"], f"direct writer of state variable: {variable_name}")

    return {
        "target": {
            "id": target_id,
            "signature": context["signature"],
            "visibility": context["visibility"],
            "source": target["source"],
        },
        "available_context": list(available.values()),
        "context_complete": False,
    }

def resolve_context_request(
        requested_ids: list[str],
        initial_payload: dict,
        catalog: FragmentCatalog,
) -> dict:
    allowed_ids = {
        item["id"] for item in initial_payload["available_context"]
    }

    fragments = []
    errors = []
    seen = set()

    for fragment_id in requested_ids:
        if fragment_id in seen:
            continue
        seen.add(fragment_id)

        if fragment_id not in allowed_ids:
            errors.append({
                "id": fragment_id,
                "message": "Fragment is not available for this target",
            })
            continue

        fragment = catalog.get(fragment_id)
        fragments.append(fragment.copy())

    return {
        "fragments": fragments,
        "errors": errors,
    }
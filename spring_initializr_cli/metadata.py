"""Metadata parsing helpers for Spring Initializr payloads."""


def metadata_values(metadata: dict, key: str) -> list[str]:
    values = metadata.get(key, {}).get("values", [])
    result: list[str] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        value_id = item.get("id")
        if isinstance(value_id, str):
            result.append(value_id)
    return result


def metadata_dependencies(metadata: dict) -> dict[str, str]:
    dep_map: dict[str, str] = {}
    dep_groups = metadata.get("dependencies", {}).get("values", [])
    for group in dep_groups:
        if not isinstance(group, dict):
            continue
        for item in group.get("values", []):
            if not isinstance(item, dict):
                continue
            dep_id = item.get("id")
            dep_name = item.get("name")
            if not isinstance(dep_id, str):
                continue
            dep_map[dep_id] = dep_name if isinstance(dep_name, str) else dep_id
    return dep_map

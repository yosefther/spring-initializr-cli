"""CLI command handlers."""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path

from .client import SpringInitializrClient
from .hooks import apply_post_generation_hooks
from .metadata import metadata_dependencies, metadata_values
from .service import collect_project_spec, resolve_extract_dir, validate_target_dir


def cmd_new(args: argparse.Namespace, client: SpringInitializrClient) -> int:
    metadata = client.fetch_metadata()
    spec = collect_project_spec(args, metadata)
    query_params = spec.to_query_params()
    starter_url = client.build_starter_url(query_params)

    output_dir = resolve_extract_dir(args.output, spec.artifact_id)

    if args.print_spec == "json":
        payload = {
            "spec": query_params,
            "starter_url": starter_url,
            "output_dir": str(output_dir),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.print_spec == "text":
        print("Project spec:")
        for key, value in query_params.items():
            print(f"- {key}: {value}")

    if bool(args.show_url):
        print(f"Starter URL: {starter_url}")

    if bool(args.dry_run):
        print("Dry run complete. No files were generated.")
        return 0

    validate_target_dir(output_dir, bool(args.force))
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Downloading project from Spring Initializr...")
    zip_bytes = client.download_starter_zip(query_params)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        safe_extractall(archive, output_dir)

    post_actions = apply_post_generation_hooks(output_dir, spec, args)

    print("Project initialized successfully.")
    print(f"Location: {output_dir}")
    print(f"Artifact: {spec.artifact_id}")
    print(f"Dependencies: {spec.dependencies_csv}")
    if spec.project_type.startswith("gradle"):
        print("Next: ./gradlew bootRun")
    else:
        print("Next: ./mvnw spring-boot:run")

    if post_actions:
        print("Post-generation actions:")
        for action in post_actions:
            print(f"- {action}")

    return 0


def cmd_list(args: argparse.Namespace, client: SpringInitializrClient) -> int:
    metadata = client.fetch_metadata()
    section = args.section

    if section == "boot-versions":
        values = metadata_values(metadata, "bootVersion")
        return _print_values(section, values, args.format)

    if section == "java-versions":
        values = metadata_values(metadata, "javaVersion")
        return _print_values(section, values, args.format)

    if section == "types":
        values = metadata_values(metadata, "type")
        return _print_values(section, values, args.format)

    if section == "languages":
        values = metadata_values(metadata, "language")
        return _print_values(section, values, args.format)

    if section == "packaging":
        values = metadata_values(metadata, "packaging")
        return _print_values(section, values, args.format)

    dep_map = metadata_dependencies(metadata)
    deps = [{"id": dep_id, "name": dep_name} for dep_id, dep_name in sorted(dep_map.items())]

    if args.format == "json":
        print(json.dumps({"section": section, "values": deps}, indent=2, sort_keys=True))
        return 0

    for dep in deps:
        print(f"{dep['id']:20} {dep['name']}")
    return 0


def cmd_search(args: argparse.Namespace, client: SpringInitializrClient) -> int:
    metadata = client.fetch_metadata()
    dep_map = metadata_dependencies(metadata)

    query = args.query.strip().lower()
    if not query:
        raise ValueError("Search query must not be empty")

    matches = _search_dependencies(dep_map, query)
    limit = args.limit if args.limit is not None else 20
    if limit < 1:
        raise ValueError("--limit must be at least 1")

    limited_matches = matches[:limit]

    if args.format == "json":
        print(
            json.dumps(
                {
                    "query": args.query,
                    "count": len(limited_matches),
                    "matches": [
                        {"id": dep_id, "name": dep_name} for _, dep_id, dep_name in limited_matches
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if not limited_matches:
        print(f"No dependencies matched '{args.query}'.")
        return 0

    for _, dep_id, dep_name in limited_matches:
        print(f"{dep_id:20} {dep_name}")
    return 0


def cmd_doctor(args: argparse.Namespace, client: SpringInitializrClient) -> int:
    checks: list[dict[str, object]] = []

    python_ok = sys.version_info >= (3, 12)
    checks.append(
        {
            "name": "python_version",
            "ok": python_ok,
            "required": True,
            "detail": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        }
    )

    launcher_path = shutil.which("spring-init")
    checks.append(
        {
            "name": "spring_init_on_path",
            "ok": launcher_path is not None,
            "required": False,
            "detail": launcher_path or "not found",
        }
    )

    git_path = shutil.which("git")
    checks.append(
        {
            "name": "git_available",
            "ok": git_path is not None,
            "required": False,
            "detail": git_path or "not found",
        }
    )

    cache_info = client.cache_info()
    cache_exists = bool(cache_info.get("exists"))
    cache_detail = (
        f"{cache_info.get('path')} (age={cache_info.get('age_seconds')}s, fresh={cache_info.get('is_fresh')})"
        if cache_exists
        else str(cache_info.get("path"))
    )
    checks.append(
        {
            "name": "metadata_cache",
            "ok": cache_exists,
            "required": False,
            "detail": cache_detail,
        }
    )

    probe_client = SpringInitializrClient(
        base_url=client.base_url,
        user_agent=client.user_agent,
        timeout_seconds=client.timeout_seconds,
        use_cache=False,
        refresh_metadata=True,
        cache_ttl_seconds=client.cache_ttl_seconds,
        max_retries=client.max_retries,
        backoff_seconds=client.backoff_seconds,
        cache_path=client.cache_path,
    )

    live_ok = False
    live_detail = ""
    try:
        metadata = probe_client.fetch_metadata()
        live_ok = True
        live_detail = f"reachable (sections={len(metadata)})"
    except Exception as exc:
        live_detail = str(exc)

    checks.append(
        {
            "name": "live_initializr_api",
            "ok": live_ok,
            "required": False,
            "detail": live_detail,
        }
    )

    availability_ok = live_ok or cache_exists
    checks.append(
        {
            "name": "metadata_availability",
            "ok": availability_ok,
            "required": True,
            "detail": "live API reachable or cache available",
        }
    )

    overall_ok = all(bool(item["ok"]) for item in checks if bool(item["required"]))

    if args.format == "json":
        print(json.dumps({"ok": overall_ok, "checks": checks}, indent=2, sort_keys=True))
    else:
        for item in checks:
            status = "OK" if bool(item["ok"]) else "FAIL"
            required = "required" if bool(item["required"]) else "optional"
            print(f"[{status}] {item['name']} ({required}) - {item['detail']}")

    return 0 if overall_ok else 1


def _print_values(section: str, values: list[str], out_format: str) -> int:
    if out_format == "json":
        print(json.dumps({"section": section, "values": values}, indent=2, sort_keys=True))
        return 0

    for value in values:
        print(value)
    return 0


def _search_dependencies(dep_map: dict[str, str], query: str) -> list[tuple[int, str, str]]:
    scored: list[tuple[int, str, str]] = []

    for dep_id, dep_name in dep_map.items():
        dep_id_l = dep_id.lower()
        dep_name_l = dep_name.lower()

        score: int | None = None
        if dep_id_l == query:
            score = 0
        elif dep_id_l.startswith(query):
            score = 1
        elif dep_name_l.startswith(query):
            score = 2
        elif query in dep_id_l:
            score = 3
        elif query in dep_name_l:
            score = 4

        if score is not None:
            scored.append((score, dep_id, dep_name))

    scored.sort(key=lambda item: (item[0], item[1]))
    return scored


def safe_extractall(archive: zipfile.ZipFile, target_dir: Path) -> None:
    base = target_dir.resolve()
    for member in archive.infolist():
        destination = (base / member.filename).resolve()
        if not destination.is_relative_to(base):
            raise ValueError(f"Archive entry escapes target directory: {member.filename}")
    archive.extractall(base)

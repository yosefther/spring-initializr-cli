"""Application service for collecting and validating project specs."""

from __future__ import annotations

import argparse
from pathlib import Path

from .metadata import metadata_dependencies, metadata_values
from .models import ProjectSpec
from .prompts import ask


def require_metadata_values(values: list[str], key: str) -> list[str]:
    if not values:
        raise ValueError(
            f"Spring Initializr metadata is missing '{key}'. "
            "The remote API format may have changed."
        )
    return values


def resolve_extract_dir(output_raw: str, artifact_id: str) -> Path:
    output_raw = output_raw.strip()
    if output_raw == ".":
        return Path.cwd()
    if output_raw == "":
        return Path.cwd() / artifact_id
    return Path(output_raw).expanduser().resolve()


def validate_target_dir(target: Path, force: bool) -> None:
    if not target.exists():
        return
    if not target.is_dir():
        raise ValueError(f"Output path exists and is not a directory: {target}")
    if any(target.iterdir()) and not force:
        raise ValueError(
            f"Output directory is not empty: {target}. Use --force if you want to extract there."
        )


def ensure_choice(value: str, valid: list[str], flag: str) -> None:
    if value and value not in valid:
        raise ValueError(f"Invalid {flag}: '{value}'. Use `list` command to inspect valid values.")


def collect_project_spec(args: argparse.Namespace, metadata: dict) -> ProjectSpec:
    boot_versions = require_metadata_values(metadata_values(metadata, "bootVersion"), "bootVersion")
    java_versions = require_metadata_values(metadata_values(metadata, "javaVersion"), "javaVersion")
    project_types = require_metadata_values(metadata_values(metadata, "type"), "type")
    languages = require_metadata_values(metadata_values(metadata, "language"), "language")
    packaging_values = require_metadata_values(metadata_values(metadata, "packaging"), "packaging")
    dep_map = metadata_dependencies(metadata)

    default_dependency = "web" if "web" in dep_map else next(iter(dep_map), "")
    defaults = {
        "type": "maven-project" if "maven-project" in project_types else project_types[0],
        "language": "java" if "java" in languages else languages[0],
        "bootVersion": boot_versions[0],
        "groupId": "com.example",
        "artifactId": "demo",
        "name": None,
        "packageName": None,
        "javaVersion": java_versions[0],
        "packaging": "jar" if "jar" in packaging_values else packaging_values[0],
        "dependencies": default_dependency,
    }

    if args.interactive:
        project_type = ask("Project type", args.type or defaults["type"])
        language = ask("Language", args.language or defaults["language"])
        boot_version = ask("Spring Boot version", args.boot_version or defaults["bootVersion"])
        group_id = ask("Group ID", args.group_id or defaults["groupId"])
        artifact_id = ask("Artifact ID", args.artifact_id or defaults["artifactId"])
        name = ask("Project name", args.name or artifact_id)
        package_name = ask("Package name", args.package_name or f"{group_id}.{artifact_id}")
        java_version = ask("Java version", args.java_version or defaults["javaVersion"])
        packaging = ask("Packaging", args.packaging or defaults["packaging"])
        dependencies_input = ask(
            "Dependencies (comma IDs)",
            args.dependencies if args.dependencies is not None else defaults["dependencies"],
        )
    else:
        artifact_id = args.artifact_id or defaults["artifactId"]
        group_id = args.group_id or defaults["groupId"]
        project_type = args.type or defaults["type"]
        language = args.language or defaults["language"]
        boot_version = args.boot_version or defaults["bootVersion"]
        name = args.name or artifact_id
        package_name = args.package_name or f"{group_id}.{artifact_id}"
        java_version = args.java_version or defaults["javaVersion"]
        packaging = args.packaging or defaults["packaging"]
        if args.dependencies is None:
            dependencies_input = defaults["dependencies"]
        else:
            dependencies_input = args.dependencies

    ensure_choice(project_type, project_types, "--type")
    ensure_choice(language, languages, "--language")
    ensure_choice(boot_version, boot_versions, "--boot-version")
    ensure_choice(java_version, java_versions, "--java-version")
    ensure_choice(packaging, packaging_values, "--packaging")

    dep_ids = [dep.strip() for dep in dependencies_input.split(",") if dep.strip()]
    invalid_deps = [dep for dep in dep_ids if dep not in dep_map]
    if invalid_deps:
        raise ValueError(f"Unknown dependencies: {', '.join(invalid_deps)}")

    return ProjectSpec(
        project_type=project_type,
        language=language,
        boot_version=boot_version,
        group_id=group_id,
        artifact_id=artifact_id,
        name=name,
        package_name=package_name,
        java_version=java_version,
        packaging=packaging,
        dependencies=dep_ids,
    )

"""Argument parser and CLI bootstrap."""

from __future__ import annotations

import argparse

from .client import (
    DEFAULT_BACKOFF_SECONDS,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    SpringInitializrClient,
)
from .commands import cmd_doctor, cmd_list, cmd_new, cmd_search
from .config import apply_preset_to_args, load_preset_file, resolve_preset_path

SECTIONS = ["boot-versions", "java-versions", "types", "languages", "packaging", "dependencies"]
OUTPUT_FORMATS = ["text", "json"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spring-init",
        description="Professional Spring Boot project generator from terminal.",
        epilog=(
            "Examples:\n"
            "  spring-init new --artifact-id store --dependencies web,data-jpa,h2\n"
            "  spring-init new --interactive --show-url\n"
            "  spring-init search jpa --format json\n"
            "  spring-init doctor"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_cmd = subparsers.add_parser("new", help="Generate a new Spring Boot project.")
    new_cmd.add_argument("--type", help="Project type, e.g. maven-project or gradle-project.")
    new_cmd.add_argument("--language", help="Language, usually java.")
    new_cmd.add_argument("--boot-version", help="Spring Boot version.")
    new_cmd.add_argument("--group-id", help="Project group ID.")
    new_cmd.add_argument("--artifact-id", help="Project artifact ID.")
    new_cmd.add_argument("--name", help="Display/project name.")
    new_cmd.add_argument("--package-name", help="Base package name.")
    new_cmd.add_argument("--java-version", help="Java version (e.g. 17, 21).")
    new_cmd.add_argument("--packaging", help="Packaging type (jar/war).")
    new_cmd.add_argument("--dependencies", help="Comma-separated dependency IDs.")
    new_cmd.add_argument(
        "--output",
        default="",
        help="'.' extracts in current directory; empty creates folder by artifact ID.",
    )
    new_cmd.add_argument(
        "--interactive",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Ask prompts interactively.",
    )
    new_cmd.add_argument(
        "--force",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Allow extraction into a non-empty output directory.",
    )
    new_cmd.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Show what would be generated without downloading files.",
    )
    new_cmd.add_argument(
        "--show-url",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Print the resolved starter.zip URL.",
    )
    new_cmd.add_argument(
        "--print-spec",
        choices=OUTPUT_FORMATS,
        default=None,
        help="Print the normalized project spec before execution.",
    )
    new_cmd.add_argument(
        "--git-init",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Initialize a git repository in generated project.",
    )
    new_cmd.add_argument(
        "--init-readme",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Create README.md if missing.",
    )
    new_cmd.add_argument(
        "--add-docker",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Create Dockerfile and .dockerignore if missing.",
    )
    new_cmd.add_argument(
        "--add-github-actions",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Create .github/workflows/ci.yml if missing.",
    )
    _add_runtime_options(new_cmd)

    list_cmd = subparsers.add_parser("list", help="List live values from start.spring.io metadata.")
    list_cmd.add_argument("section", choices=SECTIONS, help="Metadata section to print.")
    list_cmd.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=None,
        help="Output format (text/json).",
    )
    _add_runtime_options(list_cmd)

    search_cmd = subparsers.add_parser("search", help="Search dependency IDs by id or name.")
    search_cmd.add_argument("query", help="Case-insensitive search term.")
    search_cmd.add_argument("--limit", type=int, default=None, help="Maximum matches to print.")
    search_cmd.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=None,
        help="Output format (text/json).",
    )
    _add_runtime_options(search_cmd)

    doctor_cmd = subparsers.add_parser("doctor", help="Validate runtime environment and connectivity.")
    doctor_cmd.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=None,
        help="Output format (text/json).",
    )
    _add_runtime_options(doctor_cmd)

    return parser


def run(args: argparse.Namespace) -> int:
    preset_path = resolve_preset_path(args.preset)
    preset = load_preset_file(preset_path)
    apply_preset_to_args(args, preset)

    _validate_runtime_options(args)

    client = SpringInitializrClient(
        timeout_seconds=args.timeout if args.timeout is not None else DEFAULT_TIMEOUT_SECONDS,
        use_cache=True if args.use_cache is None else bool(args.use_cache),
        refresh_metadata=bool(args.refresh_metadata),
        cache_ttl_seconds=args.cache_ttl if args.cache_ttl is not None else DEFAULT_CACHE_TTL_SECONDS,
        max_retries=args.retries if args.retries is not None else DEFAULT_MAX_RETRIES,
        backoff_seconds=args.backoff if args.backoff is not None else DEFAULT_BACKOFF_SECONDS,
    )

    if not hasattr(args, "format") or args.format is None:
        args.format = "text"

    if args.command == "new":
        if args.interactive is None:
            args.interactive = False
        if args.force is None:
            args.force = False
        if args.dry_run is None:
            args.dry_run = False
        if args.show_url is None:
            args.show_url = False
        if args.git_init is None:
            args.git_init = False
        if args.init_readme is None:
            args.init_readme = False
        if args.add_docker is None:
            args.add_docker = False
        if args.add_github_actions is None:
            args.add_github_actions = False
        return cmd_new(args, client)

    if args.command == "list":
        return cmd_list(args, client)

    if args.command == "search":
        if args.limit is None:
            args.limit = 20
        return cmd_search(args, client)

    return cmd_doctor(args, client)


def _add_runtime_options(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument(
        "--preset",
        default=None,
        help="Path to preset TOML file. Default: ./.spring-init.toml if present.",
    )
    command_parser.add_argument(
        "--use-cache",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable/disable metadata cache.",
    )
    command_parser.add_argument(
        "--refresh-metadata",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Force refresh metadata from network before using cache.",
    )
    command_parser.add_argument(
        "--cache-ttl",
        type=int,
        default=None,
        help=f"Metadata cache TTL in seconds (default: {DEFAULT_CACHE_TTL_SECONDS}).",
    )
    command_parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    command_parser.add_argument(
        "--retries",
        type=int,
        default=None,
        help=f"HTTP retry count (default: {DEFAULT_MAX_RETRIES}).",
    )
    command_parser.add_argument(
        "--backoff",
        type=float,
        default=None,
        help=f"Exponential retry backoff base seconds (default: {DEFAULT_BACKOFF_SECONDS}).",
    )


def _validate_runtime_options(args: argparse.Namespace) -> None:
    if args.cache_ttl is not None and args.cache_ttl < 0:
        raise ValueError("--cache-ttl must be >= 0")
    if args.timeout is not None and args.timeout <= 0:
        raise ValueError("--timeout must be > 0")
    if args.retries is not None and args.retries < 0:
        raise ValueError("--retries must be >= 0")
    if args.backoff is not None and args.backoff < 0:
        raise ValueError("--backoff must be >= 0")

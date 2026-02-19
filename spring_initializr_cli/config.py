"""Configuration loading and preset application."""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

PRESET_FILENAME = ".spring-init.toml"
BOOL_FIELDS = {
    "interactive",
    "force",
    "dry_run",
    "show_url",
    "git_init",
    "init_readme",
    "add_docker",
    "add_github_actions",
    "use_cache",
    "refresh_metadata",
    "json",
}
INT_FIELDS = {"cache_ttl", "retries", "limit"}
FLOAT_FIELDS = {"timeout", "backoff"}


def resolve_preset_path(preset_arg: str | None) -> Path | None:
    if preset_arg:
        path = Path(preset_arg).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Preset file does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"Preset path is not a file: {path}")
        return path

    default = Path.cwd() / PRESET_FILENAME
    if default.exists() and default.is_file():
        return default
    return None


def load_preset_file(path: Path | None) -> dict:
    if path is None:
        return {}

    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid TOML in preset file {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Preset file must define a TOML table at top-level: {path}")
    return payload


def apply_preset_to_args(args: argparse.Namespace, preset: dict) -> argparse.Namespace:
    initially_unset = {
        attr_name
        for attr_name, value in vars(args).items()
        if _is_unset(value)
    }

    defaults = preset.get("defaults")
    if isinstance(defaults, dict):
        _apply_mapping(args, defaults, initially_unset)

    command_section = preset.get(args.command)
    if isinstance(command_section, dict):
        _apply_mapping(args, command_section, initially_unset)

    return args


def _apply_mapping(args: argparse.Namespace, mapping: dict, allowed_fields: set[str]) -> None:
    for raw_key, raw_value in mapping.items():
        attr = raw_key.replace("-", "_")
        if not hasattr(args, attr):
            continue

        if attr not in allowed_fields:
            continue

        value = _coerce_value(attr, raw_value)
        setattr(args, attr, value)


def _is_unset(value: object) -> bool:
    return value is None or value == ""


def _coerce_value(attr: str, value: object) -> object:
    if attr in BOOL_FIELDS:
        if isinstance(value, bool):
            return value
        raise ValueError(f"Preset value for '{attr}' must be boolean")

    if attr in INT_FIELDS:
        if isinstance(value, int):
            return value
        raise ValueError(f"Preset value for '{attr}' must be integer")

    if attr in FLOAT_FIELDS:
        if isinstance(value, (int, float)):
            return float(value)
        raise ValueError(f"Preset value for '{attr}' must be numeric")

    if attr == "dependencies":
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            return ",".join(items)
        raise ValueError("Preset value for 'dependencies' must be string or list")

    if isinstance(value, str):
        return value

    # Accept scalar TOML values for generic string-compatible args.
    if isinstance(value, (int, float)):
        return str(value)

    raise ValueError(f"Unsupported preset type for '{attr}'")

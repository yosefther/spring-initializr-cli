"""Application entrypoint."""

from __future__ import annotations

import sys

from .cli import build_parser, run


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as exc:  # Keep CLI output compact and user-facing.
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

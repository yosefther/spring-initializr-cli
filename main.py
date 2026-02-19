#!/usr/bin/env python3
"""Compatibility entrypoint for the Spring Initializr CLI."""

from spring_initializr_cli.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())

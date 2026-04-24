#!/usr/bin/env python3
"""
Backward-compatibility shim. Use the unified CLI instead:

    uv run slides serve [args]

This file exists only so that old references still produce a helpful message.
"""
import sys

print(
    "server.py has been replaced by the 'slides' CLI.\n"
    "\n"
    "Run:  uv run slides serve\n"
    "Help: uv run slides serve --help",
    file=sys.stderr,
)

from slides_builder.cli import main
main()

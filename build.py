#!/usr/bin/env python3
"""
Backward-compatibility shim. Use the unified CLI instead:

    uv run slides build [args]

This file exists only so that old references still produce a helpful message.
"""
import sys

print(
    "build.py has been replaced by the 'slides' CLI.\n"
    "\n"
    "Run:  uv run slides build\n"
    "Help: uv run slides build --help\n"
    "All commands: uv run slides --help",
    file=sys.stderr,
)

# Attempt to forward to the real CLI so existing scripts keep working.
from slides_builder.cli import main
main()

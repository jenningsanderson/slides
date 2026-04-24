"""
Config loading for slides-builder.

Looks for slides/config.yaml (or the directory set by --slides-dir) and merges
its values as defaults under any explicit CLI flags.

Config file format (all keys optional):

    title: My Presentation
    base_url: /my-repo/
    output: dist/index.html
    no_backup: false
    serve:
      port: 3000
      no_open: false
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


def find_config(slides_dir: str) -> Path | None:
    """Return path to config.yaml if it exists alongside the slides."""
    p = Path(slides_dir) / "config.yaml"
    return p if p.exists() else None


def load(slides_dir: str) -> dict:
    """Load and return the config dict for the given slides directory."""
    cfg_path = find_config(slides_dir)
    if cfg_path is None:
        return {}
    try:
        with cfg_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Warning: could not parse {cfg_path}: {e}", file=sys.stderr)
        return {}


def resolve(cfg: dict, key: str, cli_value: Any, default: Any = None) -> Any:
    """
    Return the effective value for a config key, with CLI taking precedence:
      cli_value (if not the default/empty) > config file > default
    """
    if cli_value is not None and cli_value != "":
        return cli_value
    if key in cfg and cfg[key] is not None:
        return cfg[key]
    return default

"""
Config loading for slides-builder.

Looks for slides/config.yaml (or the directory set by --slides-dir) and merges
its values as defaults under any explicit CLI flags.

Config file format (all keys optional):

    title: My Presentation
    base_url: /my-repo/
    output: dist/index.html
    css_dir: slides/css          # default: slides/css (alongside slide files)
    assets_dir: assets           # default: assets (repo root)
    no_backup: false
    serve:
      port: 3000
      no_open: false
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_SENTINEL = object()


def _load_yaml(path: Path) -> dict:
    """Load a YAML file using stdlib only (PyYAML not required for simple configs)."""
    try:
        import yaml  # type: ignore
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Minimal YAML parser — handles flat key: value and one level of nesting.
        return _parse_simple_yaml(path.read_text(encoding="utf-8"))


def _parse_simple_yaml(text: str) -> dict:
    """
    Parse a subset of YAML sufficient for config files:
      - top-level key: value pairs
      - one level of indented sub-keys (for the 'serve:' block)
      - bool/int/float coercion
      - # comments
      - quoted strings
    """
    result: dict[str, Any] = {}
    current_parent: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#")[0].rstrip()
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip())

        if ":" not in line:
            continue

        key, _, val = line.strip().partition(":")
        key = key.strip()
        val = val.strip().strip("'\"")

        if indent == 0:
            if val == "":
                current_parent = key
                result[key] = {}
            else:
                current_parent = None
                result[key] = _coerce(val)
        elif current_parent:
            result[current_parent][key] = _coerce(val)

    return result


def _coerce(val: str) -> Any:
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    if val == "null" or val == "~" or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


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
        data = _load_yaml(cfg_path)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Warning: could not parse {cfg_path}: {e}", file=sys.stderr)
        return {}


def resolve(cfg: dict, key: str, cli_value: Any, default: Any = None) -> Any:
    """
    Return the effective value for a config key, with CLI taking precedence:
      cli_value (if not the default/empty) > config file > default
    """
    # Treat empty strings and argparse defaults as "not set"
    if cli_value is not None and cli_value != "" and cli_value is not _SENTINEL:
        return cli_value
    if key in cfg and cfg[key] is not None:
        return cfg[key]
    return default

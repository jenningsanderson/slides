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
    deploy:
      provider: pages        # pages | s3  (default: pages)
      path_prefix: ""        # optional base path, provider-agnostic
      s3:
        bucket: slides.jenningsanderson.com
        region: us-east-1
        prefix: ""           # optional; derived from <owner>/<repo> when absent
        cloudfront_distribution_id: ""
        cache_control_html: "no-cache"
        cache_control_assets: "public,max-age=31536000,immutable"
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


# ---------------------------------------------------------------------------
# Deploy / publish config helpers
# ---------------------------------------------------------------------------

VALID_PROVIDERS = ("pages", "s3")


def get_deploy_config(cfg: dict) -> dict:
    """
    Return the resolved deploy sub-config with defaults applied.

    Returns a dict with at minimum:
      { "provider": "pages", "path_prefix": "", "s3": { ... defaults ... } }
    """
    deploy = cfg.get("deploy") or {}
    if not isinstance(deploy, dict):
        deploy = {}

    provider = deploy.get("provider") or "pages"
    path_prefix = deploy.get("path_prefix") or ""

    s3_defaults: dict = {
        "bucket": "",
        "region": "us-east-1",
        "prefix": "",
        "cloudfront_distribution_id": "",
        "cache_control_html": "no-cache",
        "cache_control_assets": "public,max-age=31536000,immutable",
    }
    s3_cfg = deploy.get("s3") or {}
    if not isinstance(s3_cfg, dict):
        s3_cfg = {}
    merged_s3 = {**s3_defaults, **{k: v for k, v in s3_cfg.items() if v is not None}}

    return {
        "provider": provider,
        "path_prefix": path_prefix,
        "s3": merged_s3,
    }


def validate_deploy_config(deploy: dict) -> list[str]:
    """
    Validate the deploy config dict (as returned by get_deploy_config).
    Returns a list of human-readable error strings (empty == valid).
    """
    errors: list[str] = []
    provider = deploy.get("provider", "pages")

    if provider not in VALID_PROVIDERS:
        errors.append(
            f"deploy.provider must be one of {VALID_PROVIDERS!r}, got {provider!r}"
        )
        return errors  # no point checking S3 keys if provider is unknown

    if provider == "s3":
        s3 = deploy.get("s3", {})
        if not s3.get("bucket"):
            errors.append("deploy.s3.bucket is required when provider is 's3'")
        if not s3.get("region"):
            errors.append("deploy.s3.region is required when provider is 's3'")

    return errors

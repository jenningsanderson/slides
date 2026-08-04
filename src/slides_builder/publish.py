"""
slides publish — deploy a built presentation to GitHub Pages or S3.

Build/publish concerns are intentionally separated:
  1. `slides build` produces a static output directory.
  2. `slides publish` deploys that directory to a provider.

GitHub Pages provider
---------------------
Prints instructions / sets up the Pages artifact.  In CI the workflow
handles the actual upload-pages-artifact / deploy-pages steps; this
module validates the config and summarises what will happen.

S3 provider
-----------
Uploads every file in the output directory to:
    s3://<bucket>/<prefix>/
where <prefix> defaults to <owner>/<repo> derived from the
GITHUB_REPOSITORY env var (format "owner/repo"), or can be set
explicitly via deploy.s3.prefix in config.yaml.

Requires the AWS CLI to be available and configured (OIDC role or
AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY environment variables).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def publish(
    output_dir: str,
    deploy_cfg: dict,
    *,
    dry_run: bool = False,
) -> None:
    """
    Dispatch to the correct provider.

    Parameters
    ----------
    output_dir : str
        Path to the built presentation directory (must exist).
    deploy_cfg : dict
        As returned by config.get_deploy_config().
    dry_run : bool
        If True, print what would happen but do not upload.
    """
    provider = deploy_cfg.get("provider", "pages")

    if provider == "pages":
        _publish_pages(output_dir, deploy_cfg, dry_run=dry_run)
    elif provider == "s3":
        _publish_s3(output_dir, deploy_cfg, dry_run=dry_run)
    else:
        sys.exit(
            f"Unknown provider {provider!r}.  "
            "Set deploy.provider to 'pages' or 's3' in config.yaml."
        )


# ---------------------------------------------------------------------------
# GitHub Pages
# ---------------------------------------------------------------------------

def _publish_pages(output_dir: str, deploy_cfg: dict, *, dry_run: bool) -> None:
    """
    GitHub Pages publishing is handled by the workflow (upload-pages-artifact
    + deploy-pages actions).  This function validates the output directory and
    prints a summary so the user knows what will be deployed.
    """
    out = Path(output_dir)
    if not out.is_dir():
        sys.exit(
            f"Output directory {output_dir!r} does not exist.  "
            "Run `slides build` first."
        )

    index = out / "index.html"
    if not index.exists():
        sys.exit(
            f"No index.html found in {output_dir!r}.  "
            "Run `slides build` first."
        )

    print(f"[pages] Output directory: {out.resolve()}")
    print(
        "[pages] Deploy to GitHub Pages via the 'upload-pages-artifact' and "
        "'deploy-pages' Actions steps in your workflow."
    )
    if dry_run:
        print("[pages] dry-run: no changes made.")


# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------

def _resolve_s3_prefix(s3_cfg: dict) -> str:
    """
    Determine the S3 key prefix.
    Priority: explicit config > GITHUB_REPOSITORY env var > empty string.
    """
    explicit = (s3_cfg.get("prefix") or "").strip("/")
    if explicit:
        return explicit

    repo = os.environ.get("GITHUB_REPOSITORY", "").strip("/")
    if repo:
        return repo

    return ""


def _publish_s3(output_dir: str, deploy_cfg: dict, *, dry_run: bool) -> None:
    out = Path(output_dir)
    if not out.is_dir():
        sys.exit(
            f"Output directory {output_dir!r} does not exist.  "
            "Run `slides build` first."
        )

    s3_cfg = deploy_cfg.get("s3", {})
    bucket = (s3_cfg.get("bucket") or "").strip()
    region = (s3_cfg.get("region") or "us-east-1").strip()
    prefix = _resolve_s3_prefix(s3_cfg)
    cf_dist = (s3_cfg.get("cloudfront_distribution_id") or "").strip()
    cc_html = s3_cfg.get("cache_control_html", "no-cache")
    cc_assets = s3_cfg.get(
        "cache_control_assets", "public,max-age=31536000,immutable"
    )

    if not bucket:
        sys.exit(
            "deploy.s3.bucket is required for provider 's3'.  "
            "Add it to config.yaml or pass --bucket."
        )

    dest = f"s3://{bucket}/{prefix}/" if prefix else f"s3://{bucket}/"
    print(f"[s3] Uploading {out.resolve()} → {dest}")
    print(f"[s3] Region: {region}")
    if cf_dist:
        print(f"[s3] CloudFront distribution: {cf_dist}")

    if dry_run:
        print("[s3] dry-run: no files uploaded.")
        return

    # Check that the AWS CLI is available.
    if subprocess.call(
        ["aws", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) != 0:
        sys.exit(
            "AWS CLI not found.  Install it or ensure it is on PATH.\n"
            "See https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        )

    # Upload HTML files with no-cache headers.
    _s3_sync(
        source=str(out),
        dest=dest,
        region=region,
        include="*.html",
        cache_control=cc_html,
    )

    # Upload everything else with long-lived cache headers.
    _s3_sync(
        source=str(out),
        dest=dest,
        region=region,
        exclude="*.html",
        cache_control=cc_assets,
    )

    print(f"[s3] Upload complete → {dest}")

    # Optional CloudFront invalidation.
    if cf_dist:
        _cf_invalidate(cf_dist, prefix, region)


def _s3_sync(
    *,
    source: str,
    dest: str,
    region: str,
    include: str | None = None,
    exclude: str | None = None,
    cache_control: str,
) -> None:
    cmd = [
        "aws", "s3", "sync",
        source, dest,
        "--region", region,
        "--cache-control", cache_control,
        "--delete",
    ]
    if include:
        cmd += ["--exclude", "*", "--include", include]
    if exclude:
        cmd += ["--exclude", exclude]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(f"[s3] aws s3 sync failed with exit code {result.returncode}")


def _cf_invalidate(distribution_id: str, prefix: str, region: str) -> None:
    path = f"/{prefix}/*" if prefix else "/*"
    cmd = [
        "aws", "cloudfront", "create-invalidation",
        "--distribution-id", distribution_id,
        "--paths", path,
        "--region", region,
    ]
    print(f"[s3] Invalidating CloudFront {distribution_id} path {path}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(
            f"[s3] Warning: CloudFront invalidation failed (exit {result.returncode})",
            file=sys.stderr,
        )

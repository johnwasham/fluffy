#!/usr/bin/env python3
"""
S3 publisher for Fluffy blog.

Diffs local output/ against S3:
  - Uploads new and changed files
  - Deletes S3 files that no longer exist in output/ (e.g. posts reverted to draft)
  - Invalidates all affected paths in CloudFront

Reads credentials from .env.local (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION).
Reads bucket name and CloudFront distribution ID from blog/config.yaml.

Usage:
    python src/publisher.py [--dry-run]
"""

import hashlib
import mimetypes
import os
import sys
from pathlib import Path

import boto3
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
BLOG_DIR = ROOT / "blog"
OUTPUT_DIR = ROOT / "output"

LONG_CACHE = "public, max-age=31536000, immutable"   # 1 year — static assets
SHORT_CACHE = "public, max-age=300"                   # 5 min — HTML pages


def load_config():
    with open(BLOG_DIR / "config.yaml") as f:
        return yaml.safe_load(f)


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def is_html(key: str) -> bool:
    return key.endswith(".html") or key.endswith("/")


def cache_control(key: str) -> str:
    # Long cache for assets (images, css, js); short for HTML
    if key.startswith("static/") or key.startswith("images/"):
        return LONG_CACHE
    return SHORT_CACHE


def content_type(path: Path) -> str:
    ct, _ = mimetypes.guess_type(str(path))
    return ct or "application/octet-stream"


def list_s3_objects(s3_client, bucket: str) -> dict[str, str]:
    """Returns {key: etag} for all objects in the bucket."""
    objects = {}
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            # S3 ETags are quoted MD5 for simple (non-multipart) uploads
            etag = obj["ETag"].strip('"')
            objects[obj["Key"]] = etag
    return objects


def publish(dry_run: bool = False, verbose: bool = True) -> dict:
    load_dotenv(ROOT / ".env.local")
    config = load_config()
    bucket = os.environ.get("S3_BUCKET", "").strip()
    distribution_id = config.get("cloudfront_distribution_id", "").strip()

    if not bucket:
        raise ValueError("S3_BUCKET not set in .env.local")

    s3 = boto3.client("s3")
    cf = boto3.client("cloudfront") if distribution_id and distribution_id != "CHANGE_ME" else None

    if verbose:
        print(f"Syncing to s3://{bucket}/")

    # Build local file map {key: local_path}
    local_files: dict[str, Path] = {}
    for path in OUTPUT_DIR.rglob("*"):
        if path.is_file():
            key = str(path.relative_to(OUTPUT_DIR))
            local_files[key] = path

    # Get current S3 state
    s3_objects = list_s3_objects(s3, bucket)

    to_upload: list[str] = []
    to_delete: list[str] = []
    invalidation_paths: list[str] = []

    # Find files to upload (new or changed)
    for key, local_path in local_files.items():
        local_md5 = file_md5(local_path)
        s3_etag = s3_objects.get(key)
        if s3_etag != local_md5:
            to_upload.append(key)

    # Find files to delete (exist in S3 but not locally)
    for key in s3_objects:
        if key not in local_files:
            to_delete.append(key)

    if verbose:
        print(f"  To upload:  {len(to_upload)}")
        print(f"  To delete:  {len(to_delete)}")

    # Upload changed/new files
    for key in to_upload:
        local_path = local_files[key]
        ct = content_type(local_path)
        cc = cache_control(key)
        if verbose:
            print(f"  UP  {key}")
        if not dry_run:
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=local_path.read_bytes(),
                ContentType=ct,
                CacheControl=cc,
            )
        invalidation_paths.append("/" + key)

    # Delete removed files
    for key in to_delete:
        if verbose:
            print(f"  DEL {key}")
        if not dry_run:
            s3.delete_object(Bucket=bucket, Key=key)
        invalidation_paths.append("/" + key)

    # CloudFront invalidation
    if cf and invalidation_paths and not dry_run:
        # Deduplicate and also add directory paths (index.html → parent/)
        paths = set(invalidation_paths)
        for p in list(paths):
            if p.endswith("/index.html"):
                paths.add(p[: -len("index.html")])
        paths_list = sorted(paths)
        if verbose:
            print(f"  Invalidating {len(paths_list)} CloudFront path(s)...")
        cf.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "Paths": {"Quantity": len(paths_list), "Items": paths_list},
                "CallerReference": str(__import__("time").time()),
            },
        )
    elif not cf and (to_upload or to_delete):
        if verbose:
            print("  (CloudFront distribution ID not set — skipping invalidation)")

    if verbose:
        if dry_run:
            print("Dry run complete — no changes made.")
        else:
            print("Done.")

    return {"uploaded": len(to_upload), "deleted": len(to_delete)}


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        print("DRY RUN — no changes will be made")
    publish(dry_run=dry)

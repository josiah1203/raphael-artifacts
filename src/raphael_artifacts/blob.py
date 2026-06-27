"""Blob storage — MinIO when configured, local filesystem fallback."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any


def _local_blob_dir() -> Path:
    base = Path(os.environ.get("RAPHAEL_BLOB_DIR", "/tmp/raphael-blobs"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def minio_configured() -> bool:
    return bool(os.environ.get("RAPHAEL_MINIO_ENDPOINT", "").strip())


def ensure_buckets() -> None:
    """Create configured MinIO buckets if missing (idempotent)."""
    endpoint = os.environ.get("RAPHAEL_MINIO_ENDPOINT", "").strip()
    if not endpoint:
        return
    from minio import Minio

    client = Minio(
        endpoint,
        access_key=os.environ.get("RAPHAEL_MINIO_ACCESS_KEY", "raphael"),
        secret_key=os.environ.get("RAPHAEL_MINIO_SECRET_KEY", "raphaeldev"),
        secure=os.environ.get("RAPHAEL_MINIO_SECURE", "false").lower() in ("1", "true", "yes"),
    )
    for env_key, default in (
        ("RAPHAEL_MINIO_BUCKET", "raphael-artifacts"),
        ("RAPHAEL_MINIO_BACKUP_BUCKET", "raphael-backups"),
    ):
        bucket = os.environ.get(env_key, default)
        if bucket and not client.bucket_exists(bucket):
            client.make_bucket(bucket)


def put_blob(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    endpoint = os.environ.get("RAPHAEL_MINIO_ENDPOINT", "").strip()
    if not endpoint:
        path = _local_blob_dir() / key.replace("/", "__")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"file://{path}"

    from minio import Minio

    client = Minio(
        endpoint,
        access_key=os.environ.get("RAPHAEL_MINIO_ACCESS_KEY", "raphael"),
        secret_key=os.environ.get("RAPHAEL_MINIO_SECRET_KEY", "raphaeldev"),
        secure=os.environ.get("RAPHAEL_MINIO_SECURE", "false").lower() in ("1", "true", "yes"),
    )
    bucket = os.environ.get("RAPHAEL_MINIO_BUCKET", "raphael-artifacts")
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    client.put_object(bucket, key, io.BytesIO(data), len(data), content_type=content_type)
    return f"s3://{bucket}/{key}"


def put_json_blob(key: str, payload: dict[str, Any]) -> str:
    return put_blob(key, json.dumps(payload, default=str).encode("utf-8"), "application/json")


def get_blob(key: str) -> bytes | None:
    if key.startswith("file://"):
        path = Path(key.removeprefix("file://"))
        return path.read_bytes() if path.exists() else None
    if key.startswith("s3://"):
        _, rest = key.split("s3://", 1)
        bucket, object_key = rest.split("/", 1)
        endpoint = os.environ.get("RAPHAEL_MINIO_ENDPOINT", "").strip()
        if not endpoint:
            return None
        from minio import Minio

        client = Minio(
            endpoint,
            access_key=os.environ.get("RAPHAEL_MINIO_ACCESS_KEY", "raphael"),
            secret_key=os.environ.get("RAPHAEL_MINIO_SECRET_KEY", "raphaeldev"),
            secure=os.environ.get("RAPHAEL_MINIO_SECURE", "false").lower() in ("1", "true", "yes"),
        )
        response = client.get_object(bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    path = _local_blob_dir() / key.replace("/", "__")
    return path.read_bytes() if path.exists() else None

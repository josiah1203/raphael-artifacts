"""Module file blob storage — content-addressed keys under workspace/module/branch/path."""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from raphael_artifacts.blob import get_blob, put_blob

DEFAULT_LARGE_FILE_THRESHOLD = 1_048_576  # 1MB — raphael_pages 4-06 large-file warning
LARGE_FILE_THRESHOLD_BYTES = DEFAULT_LARGE_FILE_THRESHOLD
MODULE_FILES_PREFIX = "module-files"

_BINARY_EXTENSIONS = {
    ".bin",
    ".bz2",
    ".dll",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".so",
    ".tar",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}

_TEXT_CONTENT_TYPES = {
    "application/javascript",
    "application/json",
    "application/xml",
    "application/x-yaml",
    "application/yaml",
}


def normalize_repo_path(path: str) -> str:
    normalized = path.strip().lstrip("./")
    while normalized.startswith("/"):
        normalized = normalized[1:]
    return normalized or "."


def build_module_file_key(workspace_id: str, module_id: str, branch: str, path: str) -> str:
    normalized = normalize_repo_path(path)
    return f"{MODULE_FILES_PREFIX}/{workspace_id}/{module_id}/{branch}/{normalized}"


def module_file_object_key(workspace_id: str, module_id: str, branch: str, path: str) -> str:
    return build_module_file_key(workspace_id, module_id, branch, path)


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ModuleFileMetadata:
    content_type: str
    is_binary: bool
    is_large: bool
    size: int
    content_hash: str


def detect_file_metadata(path: str, data: bytes) -> ModuleFileMetadata:
    normalized_path = normalize_repo_path(path)
    ext = Path(normalized_path).suffix.lower()
    guessed, _ = mimetypes.guess_type(normalized_path)
    content_type = guessed or "application/octet-stream"
    size = len(data)
    digest = content_hash(data)
    is_large = size > DEFAULT_LARGE_FILE_THRESHOLD

    if ext == ".md":
        return ModuleFileMetadata("text/plain", False, is_large, size, digest)

    if ext in _BINARY_EXTENSIONS:
        return ModuleFileMetadata(content_type, True, is_large, size, digest)

    if content_type.startswith(("image/", "video/", "audio/")):
        return ModuleFileMetadata(content_type, True, is_large, size, digest)

    if content_type in ("application/pdf", "application/zip", "application/gzip"):
        return ModuleFileMetadata(content_type, True, is_large, size, digest)

    if b"\x00" in data[:8192]:
        return ModuleFileMetadata("application/octet-stream", True, is_large, size, digest)

    if content_type.startswith("text/") or content_type in _TEXT_CONTENT_TYPES:
        return ModuleFileMetadata(content_type, False, is_large, size, digest)

    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return ModuleFileMetadata("application/octet-stream", True, is_large, size, digest)

    if not guessed:
        content_type = "text/plain"
    return ModuleFileMetadata(content_type, False, is_large, size, digest)


def detect_content_type(path: str, data: bytes) -> tuple[str, bool]:
    meta = detect_file_metadata(path, data)
    return meta.content_type, meta.is_binary


@dataclass(frozen=True)
class ModuleFileRecord:
    workspace_id: str
    module_id: str
    branch: str
    path: str
    blob_key: str
    content_hash: str
    content_type: str
    size: int
    is_binary: bool
    is_large: bool


@dataclass(frozen=True)
class ModuleFilePayload(ModuleFileRecord):
    data: bytes


class ModuleFileStorage:
    """Store and retrieve module file blobs scoped by workspace/module/branch/path."""

    def upload(
        self,
        workspace_id: str,
        module_id: str,
        branch: str,
        path: str,
        data: bytes,
    ) -> ModuleFileRecord:
        normalized_path = normalize_repo_path(path)
        object_key = build_module_file_key(workspace_id, module_id, branch, normalized_path)
        meta = detect_file_metadata(normalized_path, data)
        stored_key = put_blob(object_key, data, content_type=meta.content_type)
        return ModuleFileRecord(
            workspace_id=workspace_id,
            module_id=module_id,
            branch=branch,
            path=normalized_path,
            blob_key=stored_key,
            content_hash=meta.content_hash,
            content_type=meta.content_type,
            size=meta.size,
            is_binary=meta.is_binary,
            is_large=meta.is_large,
        )

    def fetch(
        self,
        workspace_id: str,
        module_id: str,
        branch: str,
        path: str,
        *,
        blob_key: str | None = None,
    ) -> ModuleFilePayload | None:
        normalized_path = normalize_repo_path(path)
        object_key = build_module_file_key(workspace_id, module_id, branch, normalized_path)
        data = None
        if blob_key:
            data = get_blob(blob_key)
        if data is None:
            data = get_blob(object_key)
        if data is None:
            from raphael_artifacts.blob import minio_configured

            if minio_configured():
                import os

                bucket = os.environ.get("RAPHAEL_MINIO_BUCKET", "raphael-artifacts")
                data = get_blob(f"s3://{bucket}/{object_key}")
        if data is None:
            return None

        meta = detect_file_metadata(normalized_path, data)
        return ModuleFilePayload(
            workspace_id=workspace_id,
            module_id=module_id,
            branch=branch,
            path=normalized_path,
            blob_key=blob_key or object_key,
            content_hash=meta.content_hash,
            content_type=meta.content_type,
            size=meta.size,
            is_binary=meta.is_binary,
            is_large=meta.is_large,
            data=data,
        )

    @staticmethod
    def record_to_dict(record: ModuleFileRecord | ModuleFilePayload) -> dict[str, Any]:
        return {
            "workspace_id": record.workspace_id,
            "module_id": record.module_id,
            "branch": record.branch,
            "path": record.path,
            "blob_key": record.blob_key,
            "content_hash": record.content_hash,
            "content_type": record.content_type,
            "size": record.size,
            "is_binary": record.is_binary,
            "is_large": record.is_large,
        }

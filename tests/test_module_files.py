"""Module file blob storage — upload, fetch, large-file flag, binary detection."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from raphael_artifacts.app import app
from raphael_artifacts.module_files import (
    DEFAULT_LARGE_FILE_THRESHOLD,
    ModuleFileStorage,
    build_module_file_key,
    detect_file_metadata,
)

client = TestClient(app)


@pytest.fixture
def blob_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("RAPHAEL_MINIO_ENDPOINT", raising=False)
    monkeypatch.setenv("RAPHAEL_BLOB_DIR", str(tmp_path / "blobs"))
    return tmp_path / "blobs"


def test_build_module_file_key_scopes_workspace_module_branch_path() -> None:
    key = build_module_file_key("ws-1", "mod-2", "main", "src/lib/foo.py")
    assert key == "module-files/ws-1/mod-2/main/src/lib/foo.py"


def test_build_module_file_key_strips_leading_slash() -> None:
    key = build_module_file_key("ws-1", "mod-2", "main", "/README.md")
    assert key == "module-files/ws-1/mod-2/main/README.md"


def test_detect_text_file_metadata() -> None:
    meta = detect_file_metadata("README.md", b"# Hello\nworld\n")
    assert meta.content_type == "text/plain"
    assert meta.is_binary is False
    assert meta.is_large is False
    assert meta.size == 14
    assert len(meta.content_hash) == 64


def test_detect_binary_file_metadata() -> None:
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    meta = detect_file_metadata("assets/logo.png", png_header)
    assert meta.is_binary is True
    assert meta.content_type == "image/png"


def test_large_file_threshold_constant() -> None:
    assert DEFAULT_LARGE_FILE_THRESHOLD == 1_048_576


def test_detect_large_file_flag() -> None:
    data = b"x" * (DEFAULT_LARGE_FILE_THRESHOLD + 1)
    meta = detect_file_metadata("big.txt", data)
    assert meta.is_large is True
    assert meta.size == DEFAULT_LARGE_FILE_THRESHOLD + 1


def test_upload_and_fetch_roundtrip(blob_dir: Path) -> None:
    storage = ModuleFileStorage()
    content = b"print('hello')\n"
    uploaded = storage.upload("ws-test", "mod-test", "develop", "main.py", content)
    assert uploaded.content_hash
    assert "ws-test" in uploaded.blob_key and "main.py" in uploaded.blob_key
    assert uploaded.is_binary is False
    assert uploaded.is_large is False

    fetched = storage.fetch("ws-test", "mod-test", "develop", "main.py")
    assert fetched is not None
    assert fetched.data == content
    assert fetched.content_hash == uploaded.content_hash


def test_fetch_missing_returns_none(blob_dir: Path) -> None:
    storage = ModuleFileStorage()
    assert storage.fetch("ws-x", "mod-x", "main", "missing.txt") is None


def test_content_hash_is_stable_for_same_bytes(blob_dir: Path) -> None:
    storage = ModuleFileStorage()
    data = b"stable content"
    first = storage.upload("ws", "mod", "main", "a.txt", data)
    second = storage.upload("ws", "mod", "main", "b.txt", data)
    assert first.content_hash == second.content_hash


def test_api_upload_and_fetch_blob(blob_dir: Path) -> None:
    res = client.put(
        "/v1/artifacts/module-files/ws-api/mod-api/main/hello.txt",
        content=b"api roundtrip",
        headers={"content-type": "text/plain"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["path"] == "hello.txt"
    assert body["branch"] == "main"
    assert body["is_binary"] is False
    assert body["content_hash"]

    got = client.get("/v1/artifacts/module-files/ws-api/mod-api/main/hello.txt")
    assert got.status_code == 200
    meta = got.json()
    assert meta["size"] == len(b"api roundtrip")
    assert base64.b64decode(meta["content_base64"]) == b"api roundtrip"


def test_api_fetch_missing_returns_404(blob_dir: Path) -> None:
    res = client.get("/v1/artifacts/module-files/ws-api/mod-api/main/nope.txt")
    assert res.status_code == 404


def test_api_upload_binary_flags_metadata(blob_dir: Path) -> None:
    binary = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    res = client.put(
        "/v1/artifacts/module-files/ws-api/mod-api/main/img.png",
        content=binary,
        headers={"content-type": "application/octet-stream"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["is_binary"] is True
    assert body["content_type"] == "image/png"


def test_api_large_file_warning_flag(blob_dir: Path) -> None:
    large = b"z" * (DEFAULT_LARGE_FILE_THRESHOLD + 1)
    res = client.put(
        "/v1/artifacts/module-files/ws-api/mod-api/main/large.bin",
        content=large,
    )
    assert res.status_code == 200
    assert res.json()["is_large"] is True

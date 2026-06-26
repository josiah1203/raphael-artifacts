"""Artifacts API — object metadata and snapshots."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["artifacts"])
_db = Path(os.environ.get("RAPHAEL_ARTIFACTS_DB", "/tmp/raphael-artifacts.db"))
_conn = sqlite3.connect(_db, check_same_thread=False)
_conn.execute(
    """CREATE TABLE IF NOT EXISTS artifacts (
        id TEXT PRIMARY KEY,
        module_id TEXT,
        kind TEXT NOT NULL,
        metadata TEXT,
        created_at TEXT NOT NULL
    )"""
)
_conn.commit()


@router.get("")
def list_artifacts(module_id: str | None = None) -> dict[str, list]:
    if module_id:
        rows = _conn.execute("SELECT id, module_id, kind, metadata, created_at FROM artifacts WHERE module_id = ?", (module_id,)).fetchall()
    else:
        rows = _conn.execute("SELECT id, module_id, kind, metadata, created_at FROM artifacts").fetchall()
    return {
        "artifacts": [
            {"id": r[0], "module_id": r[1], "kind": r[2], "metadata": r[3], "created_at": r[4]} for r in rows
        ]
    }


@router.post("")
def create_artifact(body: dict[str, Any]) -> dict[str, Any]:
    aid = body.get("id", f"art-{int(datetime.now(timezone.utc).timestamp())}")
    now = datetime.now(timezone.utc).isoformat()
    _conn.execute(
        "INSERT INTO artifacts (id, module_id, kind, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
        (aid, body.get("module_id"), body.get("kind", "snapshot"), str(body.get("metadata", "")), now),
    )
    _conn.commit()
    return {"id": aid, "kind": body.get("kind", "snapshot"), "created_at": now}


@router.post("/ingest/snapshot")
def ingest_snapshot_route(body: dict[str, Any]) -> dict[str, str]:
    return create_artifact({"kind": "design_snapshot", "metadata": body, "module_id": body.get("module_id")})


@router.get("/objects/{object_id}")
def get_object(object_id: str) -> dict[str, Any]:
    row = _conn.execute("SELECT id, module_id, kind, metadata, created_at FROM artifacts WHERE id = ?", (object_id,)).fetchone()
    if not row:
        raise HTTPException(404, detail="not_found")
    return {"id": row[0], "module_id": row[1], "kind": row[2], "metadata": row[3], "created_at": row[4]}

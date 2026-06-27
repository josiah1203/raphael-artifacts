"""Artifact metadata store — SQLite dev fallback, Postgres when configured."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ArtifactsStore:
    def __init__(self, db_path: Path | None = None) -> None:
        from raphael_contracts import db as rdb

        self._postgres = rdb.is_postgres()
        if self._postgres:
            rdb.ensure_migrations()
        else:
            self._db = db_path or Path(os.environ.get("RAPHAEL_ARTIFACTS_DB", "/tmp/raphael-artifacts.db"))
            self._db.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db, check_same_thread=False)
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    module_id TEXT,
                    kind TEXT NOT NULL,
                    metadata TEXT,
                    blob_key TEXT,
                    created_at TEXT NOT NULL
                )"""
            )
            cols = {row[1] for row in self._conn.execute("PRAGMA table_info(artifacts)").fetchall()}
            if "blob_key" not in cols:
                self._conn.execute("ALTER TABLE artifacts ADD COLUMN blob_key TEXT")
            self._conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(
        self,
        *,
        artifact_id: str | None = None,
        module_id: str | None,
        kind: str,
        metadata: dict[str, Any] | str,
        blob_key: str | None = None,
    ) -> dict[str, Any]:
        aid = artifact_id or f"art-{uuid.uuid4().hex[:10]}"
        now = self._now()
        meta_json = metadata if isinstance(metadata, str) else json.dumps(metadata)
        if self._postgres:
            from raphael_contracts import db as rdb

            rdb.pg_execute(
                "INSERT INTO artifacts (id, module_id, kind, metadata, blob_key, created_at) VALUES (%s, %s, %s, %s::jsonb, %s, %s)",
                (aid, module_id, kind, meta_json, blob_key, now),
            )
        else:
            self._conn.execute(
                "INSERT INTO artifacts (id, module_id, kind, metadata, blob_key, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (aid, module_id, kind, meta_json, blob_key, now),
            )
            self._conn.commit()
        return self.get(aid) or {"id": aid, "module_id": module_id, "kind": kind, "created_at": now}

    def list(self, module_id: str | None = None) -> list[dict[str, Any]]:
        if self._postgres:
            from raphael_contracts import db as rdb

            if module_id:
                rows = rdb.pg_fetchall(
                    "SELECT id, module_id, kind, metadata, blob_key, created_at FROM artifacts WHERE module_id = %s ORDER BY created_at DESC",
                    (module_id,),
                )
            else:
                rows = rdb.pg_fetchall(
                    "SELECT id, module_id, kind, metadata, blob_key, created_at FROM artifacts ORDER BY created_at DESC",
                )
            return [self._row_to_dict(r) for r in rows]

        if module_id:
            rows = self._conn.execute(
                "SELECT id, module_id, kind, metadata, blob_key, created_at FROM artifacts WHERE module_id = ? ORDER BY created_at DESC",
                (module_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, module_id, kind, metadata, blob_key, created_at FROM artifacts ORDER BY created_at DESC",
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        if self._postgres:
            from raphael_contracts import db as rdb

            row = rdb.pg_fetchone(
                "SELECT id, module_id, kind, metadata, blob_key, created_at FROM artifacts WHERE id = %s",
                (artifact_id,),
            )
            return self._row_to_dict(row) if row else None

        row = self._conn.execute(
            "SELECT id, module_id, kind, metadata, blob_key, created_at FROM artifacts WHERE id = ?",
            (artifact_id,),
        ).fetchone()
        return self._row_to_dict(row) if row else None

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        if isinstance(row, dict):
            metadata = row.get("metadata")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    pass
            return {
                "id": row["id"],
                "module_id": row.get("module_id"),
                "kind": row["kind"],
                "metadata": metadata,
                "blob_key": row.get("blob_key"),
                "created_at": str(row.get("created_at") or ""),
            }
        metadata = row[3]
        try:
            metadata = json.loads(metadata) if metadata else {}
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            "id": row[0],
            "module_id": row[1],
            "kind": row[2],
            "metadata": metadata,
            "blob_key": row[4],
            "created_at": row[5],
        }

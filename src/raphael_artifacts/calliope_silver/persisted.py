"""Silver projection with SQLite persistence for on-prem deployments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from raphael_audit.core.silver_store import SilverStore

from raphael_artifacts.calliope_silver.projection import SilverProjectionService


class PersistedSilverProjectionService(SilverProjectionService):
    """In-memory projection backed by ~/.calliope/silver.db."""

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self._store = SilverStore(db_path=db_path)
        self._hydrate()

    def _object_type(self, event: dict[str, Any]) -> str:
        event_type = event.get("event_type", "")
        if event_type.startswith("geometry."):
            return "geometry"
        if event_type.startswith("electrical."):
            return "electrical"
        if event_type.startswith("software."):
            return "software"
        if event_type.startswith("project."):
            return "project"
        if event_type.startswith("simulation."):
            return "simulation"
        return "unknown"

    def _hydrate(self) -> None:
        rows = self._store.list_all()
        for row in rows:
            self._state[row["object_id"]] = row["state"]

    def apply_event(self, event: dict[str, Any]) -> None:
        super().apply_event(event)
        obj_id = self._object_key(event)
        if not obj_id:
            return
        state = self.get_projection(obj_id)
        if not state:
            return
        self._store.upsert(
            object_id=obj_id,
            project_id=str(event.get("project_id", "")),
            object_type=self._object_type(event),
            state=state,
            updated_at=str(event.get("timestamp_utc", "")),
        )

    def clear(self, project_id: str | None = None) -> None:
        if project_id:
            for row in self._store.list_by_project(project_id):
                self._state.pop(row["object_id"], None)
            self._store.delete_by_project(project_id)
        else:
            self._state.clear()
            self._store.clear()

    def close(self) -> None:
        self._store.close()

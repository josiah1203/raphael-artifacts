"""Artifacts API — object metadata and snapshots."""

from __future__ import annotations

import base64
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from raphael_artifacts.blob import get_blob, put_json_blob
from raphael_artifacts.module_files import ModuleFileStorage
from raphael_artifacts.parsers.altium import parse_altium
from raphael_artifacts.parsers.bom import parse_bom
from raphael_artifacts.parsers.kicad import parse_kicad
from raphael_artifacts.parsers.solidworks import parse_solidworks
from raphael_artifacts.store import ArtifactsStore

router = APIRouter(tags=["artifacts"])
_store = ArtifactsStore()
_module_files = ModuleFileStorage()


@router.put("/module-files/{workspace_id}/{module_id}/{branch}/{path:path}")
async def put_module_file_path(
    workspace_id: str,
    module_id: str,
    branch: str,
    path: str,
    request: Request,
) -> dict[str, Any]:
    body = await request.body()
    record = _module_files.upload(workspace_id, module_id, branch, path, body)
    return ModuleFileStorage.record_to_dict(record)


@router.get("/module-files/{workspace_id}/{module_id}/{branch}/{path:path}")
def get_module_file_path(
    workspace_id: str,
    module_id: str,
    branch: str,
    path: str,
) -> dict[str, Any]:
    record = _module_files.fetch(workspace_id, module_id, branch, path)
    if record is None:
        raise HTTPException(404, detail="not_found")
    return {
        **ModuleFileStorage.record_to_dict(record),
        "content_base64": base64.b64encode(record.data).decode("ascii"),
    }


@router.get("")
def list_artifacts(module_id: str | None = None) -> dict[str, list]:
    return {"artifacts": _store.list(module_id)}


@router.post("")
def create_artifact(body: dict[str, Any]) -> dict[str, Any]:
    return _store.create(
        artifact_id=body.get("id"),
        module_id=body.get("module_id"),
        kind=body.get("kind", "snapshot"),
        metadata=body.get("metadata") or {},
        blob_key=body.get("blob_key"),
    )


@router.post("/ingest/snapshot")
def ingest_snapshot_route(body: dict[str, Any]) -> dict[str, str]:
    module_id = body.get("module_id")
    blob_key = put_json_blob(f"snapshots/{module_id or 'unknown'}/{body.get('id', 'snapshot')}.json", body)
    art = _store.create(
        kind="design_snapshot",
        module_id=module_id,
        metadata={"snapshot": True, "module_id": module_id},
        blob_key=blob_key,
    )
    return art


def _parse_tool(kind: str, body: dict[str, Any]) -> dict[str, Any]:
    if kind == "kicad":
        return parse_kicad(body)
    if kind == "bom":
        return parse_bom(body)
    if kind == "altium":
        return parse_altium(body)
    if kind == "solidworks":
        return parse_solidworks(body)
    return {"format": kind, "module_id": body.get("module_id")}


def _ingest_tool(kind: str, body: dict[str, Any]) -> dict[str, Any]:
    parsed = _parse_tool(kind, body)
    module_id = body.get("module_id")
    blob_key = put_json_blob(f"ingest/{kind}/{module_id or 'unknown'}/payload.json", body)
    art = _store.create(
        kind=kind,
        module_id=module_id,
        metadata={"parsed": parsed, "blob_key": blob_key},
        blob_key=blob_key,
    )
    try:
        from raphael_contracts.kafka import publish_event

        publish_event(
            "raphael.artifacts.ingest",
            {"kind": kind, "artifact_id": art["id"], **parsed},
            source="raphael-artifacts",
        )
    except Exception:
        pass
    return {"artifact": art, "parsed": parsed}


@router.post("/ingest/bom")
def ingest_bom(body: dict[str, Any]) -> dict[str, Any]:
    return _ingest_tool("bom", body)


@router.post("/ingest/kicad")
def ingest_kicad(body: dict[str, Any]) -> dict[str, Any]:
    return _ingest_tool("kicad", body)


@router.post("/ingest/altium")
def ingest_altium(body: dict[str, Any]) -> dict[str, Any]:
    return _ingest_tool("altium", body)


@router.post("/ingest/solidworks")
def ingest_solidworks(body: dict[str, Any]) -> dict[str, Any]:
    return _ingest_tool("solidworks", body)


@router.post("/ingest/simulation")
def ingest_simulation(body: dict[str, Any]) -> dict[str, Any]:
    return _ingest_tool("simulation", body)


@router.post("/ingest/events")
def ingest_events(body: dict[str, Any]) -> dict[str, Any]:
    events = body.get("events", [])
    blob_key = put_json_blob("ingest/events/batch.json", body)
    art = _store.create(kind="ingest_events", metadata={"event_count": len(events)}, blob_key=blob_key)
    return {"accepted": len(events), "artifact": art}


@router.get("/objects/{object_id}")
def get_object(object_id: str) -> dict[str, Any]:
    art = _store.get(object_id)
    if not art:
        raise HTTPException(404, detail="not_found")
    return art


@router.get("/objects/{object_id}/content")
def get_object_content(object_id: str) -> Response:
    art = _store.get(object_id)
    if not art or not art.get("blob_key"):
        raise HTTPException(404, detail="not_found")
    data = get_blob(str(art["blob_key"]))
    if data is None:
        raise HTTPException(404, detail="blob_not_found")
    return Response(content=data, media_type="application/json")

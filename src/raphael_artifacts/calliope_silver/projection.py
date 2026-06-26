"""Silver layer projection for all discipline event types."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SilverProjectionService:
    def __init__(self) -> None:
        self._state: Dict[str, Dict[str, Any]] = {}

    def _object_key(self, event: dict[str, Any]) -> str | None:
        payload = event.get("payload", {})
        if payload.get("document_id"):
            return str(payload["document_id"])
        if payload.get("issue_key"):
            return str(payload["issue_key"])
        if payload.get("repository"):
            return str(payload["repository"])
        return event.get("project_id")

    def apply_event(self, event: Dict[str, Any]) -> None:
        event_type = event.get("event_type")
        payload = event.get("payload", {})
        obj_id = self._object_key(event)
        if not obj_id:
            return

        corrects_id = event.get("corrects_event_id")
        if corrects_id:
            logger.info("Event %s corrects %s", event["event_id"], corrects_id)
            if event_type == "geometry.feature_modified" and obj_id in self._state:
                f_id = payload.get("feature_id")
                if f_id and f_id in self._state[obj_id]["features"]:
                    self._state[obj_id]["features"][f_id]["properties"] = payload.get("properties", {})

        if obj_id not in self._state:
            self._state[obj_id] = {
                "features": {},
                "materials": {},
                "configurations": {},
                "joints": {},
                "issues": {},
                "repos": {},
                "footprints": {},
                "simulations": {},
                "events": [],
            }

        state = self._state[obj_id]
        state["events"].append(event["event_id"])

        if event_type == "geometry.feature_created":
            f_id = payload["feature_id"]
            state["features"][f_id] = payload
        elif event_type == "geometry.feature_modified":
            f_id = payload["feature_id"]
            if f_id in state["features"]:
                props = dict(state["features"][f_id].get("properties", {}))
                if payload.get("new_parameters"):
                    props.update(payload["new_parameters"])
                if payload.get("properties"):
                    props.update(payload["properties"])
                state["features"][f_id]["properties"] = props
                for key in ("feature_name", "feature_type", "old_parameters"):
                    if payload.get(key) is not None:
                        state["features"][f_id][key] = payload[key]
        elif event_type == "geometry.feature_deleted":
            state["features"].pop(payload["feature_id"], None)
        elif event_type == "geometry.material_assigned":
            state["materials"][payload.get("material_id", "default")] = payload
        elif event_type == "geometry.configuration_created":
            state["configurations"][payload["configuration_id"]] = payload
        elif event_type == "geometry.assembly_mate_added":
            state["joints"][payload["joint_id"]] = payload
        elif event_type.startswith("electrical."):
            ref = payload.get("footprint_ref", payload.get("net_name", "unknown"))
            state["footprints"][ref] = payload
        elif event_type.startswith("software."):
            repo = payload.get("repository", obj_id)
            state["repos"][repo] = {
                **payload,
                "last_event": event_type,
                "last_event_id": event["event_id"],
            }
        elif event_type.startswith("project."):
            key = payload.get("issue_key", obj_id)
            state["issues"][key] = {
                **payload,
                "last_event": event_type,
            }
        elif event_type.startswith("simulation."):
            state["simulations"][event["event_id"]] = payload

    def get_projection(self, object_id: str) -> Dict[str, Any]:
        return self._state.get(object_id, {})

    def list_objects(self) -> list[str]:
        return list(self._state.keys())

    def timeline(self, project_id: str | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for obj_id, state in self._state.items():
            if project_id and obj_id != project_id:
                continue
            for eid in state.get("events", []):
                items.append({"object_id": obj_id, "event_id": eid})
        return items

"""SolidWorks addon snapshot reader — schema validation and feature summary."""

from __future__ import annotations

from typing import Any

from raphael_artifacts.calliope_schema.validator import validate_addon_snapshot


def parse_solidworks(body: dict[str, Any]) -> dict[str, Any]:
    errors = validate_addon_snapshot("solidworks", body)
    if errors:
        return {
            "format": "solidworks",
            "valid": False,
            "errors": errors,
            "module_id": body.get("module_id"),
        }
    features = body.get("features") or []
    return {
        "format": "solidworks",
        "valid": True,
        "document_id": body.get("document_id"),
        "document_name": body.get("document_name", ""),
        "feature_count": len(features),
        "feature_types": list(dict.fromkeys(f.get("type", "unknown") for f in features))[:20],
        "module_id": body.get("module_id"),
    }

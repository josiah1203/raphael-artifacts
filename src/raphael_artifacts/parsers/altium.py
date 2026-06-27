"""Altium addon snapshot reader — schema validation and component summary."""

from __future__ import annotations

from typing import Any

from raphael_artifacts.calliope_schema.validator import validate_addon_snapshot


def parse_altium(body: dict[str, Any]) -> dict[str, Any]:
    errors = validate_addon_snapshot("altium", body)
    if errors:
        return {
            "format": "altium",
            "valid": False,
            "errors": errors,
            "module_id": body.get("module_id"),
        }
    components = body.get("components") or []
    changes = body.get("changes") or []
    return {
        "format": "altium",
        "valid": True,
        "document_id": body.get("document_id") or body.get("board_id"),
        "document_name": body.get("document_name", ""),
        "component_count": len(components),
        "change_count": len(changes),
        "designators": [c.get("designator") for c in components[:50] if c.get("designator")],
        "module_id": body.get("module_id"),
    }

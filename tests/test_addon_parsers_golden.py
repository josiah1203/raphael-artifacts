"""Golden tests for Altium and SolidWorks addon snapshot readers."""

from __future__ import annotations

from raphael_artifacts.parsers.altium import parse_altium
from raphael_artifacts.parsers.solidworks import parse_solidworks

ALTIUM_SNAPSHOT = {
    "module_id": "power-board-v2",
    "document_id": "brd-42",
    "document_name": "Main Board",
    "tool_identifier": "altium",
    "components": [
        {"designator": "U1", "footprint": "QFN-32"},
        {"designator": "C12", "footprint": "0402"},
    ],
    "changes": [{"type": "place", "component_id": "U1"}],
}

ALTIUM_EXPECTED = {
    "format": "altium",
    "valid": True,
    "document_id": "brd-42",
    "document_name": "Main Board",
    "component_count": 2,
    "change_count": 1,
    "designators": ["U1", "C12"],
    "module_id": "power-board-v2",
}

SOLIDWORKS_SNAPSHOT = {
    "module_id": "housing-v1",
    "document_id": "sw-100",
    "document_name": "Enclosure",
    "captured_at_utc": "2026-06-27T12:00:00Z",
    "tool_identifier": "solidworks",
    "features": [
        {"id": "f1", "name": "Boss-Extrude1", "type": "extrude"},
        {"id": "f2", "name": "Fillet1", "type": "fillet"},
        {"id": "f3", "name": "Boss-Extrude2", "type": "extrude"},
    ],
}

SOLIDWORKS_EXPECTED = {
    "format": "solidworks",
    "valid": True,
    "document_id": "sw-100",
    "document_name": "Enclosure",
    "feature_count": 3,
    "feature_types": ["extrude", "fillet"],
    "module_id": "housing-v1",
}


def test_parse_altium_golden() -> None:
    assert parse_altium(ALTIUM_SNAPSHOT) == ALTIUM_EXPECTED


def test_parse_altium_invalid_snapshot() -> None:
    out = parse_altium({"module_id": "missing-doc"})
    assert out["format"] == "altium"
    assert out["valid"] is False
    assert out["errors"]


def test_parse_solidworks_golden() -> None:
    assert parse_solidworks(SOLIDWORKS_SNAPSHOT) == SOLIDWORKS_EXPECTED


def test_parse_solidworks_invalid_snapshot() -> None:
    out = parse_solidworks({"module_id": "incomplete"})
    assert out["format"] == "solidworks"
    assert out["valid"] is False
    assert out["errors"]

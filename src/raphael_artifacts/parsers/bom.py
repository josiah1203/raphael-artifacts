"""BOM CSV metadata extraction."""

from __future__ import annotations

import csv
import io
from typing import Any


def parse_bom(body: dict[str, Any]) -> dict[str, Any]:
    content = body.get("content") or ""
    rows: list[dict[str, str]] = []
    if content.strip():
        reader = csv.DictReader(io.StringIO(content))
        rows = [dict(r) for r in reader]
    elif body.get("lines"):
        rows = [{"reference": str(line)} for line in body["lines"][:200]]
    refs = [r.get("Reference") or r.get("reference") or r.get("Designator", "") for r in rows]
    refs = [r for r in refs if r]
    return {
        "format": "bom",
        "line_count": len(rows),
        "unique_parts": len({r.get("Value") or r.get("value", "") for r in rows}),
        "references": refs[:100],
        "module_id": body.get("module_id"),
    }

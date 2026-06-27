"""KiCad schematic/board metadata extraction — no full parser, real refs/counts."""

from __future__ import annotations

import re
from typing import Any


def parse_kicad(body: dict[str, Any]) -> dict[str, Any]:
    content = body.get("content") or body.get("schematic") or ""
    if not content and body.get("file_path"):
        content = str(body["file_path"])
    refs = re.findall(r'\(property\s+"Reference"\s+"([^"]+)"', content)
    footprints = re.findall(r'\(footprint\s+"([^"]+)"', content)
    nets = re.findall(r'\(net\s+\d+\s+"([^"]+)"', content)
    return {
        "format": "kicad",
        "component_count": len(refs),
        "references": refs[:100],
        "footprint_count": len(footprints),
        "footprints": footprints[:50],
        "net_count": len(set(nets)),
        "nets": list(dict.fromkeys(nets))[:50],
        "module_id": body.get("module_id"),
    }

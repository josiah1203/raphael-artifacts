"""Load bundled JSON Schema documents."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

_SCHEMA_PKG = "raphael_artifacts.calliope_schema.schemas"


@lru_cache(maxsize=8)
def load_schema(name: str) -> dict[str, Any]:
    """Load a schema by filename (e.g. ``event_envelope.v0.json``)."""
    resource = resources.files(_SCHEMA_PKG).joinpath(name)
    with resources.as_file(resource) as path:
        return json.loads(path.read_text(encoding="utf-8"))

"""Schema Registry implementation (Confluent-compatible)."""

from __future__ import annotations

import enum
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class CompatibilityLevel(enum.Enum):
    NONE = "NONE"
    BACKWARD = "BACKWARD"
    FORWARD = "FORWARD"
    FULL = "FULL"


@dataclass
class Schema:
    subject: str
    version: int
    id: int
    schema: str  # JSON string
    schema_type: str = "JSON"


class SchemaRegistry:
    def __init__(self, persistence_path: Optional[Path] = None):
        self._schemas: Dict[int, Schema] = {}
        self._subjects: Dict[str, List[Schema]] = {}
        self._next_id = 1
        self._lock = threading.Lock()
        self._compatibility: Dict[str, CompatibilityLevel] = {}
        self._persistence_path = persistence_path
        if self._persistence_path:
            self._load()

    def _load(self):
        if self._persistence_path and self._persistence_path.exists():
            try:
                data = json.loads(self._persistence_path.read_text(encoding="utf-8"))
                self._next_id = data.get("next_id", 1)
                for s_data in data.get("schemas", []):
                    schema = Schema(**s_data)
                    self._schemas[schema.id] = schema
                    self._subjects.setdefault(schema.subject, []).append(schema)
            except Exception:
                pass

    def _save(self):
        if self._persistence_path:
            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "next_id": self._next_id,
                "schemas": [vars(s) for s in self._schemas.values()]
            }
            self._persistence_path.write_text(json.dumps(data), encoding="utf-8")

    def register(self, subject: str, schema_str: str, schema_type: str = "JSON") -> int:
        with self._lock:
            if subject not in self._subjects:
                self._subjects[subject] = []
            
            # Check if exactly same schema already exists for this subject
            for s in self._subjects[subject]:
                if s.schema == schema_str and s.schema_type == schema_type:
                    return s.id
            
            if not self.check_compatibility(subject, schema_str, schema_type):
                raise ValueError(f"Schema is incompatible with existing schemas for subject {subject}")
            
            version = len(self._subjects[subject]) + 1
            schema_id = self._next_id
            self._next_id += 1
            
            schema = Schema(
                subject=subject,
                version=version,
                id=schema_id,
                schema=schema_str,
                schema_type=schema_type
            )
            
            self._schemas[schema_id] = schema
            self._subjects[subject].append(schema)
            self._save()
            return schema_id

    def get_by_id(self, schema_id: int) -> Optional[Schema]:
        return self._schemas.get(schema_id)

    def get_latest(self, subject: str) -> Optional[Schema]:
        if subject not in self._subjects or not self._subjects[subject]:
            return None
        return self._subjects[subject][-1]

    def get_versions(self, subject: str) -> List[int]:
        if subject not in self._subjects:
            return []
        return [s.version for s in self._subjects[subject]]

    def get_by_version(self, subject: str, version: int) -> Optional[Schema]:
        if subject not in self._subjects:
            return None
        for s in self._subjects[subject]:
            if s.version == version:
                return s
        return None

    def check_compatibility(
        self, subject: str, new_schema_str: str, schema_type: str = "JSON"
    ) -> bool:
        """Check if new schema is compatible with existing schemas for subject."""
        level = self._compatibility.get(subject, CompatibilityLevel.BACKWARD)
        if level == CompatibilityLevel.NONE:
            return True

        latest = self.get_latest(subject)
        if not latest:
            return True

        if schema_type == "JSON":
            try:
                old_schema = json.loads(latest.schema)
                new_schema = json.loads(new_schema_str)

                # Protobuf-style rules: No field renames/removals from 'required', only deprecations (optional)
                # In JSON Schema terms, BACKWARD compatibility:
                # 1. New schema must be able to read old data.
                # 2. All required fields in old schema MUST be present in new schema.
                # 3. If new fields are added to 'required', they must have defaults (not easy in pure JSonschema validation)
                #    or we must ensure old data can still be validated.
                
                old_props = old_schema.get("properties", {})
                new_props = new_schema.get("properties", {})
                
                if level in (CompatibilityLevel.BACKWARD, CompatibilityLevel.FULL):
                    # Ensure no fields removed from old_schema properties if they were required
                    old_req = set(old_schema.get("required", []))
                    for req_field in old_req:
                        if req_field not in new_props:
                            return False # Field removed

                if level in (CompatibilityLevel.FORWARD, CompatibilityLevel.FULL):
                    # FORWARD: Old schema must be able to read new data
                    new_req = set(new_schema.get("required", []))
                    for req_field in new_req:
                        if req_field not in old_props:
                            return False # New required field added that old schema doesn't know

                return True
            except Exception:
                return False

        return True  # Default to true for other types for now

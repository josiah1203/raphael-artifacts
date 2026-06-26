"""Calliope JSON Schema definitions and validation helpers."""

from raphael_artifacts.calliope_schema.loader import load_schema
from raphael_artifacts.calliope_schema.validator import validate_design_snapshot, validate_event

__all__ = [
    "load_schema",
    "validate_event",
    "validate_design_snapshot",
    "GEOMETRY_EVENT_TYPES",
    "ELECTRICAL_EVENT_TYPES",
    "SOFTWARE_EVENT_TYPES",
    "PROJECT_EVENT_TYPES",
    "SIMULATION_EVENT_TYPES",
    "ALL_EVENT_TYPES",
    "TOOL_IDENTIFIERS",
]

GEOMETRY_EVENT_TYPES = (
    "geometry.feature_created",
    "geometry.feature_modified",
    "geometry.feature_deleted",
    "geometry.material_assigned",
    "geometry.configuration_created",
    "geometry.assembly_mate_added",
)

ELECTRICAL_EVENT_TYPES = (
    "electrical.footprint_added",
    "electrical.footprint_modified",
    "electrical.net_changed",
)

SOFTWARE_EVENT_TYPES = (
    "software.commit_pushed",
    "software.pull_request_opened",
    "software.pull_request_merged",
    "software.pull_request_closed",
)

PROJECT_EVENT_TYPES = (
    "project.issue_created",
    "project.issue_updated",
    "project.issue_transitioned",
)

SIMULATION_EVENT_TYPES = (
    "simulation.setup_captured",
    "simulation.result_captured",
)

ALL_EVENT_TYPES = (
    GEOMETRY_EVENT_TYPES
    + ELECTRICAL_EVENT_TYPES
    + SOFTWARE_EVENT_TYPES
    + PROJECT_EVENT_TYPES
    + SIMULATION_EVENT_TYPES
)

TOOL_IDENTIFIERS = (
    "fusion360",
    "onshape",
    "kicad",
    "github",
    "gitlab",
    "solidworks",
    "altium",
    "jira",
    "ansys",
    "comsol",
    "migration",
    "cadence",
    "inventor",
    "rhino",
    "freecad",
)

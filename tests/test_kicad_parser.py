"""KiCad parser tests."""

from raphael_artifacts.parsers.kicad import parse_kicad


def test_parse_kicad_references() -> None:
    content = '(symbol (property "Reference" "U1") (property "Reference" "R2"))'
    out = parse_kicad({"content": content, "module_id": "m1"})
    assert out["component_count"] == 2
    assert "U1" in out["references"]

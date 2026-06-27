"""Artifacts API tests."""

from fastapi.testclient import TestClient

from raphael_artifacts.app import app

client = TestClient(app)


def test_list_and_create_artifact() -> None:
    created = client.post(
        "/v1/artifacts",
        json={"module_id": "test-module-artifacts", "kind": "snapshot", "metadata": {"note": "test"}},
    )
    assert created.status_code == 200
    listed = client.get("/v1/artifacts?module_id=test-module-artifacts").json()["artifacts"]
    assert any(a["module_id"] == "test-module-artifacts" for a in listed)


def test_ingest_kicad_stores_blob() -> None:
    res = client.post(
        "/v1/artifacts/ingest/kicad",
        json={
            "module_id": "test-kicad-module",
            "content": '(property "Reference" "U1") (footprint "QFN-32")',
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["parsed"]["component_count"] >= 1
    art_id = body["artifact"]["id"]
    obj = client.get(f"/v1/artifacts/objects/{art_id}")
    assert obj.status_code == 200
    assert obj.json().get("blob_key")
    content = client.get(f"/v1/artifacts/objects/{art_id}/content")
    assert content.status_code == 200


def test_ingest_altium_validates_schema() -> None:
    res = client.post(
        "/v1/artifacts/ingest/altium",
        json={
            "module_id": "board-1",
            "document_id": "brd-1",
            "components": [{"designator": "U1", "footprint": "QFN-32"}],
        },
    )
    assert res.status_code == 200
    parsed = res.json()["parsed"]
    assert parsed["format"] == "altium"
    assert parsed.get("valid") is True

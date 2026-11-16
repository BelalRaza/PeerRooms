import pytest
from fastapi.testclient import TestClient

from peerrooms.api.main import create_app


def test_static_app_and_openapi(client: TestClient) -> None:
    assert "PeerRooms" in client.get("/").text
    assert client.get("/styles.css").status_code == 200
    assert client.get("/app.js").status_code == 200
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "_swagger/swagger-ui-bundle.js" in docs.text and "_swagger/swagger-ui.css" in docs.text
    assert "https://" not in docs.text
    assert client.get("/_swagger/swagger-ui-bundle.js").status_code == 200
    spec = client.get("/openapi.json").json()
    assert spec["components"]["securitySchemes"]["Student identity"]["name"] == "X-Student-Id"
    assert len(spec["paths"]) == 21


def test_seeded_and_empty_lifespans_are_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PEERROOMS_SEED", "1")
    with TestClient(create_app()) as client:
        signed_in = client.post("/api/sessions", json={"email": "aman@college.edu"})
        assert signed_in.status_code == 200
        headers = {"X-Student-Id": signed_in.json()["id"]}
        assert client.get("/api/rooms", headers=headers).json() == []
        assert len(client.get("/api/rooms?status=CLOSED", headers=headers).json()) == 2
    monkeypatch.delenv("PEERROOMS_SEED")
    with TestClient(create_app()) as client:
        assert client.post("/api/sessions", json={"email": "aman@college.edu"}).status_code == 404

from fastapi.testclient import TestClient

from peerrooms.app.facade import PeerRoomsApp


def test_discovery_requests_network_and_notifications(client: TestClient, application: PeerRoomsApp) -> None:
    maya, leo = (
        application.register(name, f"{name.lower()}@college.edu", "CS", 2, ["AI", "design"])
        for name in ("Maya", "Leo")
    )
    a, b = ({"X-Student-Id": student.id} for student in (maya, leo))
    for key, score in (("jaccard", 1.0), ("weighted", 0.7), ("jaccard", 1.0)):
        result = client.get("/api/discover/peers", headers=a, params={"strategy": key, "limit": 1})
        assert result.status_code == 200
        peer, = result.json()
        assert peer["student"]["id"] == leo.id and peer["score"] == score
        assert peer["common_interests"] == ["ai", "design"]
    assert client.get("/api/discover/peers?strategy=bad", headers=a).status_code == 400
    sent = client.post("/api/connections/requests", headers=a, json={"receiver_id": leo.id})
    assert sent.status_code == 201
    req = sent.json()
    assert client.get("/api/connections/requests", headers=a).json() == {"incoming": [], "outgoing": [req]}
    assert client.get("/api/connections/requests", headers=b).json() == {"incoming": [req], "outgoing": []}
    assert client.get("/api/discover/peers", headers=a).json() == []
    duplicate = client.post("/api/connections/requests", headers=b, json={"receiver_id": maya.id})
    assert duplicate.status_code == 409 and "They already sent you" in duplicate.json()["message"]

    incoming = client.get("/api/notifications", headers=b)
    assert incoming.status_code == 200
    item, = incoming.json()
    assert item["type"] == "CONNECTION_REQUESTED" and not item["is_read"]
    mark_read = "/api/notifications/" + item["id"] + "/read"
    assert client.post(mark_read, headers=a).status_code == 403
    assert client.post(mark_read, headers=b).status_code == 204
    assert client.get("/api/notifications", headers=b).json()[0]["is_read"]

    accept = "/api/connections/requests/" + req["id"] + "/accept"
    assert client.post(accept, headers=a).status_code == 403
    accepted = client.post(accept, headers=b)
    assert accepted.status_code == 200 and accepted.json()["student"]["id"] == maya.id
    assert client.post(accept, headers=b).status_code == 409
    network = client.get("/api/connections", headers=a)
    assert network.status_code == 200 and network.json()[0]["id"] == leo.id
    assert client.get("/api/connections", headers=b).json()[0]["id"] == maya.id
    assert client.get("/api/notifications", headers=a).json()[0]["type"] == "CONNECTION_ACCEPTED"


def test_reject_cancel_and_block(client: TestClient, application: PeerRoomsApp) -> None:
    maya, leo = (
        application.register(name, f"{name.lower()}@college.edu", "CS", 2, ["ai"])
        for name in ("Maya", "Leo")
    )
    a, b = ({"X-Student-Id": student.id} for student in (maya, leo))
    req_path = "/api/connections/requests"
    body = {"receiver_id": leo.id}
    for action, headers in [("reject", b), ("cancel", a)]:
        pending = client.post(req_path, headers=a, json=body).json()
        response = client.post(f"{req_path}/{pending['id']}/{action}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == {"reject": "REJECTED", "cancel": "CANCELLED"}[action]
    assert client.post("/api/students/me/blocks/" + maya.id, headers=b).status_code == 204
    assert client.get("/api/discover/peers", headers=a).json() == []
    blocked = client.post(req_path, headers=a, json=body)
    assert blocked.status_code == 403 and blocked.json()["error"] == "BlockedError"

from fastapi.testclient import TestClient

from peerrooms.app.facade import PeerRoomsApp

NEW_ROOM = {
    "topic": "Systems", "prompt": "How should we study?",
    "tags": [" AI ", "study"], "room_type": "QUICK_CHAT", "capacity": 2,
}


def test_create_browse_filter_and_recommend(client: TestClient, application: PeerRoomsApp) -> None:
    host = application.register("Host", "host@college.edu", "CS", 2, ["ai"])
    guest = application.register("Guest", "guest@college.edu", "CS", 2, ["ai"])
    headers = {"X-Student-Id": host.id}
    guest_headers = {"X-Student-Id": guest.id}
    invalid = client.post("/api/rooms", headers=headers, json={**NEW_ROOM, "capacity": 1})
    assert invalid.status_code == 400 and invalid.json()["error"] == "InvalidCapacityError"
    response = client.post("/api/rooms", headers=headers, json=NEW_ROOM)
    assert response.status_code == 201
    card = response.json()
    assert card["tags"] == ["ai", "study"]
    assert card["seated_count"] == 1 and card["viewer_role"] == "HOST"
    listing = client.get("/api/rooms", headers=headers, params={"tag": " AI ", "status": "OPEN"})
    assert listing.status_code == 200 and listing.json() == [card]
    assert not client.get("/api/rooms?tag=math", headers=guest_headers).json()
    candidates = client.get("/api/rooms/recommended", headers=guest_headers)
    assert candidates.status_code == 200 and candidates.json()[0]["id"] == card["id"]
    assert client.get("/api/rooms/recommended", headers=headers).json() == []
    detail = client.get(f"/api/rooms/{card['id']}", headers=guest_headers)
    assert detail.status_code == 200 and detail.json()["prompt"] == NEW_ROOM["prompt"]
    assert detail.json()["members"][0]["name"] == "Host"
    assert client.get("/api/rooms/missing", headers=headers).status_code == 404


def test_join_waitlist_chat_leave_remove_and_close(client: TestClient, application: PeerRoomsApp) -> None:
    host, first, second, third = (
        application.register(name, f"{name.lower()}@college.edu", "CS", 2, ["ai"])
        for name in ("Host", "First", "Second", "Third")
    )
    a, b, c, d = ({"X-Student-Id": student.id} for student in (host, first, second, third))
    room = client.post("/api/rooms", headers=a, json=NEW_ROOM).json()
    path = f"/api/rooms/{room['id']}"
    joined = client.post(path + "/join", headers=b)
    assert joined.status_code == 200 and joined.json() == {"result": "JOINED", "position": None}
    queued = client.post(path + "/join", headers=c)
    assert queued.status_code == 200 and queued.json() == {"result": "WAITLISTED", "position": 1}
    assert client.post(path + "/join", headers=d).json()["position"] == 2
    duplicate = client.post(path + "/join", headers=c)
    assert duplicate.status_code == 409 and duplicate.json()["error"] == "AlreadyInRoomError"
    assert client.get(path, headers=d).json()["waitlist"] == [
        {"position": 1, "is_you": False}, {"position": 2, "is_you": True},
    ]
    msg = {"content": "Hello, classmates"}
    assert client.post(path + "/messages", headers=c, json=msg).status_code == 409
    sent = client.post(path + "/messages", headers=b, json=msg)
    assert sent.status_code == 201 and sent.json()["sender_name"] == "First"
    assert client.get(path, headers=c).json()["messages"] == [sent.json()]
    forbidden = client.post(path + "/close", headers=b)
    assert forbidden.status_code == 403 and forbidden.json()["error"] == "PermissionDeniedError"
    assert client.delete(path + "/members/" + host.id, headers=b).status_code == 403
    departure = client.post(path + "/leave", headers=a)
    assert departure.status_code == 200
    assert departure.json() == {"promoted_id": second.id, "new_host_id": first.id, "closed": False}
    removed = client.delete(path + "/members/" + second.id, headers=b)
    assert removed.status_code == 204 and removed.content == b""
    assert client.get(path, headers=d).json()["viewer_role"] == "MEMBER"
    closed = client.post(path + "/close", headers=b)
    assert closed.status_code == 204 and closed.content == b""
    assert client.get(path, headers=a).json()["members"] == []
    assert client.get("/api/rooms", headers=a).json() == []
    assert client.get("/api/rooms?status=CLOSED", headers=a).json()[0]["id"] == room["id"]
    assert client.post(path + "/join", headers=d).json()["error"] == "RoomClosedError"


def test_room_detail_returns_only_last_fifty_messages(client: TestClient, application: PeerRoomsApp) -> None:
    from peerrooms.domain.enums import RoomType

    host = application.register("Host", "host@college.edu", "CS", 2, ["ai"])
    room = application.create_room(host.id, RoomType.QUICK_CHAT, "Chat", "Prompt", ["ai"])
    for number in range(52):
        application.post_message(host.id, room.id, f"Message {number}")
    result = client.get(f"/api/rooms/{room.id}", headers={"X-Student-Id": host.id})
    assert [msg["content"] for msg in result.json()["messages"]] == [
        f"Message {number}" for number in range(2, 52)
    ]

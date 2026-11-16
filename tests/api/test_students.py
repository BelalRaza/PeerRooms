from fastapi.testclient import TestClient

STUDENT = {
    "name": "Anita", "email": "anita@college.edu", "department": "CS",
    "year": 2, "interests": [" ai ", "AI", "Python"],
}


def test_register_sign_in_edit_and_profile(client: TestClient) -> None:
    created = client.post("/api/students", json=STUDENT)
    assert created.status_code == 201
    student = created.json()
    assert student["interests"] == ["ai", "python"]
    signed_in = client.post("/api/sessions", json={"email": " ANITA@COLLEGE.EDU "})
    assert signed_in.status_code == 200 and signed_in.json() == student
    headers = {"X-Student-Id": student["id"]}
    assert client.get("/api/students/me", headers=headers).json() == student
    edited = client.put("/api/students/me/interests", headers=headers, json={"interests": ["Design"]})
    assert edited.status_code == 200 and edited.json()["interests"] == ["design"]
    assert client.get("/api/students/me", headers=headers).json()["interests"] == ["design"]


def test_schema_and_domain_errors_remain_distinct(client: TestClient) -> None:
    assert client.get("/api/students/me").status_code == 401
    assert client.get("/api/rooms", headers={"X-Student-Id": "unknown"}).status_code == 404
    assert client.post("/api/sessions", json={"email": "unknown@college.edu"}).status_code == 404
    assert client.post("/api/students", json={**STUDENT, "year": "2"}).status_code == 422
    assert client.post("/api/students", json={**STUDENT, "interests": []}).status_code == 400
    assert client.post("/api/students", json=STUDENT).status_code == 201
    duplicate = client.post("/api/students", json={**STUDENT, "email": " ANITA@COLLEGE.EDU "})
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "error": "DuplicateEmailError", "message": "anita@college.edu is already registered.",
    }

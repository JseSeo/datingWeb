from fastapi.testclient import TestClient


def _register_and_get_headers(client: TestClient, email: str = "reporter@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "신고자",
        "university": "서울대학교",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _register_target(client: TestClient, email: str = "target@test.com") -> int:
    res = client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "대상자",
        "university": "서울대학교",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    return res.json()["id"]


def test_create_report(client: TestClient):
    headers = _register_and_get_headers(client)
    target_id = _register_target(client)
    response = client.post("/reports", json={
        "target_id": target_id,
        "reason": "부적절한 프로필 사진",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["target_id"] == target_id
    assert data["reason"] == "부적절한 프로필 사진"
    assert "id" in data
    assert "created_at" in data


def test_report_nonexistent_target(client: TestClient):
    headers = _register_and_get_headers(client, "r2@test.com")
    response = client.post("/reports", json={
        "target_id": 99999,
        "reason": "없는 유저",
    }, headers=headers)
    assert response.status_code == 404


def test_report_self_forbidden(client: TestClient):
    client.post("/auth/register", json={
        "email": "self@test.com",
        "password": "password123",
        "name": "자기자신",
        "university": "서울대학교",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    res = client.post("/auth/login", json={"email": "self@test.com", "password": "password123"})
    me = client.get("/me", headers={"Authorization": f"Bearer {res.json()['access_token']}"})
    my_id = me.json()["id"]
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    response = client.post("/reports", json={
        "target_id": my_id,
        "reason": "자기신고",
    }, headers=headers)
    assert response.status_code == 400


def test_report_empty_reason(client: TestClient):
    headers = _register_and_get_headers(client, "r3@test.com")
    target_id = _register_target(client, "t3@test.com")
    response = client.post("/reports", json={
        "target_id": target_id,
        "reason": "",
    }, headers=headers)
    assert response.status_code == 422


def test_report_unauthorized(client: TestClient):
    response = client.post("/reports", json={"target_id": 1, "reason": "x"})
    assert response.status_code == 401

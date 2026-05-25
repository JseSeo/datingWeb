from fastapi.testclient import TestClient


def _register_and_get_headers(client: TestClient, email: str = "me@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "김미",
        "university": "서울대학교",
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_get_me(client: TestClient):
    headers = _register_and_get_headers(client)
    response = client.get("/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["status"] == "pending"


def test_get_me_unauthorized(client: TestClient):
    response = client.get("/me")
    assert response.status_code == 401


def test_update_profile(client: TestClient):
    headers = _register_and_get_headers(client, "profile@test.com")
    response = client.put("/me/profile", json={
        "bio": "안녕하세요!",
        "instagram": "myinsta",
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "안녕하세요!"
    assert data["instagram"] == "myinsta"
    assert data["kakao_id"] is None


def test_update_profile_clears_field_with_empty_string(client: TestClient):
    headers = _register_and_get_headers(client, "clear@test.com")
    client.put("/me/profile", json={"instagram": "myinsta"}, headers=headers)
    response = client.put("/me/profile", json={"instagram": ""}, headers=headers)
    assert response.status_code == 200
    assert response.json()["instagram"] is None


def test_toggle_matching_pause(client: TestClient):
    headers = _register_and_get_headers(client, "pause@test.com")
    res = client.put("/me/matching-pause", json={"matching_paused": True}, headers=headers)
    assert res.status_code == 200
    assert res.json()["matching_paused"] is True

    res = client.put("/me/matching-pause", json={"matching_paused": False}, headers=headers)
    assert res.status_code == 200
    assert res.json()["matching_paused"] is False

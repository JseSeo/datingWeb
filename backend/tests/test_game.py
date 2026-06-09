from fastapi.testclient import TestClient


def _auth(client: TestClient, email="user@test.com", name="홍길동", university="서울대학교") -> dict:
    client.post("/auth/register", json={
        "email": email, "password": "password123",
        "name": name, "university": university,
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_ojakgyo_create(client: TestClient):
    headers = _auth(client)
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "김철수", "person_a_university": "연세대학교",
        "person_b_name": "이영희", "person_b_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert "created_at" in data
    assert {data["person_a_name"], data["person_b_name"]} == {"김철수", "이영희"}


def test_ojakgyo_empty_field(client: TestClient):
    headers = _auth(client, "empty@test.com")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }, headers=headers)
    assert res.status_code == 422


def test_ojakgyo_unauthorized(client: TestClient):
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "가", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    })
    assert res.status_code == 401

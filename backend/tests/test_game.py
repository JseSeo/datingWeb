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


def test_ojakgyo_self_forbidden(client: TestClient):
    headers = _auth(client, "self@test.com", "나본인", "서울대학교")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "나본인", "person_a_university": "서울대학교",
        "person_b_name": "남", "person_b_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_same_pair_forbidden(client: TestClient):
    headers = _auth(client, "same@test.com")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "동일", "person_a_university": "연세대학교",
        "person_b_name": "동일", "person_b_university": "연세대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_duplicate_pair_conflict(client: TestClient):
    headers = _auth(client, "dup@test.com")
    body1 = {
        "person_a_name": "가", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }
    assert client.post("/game/ojakgyo", json=body1, headers=headers).status_code == 201
    body2 = {
        "person_a_name": "나", "person_a_university": "B대",
        "person_b_name": "가", "person_b_university": "A대",
    }
    assert client.post("/game/ojakgyo", json=body2, headers=headers).status_code == 409


def test_ojakgyo_different_recommender_same_pair_ok(client: TestClient):
    h1 = _auth(client, "rec1@test.com")
    h2 = _auth(client, "rec2@test.com")
    body = {
        "person_a_name": "가", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }
    assert client.post("/game/ojakgyo", json=body, headers=h1).status_code == 201
    assert client.post("/game/ojakgyo", json=body, headers=h2).status_code == 201

from fastapi.testclient import TestClient

BASE = {
    "password": "password123", "name": "연락처", "university": "서울대학교",
    "gender": "male", "agreed_terms": True, "agreed_privacy": True,
    "agreed_age_14": True,
}


def _register(client: TestClient, email: str, **contacts):
    return client.post("/auth/register", json={**BASE, "email": email, **contacts})


def test_register_without_contact_is_rejected(client: TestClient):
    assert _register(client, "none@test.com").status_code == 422


def test_register_with_empty_strings_is_rejected(client: TestClient):
    """빈 문자열은 None으로 정규화되므로 연락처가 없는 것과 같다 (설계 §7.1)."""
    res = _register(client, "empty@test.com", instagram="", kakao_id="", phone="")
    assert res.status_code == 422


def test_register_with_one_contact_succeeds(client: TestClient):
    assert _register(client, "one@test.com", kakao_id="drop_kakao").status_code == 201


def test_register_stores_contact(client: TestClient):
    _register(client, "store@test.com", instagram="drop_insta")
    token = client.post("/auth/login", json={
        "email": "store@test.com", "password": "password123",
    }).json()["access_token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["instagram"] == "drop_insta"

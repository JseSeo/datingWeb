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


def test_register_with_whitespace_only_contact_is_rejected(client: TestClient):
    """공백만 있는 연락처는 닿을 방법이 없다 — 정규화 후 빈 값과 같아야 한다."""
    res = _register(client, "whitespace@test.com", kakao_id=" ")
    assert res.status_code == 422


def test_register_strips_contact_before_storing(client: TestClient):
    _register(client, "strip@test.com", kakao_id="  drop_kakao  ")
    token = client.post("/auth/login", json={
        "email": "strip@test.com", "password": "password123",
    }).json()["access_token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["kakao_id"] == "drop_kakao"


def _login(client: TestClient, email: str) -> dict:
    token = client.post("/auth/login", json={
        "email": email, "password": "password123",
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_cannot_clear_last_contact(client: TestClient):
    _register(client, "last@test.com", kakao_id="only_one")
    headers = _login(client, "last@test.com")
    res = client.put("/me/profile", json={"kakao_id": ""}, headers=headers)
    assert res.status_code == 422


def test_can_clear_one_of_two_contacts(client: TestClient):
    _register(client, "two@test.com", kakao_id="a", instagram="b")
    headers = _login(client, "two@test.com")
    res = client.put("/me/profile", json={"kakao_id": ""}, headers=headers)
    assert res.status_code == 200
    assert res.json()["kakao_id"] is None
    assert res.json()["instagram"] == "b"


def test_rejected_clear_does_not_touch_db(client: TestClient):
    """422를 받은 뒤에도 기존 연락처가 살아 있어야 한다 (설계 §7.1)."""
    _register(client, "intact@test.com", kakao_id="keep_me")
    headers = _login(client, "intact@test.com")
    client.put("/me/profile", json={"kakao_id": ""}, headers=headers)
    assert client.get("/me", headers=headers).json()["kakao_id"] == "keep_me"


def test_bio_only_update_still_works(client: TestClient):
    """연락처를 건드리지 않는 수정은 영향받지 않는다."""
    _register(client, "bio@test.com", kakao_id="x")
    headers = _login(client, "bio@test.com")
    res = client.put("/me/profile", json={"bio": "안녕하세요"}, headers=headers)
    assert res.status_code == 200


def test_cannot_clear_last_contact_with_whitespace(client: TestClient):
    """공백만 있는 값도 빈 값과 같아야 한다 — 마지막 연락처를 우회로 지울 수 없다."""
    _register(client, "wslast@test.com", kakao_id="keep_me")
    headers = _login(client, "wslast@test.com")
    res = client.put("/me/profile", json={"kakao_id": "   "}, headers=headers)
    assert res.status_code == 422
    assert client.get("/me", headers=headers).json()["kakao_id"] == "keep_me"

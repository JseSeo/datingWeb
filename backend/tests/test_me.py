from fastapi.testclient import TestClient

from app.models.user import User
from tests.conftest import TestingSessionLocal


def _register_and_get_headers(client: TestClient, email: str = "me@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "김미",
        "university": "서울대학교",
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
        "phone": "01000000000",
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


def test_cannot_clear_last_real_contact_when_other_is_whitespace_only(client: TestClient):
    """DB에 공백만 있는 연락처가 남아있어도(과거 데이터·직접수정) 실제 연락처를
    지울 수 없다 — merged 판정도 트림해야 한다."""
    headers = _register_and_get_headers(client, "whitespace@test.com")
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "whitespace@test.com").first()
    user.kakao_id = "   "
    db.commit()
    db.close()

    # 등록 시 넣은 phone(실제 연락처)을 지우려 함 — kakao_id는 공백뿐이라 없는 것과 같다
    response = client.put("/me/profile", json={"phone": ""}, headers=headers)
    assert response.status_code == 422


def test_toggle_matching_pause(client: TestClient):
    headers = _register_and_get_headers(client, "pause@test.com")
    res = client.put("/me/matching-pause", json={"matching_paused": True}, headers=headers)
    assert res.status_code == 200
    assert res.json()["matching_paused"] is True

    res = client.put("/me/matching-pause", json={"matching_paused": False}, headers=headers)
    assert res.status_code == 200
    assert res.json()["matching_paused"] is False

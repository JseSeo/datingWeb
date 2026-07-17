import io
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from app.models.user import User, UserStatus
from app.models.verification import StudentVerification
from app.models.survey import Survey


def _register_and_get_headers(client: TestClient, email: str) -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "테스터",
        "university": "서울대학교",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_withdraw_anonymizes_and_deletes(client: TestClient):
    headers = _register_and_get_headers(client, "bye@test.com")
    # 프로필·학생증·설문 채우기
    client.put("/me/profile", json={
        "bio": "안녕", "instagram": "ig", "kakao_id": "kk", "phone": "010",
    }, headers=headers)
    client.post(
        "/me/profile-photo",
        files={"file": ("me.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers=headers,
    )
    client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers=headers,
    )
    client.put("/me/survey", json={"answers": {"q1": "a"}}, headers=headers)

    response = client.delete("/me", headers=headers)
    assert response.status_code == 204

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.name == "탈퇴회원").first()
        assert user is not None
        assert user.status == UserStatus.withdrawn
        assert user.email == f"withdrawn_{user.id}@deleted.local"
        assert user.instagram is None
        assert user.kakao_id is None
        assert user.phone is None
        assert user.bio is None
        assert user.profile_photo is None
        assert db.query(StudentVerification).filter(
            StudentVerification.user_id == user.id
        ).first() is None
        assert db.query(Survey).filter(Survey.user_id == user.id).first() is None
    finally:
        db.close()


def test_withdraw_blocks_relogin(client: TestClient):
    headers = _register_and_get_headers(client, "byerelogin@test.com")
    client.delete("/me", headers=headers)
    res = client.post("/auth/login", json={
        "email": "byerelogin@test.com", "password": "password123",
    })
    assert res.status_code == 401


def test_withdraw_unauthenticated(client: TestClient):
    response = client.delete("/me")
    assert response.status_code == 401


def test_withdrawn_token_cannot_rewrite_profile(client: TestClient):
    # 탈퇴 후에도 살아있는 토큰으로 익명화된 필드를 되살릴 수 없어야 함
    headers = _register_and_get_headers(client, "ghost@test.com")
    client.delete("/me", headers=headers)

    res = client.put("/me/profile", json={"instagram": "back"}, headers=headers)
    assert res.status_code == 401

    res = client.post(
        "/me/profile-photo",
        files={"file": ("me.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers=headers,
    )
    assert res.status_code == 401

    res = client.get("/me", headers=headers)
    assert res.status_code == 401

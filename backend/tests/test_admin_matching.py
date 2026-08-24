from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.models.match import MatchRound, RoundStatus
from app.models.survey import Survey
from app.models.user import Gender, User, UserStatus
from tests.conftest import TestingSessionLocal

NIGHT = {"sleep_self": "night", "sleep_pref": "night"}


def _seed_pool_and_round() -> int:
    db = TestingSessionLocal()
    for email, gender in (("m@test.com", Gender.male), ("w@test.com", Gender.female)):
        user = User(
            email=email, password_hash="x", name="테스트", university="서울대학교",
            gender=gender, status=UserStatus.active,
        )
        db.add(user)
        db.commit()
        db.add(Survey(user_id=user.id, answers={"responses": NIGHT, "absolute": []}))
        db.commit()
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()
    round_id = round_.id
    db.close()
    return round_id


def test_admin_runs_matching(admin_client: TestClient):
    round_id = _seed_pool_and_round()

    res = admin_client.post(f"/admin/match-rounds/{round_id}/run")

    assert res.status_code == 200
    assert res.json() == {"matched": 1, "unmatched": 0, "guaranteed": 0}


def test_round_becomes_done(admin_client: TestClient):
    round_id = _seed_pool_and_round()
    admin_client.post(f"/admin/match-rounds/{round_id}/run")

    listed = admin_client.get("/admin/match-rounds").json()
    assert listed[0]["status"] == RoundStatus.done.value


def test_second_run_is_conflict(admin_client: TestClient):
    round_id = _seed_pool_and_round()
    admin_client.post(f"/admin/match-rounds/{round_id}/run")

    res = admin_client.post(f"/admin/match-rounds/{round_id}/run")
    assert res.status_code == 409


def test_missing_round_is_404(admin_client: TestClient):
    res = admin_client.post("/admin/match-rounds/9999/run")
    assert res.status_code == 404


def test_normal_user_is_forbidden(client: TestClient):
    round_id = _seed_pool_and_round()
    client.post("/auth/register", json={
        "email": "normal@test.com", "password": "password123", "name": "김일반",
        "university": "서울대학교", "gender": "male",
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
    })
    token = client.post("/auth/login", json={
        "email": "normal@test.com", "password": "password123",
    }).json()["access_token"]

    res = client.post(
        f"/admin/match-rounds/{round_id}/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_requires_auth(client: TestClient):
    assert client.post("/admin/match-rounds/9999/run").status_code == 401

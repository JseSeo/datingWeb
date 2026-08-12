from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.models.match import MatchRound, RoundStatus
from tests.conftest import TestingSessionLocal


def _add_rounds(*rounds: MatchRound) -> list[int]:
    db = TestingSessionLocal()
    db.add_all(rounds)
    db.commit()
    ids = [r.id for r in rounds]
    db.close()
    return ids


def _hours(n: int) -> datetime:
    return datetime.utcnow() + timedelta(hours=n)


def _iso(n: int) -> str:
    """n시간 뒤를 타임존 없는 ISO 문자열로. 마이크로초는 버린다."""
    return _hours(n).replace(microsecond=0).isoformat()


def _register_normal_user(client: TestClient) -> dict:
    client.post("/auth/register", json={
        "email": "normal@test.com",
        "password": "password123",
        "name": "김일반",
        "university": "서울대학교",
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    res = client.post("/auth/login", json={
        "email": "normal@test.com",
        "password": "password123",
    })
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_list_returns_all_rounds_newest_first(admin_client: TestClient):
    _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending),
        MatchRound(scheduled_at=_hours(72), status=RoundStatus.pending),
        MatchRound(scheduled_at=_hours(-48), status=RoundStatus.done),
    )
    res = admin_client.get("/admin/match-rounds")
    assert res.status_code == 200
    data = res.json()
    # 과거·done 포함 전부, scheduled_at 내림차순
    assert len(data) == 3
    assert [r["scheduled_at"] for r in data] == sorted(
        [r["scheduled_at"] for r in data], reverse=True
    )
    assert set(data[0].keys()) == {"id", "scheduled_at", "status"}


def test_create_returns_201_with_pending_status(admin_client: TestClient):
    res = admin_client.post("/admin/match-rounds", json={"scheduled_at": _iso(24)})
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "pending"
    assert body["id"] > 0


def test_create_ignores_client_supplied_status(admin_client: TestClient):
    res = admin_client.post(
        "/admin/match-rounds",
        json={"scheduled_at": _iso(24), "status": "done"},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "pending"


def test_create_stores_aware_input_as_naive_utc(admin_client: TestClient):
    # 프론트가 toISOString()으로 보내는 형태
    res = admin_client.post(
        "/admin/match-rounds",
        json={"scheduled_at": "2030-01-01T12:00:00.000Z"},
    )
    assert res.status_code == 201
    db = TestingSessionLocal()
    row = db.query(MatchRound).first()
    stored = row.scheduled_at
    db.close()
    assert stored.tzinfo is None
    assert stored == datetime(2030, 1, 1, 12, 0)


def test_create_converts_offset_input_to_utc(admin_client: TestClient):
    # KST 21:00 = UTC 12:00
    res = admin_client.post(
        "/admin/match-rounds",
        json={"scheduled_at": "2030-01-01T21:00:00+09:00"},
    )
    assert res.status_code == 201
    db = TestingSessionLocal()
    stored = db.query(MatchRound).first().scheduled_at
    db.close()
    assert stored == datetime(2030, 1, 1, 12, 0)


def test_create_rejects_past(admin_client: TestClient):
    res = admin_client.post("/admin/match-rounds", json={"scheduled_at": _iso(-1)})
    assert res.status_code == 400
    assert res.json()["detail"] == "예정 시각은 현재보다 미래여야 합니다"


def test_create_rejects_duplicate(admin_client: TestClient):
    when = _iso(24)
    assert admin_client.post(
        "/admin/match-rounds", json={"scheduled_at": when}
    ).status_code == 201
    res = admin_client.post("/admin/match-rounds", json={"scheduled_at": when})
    assert res.status_code == 409
    assert res.json()["detail"] == "같은 시각의 라운드가 이미 있습니다"


def test_list_rejects_non_admin(client: TestClient):
    headers = _register_normal_user(client)
    res = client.get("/admin/match-rounds", headers=headers)
    assert res.status_code == 403


def test_create_rejects_non_admin(client: TestClient):
    headers = _register_normal_user(client)
    res = client.post(
        "/admin/match-rounds",
        json={"scheduled_at": _iso(24)},
        headers=headers,
    )
    assert res.status_code == 403


def test_requires_auth(client: TestClient):
    assert client.get("/admin/match-rounds").status_code == 401

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.models.match import MatchRound, RoundStatus
from tests.conftest import TestingSessionLocal


def _register_and_get_headers(client: TestClient, email: str = "round@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "김라운드",
        "university": "서울대학교",
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
        "kakao_id": "register_kakao",
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _add_rounds(*rounds: MatchRound) -> None:
    db = TestingSessionLocal()
    db.add_all(rounds)
    db.commit()
    for r in rounds:
        db.refresh(r)  # id 등 속성을 로드해둬야 커밋 후 세션 종료돼도 접근 가능
    db.close()


def _hours(n: int) -> datetime:
    return datetime.utcnow() + timedelta(hours=n)


def test_returns_nearest_future_pending_round(client: TestClient):
    headers = _register_and_get_headers(client)
    nearest = MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    _add_rounds(
        MatchRound(scheduled_at=_hours(72), status=RoundStatus.pending),
        nearest,
        MatchRound(scheduled_at=_hours(48), status=RoundStatus.pending),
    )
    response = client.get("/match-rounds/next", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    # 가장 이른 것 = 24시간 뒤
    assert data["id"] == nearest.id
    # 절단선: 결과 영역 필드는 내려가지 않는다
    assert set(data.keys()) == {"id", "scheduled_at"}


def test_returns_null_when_no_rounds(client: TestClient):
    headers = _register_and_get_headers(client, "none@test.com")
    response = client.get("/match-rounds/next", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_ignores_past_pending_round(client: TestClient):
    headers = _register_and_get_headers(client, "past@test.com")
    _add_rounds(MatchRound(scheduled_at=_hours(-1), status=RoundStatus.pending))
    response = client.get("/match-rounds/next", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_ignores_done_round(client: TestClient):
    headers = _register_and_get_headers(client, "done@test.com")
    _add_rounds(MatchRound(
        scheduled_at=_hours(24),
        executed_at=datetime.utcnow(),
        status=RoundStatus.done,
    ))
    response = client.get("/match-rounds/next", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_requires_auth(client: TestClient):
    response = client.get("/match-rounds/next")
    assert response.status_code == 401

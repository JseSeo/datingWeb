from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.models.match import Match, MatchRound, RoundStatus
from app.models.user import Gender, User, UserStatus
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
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _make_partner(email: str = "partner@test.com") -> int:
    """상대 유저를 만들고 id를 준다. 연락처는 인스타·카톡만 채운다."""
    db = TestingSessionLocal()
    partner = User(
        email=email, password_hash="x", name="이상대", university="연세대학교",
        gender=Gender.female, status=UserStatus.active,
        instagram="partner_insta", kakao_id="partner_kakao",
    )
    db.add(partner)
    db.commit()
    partner_id = partner.id
    db.close()
    return partner_id


def _make_done_round(executed_at: datetime) -> int:
    db = TestingSessionLocal()
    round_ = MatchRound(
        scheduled_at=executed_at,
        executed_at=executed_at,
        status=RoundStatus.done,
    )
    db.add(round_)
    db.commit()
    round_id = round_.id
    db.close()
    return round_id


def _make_match(round_id: int, a_id: int, b_id: int) -> None:
    db = TestingSessionLocal()
    db.add(Match(match_round_id=round_id, user_a_id=a_id, user_b_id=b_id, score=77))
    db.commit()
    db.close()


def _my_id(client: TestClient, headers: dict) -> int:
    return client.get("/me", headers=headers).json()["id"]


def test_no_executed_round_returns_null(client: TestClient):
    headers = _register_and_get_headers(client)
    res = client.get("/me/match", headers=headers)
    assert res.status_code == 200
    assert res.json() is None


def test_matched_returns_partner_and_contacts(client: TestClient):
    headers = _register_and_get_headers(client)
    me_id = _my_id(client, headers)
    partner_id = _make_partner()
    round_id = _make_done_round(datetime(2026, 8, 14, 12, 0))
    _make_match(round_id, me_id, partner_id)

    res = client.get("/me/match", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "이상대"
    assert data["university"] == "연세대학교"
    assert data["instagram"] == "partner_insta"
    assert data["kakao_id"] == "partner_kakao"
    assert data["phone"] is None
    assert data["executed_at"].startswith("2026-08-14T12:00:00")


def test_partner_found_when_i_am_user_b(client: TestClient):
    """user_a/user_b 어느 쪽에 있든 상대를 찾아야 한다."""
    headers = _register_and_get_headers(client)
    me_id = _my_id(client, headers)
    partner_id = _make_partner()
    round_id = _make_done_round(datetime(2026, 8, 14, 12, 0))
    _make_match(round_id, partner_id, me_id)

    res = client.get("/me/match", headers=headers)

    assert res.json()["name"] == "이상대"


def test_score_is_not_exposed(client: TestClient):
    headers = _register_and_get_headers(client)
    me_id = _my_id(client, headers)
    partner_id = _make_partner()
    round_id = _make_done_round(datetime(2026, 8, 14, 12, 0))
    _make_match(round_id, me_id, partner_id)

    assert "score" not in client.get("/me/match", headers=headers).json()


def test_unmatched_in_latest_round_returns_null(client: TestClient):
    """실행된 라운드는 있는데 내 짝이 없으면 null."""
    headers = _register_and_get_headers(client)
    _make_done_round(datetime(2026, 8, 14, 12, 0))

    assert client.get("/me/match", headers=headers).json() is None


def test_previous_round_result_is_not_returned(client: TestClient):
    """지난 라운드에 매칭됐어도 최신 done 라운드에서 미매칭이면 null (설계 §7.1)."""
    headers = _register_and_get_headers(client)
    me_id = _my_id(client, headers)
    partner_id = _make_partner()
    old_round = _make_done_round(datetime(2026, 8, 7, 12, 0))
    _make_match(old_round, me_id, partner_id)
    _make_done_round(datetime(2026, 8, 14, 12, 0))

    assert client.get("/me/match", headers=headers).json() is None


def test_pending_round_is_ignored(client: TestClient):
    """아직 안 돌린 라운드에 딸린 행은 결과가 아니다."""
    headers = _register_and_get_headers(client)
    me_id = _my_id(client, headers)
    partner_id = _make_partner()
    db = TestingSessionLocal()
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()
    round_id = round_.id
    db.close()
    _make_match(round_id, me_id, partner_id)

    assert client.get("/me/match", headers=headers).json() is None


def test_requires_auth(client: TestClient):
    assert client.get("/me/match").status_code == 401

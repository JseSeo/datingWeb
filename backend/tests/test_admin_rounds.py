from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api import rounds
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


def test_update_changes_scheduled_at(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    new_when = _iso(48)
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": new_when}
    )
    assert res.status_code == 200
    assert res.json()["id"] == round_id
    assert res.json()["scheduled_at"].startswith(new_when[:16])


def test_update_allows_moving_a_past_pending_round_to_future(admin_client: TestClient):
    """관리자가 실행하지 못하고 지나간 라운드를 다음 주로 옮기는 정상 경로."""
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(-24), status=RoundStatus.pending)
    )
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": _iso(48)}
    )
    assert res.status_code == 200


def test_update_rejects_past(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": _iso(-1)}
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "예정 시각은 현재보다 미래여야 합니다"


def test_update_rejects_duplicate_of_another_round(admin_client: TestClient):
    taken = _hours(72).replace(microsecond=0)
    ids = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending),
        MatchRound(scheduled_at=taken, status=RoundStatus.pending),
    )
    res = admin_client.put(
        f"/admin/match-rounds/{ids[0]}", json={"scheduled_at": taken.isoformat()}
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "같은 시각의 라운드가 이미 있습니다"


def test_update_to_its_own_current_time_is_allowed(admin_client: TestClient):
    """자기 자신은 중복 판정에서 제외한다."""
    when = _hours(24).replace(microsecond=0)
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=when, status=RoundStatus.pending)
    )
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": when.isoformat()}
    )
    assert res.status_code == 200


def test_update_rejects_done_round(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.done)
    )
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": _iso(48)}
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "완료된 라운드는 수정할 수 없습니다"


def test_update_rejects_running_round(admin_client: TestClient):
    """실행 중 라운드를 고치면 _execute가 도는 도중 데이터가 바뀐다."""
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.running)
    )
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": _iso(48)}
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "실행 중인 라운드는 수정할 수 없습니다"


def test_update_missing_round_returns_404(admin_client: TestClient):
    res = admin_client.put(
        "/admin/match-rounds/9999", json={"scheduled_at": _iso(24)}
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "존재하지 않는 라운드입니다"


def test_delete_removes_round(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    assert admin_client.delete(f"/admin/match-rounds/{round_id}").status_code == 204
    assert admin_client.get("/admin/match-rounds").json() == []


def test_delete_allows_past_pending_round(admin_client: TestClient):
    """지나간 pending 라운드도 지울 수 있어야 한다 — 삭제엔 시각 규칙을 걸지 않는다."""
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(-24), status=RoundStatus.pending)
    )
    assert admin_client.delete(f"/admin/match-rounds/{round_id}").status_code == 204


def test_delete_rejects_done_round(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(-24), status=RoundStatus.done)
    )
    res = admin_client.delete(f"/admin/match-rounds/{round_id}")
    assert res.status_code == 409
    assert res.json()["detail"] == "완료된 라운드는 삭제할 수 없습니다"


def test_delete_rejects_running_round(admin_client: TestClient):
    """실행 중 라운드가 지워지면 Match INSERT가 없는 라운드를 참조한다."""
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.running)
    )
    res = admin_client.delete(f"/admin/match-rounds/{round_id}")
    assert res.status_code == 409
    assert res.json()["detail"] == "실행 중인 라운드는 삭제할 수 없습니다"


def test_delete_missing_round_returns_404(admin_client: TestClient):
    res = admin_client.delete("/admin/match-rounds/9999")
    assert res.status_code == 404


def test_update_rejects_non_admin(client: TestClient):
    headers = _register_normal_user(client)
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    res = client.put(
        f"/admin/match-rounds/{round_id}",
        json={"scheduled_at": _iso(48)},
        headers=headers,
    )
    assert res.status_code == 403


def test_delete_rejects_non_admin(client: TestClient):
    headers = _register_normal_user(client)
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    res = client.delete(f"/admin/match-rounds/{round_id}", headers=headers)
    assert res.status_code == 403


def test_db_rejects_duplicate_scheduled_at():
    """앱 검사와 별개로 DB가 중복을 막는다 — 검사와 INSERT 사이 경쟁의 최후 방어선."""
    when = datetime(2030, 1, 1, 12, 0)
    _add_rounds(MatchRound(scheduled_at=when, status=RoundStatus.pending))
    db = TestingSessionLocal()
    db.add(MatchRound(scheduled_at=when, status=RoundStatus.pending))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_create_returns_409_when_precheck_is_bypassed(
    admin_client: TestClient, monkeypatch
):
    """_reject_duplicate를 무력화해 TOCTOU를 흉내낸다. 500이 아니라 409여야 한다."""
    when = "2030-01-01T12:00:00"
    assert admin_client.post(
        "/admin/match-rounds", json={"scheduled_at": when}
    ).status_code == 201
    monkeypatch.setattr(rounds, "_reject_duplicate", lambda *args, **kwargs: None)
    res = admin_client.post("/admin/match-rounds", json={"scheduled_at": when})
    assert res.status_code == 409
    assert res.json()["detail"] == "같은 시각의 라운드가 이미 있습니다"


def test_update_returns_409_when_precheck_is_bypassed(
    admin_client: TestClient, monkeypatch
):
    _, second_id = _add_rounds(
        MatchRound(scheduled_at=datetime(2030, 1, 1, 12, 0), status=RoundStatus.pending),
        MatchRound(scheduled_at=datetime(2030, 1, 2, 12, 0), status=RoundStatus.pending),
    )
    monkeypatch.setattr(rounds, "_reject_duplicate", lambda *args, **kwargs: None)
    res = admin_client.put(
        f"/admin/match-rounds/{second_id}",
        json={"scheduled_at": "2030-01-01T12:00:00"},
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "같은 시각의 라운드가 이미 있습니다"


def _minutes_ago(n: int) -> datetime:
    return datetime.utcnow() - timedelta(minutes=n)


def test_reset_returns_stuck_running_round_to_pending(admin_client: TestClient):
    """서버가 죽어 running에 멈춘 라운드의 유일한 복구 수단."""
    [round_id] = _add_rounds(MatchRound(
        scheduled_at=_hours(-1),
        status=RoundStatus.running,
        started_at=_minutes_ago(20),
    ))
    res = admin_client.post(f"/admin/match-rounds/{round_id}/reset")
    assert res.status_code == 200
    assert res.json()["status"] == "pending"

    listed = admin_client.get("/admin/match-rounds").json()
    assert listed[0]["status"] == "pending"


def test_reset_rejects_recently_started_round(admin_client: TestClient):
    """아직 실행 중일 수 있다. 되돌리면 이중 실행이 난다."""
    [round_id] = _add_rounds(MatchRound(
        scheduled_at=_hours(-1),
        status=RoundStatus.running,
        started_at=_minutes_ago(1),
    ))
    res = admin_client.post(f"/admin/match-rounds/{round_id}/reset")
    assert res.status_code == 409
    assert "1분" in res.json()["detail"]


def test_reset_allows_running_round_without_started_at(admin_client: TestClient):
    """started_at 추적 이전에 멈춘 행. 확실히 오래된 것이므로 유예를 적용하지 않는다."""
    [round_id] = _add_rounds(MatchRound(
        scheduled_at=_hours(-1),
        status=RoundStatus.running,
        started_at=None,
    ))
    res = admin_client.post(f"/admin/match-rounds/{round_id}/reset")
    assert res.status_code == 200
    assert res.json()["status"] == "pending"


def test_reset_rejects_pending_round(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    res = admin_client.post(f"/admin/match-rounds/{round_id}/reset")
    assert res.status_code == 409
    assert res.json()["detail"] == "실행 중인 라운드만 되돌릴 수 있습니다"


def test_reset_rejects_done_round(admin_client: TestClient):
    """done은 매칭 결과가 딸린 상태다. 되돌리면 결과 있는 라운드를 재실행하게 된다."""
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(-24), status=RoundStatus.done)
    )
    res = admin_client.post(f"/admin/match-rounds/{round_id}/reset")
    assert res.status_code == 409
    assert res.json()["detail"] == "실행 중인 라운드만 되돌릴 수 있습니다"


def test_reset_missing_round_returns_404(admin_client: TestClient):
    res = admin_client.post("/admin/match-rounds/9999/reset")
    assert res.status_code == 404
    assert res.json()["detail"] == "존재하지 않는 라운드입니다"


def test_reset_rejects_non_admin(client: TestClient):
    headers = _register_normal_user(client)
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(-1), status=RoundStatus.running)
    )
    res = client.post(f"/admin/match-rounds/{round_id}/reset", headers=headers)
    assert res.status_code == 403


def test_reset_requires_auth(client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(-1), status=RoundStatus.running)
    )
    assert client.post(f"/admin/match-rounds/{round_id}/reset").status_code == 401


def test_reset_rejects_just_before_the_grace_period_ends(admin_client: TestClient):
    """유예 임계값을 잠근다 — RUNNING_GRACE를 줄이면 이 테스트가 깨진다."""
    [round_id] = _add_rounds(MatchRound(
        scheduled_at=_hours(-1),
        status=RoundStatus.running,
        started_at=datetime.utcnow() - timedelta(minutes=9, seconds=59),
    ))
    res = admin_client.post(f"/admin/match-rounds/{round_id}/reset")
    assert res.status_code == 409


def test_reset_allows_just_after_the_grace_period_ends(admin_client: TestClient):
    """반대쪽 경계 — RUNNING_GRACE를 늘리면 이 테스트가 깨진다."""
    [round_id] = _add_rounds(MatchRound(
        scheduled_at=_hours(-1),
        status=RoundStatus.running,
        started_at=datetime.utcnow() - timedelta(minutes=10, seconds=1),
    ))
    res = admin_client.post(f"/admin/match-rounds/{round_id}/reset")
    assert res.status_code == 200
    assert res.json()["status"] == "pending"

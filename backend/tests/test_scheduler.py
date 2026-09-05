"""예약 실행 판정 (설계 2026-09-05). now를 주입하므로 실제 시간을 기다리지 않는다."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.match import MatchRound, RoundStatus
from app.services import scheduler
from app.services.matching import RoundNotPending
from app.services.scheduler import CATCHUP_GRACE, MISSED_MESSAGE, run_due_once
from tests.conftest import TestingSessionLocal

BASE = datetime(2026, 9, 5, 12, 0, 0)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


def _round(db, scheduled_at: datetime, **kwargs) -> int:
    round_ = MatchRound(scheduled_at=scheduled_at, **kwargs)
    db.add(round_)
    db.commit()
    return round_.id


def _status(db, round_id: int) -> RoundStatus:
    db.expire_all()
    return db.get(MatchRound, round_id).status


def _error(db, round_id: int) -> str | None:
    db.expire_all()
    return db.get(MatchRound, round_id).last_error


# 유저 풀이 비어 있으면 매칭은 0쌍으로 정상 종료한다. 이 테스트들이 보는 것은
# "언제 도느냐"이지 "누가 짝이 되느냐"가 아니다 (그건 test_matching.py 담당)


def test_runs_exactly_at_scheduled_time(db):
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE)
    assert _status(db, round_id) == RoundStatus.done


def test_runs_within_grace(db):
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE + timedelta(minutes=59))
    assert _status(db, round_id) == RoundStatus.done


def test_does_not_run_before_scheduled_time(db):
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE - timedelta(seconds=1))
    assert _status(db, round_id) == RoundStatus.pending
    assert _error(db, round_id) is None


def test_marks_missed_after_grace(db):
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE + timedelta(minutes=61))
    assert _status(db, round_id) == RoundStatus.pending
    assert _error(db, round_id) == MISSED_MESSAGE


def test_grace_boundary_is_exclusive(db):
    """정확히 유예 경계면 실행하지 않는다 — 표의 부등호를 고정한다."""
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE + CATCHUP_GRACE)
    assert _status(db, round_id) == RoundStatus.pending
    assert _error(db, round_id) == MISSED_MESSAGE


def test_missed_round_is_marked_only_once(db):
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE + timedelta(minutes=61))
    run_due_once(db, BASE + timedelta(minutes=62))
    assert _error(db, round_id) == MISSED_MESSAGE
    assert _status(db, round_id) == RoundStatus.pending


def test_round_with_error_is_not_retried_within_grace(db):
    round_id = _round(
        db, BASE, status=RoundStatus.pending, last_error="이전 실패"
    )
    run_due_once(db, BASE + timedelta(minutes=5))
    assert _status(db, round_id) == RoundStatus.pending
    assert _error(db, round_id) == "이전 실패"


def test_running_and_done_rounds_are_ignored(db):
    running_id = _round(db, BASE, status=RoundStatus.running)
    done_id = _round(db, BASE - timedelta(days=7), status=RoundStatus.done)
    run_due_once(db, BASE + timedelta(minutes=5))
    assert _status(db, running_id) == RoundStatus.running
    assert _status(db, done_id) == RoundStatus.done


def test_failure_records_error_and_keeps_pending(db, monkeypatch):
    round_id = _round(db, BASE, status=RoundStatus.pending)

    def boom(_db, _round_id):
        raise ValueError("점수 계산 폭발")

    monkeypatch.setattr(scheduler, "run_matching", boom)
    run_due_once(db, BASE)
    assert _status(db, round_id) == RoundStatus.pending
    assert _error(db, round_id) == "ValueError: 점수 계산 폭발"


def test_long_error_is_truncated(db, monkeypatch):
    round_id = _round(db, BASE, status=RoundStatus.pending)

    def boom(_db, _round_id):
        raise ValueError("x" * 1000)

    monkeypatch.setattr(scheduler, "run_matching", boom)
    run_due_once(db, BASE)
    assert len(_error(db, round_id)) == 500


def test_round_not_pending_is_silent(db, monkeypatch):
    """다른 워커가 먼저 선점한 경우. 그쪽은 정상 실행 중이므로 에러를 남기면 안 된다."""
    round_id = _round(db, BASE, status=RoundStatus.pending)

    def taken(_db, _round_id):
        raise RoundNotPending

    monkeypatch.setattr(scheduler, "run_matching", taken)
    run_due_once(db, BASE)
    assert _error(db, round_id) is None


def test_error_is_not_written_if_round_finished_meanwhile(db, monkeypatch):
    """_record_error가 UPDATE를 쏘기 전, 그 사이 라운드가 done이 됐다면 쓰면 안 된다.

    due 목록은 미리 굳힌 것이라, 앞선 라운드의 run_matching이 오래 걸리는 동안
    관리자가 뒤 라운드를 수동으로 done까지 돌릴 수 있다. done은 재실행이 불가능하므로
    last_error가 한 번 잘못 찍히면 지울 방법이 없다 (F1 회귀 테스트).

    first를 처리하다 second를 done으로 바꿔놓고, 그 다음 second 처리도 실패로
    떨어지게 만든다 — 가드가 없으면 이미 done인 second에 last_error가 그대로 찍힌다.
    """
    first = _round(db, BASE - timedelta(minutes=5), status=RoundStatus.pending)
    second = _round(db, BASE - timedelta(minutes=3), status=RoundStatus.pending)

    def boom(inner_db, round_id):
        if round_id == first:
            # first를 처리하는 실제 run_matching이 오래 걸리는 동안 관리자가
            # second를 수동으로 끝까지 돌렸다고 가정한다
            inner_db.query(MatchRound).filter(MatchRound.id == second).update(
                {MatchRound.status: RoundStatus.done}
            )
            inner_db.commit()
        raise ValueError("점수 계산 폭발")

    monkeypatch.setattr(scheduler, "run_matching", boom)
    run_due_once(db, BASE)

    assert _status(db, second) == RoundStatus.done
    assert _error(db, second) is None


def test_processes_multiple_due_rounds(db):
    first = _round(db, BASE - timedelta(minutes=30), status=RoundStatus.pending)
    second = _round(db, BASE - timedelta(minutes=10), status=RoundStatus.pending)
    run_due_once(db, BASE)
    assert _status(db, first) == RoundStatus.done
    assert _status(db, second) == RoundStatus.done


def test_rescheduled_round_with_cleared_error_is_picked_up_again(
    db, admin_client: TestClient
):
    """놓쳐서 last_error가 찍힌 라운드를 관리자가 PUT으로 미래에 재예약하면
    (last_error가 함께 지워지면) 그 시각에 스케줄러가 실제로 다시 집어간다.
    지우지 않으면 재시도 금지 필터에 걸려 영구 제외된다 — 그 결함이 닫혔다는 증거."""
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE + timedelta(minutes=61))
    assert _error(db, round_id) == MISSED_MESSAGE
    assert _status(db, round_id) == RoundStatus.pending

    new_when = BASE + timedelta(days=7)
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}",
        json={"scheduled_at": new_when.isoformat()},
    )
    assert res.status_code == 200

    db.expire_all()
    run_due_once(db, new_when)
    assert _status(db, round_id) == RoundStatus.done
    assert _error(db, round_id) is None


def test_tick_opens_a_session_and_calls_run_due_once(monkeypatch):
    """루프가 판정 함수에 세션과 현재 시각을 넘기는 이음매만 확인한다.
    루프 자체(asyncio.sleep)는 타이밍 테스트가 flaky해지므로 테스트하지 않는다."""
    calls = []

    def spy(db, now):
        calls.append((db, now))

    monkeypatch.setattr(scheduler, "run_due_once", spy)
    monkeypatch.setattr(scheduler, "SessionLocal", TestingSessionLocal)

    scheduler._tick()

    assert len(calls) == 1
    db, now = calls[0]
    assert isinstance(db, Session)
    assert isinstance(now, datetime)

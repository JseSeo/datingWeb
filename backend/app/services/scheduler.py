"""예약된 라운드를 제 시간에 실행한다 (설계 2026-09-05).

판정은 run_due_once에 모아 now를 주입받는다 — 루프에는 테스트할 것이 남지 않는다.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.match import MatchRound, RoundStatus
from app.services.matching import RoundNotPending, run_matching

logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # 초. 최대 이만큼 늦게 실행된다
CATCHUP_GRACE = timedelta(hours=1)  # 예정 시각 + 이 시간까지는 늦어도 실행한다
MISSED_MESSAGE = "예정 시각을 놓쳐 자동 실행되지 않았습니다. 수동으로 실행해주세요"
_ERROR_MAX = 500  # last_error 컬럼 길이


def run_due_once(db: Session, now: datetime) -> None:
    """실행할 때가 된 라운드를 처리한다. 한 번의 폴링이 하는 일 전부."""
    # last_error가 찬 라운드를 애초에 뽑지 않는 것이 '재시도 없음'의 구현이다.
    # 이 필터가 없으면 실패한 라운드가 유예 1시간 동안 60초마다 다시 터진다.
    # (id, scheduled_at)으로 먼저 굳힌다 — run_matching이 커밋하면 ORM 객체가 만료된다
    due = [
        (round_.id, round_.scheduled_at)
        for round_ in db.query(MatchRound)
        .filter(
            MatchRound.status == RoundStatus.pending,
            MatchRound.scheduled_at <= now,
            MatchRound.last_error.is_(None),
        )
        .order_by(MatchRound.scheduled_at.asc())
        .all()
    ]

    for round_id, scheduled_at in due:
        if now - scheduled_at >= CATCHUP_GRACE:
            # 너무 늦었다. 유저가 모르는 사이 도는 것보다 관리자 판단에 맡긴다
            _record_error(db, round_id, MISSED_MESSAGE)
            continue
        try:
            run_matching(db, round_id)
        except RoundNotPending:
            # 다른 워커가 먼저 선점했다. 그쪽이 정상 실행 중이므로 에러가 아니다
            logger.info("라운드 %s는 이미 다른 실행이 선점했다", round_id)
        except Exception as exc:
            logger.exception("라운드 %s 자동 실행 실패", round_id)
            _record_error(db, round_id, f"{type(exc).__name__}: {exc}")


def _record_error(db: Session, round_id: int, message: str) -> None:
    """실패 사유를 별도 트랜잭션으로 기록한다.

    run_matching이 실패하며 세션을 rollback 해둔 상태라, 그 위에 얹지 않고
    UPDATE 하나로 새로 쓴다. status는 건드리지 않는다 — 실패한 라운드는 여전히 pending이다.
    """
    db.rollback()
    db.query(MatchRound).filter(MatchRound.id == round_id).update(
        {MatchRound.last_error: message[:_ERROR_MAX]},
        synchronize_session=False,
    )
    db.commit()

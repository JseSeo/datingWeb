"""매칭 파이프라인 오케스트레이션 (설계 §2). HTTP는 모른다."""

from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.survey import Survey
from app.models.user import User, UserStatus

# 설계 §4.1 — 상한이 없으면 대기자끼리 묶이는 최악 궁합 매칭이 양산된다
CARRYOVER_PER_ROUND = 15
CARRYOVER_CAP = 45

# 설계 §4.2는 3단계 작업이다. 지금은 자리만 마련해 둔다
UNIVERSITY_BONUS = 0


def pair_key(a: int, b: int) -> tuple[int, int]:
    """페어를 순서 무관하게 다루기 위한 정규화 키."""
    return (a, b) if a < b else (b, a)


def eligible_users(db: Session) -> list[User]:
    """매칭 자격: active + 일시정지 OFF + 설문 행 존재 (설계 §6.2).

    응답 개수는 따지지 않는다 — 부분 응답도 풀에 넣는다.
    """
    return (
        db.query(User)
        .join(Survey, Survey.user_id == User.id)
        .filter(
            User.status == UserStatus.active,
            User.matching_paused.is_(False),
        )
        .order_by(User.id)
        .all()
    )


def past_pairs(db: Session) -> set[tuple[int, int]]:
    """한 번이라도 짝이었던 페어. 라운드와 무관하게 영구 제외한다 (설계 §5.4)."""
    return {
        pair_key(a, b)
        for a, b in db.query(Match.user_a_id, Match.user_b_id).all()
    }


def carryover_bonus(user: User) -> int:
    """미매칭 라운드마다 쌓이는 보너스. 상한 있음 (설계 §4.1)."""
    return min(user.missed_rounds * CARRYOVER_PER_ROUND, CARRYOVER_CAP)

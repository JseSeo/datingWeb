"""매칭 파이프라인 오케스트레이션 (설계 §2). HTTP는 모른다."""

from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.models.game import Ojakgyo, RedThread
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


# 설계 §4.3 — 상위 스펙의 "+33%"를 100점 만점 기준 점수로 환산
OJAKGYO_BONUS = 33
OJAKGYO_GUARANTEE_COUNT = 3


def _identity_resolver(db: Session):
    """이름+학교가 유일할 때만 유저를 특정한다 (설계 §4.4).

    학번(admission_year)은 아직 없다 — 도입 전까지 이름+학교로만 판정하되
    '유일할 때만 적용' 규칙은 그대로 지킨다. 2명 이상이면 무시(None).
    """
    index: dict[tuple[str, str], list[int]] = defaultdict(list)
    for user_id, name, university in db.query(
        User.id, User.name, User.university
    ).all():
        index[(name.strip(), university.strip())].append(user_id)

    def resolve(name: str, university: str) -> int | None:
        hits = index.get((name.strip(), university.strip()), [])
        return hits[0] if len(hits) == 1 else None

    return resolve


def game_signals(
    db: Session, pool: list[User]
) -> tuple[set[tuple[int, int]], dict[tuple[int, int], int]]:
    """(붉은실 상호 페어, 페어별 오작교 지목자 수).

    둘 다 풀 안에 있고 성별이 다른 페어만 남긴다 — 남녀 1:1 전제.
    """
    by_id = {user.id: user for user in pool}
    resolve = _identity_resolver(db)

    def usable(a: int, b: int) -> bool:
        left, right = by_id.get(a), by_id.get(b)
        return left is not None and right is not None and left.gender != right.gender

    targets: dict[int, set[int]] = defaultdict(set)
    for thread in db.query(RedThread).all():
        target_id = resolve(thread.target_name, thread.target_university)
        if target_id is not None:
            targets[thread.user_id].add(target_id)

    red: set[tuple[int, int]] = set()
    for user_id, target_ids in targets.items():
        for target_id in target_ids:
            if user_id in targets.get(target_id, set()) and usable(user_id, target_id):
                red.add(pair_key(user_id, target_id))

    counts: Counter[tuple[int, int]] = Counter()
    for entry in db.query(Ojakgyo).all():
        a = resolve(entry.person_a_name, entry.person_a_university)
        b = resolve(entry.person_b_name, entry.person_b_university)
        # 같은 지목자가 같은 쌍을 두 번 넣는 건 DB 유니크 제약이 이미 막는다
        if a is None or b is None or a == b or not usable(a, b):
            continue
        counts[pair_key(a, b)] += 1

    return red, dict(counts)


def resolve_guarantees(
    red: set[tuple[int, int]],
    ojakgyo: set[tuple[int, int]],
    score: dict[tuple[int, int], float],
) -> list[tuple[int, int]]:
    """보장 충돌 해소 (설계 §4.3).

    우선순위: 붉은실 상호 > 오작교 3인 → 궁합 점수 높은 쪽 → user_id 작은 쪽.
    버려진 페어는 일반 매칭 풀로 돌아간다(여기서 반환하지 않는 것이 곧 그 뜻).
    """
    ranked = sorted(
        [(0, pair) for pair in red] + [(1, pair) for pair in ojakgyo],
        key=lambda item: (item[0], -score.get(item[1], 0.0), item[1]),
    )
    used: set[int] = set()
    confirmed: list[tuple[int, int]] = []
    for _, (a, b) in ranked:
        if a in used or b in used:
            continue
        used.update((a, b))
        confirmed.append((a, b))
    return confirmed

"""매칭 파이프라인 오케스트레이션 (설계 §2). HTTP는 모른다."""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.game import Ojakgyo, RedThread
from app.models.match import Match, MatchingUniversityWeight, MatchRound, RoundStatus
from app.models.survey import Survey
from app.models.user import Gender, User, UserStatus
from app.services.pairing import optimal_pairs
from app.services.scoring import pair_allowed, pair_score

logger = logging.getLogger(__name__)

# 설계 §4.1 — 상한이 없으면 대기자끼리 묶이는 최악 궁합 매칭이 양산된다
CARRYOVER_PER_ROUND = 15
CARRYOVER_CAP = 45

# 설계 §4.2 — 관리자가 실수로 큰 값을 넣어도 매칭 전체가 망가지지 않게 하는 상한
UNIVERSITY_BONUS_CAP = 50


def university_pair_key(a: str, b: str) -> tuple[str, str]:
    """대학쌍을 순서 무관하게 다루기 위한 사전순 정규화 키 (설계 §4.2)."""
    return (a, b) if a <= b else (b, a)


def university_weights(
    db: Session,
) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    """active 규칙을 단일용·쌍용 조회표 두 개로 나눠 한 번에 읽는다.

    라운드가 도는 중에 관리자가 규칙을 바꿔도 결과가 흔들리지 않도록 실행 시작에
    한 번만 읽는다 (설계 §5.2 결정론성).
    """
    singles: dict[str, int] = {}
    pairs: dict[tuple[str, str], int] = {}
    rows = (
        db.query(MatchingUniversityWeight)
        .filter(MatchingUniversityWeight.active.is_(True))
        .order_by(MatchingUniversityWeight.id)
        .all()
    )
    for row in rows:
        if row.university_b == "":
            singles[row.university_a] = row.bonus
        else:
            key = university_pair_key(row.university_a, row.university_b)
            # 순서가 뒤집힌 중복 행은 유니크가 못 막는다 — 덮어쓰면 어느 쪽이 남는지가
            # DB 반환 순서에 좌우되므로 합산한다
            pairs[key] = pairs.get(key, 0) + row.bonus
    return singles, pairs


def university_bonus(
    a: str,
    b: str,
    singles: dict[str, int],
    pairs: dict[tuple[str, str], int],
) -> int:
    """겹치는 규칙은 합산하되 ±UNIVERSITY_BONUS_CAP으로 자른다 (설계 §4.2).

    합산은 규칙 행 기준이다 — 같은 대학끼리인 페어에서 그 대학의 단일 규칙은
    한 번만 붙는다.
    """
    total = singles.get(a, 0)
    if b != a:
        total += singles.get(b, 0)
    total += pairs.get(university_pair_key(a, b), 0)
    return max(-UNIVERSITY_BONUS_CAP, min(UNIVERSITY_BONUS_CAP, total))


def pair_key(a: int, b: int) -> tuple[int, int]:
    """페어를 순서 무관하게 다루기 위한 정규화 키."""
    return (a, b) if a < b else (b, a)


def _has_contact():
    """연락처 1개 이상 (설계 §7.2). 빈 문자열·공백만 있는 값도 없는 것으로 본다 —
    스키마는 None으로 정규화하지만 과거 데이터나 DB 직접 수정이 남길 수 있다.

    문자 집합을 명시해야 한다 — 인자 없는 SQL TRIM은 스페이스만 지운다
    (SQLite·PostgreSQL 공통). 지정 없이 쓰면 탭·개행만 있는 값이 스키마에서는
    없는 것으로 보이는데 여기서는 있는 것으로 남아 세 층위 판정이 갈라진다.
    """
    return or_(
        *[
            and_(column.isnot(None), func.trim(column, " \t\r\n") != "")
            for column in (User.instagram, User.kakao_id, User.phone)
        ]
    )


def eligible_users(db: Session) -> list[User]:
    """매칭 자격: active + 일시정지 OFF + 설문 행 존재 + 연락처 1개 이상 (설계 §6.2).

    응답 개수는 따지지 않는다 — 부분 응답도 풀에 넣는다.
    """
    return (
        db.query(User)
        .join(Survey, Survey.user_id == User.id)
        .options(joinedload(User.survey))
        .filter(
            User.status == UserStatus.active,
            User.matching_paused.is_(False),
            _has_contact(),
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
    """이름+학교로 후보를 찾고 학번으로 좁힌다 (설계 §6).

    학번은 후보를 좁히는 추가 필터일 뿐이다. 학번 미등록 유저를 후보에서 빼지 않는다 —
    그러면 대상이 학번을 안 넣었다는 이유만으로 지목이 조용히 사라진다.
    """
    index: dict[tuple[str, str], list[tuple[int, int | None]]] = defaultdict(list)
    for user_id, name, university, admission_year in db.query(
        User.id, User.name, User.university, User.admission_year
    ).all():
        index[(name.strip(), university.strip())].append((user_id, admission_year))

    def resolve(name: str, university: str, admission_year: int = 0) -> int | None:
        hits = index.get((name.strip(), university.strip()), [])
        if admission_year:
            narrowed = [hit for hit in hits if hit[1] == admission_year]
            if len(narrowed) == 1:
                return narrowed[0][0]
            # 0명이거나 2명 이상이면 학번으로 못 좁힌다 — 이름+학교 결과로 폴백 (설계 §6.3)
        return hits[0][0] if len(hits) == 1 else None

    return resolve


def get_identity_resolver(db: Session):
    """`_identity_resolver`의 공개 창구.

    매칭 파이프라인 밖(API 계층)에서도 "이름+학교+학번이 어느 유저를 가리키는가"를
    매칭과 똑같은 규칙(학번 불일치 시 이름+학교 단일후보 폴백, 설계 §6.3)으로 판정해야
    할 때가 있다 — 예: 붉은실 수신함 집계가 매칭 결과와 수가 어긋나면 안 된다. 그렇다고
    API가 밑줄 붙은 내부 함수를 직접 넘어가 부르게 하면 매칭 모듈의 캡슐화가 깨지므로,
    동작은 그대로 두고 이 이름으로만 내보낸다. 반환된 resolver는 유저 전체를 인덱싱해
    만들어지므로 요청당 한 번만 만들어 재사용해야 한다(행마다 새로 만들면 안 됨).
    """
    return _identity_resolver(db)


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
        target_id = resolve(
            thread.target_name, thread.target_university, thread.target_admission_year
        )
        if target_id is not None:
            targets[thread.user_id].add(target_id)

    # 붉은실은 제출자 자신이 페어의 한쪽이라 자기지목 우회 구조가 아니다 — 대상이
    # 학번만 다르게 적은 자신으로 풀려도 usable()의 성별 비교(자기 자신과는 항상
    # 같음)가 이미 걸러낸다. 오작교처럼 "제3자가 지목한 두 사람" 구조가 아니므로
    # 지목자 자신을 별도로 걸러낼 지점이 없다.
    red: set[tuple[int, int]] = set()
    for user_id, target_ids in targets.items():
        for target_id in target_ids:
            if user_id in targets.get(target_id, set()) and usable(user_id, target_id):
                red.add(pair_key(user_id, target_id))

    counts: Counter[tuple[int, int]] = Counter()
    for entry in db.query(Ojakgyo).all():
        a = resolve(
            entry.person_a_name, entry.person_a_university, entry.person_a_admission_year
        )
        b = resolve(
            entry.person_b_name, entry.person_b_university, entry.person_b_admission_year
        )
        # 같은 지목자가 같은 쌍을 두 번 넣는 건 DB 유니크 제약이 이미 막는다
        if a is None or b is None or a == b or not usable(a, b):
            continue
        # 지목자가 자기 학번만 다르게 적어 §6.3 폴백(후보 1명이면 학번 무시하고
        # 확정)으로 스스로에게 되돌아오는 경우 — API 단계에선 학번이 다르면
        # "다른 사람"이라 판단해 막을 수 없으므로 투표가 집계되는 여기서 막는다
        if entry.recommender_id in (a, b):
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


class RoundNotFound(Exception):
    """존재하지 않는 라운드."""


class RoundNotPending(Exception):
    """이미 실행 중이거나 완료된 라운드 — 중복 실행 방어 (설계 §5.5)."""


@dataclass(frozen=True)
class MatchingResult:
    matched: int
    unmatched: int
    guaranteed: int


def run_matching(db: Session, round_id: int) -> MatchingResult:
    """라운드 하나를 실행한다. 실패하면 라운드를 pending으로 되돌린다."""
    if db.get(MatchRound, round_id) is None:
        raise RoundNotFound

    # 조건부 UPDATE 한 번으로 검사와 선점을 동시에 한다 — 경쟁 구간이 없다
    claimed_at = datetime.utcnow()
    claimed = (
        db.query(MatchRound)
        .filter(MatchRound.id == round_id, MatchRound.status == RoundStatus.pending)
        .update(
            {
                MatchRound.status: RoundStatus.running,
                MatchRound.started_at: claimed_at,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    if claimed == 0:
        raise RoundNotPending

    round_ = db.get(MatchRound, round_id)
    try:
        result = _execute(db, round_)
        db.commit()
        return result
    except Exception:
        db.rollback()
        # 중간 실패는 전부 롤백된다. 절반만 매칭된 상태는 남지 않는다 (설계 §2)
        #
        # 선점 시각까지 걸어 "내가 잡은 그 실행"일 때만 되돌린다. reset(설계 §5.5)으로
        # 라운드가 pending이 되고 다른 실행이 끝난 뒤 이쪽이 뒤늦게 실패하면, 무조건
        # 대입은 남의 done을 pending으로 덮어 "매칭 결과는 있는데 status는 pending"인
        # 깨진 상태를 만든다
        db.query(MatchRound).filter(
            MatchRound.id == round_id,
            MatchRound.status == RoundStatus.running,
            MatchRound.started_at == claimed_at,
        ).update({MatchRound.status: RoundStatus.pending}, synchronize_session=False)
        db.commit()
        raise


def _execute(db: Session, round_: MatchRound) -> MatchingResult:
    pool = eligible_users(db)
    answers = {user.id: (user.survey.answers or {}) for user in pool}
    men = [u for u in pool if u.gender == Gender.male]
    women = [u for u in pool if u.gender == Gender.female]
    excluded = past_pairs(db)
    red, ojakgyo_counts = game_signals(db, pool)
    uni_singles, uni_pairs = university_weights(db)

    base: dict[tuple[int, int], float] = {}   # 보정 전 궁합 점수 (Match.score에 기록)
    adjusted: dict[tuple[int, int], float] = {}  # 보정까지 얹은 매칭용 점수
    skipped: Counter[int] = Counter()  # 설문 응답 예외에 관여한 유저
    for man in men:
        for woman in women:
            key = pair_key(man.id, woman.id)
            if key in excluded:
                continue
            try:
                if not pair_allowed(answers[man.id], answers[woman.id]):
                    continue
                score = pair_score(answers[man.id], answers[woman.id])
            except Exception:
                # 설문 응답은 저장 시 검증되지 않아 예외 종류를 열거할 수 없다.
                # 잘못된 값 한 건이 라운드 전체를 롤백시키지 않게 그 페어만 버린다.
                # 원인 유저는 자기가 낀 거의 모든 페어에서 실패해 아래 로그에 드러난다
                skipped[man.id] += 1
                skipped[woman.id] += 1
                continue
            base[key] = score
            bonus = (
                carryover_bonus(man)
                + carryover_bonus(woman)
                + university_bonus(man.university, woman.university, uni_singles, uni_pairs)
            )
            count = ojakgyo_counts.get(key, 0)
            if 0 < count < OJAKGYO_GUARANTEE_COUNT:
                bonus += OJAKGYO_BONUS * count
            # 0에서 바닥. 음수가 되면 pairing이 "둘 다 미매칭"을 더 낫다고 봐서
            # 설계에 없는 최소 점수 컷이 생긴다 (pairing.py의 _MATCH_BONUS 주석 참고)
            adjusted[key] = max(0.0, score + bonus)

    if skipped:
        logger.error(
            "설문 응답 오류로 건너뛴 페어 있음 — 유저별 실패 수 상위: %s",
            skipped.most_common(10),
        )

    # 하드필터를 통과한 페어만 보장 대상이다 — 절대질문이 보장을 이긴다
    guaranteed = resolve_guarantees(
        red={key for key in red if key in base},
        ojakgyo={
            key for key, count in ojakgyo_counts.items()
            if count >= OJAKGYO_GUARANTEE_COUNT and key in base
        },
        # 설계 §4.3의 tie-break 기준은 보정 전 궁합 점수다 — 이월·오작교 보너스는 안 쓴다
        score=base,
    )
    taken = {user_id for pair in guaranteed for user_id in pair}
    remaining = {
        key: value for key, value in adjusted.items()
        if key[0] not in taken and key[1] not in taken
    }

    male_ids = {user.id for user in men}
    pairs = guaranteed + optimal_pairs(remaining, male_ids)
    for a, b in pairs:
        # user_a = 남성, user_b = 여성 (설계 §6.1). 유니크 제약 2개는 이 축 고정 위에서만
        # "한 라운드 한 사람 한 번"을 보장한다 — id 대소로 정규화하면 사람이 축을 넘나들어 빠져나간다
        man_id, woman_id = (a, b) if a in male_ids else (b, a)
        db.add(Match(
            user_a_id=man_id, user_b_id=woman_id,
            match_round_id=round_.id,
            score=int(round(base[pair_key(a, b)])),
        ))

    matched_ids = {user_id for pair in pairs for user_id in pair}
    for user in pool:
        user.missed_rounds = 0 if user.id in matched_ids else user.missed_rounds + 1

    round_.status = RoundStatus.done
    round_.executed_at = datetime.utcnow()
    round_.last_error = None  # 성공했으니 옛 실패 사유를 지운다 (자동·수동 공통)
    return MatchingResult(
        matched=len(pairs),
        unmatched=len(pool) - len(matched_ids),
        guaranteed=len(guaranteed),
    )

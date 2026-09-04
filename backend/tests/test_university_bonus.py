from datetime import datetime, timedelta

from app.models.match import MatchingUniversityWeight, MatchRound
from app.models.survey import Survey
from app.models.user import Gender, User, UserStatus
from app.services.matching import (
    UNIVERSITY_BONUS_CAP,
    run_matching,
    university_bonus,
    university_pair_key,
    university_weights,
)
from app.services.scoring import pair_score
from tests.conftest import TestingSessionLocal

SNU = "서울대학교"
YONSEI = "연세대학교"
KOREA = "고려대학교"


def test_pair_key_is_order_free():
    assert university_pair_key(YONSEI, SNU) == university_pair_key(SNU, YONSEI)


def test_no_rules_gives_zero():
    assert university_bonus(SNU, YONSEI, {}, {}) == 0


def test_single_rule_on_one_side():
    assert university_bonus(SNU, YONSEI, {SNU: 30}, {}) == 30


def test_single_rules_on_both_sides_are_summed():
    assert university_bonus(SNU, YONSEI, {SNU: 30, YONSEI: 10}, {}) == 40


def test_same_university_counts_the_single_rule_once():
    """규칙 행 기준 합산 — 사람당 두 번이 아니다 (설계 §4.2, 2026-09-03 확정)."""
    assert university_bonus(SNU, SNU, {SNU: 30}, {}) == 30


def test_pair_rule_applies_regardless_of_order():
    pairs = {university_pair_key(SNU, YONSEI): 25}
    assert university_bonus(SNU, YONSEI, {}, pairs) == 25
    assert university_bonus(YONSEI, SNU, {}, pairs) == 25


def test_single_and_pair_rules_under_cap_are_summed():
    pairs = {university_pair_key(SNU, YONSEI): 5}
    assert university_bonus(SNU, YONSEI, {SNU: 10}, pairs) == 15


def test_single_and_pair_rules_are_summed_then_capped():
    """단일 30 + 쌍 25 = 55지만 상한 50에 걸린다."""
    pairs = {university_pair_key(SNU, YONSEI): 25}
    assert university_bonus(SNU, YONSEI, {SNU: 30}, pairs) == UNIVERSITY_BONUS_CAP


def test_sum_is_capped_at_plus_cap():
    """상한이 없으면 관리자 오타 하나가 매칭 전체를 망친다 (설계 §4.2)."""
    assert university_bonus(SNU, YONSEI, {SNU: 900, YONSEI: 900}, {}) == UNIVERSITY_BONUS_CAP


def test_sum_is_capped_at_minus_cap():
    assert university_bonus(SNU, YONSEI, {SNU: -900}, {}) == -UNIVERSITY_BONUS_CAP


def test_unrelated_universities_are_ignored():
    assert university_bonus(SNU, YONSEI, {KOREA: 30}, {}) == 0


def test_weights_lookup_skips_inactive_rows(setup_db):
    """active=false는 삭제 대신 끄기다 — 조회표에 들어오면 안 된다 (설계 §4.2)."""
    db = TestingSessionLocal()
    db.add(MatchingUniversityWeight(university_a=SNU, university_b="", bonus=30, active=False))
    db.add(MatchingUniversityWeight(university_a=YONSEI, university_b="", bonus=10, active=True))
    db.commit()

    singles, pairs = university_weights(db)

    assert singles == {YONSEI: 10}
    assert pairs == {}
    db.close()


def test_weights_lookup_normalizes_pair_keys(setup_db):
    """저장이 뒤집힌 순서로 들어와 있어도 조회 시 정규화된다."""
    db = TestingSessionLocal()
    db.add(MatchingUniversityWeight(university_a=YONSEI, university_b=SNU, bonus=25))
    db.commit()

    singles, pairs = university_weights(db)

    assert singles == {}
    assert pairs == {university_pair_key(SNU, YONSEI): 25}
    db.close()


def test_penalized_pair_still_matches(setup_db):
    """대학 페널티가 페어를 미매칭으로 떨어뜨리면 안 된다.

    설계에 최소 점수 컷은 없다 (2026-09-03 확정) — 페널티는 순위를 내리는
    수단이지 배제 수단이 아니다.
    """
    man_answers = {
        "responses": {"sleep_pref": "night", "sleep_self": "night"},
        "absolute": [],
    }
    woman_answers = {
        "responses": {"sleep_pref": "morning", "sleep_self": "night"},
        "absolute": [],
    }

    # 전제: 이 페어의 pair_score가 50 미만이어야 -50 페널티가 바닥(0)을 실제로 시험한다.
    # 이 값이 50 이상으로 바뀌면(카탈로그 변경 등) 아래 단언이 여기서 먼저 터진다.
    assert pair_score(man_answers, woman_answers) < 50

    db = TestingSessionLocal()
    for email, gender, answers in (
        ("m@test.com", Gender.male, man_answers),
        ("w@test.com", Gender.female, woman_answers),
    ):
        user = User(
            email=email, password_hash="x", name="테스트", university=SNU,
            gender=gender, status=UserStatus.active, kakao_id="kakao_default",
        )
        db.add(user)
        db.commit()
        db.add(Survey(user_id=user.id, answers=answers))
        db.commit()

    db.add(MatchingUniversityWeight(university_a=SNU, university_b="", bonus=-50, active=True))
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()
    round_id = round_.id

    result = run_matching(db, round_id)

    # 바닥이 없으면 adjusted < 0이 되어 pairing이 "둘 다 미매칭"을 고르고 matched == 0이 된다.
    assert result.matched == 1
    db.close()

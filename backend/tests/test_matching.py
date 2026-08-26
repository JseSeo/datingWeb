from datetime import datetime, timedelta
from unittest.mock import patch

from app.models.game import Ojakgyo, RedThread
from app.models.match import Match, MatchRound, RoundStatus
from app.models.survey import Survey
from app.models.user import Gender, User, UserStatus
from app.services import matching
from tests.conftest import TestingSessionLocal


def make_user(
    db,
    email: str,
    gender: Gender = Gender.male,
    responses: dict | None = None,
    absolute: list[str] | None = None,
    status: UserStatus = UserStatus.active,
    paused: bool = False,
    missed_rounds: int = 0,
    with_survey: bool = True,
    name: str = "테스트",
    university: str = "서울대학교",
) -> User:
    user = User(
        email=email, password_hash="x", name=name, university=university,
        gender=gender, status=status, matching_paused=paused,
        missed_rounds=missed_rounds,
    )
    db.add(user)
    db.commit()
    if with_survey:
        db.add(Survey(user_id=user.id, answers={
            "responses": responses or {}, "absolute": absolute or [],
        }))
        db.commit()
    db.refresh(user)
    return user


def make_round(db) -> MatchRound:
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()
    db.refresh(round_)
    return round_


def test_eligible_pool_requires_active_unpaused_and_survey():
    db = TestingSessionLocal()
    ok = make_user(db, "ok@test.com")
    make_user(db, "pending@test.com", status=UserStatus.pending)
    make_user(db, "paused@test.com", paused=True)
    make_user(db, "nosurvey@test.com", with_survey=False)

    assert [u.id for u in matching.eligible_users(db)] == [ok.id]
    db.close()


def test_past_pairs_are_collected_regardless_of_round():
    db = TestingSessionLocal()
    a = make_user(db, "a@test.com", Gender.male)
    b = make_user(db, "b@test.com", Gender.female)
    round_ = make_round(db)
    db.add(Match(user_a_id=b.id, user_b_id=a.id, match_round_id=round_.id, score=50))
    db.commit()

    assert matching.past_pairs(db) == {matching.pair_key(a.id, b.id)}
    db.close()


def test_carryover_bonus_is_capped():
    db = TestingSessionLocal()
    fresh = make_user(db, "fresh@test.com", missed_rounds=0)
    twice = make_user(db, "twice@test.com", missed_rounds=2)
    long_wait = make_user(db, "long@test.com", missed_rounds=10)

    assert matching.carryover_bonus(fresh) == 0
    assert matching.carryover_bonus(twice) == 30
    assert matching.carryover_bonus(long_wait) == 45  # 상한
    db.close()


def test_pair_key_is_order_independent():
    assert matching.pair_key(7, 3) == matching.pair_key(3, 7) == (3, 7)


def test_red_thread_needs_both_directions():
    db = TestingSessionLocal()
    a = make_user(db, "a@test.com", Gender.male, name="김남자", university="A대")
    b = make_user(db, "b@test.com", Gender.female, name="박여자", university="B대")
    db.add(RedThread(user_id=a.id, target_name="박여자", target_university="B대"))
    db.commit()

    pool = matching.eligible_users(db)
    red, _ = matching.game_signals(db, pool)
    assert red == set()  # 한쪽만 입력 → 상호 아님

    db.add(RedThread(user_id=b.id, target_name="김남자", target_university="A대"))
    db.commit()
    red, _ = matching.game_signals(db, matching.eligible_users(db))
    assert red == {matching.pair_key(a.id, b.id)}
    db.close()


def test_same_gender_red_thread_is_ignored():
    db = TestingSessionLocal()
    a = make_user(db, "a@test.com", Gender.male, name="김남자", university="A대")
    b = make_user(db, "b@test.com", Gender.male, name="이남자", university="B대")
    db.add_all([
        RedThread(user_id=a.id, target_name="이남자", target_university="B대"),
        RedThread(user_id=b.id, target_name="김남자", target_university="A대"),
    ])
    db.commit()

    red, _ = matching.game_signals(db, matching.eligible_users(db))
    assert red == set()  # 남녀 1:1 전제 (설계 §4.3)
    db.close()


def test_duplicate_name_and_university_is_ignored():
    """이름+학교가 유일하지 않으면 게임 효과를 적용하지 않는다 (설계 §4.4)."""
    db = TestingSessionLocal()
    a = make_user(db, "a@test.com", Gender.male, name="김남자", university="A대")
    make_user(db, "twin1@test.com", Gender.female, name="박여자", university="B대")
    twin2 = make_user(db, "twin2@test.com", Gender.female, name="박여자", university="B대")
    db.add_all([
        RedThread(user_id=a.id, target_name="박여자", target_university="B대"),
        RedThread(user_id=twin2.id, target_name="김남자", target_university="A대"),
    ])
    db.commit()

    red, _ = matching.game_signals(db, matching.eligible_users(db))
    assert red == set()
    db.close()


def test_ojakgyo_counts_recommenders():
    db = TestingSessionLocal()
    a = make_user(db, "a@test.com", Gender.male, name="김남자", university="A대")
    b = make_user(db, "b@test.com", Gender.female, name="박여자", university="B대")
    r1 = make_user(db, "r1@test.com", Gender.female, name="추천1", university="C대")
    r2 = make_user(db, "r2@test.com", Gender.male, name="추천2", university="C대")
    for recommender in (r1, r2):
        db.add(Ojakgyo(
            recommender_id=recommender.id,
            person_a_name="김남자", person_a_university="A대",
            person_b_name="박여자", person_b_university="B대",
        ))
    db.commit()

    _, counts = matching.game_signals(db, matching.eligible_users(db))
    assert counts == {matching.pair_key(a.id, b.id): 2}
    db.close()


def test_red_thread_wins_over_ojakgyo_when_a_user_is_in_both():
    """붉은실 상호 > 오작교 3인 (설계 §4.3)."""
    red = {(1, 2)}
    ojakgyo = {(1, 3)}
    score = {(1, 2): 40.0, (1, 3): 90.0}
    assert matching.resolve_guarantees(red, ojakgyo, score) == [(1, 2)]


def test_same_tier_conflict_prefers_higher_score():
    red = {(1, 2), (1, 3)}
    score = {(1, 2): 40.0, (1, 3): 90.0}
    assert matching.resolve_guarantees(red, set(), score) == [(1, 3)]


def test_same_tier_tie_prefers_smaller_user_id():
    red = {(1, 3), (1, 2)}
    score = {(1, 2): 50.0, (1, 3): 50.0}
    assert matching.resolve_guarantees(red, set(), score) == [(1, 2)]


def test_non_conflicting_guarantees_all_survive():
    red = {(1, 2)}
    ojakgyo = {(3, 4)}
    score = {(1, 2): 10.0, (3, 4): 10.0}
    assert matching.resolve_guarantees(red, ojakgyo, score) == [(1, 2), (3, 4)]


import pytest


NIGHT = {"sleep_self": "night", "sleep_pref": "night"}
MORNING = {"sleep_self": "morning", "sleep_pref": "morning"}


def test_run_matching_pairs_and_marks_round_done():
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    woman = make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.matched == 1
    assert result.unmatched == 0
    assert result.guaranteed == 0
    saved = db.query(Match).one()
    # user_a = 남성, user_b = 여성 (설계 §6.1)
    assert (saved.user_a_id, saved.user_b_id) == (man.id, woman.id)
    assert saved.score == 100
    db.refresh(round_)
    assert round_.status == RoundStatus.done
    assert round_.executed_at is not None
    db.close()


def test_match_stores_male_as_user_a_even_when_female_id_is_smaller():
    """저장 축은 성별로 고정된다 — id 대소로 되돌리면 이 테스트가 잡는다 (설계 §6.1)."""
    db = TestingSessionLocal()
    woman = make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    assert woman.id < man.id  # 전제 확인: 여성 id가 더 작다
    round_ = make_round(db)

    matching.run_matching(db, round_.id)

    saved = db.query(Match).one()
    assert (saved.user_a_id, saved.user_b_id) == (man.id, woman.id)
    db.close()


def test_absolute_question_removes_the_pair():
    db = TestingSessionLocal()
    make_user(db, "m@test.com", Gender.male,
              responses=NIGHT, absolute=["sleep_pref"])
    make_user(db, "w@test.com", Gender.female, responses=MORNING)
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.matched == 0
    assert result.unmatched == 2
    assert db.query(Match).count() == 0
    db.close()


def test_past_pair_is_never_rematched():
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    woman = make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    old = make_round(db)
    db.add(Match(user_a_id=man.id, user_b_id=woman.id,
                 match_round_id=old.id, score=100))
    old.status = RoundStatus.done
    db.commit()

    fresh = make_round(db)
    result = matching.run_matching(db, fresh.id)

    assert result.matched == 0
    assert db.query(Match).filter(Match.match_round_id == fresh.id).count() == 0
    db.close()


def test_missed_rounds_reset_and_increment():
    """이월 보너스는 그 사람이 낀 모든 페어에 더해져 최적 계산이 그 사람을 포함시키는
    쪽으로 기운다 (설계 §4.1). lonely(+15)가 woman(+0)보다 우선한다 — 궁합은 동점(100)이다.
    """
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT, missed_rounds=2)
    woman = make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    lonely = make_user(db, "l@test.com", Gender.female, responses=NIGHT, missed_rounds=1)
    round_ = make_round(db)

    matching.run_matching(db, round_.id)

    db.refresh(man), db.refresh(woman), db.refresh(lonely)
    assert man.missed_rounds == 0
    assert lonely.missed_rounds == 0
    assert woman.missed_rounds == 1  # 풀에 있었지만 못 붙었다
    db.close()


def test_paused_user_missed_rounds_untouched():
    """풀에 없는 유저는 우선순위를 쌓지 못한다 (설계 §4.1)."""
    db = TestingSessionLocal()
    paused = make_user(db, "p@test.com", Gender.female,
                       responses=NIGHT, paused=True, missed_rounds=1)
    make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    round_ = make_round(db)

    matching.run_matching(db, round_.id)

    db.refresh(paused)
    assert paused.missed_rounds == 1
    db.close()


def test_carryover_bonus_cannot_override_compatibility():
    """이월 보너스는 순위를 밀어줄 뿐 궁합을 뒤집지 못한다 — 상한의 목적 (설계 §4.1)."""
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    good = make_user(db, "good@test.com", Gender.female, responses=NIGHT)
    waiting = make_user(db, "wait@test.com", Gender.female,
                        responses=MORNING, missed_rounds=3)
    round_ = make_round(db)

    matching.run_matching(db, round_.id)

    partner = db.query(Match).one()
    # 궁합만 보면 good(100점)이지만 waiting은 45점 보너스 → 0 + 45 > 100? 아니다.
    # 보너스가 궁합을 뒤집지 못하는 것이 상한의 목적이다
    assert waiting.id not in (partner.user_a_id, partner.user_b_id)
    assert good.id in (partner.user_a_id, partner.user_b_id)
    assert man.id in (partner.user_a_id, partner.user_b_id)
    db.close()


def test_red_thread_guarantees_the_pair():
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=MORNING,
                    name="김남자", university="A대")
    fated = make_user(db, "f@test.com", Gender.female, responses=MORNING,
                      name="박여자", university="B대")
    better = make_user(db, "b@test.com", Gender.female, responses=MORNING,
                       name="최여자", university="C대")
    db.add_all([
        RedThread(user_id=man.id, target_name="박여자", target_university="B대"),
        RedThread(user_id=fated.id, target_name="김남자", target_university="A대"),
    ])
    db.commit()
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.guaranteed == 1
    saved = db.query(Match).one()
    assert saved.user_a_id in (man.id, fated.id)
    assert saved.user_b_id in (man.id, fated.id)
    assert better.id not in (saved.user_a_id, saved.user_b_id)
    db.close()


def test_absolute_question_beats_a_guarantee():
    """절대질문이 보장을 이긴다 (설계 §4.3)."""
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT,
                    absolute=["sleep_pref"], name="김남자", university="A대")
    fated = make_user(db, "f@test.com", Gender.female, responses=MORNING,
                      name="박여자", university="B대")
    db.add_all([
        RedThread(user_id=man.id, target_name="박여자", target_university="B대"),
        RedThread(user_id=fated.id, target_name="김남자", target_university="A대"),
    ])
    db.commit()
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.guaranteed == 0
    assert db.query(Match).count() == 0
    db.close()


def test_uneven_gender_counts_leave_people_unmatched():
    db = TestingSessionLocal()
    make_user(db, "m1@test.com", Gender.male, responses=NIGHT)
    make_user(db, "m2@test.com", Gender.male, responses=NIGHT)
    make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.matched == 1
    assert result.unmatched == 1
    db.close()


def test_second_run_returns_conflict():
    db = TestingSessionLocal()
    make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    round_ = make_round(db)

    matching.run_matching(db, round_.id)
    with pytest.raises(matching.RoundNotPending):
        matching.run_matching(db, round_.id)
    db.close()


def test_mid_pipeline_failure_rolls_back_round_to_pending():
    """중간 실패는 전부 롤백되고 라운드는 pending으로 돌아간다 (설계 §5.5)."""
    db = TestingSessionLocal()
    make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    round_ = make_round(db)

    with patch("app.services.matching.optimal_pairs", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            matching.run_matching(db, round_.id)

    db.refresh(round_)
    assert round_.status == RoundStatus.pending
    assert db.query(Match).count() == 0
    db.close()


def test_missing_round_raises():
    db = TestingSessionLocal()
    with pytest.raises(matching.RoundNotFound):
        matching.run_matching(db, 9999)
    db.close()


def test_same_input_produces_same_result():
    """결정론성 (설계 §5.2). 같은 풀을 두 라운드에 넣어도 짝이 같아야 한다."""
    db = TestingSessionLocal()
    for i in range(3):
        make_user(db, f"m{i}@test.com", Gender.male, responses=NIGHT)
        make_user(db, f"w{i}@test.com", Gender.female, responses=NIGHT)
    first = make_round(db)
    matching.run_matching(db, first.id)
    pairs_first = sorted(
        (m.user_a_id, m.user_b_id)
        for m in db.query(Match).filter(Match.match_round_id == first.id).all()
    )
    db.query(Match).delete()
    db.commit()

    second = make_round(db)
    matching.run_matching(db, second.id)
    pairs_second = sorted(
        (m.user_a_id, m.user_b_id)
        for m in db.query(Match).filter(Match.match_round_id == second.id).all()
    )
    assert pairs_first == pairs_second
    db.close()


# ── C1 최소 봉합: 검증되지 않은 설문 응답 ──────────────────

BROKEN_ORDINAL = {"politics_pref": ["progressive"], "politics_self": "moderate"}


def test_broken_answer_skips_only_that_pair_not_the_round(caplog):
    """설문 응답 예외 한 건이 라운드 전체를 롤백시키지 않는다 (C1)."""
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    woman = make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    broken = make_user(db, "b@test.com", Gender.female,
                       responses=NIGHT, absolute=[7])
    round_ = make_round(db)

    with caplog.at_level("ERROR"):
        result = matching.run_matching(db, round_.id)

    assert result.matched == 1
    saved = db.query(Match).one()
    assert (saved.user_a_id, saved.user_b_id) == (man.id, woman.id)
    db.refresh(round_)
    assert round_.status == RoundStatus.done
    db.refresh(broken)
    assert broken.missed_rounds == 1  # 매칭 안 됐으니 이월은 쌓인다
    # 원인 유저는 실패 횟수로 로그에 드러난다
    assert any(str(broken.id) in record.getMessage() for record in caplog.records)
    db.close()


def test_ordinal_pref_given_a_list_does_not_crash_the_round():
    """`politics_pref`에 리스트 → `_ordinal`의 `order.get`이 TypeError (C1)."""
    db = TestingSessionLocal()
    make_user(db, "m@test.com", Gender.male, responses=BROKEN_ORDINAL)
    make_user(db, "w@test.com", Gender.female,
              responses={**NIGHT, "politics_self": "moderate"})
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.matched == 0
    db.refresh(round_)
    assert round_.status == RoundStatus.done
    db.close()

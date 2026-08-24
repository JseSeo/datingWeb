from datetime import datetime, timedelta

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

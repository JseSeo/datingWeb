from datetime import datetime, timedelta

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

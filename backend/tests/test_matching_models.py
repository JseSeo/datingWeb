from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.match import Match, MatchRound, RoundStatus
from app.models.user import Gender, User, UserStatus
from tests.conftest import TestingSessionLocal


def _user(db, email: str, gender: Gender = Gender.male) -> User:
    user = User(
        email=email, password_hash="x", name="테스트",
        university="서울대학교", gender=gender, status=UserStatus.active,
    )
    db.add(user)
    db.commit()
    return user


def test_missed_rounds_defaults_to_zero():
    db = TestingSessionLocal()
    user = _user(db, "carry@test.com")
    assert user.missed_rounds == 0
    db.close()


def test_round_status_has_running():
    assert RoundStatus.running.value == "running"


def test_match_stores_score():
    db = TestingSessionLocal()
    a = _user(db, "a@test.com", Gender.male)
    b = _user(db, "b@test.com", Gender.female)
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()

    db.add(Match(user_a_id=a.id, user_b_id=b.id, match_round_id=round_.id, score=72))
    db.commit()
    assert db.query(Match).one().score == 72
    db.close()


def test_same_user_cannot_match_twice_in_one_round():
    """한 라운드에서 한 사람이 두 번 짝지어지는 사고를 DB가 막는다 (설계 §6.1)."""
    db = TestingSessionLocal()
    a = _user(db, "a@test.com", Gender.male)
    b = _user(db, "b@test.com", Gender.female)
    c = _user(db, "c@test.com", Gender.female)
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()

    db.add(Match(user_a_id=a.id, user_b_id=b.id, match_round_id=round_.id, score=50))
    db.commit()
    db.add(Match(user_a_id=a.id, user_b_id=c.id, match_round_id=round_.id, score=50))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_same_woman_cannot_match_twice_in_one_round():
    """user_b 축(여성)도 DB가 막는다. user_a 축만 덮던 갭을 메운다 (설계 §6.1)."""
    db = TestingSessionLocal()
    a = _user(db, "a@test.com", Gender.male)
    b = _user(db, "b@test.com", Gender.male)
    c = _user(db, "c@test.com", Gender.female)
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()

    db.add(Match(user_a_id=a.id, user_b_id=c.id, match_round_id=round_.id, score=50))
    db.commit()
    db.add(Match(user_a_id=b.id, user_b_id=c.id, match_round_id=round_.id, score=50))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()

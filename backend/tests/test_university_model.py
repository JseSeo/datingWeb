import pytest
from sqlalchemy.exc import IntegrityError

from tests.conftest import TestingSessionLocal
from app.models.university import University
from app.models.game import Ojakgyo, RedThread
from app.models.user import User


def test_name_is_unique():
    db = TestingSessionLocal()
    db.add(University(name="한양대학교"))
    db.commit()
    db.add(University(name="한양대학교"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_active_defaults_true():
    db = TestingSessionLocal()
    uni = University(name="한양대학교")
    db.add(uni)
    db.commit()
    assert uni.active is True
    db.close()


def test_user_admission_year_is_optional():
    """모르는 사람이 있어 선택 입력이다 (설계 §4.2)."""
    db = TestingSessionLocal()
    user = User(
        email="noyear@test.com", password_hash="x", name="김노학번",
        university="서울대학교", gender="female",
    )
    db.add(user)
    db.commit()
    assert user.admission_year is None
    db.close()


def _recommender(db) -> int:
    """지목 행의 recommender_id가 가리킬 유저. SQLite는 기본적으로 FK를 강제하지
    않지만, 실재하는 id를 쓰는 편이 테스트 의도가 분명하다."""
    user = User(
        email="rec@test.com", password_hash="x", name="지목자",
        university="서울대학교", gender="male",
    )
    db.add(user)
    db.commit()
    return user.id


def test_ojakgyo_same_pair_with_different_admission_year_is_allowed():
    """동명이인 두 명을 각각 지목할 수 있어야 한다 (설계 §4.2)."""
    db = TestingSessionLocal()
    common = dict(
        recommender_id=_recommender(db),
        person_a_name="김철수", person_a_university="서울대학교",
        person_b_name="이영희", person_b_university="연세대학교",
        person_b_admission_year=0,
    )
    db.add(Ojakgyo(person_a_admission_year=2021, **common))
    db.add(Ojakgyo(person_a_admission_year=2022, **common))
    db.commit()
    assert db.query(Ojakgyo).count() == 2
    db.close()


def test_ojakgyo_identical_rows_still_conflict():
    """학번까지 같으면 여전히 중복이다 — 0 센티넬이 NULL이었다면 이게 통과해버린다."""
    db = TestingSessionLocal()
    common = dict(
        recommender_id=_recommender(db),
        person_a_name="김철수", person_a_university="서울대학교", person_a_admission_year=0,
        person_b_name="이영희", person_b_university="연세대학교", person_b_admission_year=0,
    )
    db.add(Ojakgyo(**common))
    db.commit()
    db.add(Ojakgyo(**common))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_red_thread_same_target_different_year_is_allowed():
    db = TestingSessionLocal()
    user_id = _recommender(db)
    db.add(RedThread(user_id=user_id, target_name="박민수", target_university="고려대학교", target_admission_year=2020))
    db.add(RedThread(user_id=user_id, target_name="박민수", target_university="고려대학교", target_admission_year=2023))
    db.commit()
    assert db.query(RedThread).count() == 2
    db.close()

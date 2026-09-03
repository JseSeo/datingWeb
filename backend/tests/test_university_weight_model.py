import pytest
from sqlalchemy.exc import IntegrityError

from app.models.match import MatchingUniversityWeight
from tests.conftest import TestingSessionLocal


def _add(db, a: str, b: str = "", bonus: int = 10) -> MatchingUniversityWeight:
    weight = MatchingUniversityWeight(university_a=a, university_b=b, bonus=bonus)
    db.add(weight)
    db.commit()
    return weight


def test_defaults(setup_db):
    """단일 규칙은 university_b가 빈 문자열, active는 켜진 상태로 저장된다."""
    db = TestingSessionLocal()
    weight = _add(db, "서울대학교")
    assert weight.university_b == ""
    assert weight.active is True
    assert weight.note is None
    db.close()


def test_duplicate_single_rule_is_rejected(setup_db):
    """같은 대학에 단일 규칙이 두 번 들어가면 합산돼 의도치 않게 커진다 (설계 §4.2)."""
    db = TestingSessionLocal()
    _add(db, "서울대학교")
    with pytest.raises(IntegrityError):
        _add(db, "서울대학교")
    db.rollback()
    db.close()


def test_duplicate_pair_rule_is_rejected(setup_db):
    db = TestingSessionLocal()
    _add(db, "서울대학교", "연세대학교")
    with pytest.raises(IntegrityError):
        _add(db, "서울대학교", "연세대학교")
    db.rollback()
    db.close()


def test_single_and_pair_rules_coexist(setup_db):
    """단일 (A, '') 과 쌍 (A, B) 는 서로 다른 규칙이다."""
    db = TestingSessionLocal()
    _add(db, "서울대학교")
    _add(db, "서울대학교", "연세대학교")
    assert db.query(MatchingUniversityWeight).count() == 2
    db.close()


def test_negative_bonus_is_allowed(setup_db):
    """음수는 페널티다 (설계 §4.2)."""
    db = TestingSessionLocal()
    weight = _add(db, "서울대학교", bonus=-20)
    assert weight.bonus == -20
    db.close()

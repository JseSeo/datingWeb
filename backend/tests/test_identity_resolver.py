from tests.conftest import TestingSessionLocal
from app.models.user import User
from app.services.matching import _identity_resolver

SNU = "서울대학교"


def _add(db, email, name, university=SNU, admission_year=None):
    user = User(
        email=email, password_hash="x", name=name, university=university,
        gender="female", admission_year=admission_year, kakao_id="k",
    )
    db.add(user)
    db.commit()
    return user


def test_single_candidate_without_year():
    db = TestingSessionLocal()
    user = _add(db, "solo@test.com", "김유일")
    assert _identity_resolver(db)("김유일", SNU) == user.id
    db.close()


def test_namesakes_resolved_by_year():
    """학번의 존재 이유 (설계 §6.2)."""
    db = TestingSessionLocal()
    a = _add(db, "n1@test.com", "김동명", admission_year=2021)
    _add(db, "n2@test.com", "김동명", admission_year=2022)
    assert _identity_resolver(db)("김동명", SNU, 2021) == a.id
    db.close()


def test_namesakes_without_year_are_ignored():
    db = TestingSessionLocal()
    _add(db, "n1@test.com", "김동명", admission_year=2021)
    _add(db, "n2@test.com", "김동명", admission_year=2022)
    assert _identity_resolver(db)("김동명", SNU) is None
    db.close()


def test_namesakes_with_same_year_are_ignored():
    db = TestingSessionLocal()
    _add(db, "n1@test.com", "김동명", admission_year=2021)
    _add(db, "n2@test.com", "김동명", admission_year=2021)
    assert _identity_resolver(db)("김동명", SNU, 2021) is None
    db.close()


def test_single_candidate_with_mismatched_year_still_resolves():
    """학번을 안 적었으면 성공했을 지목이 적었다는 이유로 실패하면 안 된다 (설계 §6.3)."""
    db = TestingSessionLocal()
    user = _add(db, "solo@test.com", "김유일", admission_year=2020)
    assert _identity_resolver(db)("김유일", SNU, 2019) == user.id
    db.close()


def test_year_does_not_exclude_unregistered_candidates():
    """대상이 학번을 안 넣었다는 이유로 지목이 사라지면 안 된다 (설계 §6.1)."""
    db = TestingSessionLocal()
    user = _add(db, "solo@test.com", "김유일", admission_year=None)
    assert _identity_resolver(db)("김유일", SNU, 2021) == user.id
    db.close()


def test_different_university_is_not_a_candidate():
    db = TestingSessionLocal()
    _add(db, "y@test.com", "김동명", university="연세대학교")
    assert _identity_resolver(db)("김동명", SNU) is None
    db.close()

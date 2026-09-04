import pytest

from tests.conftest import TestingSessionLocal
from app.models.university import University
from app.services.universities import (
    UnknownUniversity,
    known_names,
    require_known,
)


def _seed(**kwargs):
    db = TestingSessionLocal()
    db.add(University(**kwargs))
    db.commit()
    db.close()


def test_known_names_returns_active_only():
    _seed(name="활성대학교", active=True)
    _seed(name="비활성대학교", active=False)
    db = TestingSessionLocal()
    names = known_names(db)
    db.close()
    assert "활성대학교" in names
    assert "비활성대학교" not in names


def test_require_known_passes_for_active():
    _seed(name="활성대학교")
    db = TestingSessionLocal()
    require_known(db, "활성대학교")  # 예외 없이 통과
    db.close()


def test_require_known_rejects_inactive():
    """비활성 대학은 신규 입력에 못 쓴다 (설계 §5.3)."""
    _seed(name="비활성대학교", active=False)
    db = TestingSessionLocal()
    with pytest.raises(UnknownUniversity) as exc:
        require_known(db, "비활성대학교")
    db.close()
    assert exc.value.name == "비활성대학교"


def test_require_known_rejects_unlisted():
    db = TestingSessionLocal()
    with pytest.raises(UnknownUniversity):
        require_known(db, "없는대학교")
    db.close()


def test_require_known_checks_every_name():
    _seed(name="활성대학교")
    db = TestingSessionLocal()
    with pytest.raises(UnknownUniversity) as exc:
        require_known(db, "활성대학교", "없는대학교")
    db.close()
    assert exc.value.name == "없는대학교"

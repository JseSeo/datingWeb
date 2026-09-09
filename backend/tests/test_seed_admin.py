import pytest

from app.config import settings
from app.core.security import verify_password
from app.models.user import User, UserStatus
from app.seed_admin import MESSAGES, main, seed_admin
from tests.conftest import TestingSessionLocal


def test_creates_admin_when_absent():
    db = TestingSessionLocal()
    try:
        result = seed_admin(db, "admin@admin.com", "seedpass123")

        user = db.query(User).filter(User.email == "admin@admin.com").one()
        assert result == "created"
        assert user.is_admin is True
        assert user.status == UserStatus.active
        assert verify_password("seedpass123", user.password_hash)
    finally:
        db.close()


def test_second_run_leaves_existing_account_untouched():
    db = TestingSessionLocal()
    try:
        seed_admin(db, "admin@admin.com", "seedpass123")
        before = db.query(User).filter(User.email == "admin@admin.com").one().password_hash

        result = seed_admin(db, "admin@admin.com", "differentpass456")

        user = db.query(User).filter(User.email == "admin@admin.com").one()
        assert result == "unchanged"
        assert user.password_hash == before
    finally:
        db.close()


def test_force_resets_password_and_restores_admin_access():
    db = TestingSessionLocal()
    try:
        seed_admin(db, "admin@admin.com", "seedpass123")
        user = db.query(User).filter(User.email == "admin@admin.com").one()
        user.is_admin = False
        user.status = UserStatus.suspended
        db.commit()

        result = seed_admin(db, "admin@admin.com", "newpass456", force=True)

        db.refresh(user)
        assert result == "updated"
        assert verify_password("newpass456", user.password_hash)
        assert user.is_admin is True
        assert user.status == UserStatus.active
    finally:
        db.close()


def test_main_exits_when_env_vars_missing(monkeypatch, capsys):
    monkeypatch.setattr(settings, "admin_email", None)
    monkeypatch.setattr(settings, "admin_password", None)

    with pytest.raises(SystemExit) as exc:
        main([])

    assert exc.value.code == 1
    assert "ADMIN_EMAIL" in capsys.readouterr().err


def test_output_survives_windows_console_encoding():
    """윈도우 기본 콘솔은 cp949다. 여기서 못 쓰는 문자를 넣으면 시드가 DB 작업을
    마친 뒤 print에서 UnicodeEncodeError로 죽어 성공을 실패처럼 보이게 한다."""
    for message in MESSAGES.values():
        message.encode("cp949")

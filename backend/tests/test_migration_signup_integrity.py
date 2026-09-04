import pathlib
import tempfile

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.database import Base
import app.models  # noqa: F401  — 모든 모델을 메타데이터에 등록시킨다

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _config(url: str) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_then_downgrade_runs_clean():
    with tempfile.TemporaryDirectory() as tmp:
        url = f"sqlite:///{tmp}/mig.db"
        cfg = _config(url)
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")


def test_migrations_match_models():
    """모델↔마이그레이션 드리프트 0. 하나라도 어긋나면 diff가 비지 않는다."""
    with tempfile.TemporaryDirectory() as tmp:
        url = f"sqlite:///{tmp}/mig.db"
        command.upgrade(_config(url), "head")
        engine = create_engine(url)
        with engine.connect() as conn:
            diff = compare_metadata(
                MigrationContext.configure(conn), Base.metadata
            )
        engine.dispose()
        assert diff == [], diff

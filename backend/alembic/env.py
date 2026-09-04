from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.config import settings
import app.models  # noqa: F401 — registers all models
from app.database import Base

config = context.config
# alembic.ini의 sqlalchemy.url은 플레이스홀더. 호출자가 이미 실제 url을 넣어뒀으면
# (테스트에서 임시 sqlite로 격리하는 경우 등) 그대로 두고, 아니면 설정값으로 채운다.
if config.get_main_option("sqlalchemy.url") in (None, "driver://user:pass@localhost/dbname"):
    config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

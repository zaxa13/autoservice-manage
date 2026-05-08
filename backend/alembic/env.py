"""Alembic environment для tenant-app в shared-DB архитектуре.

Подключение:
    settings.DATABASE_URL_MIGRATOR — sync-URL под ролью migrator_app
    (BYPASSRLS), через pgbouncer session-pool.

Метаданные приложения живут в схеме `app` (Base.metadata.schema='app'),
поэтому версии Alembic тоже храним в этой же схеме — иначе платформенный
и тенант-приложения боролись бы за `public.alembic_version`.
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Добавляем путь к приложению.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings  # noqa: E402
from app.models._base import Base  # noqa: E402  напрямую, чтобы не тащить async engine
from app.models import *  # noqa: F401,F403,E402  гарантируем регистрацию всех моделей в metadata

config = context.config

# % экранируем — пароли могут содержать %-encoded символы.
config.set_main_option(
    "sqlalchemy.url", settings.DATABASE_URL_MIGRATOR.replace("%", "%%")
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _configure_context(connection_or_url, *, is_url: bool = False) -> None:
    kwargs = dict(
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="app",
        # Явно сравниваем server_default и type-changes — иначе автогенерация
        # будет молчаливо игнорировать дрифт.
        compare_server_default=True,
        compare_type=True,
    )
    if is_url:
        context.configure(
            url=connection_or_url,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            **kwargs,
        )
    else:
        context.configure(connection=connection_or_url, **kwargs)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    _configure_context(url, is_url=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _configure_context(connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

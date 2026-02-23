from __future__ import annotations

import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# allow imports when running alembic from repo root
ROOT = Path(__file__).resolve().parents[1].parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.db import Base  # noqa: E402
from app import models  # noqa: F401,E402

target_metadata = Base.metadata


def get_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        url = (config.get_main_option("sqlalchemy.url") or "").strip()
    return url


def run_migrations_offline() -> None:
    url = get_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set and sqlalchemy.url is missing")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set and sqlalchemy.url is missing")

    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
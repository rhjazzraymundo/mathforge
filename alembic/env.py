"""Alembic environment configuration.

Key customisation vs the stock template:
  * Loads DATABASE_URL from ``.env`` via python-dotenv.
  * Imports ``db.models.Base`` so autogenerate can diff against our ORM.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# ── Make our project packages importable ──────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# ── Alembic Config object ────────────────────────────────────────
config = context.config

# Override the placeholder URL in alembic.ini with the real one.
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL", ""),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Target metadata for autogenerate support ─────────────────────
from db.models import Base          # noqa: E402 (must come after sys.path fix)
target_metadata = Base.metadata


# ── Migration runners ────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL without a live connection."""
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
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


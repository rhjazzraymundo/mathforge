"""Shared test fixtures for MathForge.

Provides:
  SEED_COUNT  — number of random seeds for generator tests (Phase 1)
  db_session  — in-memory SQLite session with all tables (Phase 2+)
  default_user — the anonymous MVP user inside that session
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Phase 1 — generator tests
# ---------------------------------------------------------------------------

# 20 seeds × 5 difficulties = 100 combos per generator — good coverage
# without making the suite slow.
SEED_COUNT = 20

# ---------------------------------------------------------------------------
# Phase 2+ — database tests
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database for each test.

    All ORM tables are created via ``Base.metadata.create_all`` so we
    don't need Docker or Alembic for the test suite.
    """
    from db.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def default_user(db_session):
    """Insert and return the anonymous default user."""
    from db.models import User
    from db.repositories import DEFAULT_USER_ID

    user = User(id=DEFAULT_USER_ID)
    db_session.add(user)
    db_session.commit()
    return user

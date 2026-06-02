"""
Database session factory with lazy initialisation.

Engine and session factory are NOT created at import time — they are
created on first use. This keeps unit tests that import domain/service
modules isolated from Postgres without requiring mocking.
"""

from __future__ import annotations

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        import os

        # Read DATABASE_URL from the environment at engine-creation time so that
        # test fixtures can override it after module import. The Settings object is
        # frozen and only reads env vars once at instantiation, so re-reading the
        # raw env var here allows runtime overrides (e.g. testcontainers fixtures).
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            from apollo.config import settings

            db_url = settings.database_url
        _engine = create_engine(db_url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the lazily-initialised session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=_get_engine())
    return _SessionFactory

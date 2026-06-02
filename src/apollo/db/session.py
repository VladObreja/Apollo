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
        # Import deferred so tests can patch settings before the engine is built.
        from apollo.config import settings

        _engine = create_engine(settings.database_url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the lazily-initialised session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=_get_engine())
    return _SessionFactory

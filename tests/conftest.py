"""
Pytest configuration for the Apollo test suite.

Adds `src/` to sys.path so all unit tests can import `apollo.*`
without requiring the package to be installed in the test environment.
"""

import sys
from pathlib import Path

# Make `src/apollo` importable without `pip install -e .`
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from apollo.db import session as sess_mod
from tests.factories import CorpusRecordFactory


@pytest.fixture(scope="session")
def postgres_container():
    """Spin up a real Postgres container for the test suite."""
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_engine(postgres_container):
    """Create engine + run all Alembic migrations against the container."""
    db_url = postgres_container.get_connection_url()
    engine = create_engine(db_url)

    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "src/apollo/db/alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Provide a clean-slate session per test using DELETE (for cross-connection visibility)."""
    from sqlalchemy import text

    SessionFactory = sessionmaker(bind=db_engine)
    with SessionFactory() as session:
        session.execute(text("DELETE FROM corpus_record"))
        session.commit()

        # Bind the session to factory_boy so tests can use it automatically
        CorpusRecordFactory._meta.sqlalchemy_session = session

        yield session
        session.rollback()


@pytest.fixture()
def patched_db_url(postgres_container, monkeypatch):
    """Patch the app's settings so worker.tick() connects to the test container."""
    db_url = postgres_container.get_connection_url()
    monkeypatch.setenv("DATABASE_URL", db_url)

    sess_mod._engine = None
    sess_mod._SessionFactory = None

    yield db_url

    sess_mod._engine = None
    sess_mod._SessionFactory = None

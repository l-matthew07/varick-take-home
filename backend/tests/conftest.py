"""Session-scoped PostgreSQL container shared by all tests."""

import os

# Must be set before any app module is imported — database.py reads it at module level.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://placeholder/placeholder")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

import app.core.database as _db_module
from app.core.database import Base, get_db
from app.main import app

_PG_IMAGE = "postgres:16-alpine"


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer(_PG_IMAGE) as container:
        yield container


@pytest.fixture(scope="session")
def pg_engine(pg_container):
    url = pg_container.get_connection_url()
    url = url.replace("postgresql+psycopg2://", "postgresql+psycopg://")
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def pg_session_factory(pg_engine):
    return sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def _reset_db(pg_engine, pg_session_factory):
    """Point the app's module-level engine to the container, wire get_db, wipe rows between tests."""
    # Patch the module-level engine so on_startup/init_db connects to the container.
    _db_module.engine = pg_engine

    def override_get_db():
        db = pg_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)

    with pg_engine.connect() as conn:
        conn.execute(text(
            "TRUNCATE ticket_history, tickets, routing_rules, users, teams RESTART IDENTITY CASCADE"
        ))
        conn.commit()

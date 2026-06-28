"""Integration test fixtures.

Tests run against a dedicated `farm_local_test` database (same creds as dev, different
db name). The test DB URL is injected via the DATABASE_URL env var *before* the app is
imported — env vars take precedence over the .env file in pydantic-settings, so the global
engine in app.database binds to the test database.
"""

import os

TEST_DATABASE_URL = "postgresql+psycopg://azeek:0889@localhost:5432/farm_local_test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, delete  # noqa: E402

from app.animals.models import Animal  # noqa: E402  (registers the table on metadata)
from app.database import _PROJECT_ROOT, engine  # noqa: E402
from app.main import app  # noqa: E402


def _alembic_config() -> Config:
    cfg = Config(str(_PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "migrations"))
    return cfg


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Iterator[None]:
    # Build the test schema through migrations (same path as prod), so the
    # app lifespan's `alembic upgrade head` is a no-op rather than a conflict.
    cfg = _alembic_config()
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")
    engine.dispose()


@pytest.fixture
def db_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Clean slate before every test for deterministic counts/listings.
    with Session(engine) as session:
        session.exec(delete(Animal))
        session.commit()
    with TestClient(app) as c:
        yield c


def make_animal(**overrides) -> dict:
    """Build a valid AnimalCreate payload, with field overrides."""
    payload = {
        "type": "cattle",
        "tag": "UK000001",
        "name": "Bessie",
        "breed": "Angus",
        "gender": "female",
        "date_of_birth": "2022-01-01",
        "status": "active",
    }
    payload.update(overrides)
    return payload

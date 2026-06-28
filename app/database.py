from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, create_engine

from app.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def init_db() -> None:
    """Bring the database schema up to date by running Alembic migrations."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(_PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "migrations"))
    command.upgrade(cfg, "head")


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    with Session(engine) as session:
        yield session

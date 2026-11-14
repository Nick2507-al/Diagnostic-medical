"""Database engine and session factory (SQLAlchemy 2, psycopg 3)."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,  # survive Postgres restarts / idle disconnects
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

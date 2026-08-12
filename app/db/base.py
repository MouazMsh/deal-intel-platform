"""SQLAlchemy 2.0 async engine/session setup.

The ORM layer is deliberately restricted to the intersection of SQLite and
PostgreSQL feature sets (no native Postgres ENUM types, no dialect-specific
tricks) so that swapping ``DATABASE_URL`` from a local SQLite file to a Neon
Postgres URL is a configuration change, not a rewrite. Foreign keys are
explicitly enabled for SQLite, which does not enforce them by default.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, event
from sqlalchemy.engine import Dialect, Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """A DateTime that always round-trips as UTC-aware, on every backend.

    SQLite has no native timestamp-with-timezone type: SQLAlchemy's
    ``DateTime(timezone=True)`` writes an aware datetime's string form, but
    reads it back *naive* -- tzinfo is silently lost. Comparing that naive
    result against a fresh ``datetime.now(timezone.utc)`` elsewhere in the
    app then raises ``TypeError: can't compare offset-naive and
    offset-aware datetimes`` (this was caught by real test execution against
    SQLite, not by inspection -- Postgres/Neon would not have hit it, since
    asyncpg returns properly aware datetimes for ``timestamptz`` columns).

    This type normalizes on both sides of that gap:
    - **write**: any incoming datetime is converted to UTC and made aware
      (a naive input is *assumed* to already be UTC, per the app-wide
      convention that naive datetimes are always UTC -- see
      ``core/timezone.py``).
    - **read**: if the underlying DBAPI hands back a naive datetime (SQLite),
      UTC tzinfo is reattached -- safe, because the write side guarantees
      whatever was stored numerically *is* UTC already. If the backend
      already returns an aware datetime (Postgres/asyncpg), it's used as-is.

    Every model in ``db/models/`` uses this instead of bare
    ``sa.DateTime(timezone=True)`` for exactly this reason.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    pass


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection: object, connection_record: object) -> None:
    """SQLite does not enforce FKs unless told to, per connection."""
    if type(dbapi_connection).__module__.startswith("sqlite3") or type(
        dbapi_connection
    ).__module__.startswith("aiosqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    return create_async_engine(database_url, echo=echo, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)

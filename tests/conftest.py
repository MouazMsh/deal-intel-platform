from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.base import Base, create_engine, create_session_factory
import app.db.models  # noqa: F401  (populate Base.metadata)


def make_settings(**overrides: object) -> Settings:
    """Build a Settings instance for tests without touching the real .env
    or the process-wide get_settings() cache.
    """
    defaults: dict[str, object] = {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "DRY_RUN": True,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        yield session

    await engine.dispose()

import os
import tempfile
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.db.session import get_session
from app.main import app
from app.models.plan import Plan


@pytest_asyncio.fixture(name="session")
async def session_fixture() -> AsyncIterator[AsyncSession]:
    """Creates a clean SQLite database for each test (async)."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Import models before create_all so metadata contains tables
    from app import models  # noqa: F401
    from app.db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with SessionLocal() as session:
        session.add(Plan(name="FREE", request_limit=2, is_active=True))
        await session.commit()
        yield session

    await engine.dispose()
    os.remove(db_path)


@pytest_asyncio.fixture()
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Override dependency get_session so app uses the test DB."""

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()

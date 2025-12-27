from datetime import date
import asyncio
import os
import tempfile

import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    async_sessionmaker, 
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.models.api_key import APIKey
from app.models.user import User
from app.models.usage import Usage
from app.services import usage_service


async def _create_test_db_sessionmaker():
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

    from app.db.base import Base
    from app import models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    return engine, db_path, SessionLocal


@pytest.mark.asyncio
async def test_increment_usage_is_atomic_under_concurrency(monkeypatch: pytest.MonkeyPatch):
    today = date.today()
    monkeypatch.setattr(usage_service, "utc_today", lambda: today)

    engine, db_path, SessionLocal = await _create_test_db_sessionmaker()

    try:
        async with SessionLocal() as seed:
            user = User(email="race@example.com", hashed_password="pass123")
            seed.add(user)
            await seed.commit()
            await seed.refresh(user)

            api_key = APIKey(user_id=user.id)
            seed.add(api_key)
            await seed.commit()
            await seed.refresh(api_key)

            key_id = api_key.id

        async with SessionLocal() as s1, SessionLocal() as s2:
            await asyncio.gather(
                usage_service.increment_usage(s1, api_key_id=key_id),
                usage_service.increment_usage(s2, api_key_id=key_id),
            )

        async with SessionLocal() as verify:
            result = await verify.execute(
                select(Usage.request_count).where(
                    Usage.api_key_id == key_id,
                    Usage.day == today,
                )
            )
            assert result.scalar_one() == 2
    finally:
        await engine.dispose()
        os.remove(db_path)

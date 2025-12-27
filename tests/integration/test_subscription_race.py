import asyncio
import os
import tempfile

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services import subscription_service


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

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, db_path, SessionLocal


@pytest.mark.asyncio
async def test_ensure_active_subscription_is_safe_under_concurrency():
    engine, db_path, SessionLocal = await _create_test_db_sessionmaker()

    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX ux_subscriptions_user_active
                    ON subscriptions(user_id)
                    WHERE is_active = 1;
                    """
                )
            )

        async with SessionLocal() as seed:
            seed.add(Plan(name="FREE", request_limit=100, is_active=True))
            user = User(email="sub-race@example.com", hashed_password="pass123")
            seed.add(user)
            await seed.commit()
            await seed.refresh(user)
            user_id = user.id

        async with SessionLocal() as s1, SessionLocal() as s2:
            sub1, sub2 = await asyncio.gather(
                subscription_service.ensure_active_subscription(s1, user_id=user_id),
                subscription_service.ensure_active_subscription(s2, user_id=user_id),
            )

        async with SessionLocal() as verify:
            result = await verify.execute(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.is_active == True,
                )
            )
            active_subs = list(result.scalars())
            assert len(active_subs) == 1

        assert sub1.user_id == user_id
        assert sub2.user_id == user_id
        assert sub1.id == sub2.id
    finally:
        await engine.dispose()
        os.remove(db_path)

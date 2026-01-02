import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.v1 import (
    admin_plans_router,
    api_keys_router,
    auth_router,
    data_router,
    plans_router,
)
from app.core.logging import setup_logging
from app.tasks.usage_cleanup import start_usage_cleanup_loop

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    usage_cleanup_task = asyncio.create_task(
        start_usage_cleanup_loop(),
        name="usage-cleanup-loop",
    )
    try:
        yield
    finally:
        usage_cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await usage_cleanup_task


app = FastAPI(title="Subscription API", version="0.1.0", lifespan=lifespan)


app.include_router(auth_router, prefix="/api/v1")
app.include_router(api_keys_router, prefix="/api/v1")
app.include_router(data_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(admin_plans_router, prefix="/api/v1")


@app.get("/", tags=["root"])
async def root() -> dict:
    return {
        "message": "Subscription API is running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["health"])
async def healthcheck() -> dict:
    return {"status": "ok"}

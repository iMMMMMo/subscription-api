from fastapi import FastAPI

app = FastAPI(
    title="Subscription API",
    version="0.1.0",
)


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

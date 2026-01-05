# Subscription-based API

Asynchronous REST API that demonstrates **subscription-style access control** for protected endpoints.

Users authenticate with JWT to manage API keys, and clients call protected endpoints using `X-API-Key`. Each request is tracked per day and enforced against the user’s active plan limit.

This project is designed to demonstrate backend engineering practices, focusing on architecture, correctness (including concurrency), and testability rather than UI or payments.

## Key Features

- Async API (FastAPI + async SQLAlchemy)
- JWT authentication (access + refresh tokens) for user actions
- API key (`X-API-Key`) authentication for protected endpoints
- Subscription plans with per-day request limits
- Plan listing (public) and subscription switching (upgrades/downgrades)
- Lazy subscription creation on first API key
- Per-day usage tracking with atomic increments + limit enforcement
- Admin (superuser) endpoints for managing plans
- Concurrency safety via DB constraints + `IntegrityError` fallbacks
- Background job for cleaning up old usage data
- CI checks with ruff + pytest (GitHub Actions)

## High-level Architecture

### Authentication vs API Access

This API has two separate ways to authenticate:

- **JWT (Bearer token)** for user actions (login, creating/revoking API keys, admin endpoints)
- **API key (`X-API-Key`)** for calling protected API endpoints

Token lifetimes (current defaults):

- Access token: 15 minutes
- Refresh token: 7 days

API keys are managed using JWT, but they are used separately for API access.

### Access Control Flow

```
Client → API Key → User → Active Subscription → Plan → Request Limit
```

For every protected request:

1. API key is validated
2. Owning user is resolved
3. Active subscription is retrieved
4. Daily usage counter is incremented (atomically)
5. Usage is compared with the plan request limit
6. Request is accepted or rejected (401/403/429 depending on the case)

### Core Domain Models

- **User** - account + role (regular user or admin)
- **Plan** - request limit settings (e.g. FREE, PRO)
- **Subscription** - assigns a plan to a user (only one active at a time)
- **APIKey** - credential for protected endpoints
- **Usage** - per-day request counter per API key

### Subscription Lifecycle (Lazy Initialization)

A subscription is **not created during registration**.

It is created automatically when the user generates their **first API key** (that's when API access starts to matter).

## Notable Design Decisions

- A partial unique index (PostgreSQL) enforces one active subscription per user.
- Concurrency edge cases are handled in `ensure_active_subscription()` and `increment_usage()`.
- Daily usage windows are UTC-based (the "day" boundary comes from `app.core.time.utc_today`).
- Old usage rows are cleaned up by a background task started in the app `lifespan`.

## Project Architecture

Directory structure (simplified):

```
subscription-api/
├── app/
│   ├── api/            # routers and dependencies (guards)
│   ├── core/           # configuration, security, logging, time
│   ├── db/             # engine/session + Base
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic (request/response)
│   ├── services/       # business logic
│   └── tasks/          # background jobs (cleanup)
├── alembic/            # migrations
└── tests/              # integration and unit tests
```

The project uses a simple separation of responsibilities:

- **Routers**: input/output validation, HTTP codes, dependency injection
- **Services**: domain logic (subscriptions, usage, keys)
- **Models**: database schema and constraints

## Technology Stack

| Category | Technology |
|-----------|-----------|
| **Python** | 3.10+ |
| **Package manager** | Poetry |
| **Framework** | FastAPI (async) |
| **Database** | PostgreSQL |
| **ORM** | SQLAlchemy (async) |
| **Migrations** | Alembic |
| **Auth** | JWT |
| **Deployment** | Docker & Docker Compose |
| **CI** | GitHub Actions |
| **Lint/format** | ruff |
| **Tests** | pytest-asyncio |

## Testing Strategy

Tests are asynchronous (`pytest-asyncio`) and use `httpx.AsyncClient`.

### Unit Tests

- Service-layer logic (API keys, usage counting, guards)
- Dependencies are mocked explicitly
- No HTTP and no real database required (sessions are mocked)

### Integration Tests

- Most tests run the full request flow using FastAPI + SQLite (async)
- Covers:
  - Auth (register / login / refresh / me)
  - API key creation (revocation is covered in unit tests)
  - Request limits
  - Subscription switching (upgrade/downgrade)
  - Admin-only plan management

- Additional correctness checks under concurrency:
  - ensuring a single active subscription under parallel requests (service-level)
  - atomic per-day usage counting under parallel requests (service-level)
- Daily usage reset behavior across days

SQLite is used for speed and isolation; PostgreSQL is used in production.

## Running the project

### Requirements

- Docker + Docker Compose (recommended)
- Python 3.10+ + Poetry (for local setup)

### Option 1: Docker Compose (recommended)

1. Copy `.env.docker.example` to `.env.docker` and fill in your own values
2. Run:

```bash
docker compose up --build
```

The container starts with automatic migrations (`alembic upgrade head`).

### Option 2: Local (without Docker)

1. Install dependencies (Poetry):

```bash
poetry install
```

2. Copy `.env.example` to `.env` and fill in your own values
3. Run migrations:

```bash
poetry run alembic upgrade head
```

4. Start the server:

```bash
poetry run uvicorn app.main:app --reload
```

### Local URLs

- `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/health`

## Creating an admin (superuser)

Admin endpoints (plan CRUD) require a user with `is_superuser=true`.

Instead of exposing a REST endpoint to create admins, this project provides an **idempotent** script that can be run after migrations.

Local:

```bash
poetry run python -m app.scripts.create_superuser \
  --email admin@example.com \
  --password pass123 \
  --full-name "Admin"
```

Docker Compose:

```bash
docker compose exec api poetry run python -m app.scripts.create_superuser \
  --email admin@example.com \
  --password pass123
```

Notes:

- Safe to re-run: if the user exists, it promotes them to superuser.
- For an existing user, the script will not overwrite the password unless you pass `--update-password`.
- Safety guard: the script refuses to run when `APP_ENV` is `prod`, `production` or `staging` unless you pass `--allow-prod`.
- The script also supports env vars: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_FULL_NAME`.

## Configuration (environment variables)

Environment variables are loaded via `pydantic-settings`.

- For local runs: copy `.env.example` to `.env`
- For Docker Compose: copy `.env.docker.example` to `.env.docker`

Required variables:

- `DATABASE_URL` - async SQLAlchemy URL (e.g. `postgresql+asyncpg://...`)
- `SECRET_KEY` - key used to sign JWT tokens (make it long and random)

Optional variables:

- `APP_ENV` - environment label (e.g. `local`, `docker`)
- `DEFAULT_PLAN_NAME` - plan assigned automatically when the first API key is created (default: `FREE`)

Important:

- `DEFAULT_PLAN_NAME` must refer to an **existing active plan** in the database. By default, migrations seed `FREE` (100 requests/day).

Docker-only (Postgres container):

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

## Endpoints

Base prefix: `/api/v1`

### Auth (`/auth`, Bearer)

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`

### API Keys (`/api-keys`, Bearer)

- `POST /api-keys`
- `GET /api-keys`
- `DELETE /api-keys/{key_id}`

### Protected (`/data`, X-API-Key)

- `GET /data`

### Plans (`/plans`, public)

- `GET /plans`

### Subscriptions (`/subscriptions`, Bearer)

- `POST /subscriptions/switch`

### Admin (`/admin/plans`, Bearer + is_superuser)

- `POST /admin/plans`
- `GET /admin/plans`
- `PATCH /admin/plans/{plan_id}`

### Other

- `GET /`
- `GET /health`

## Example usage (curl)

Assumes the API is running on `http://localhost:8000`.

### Register and login

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123","full_name":"Test User"}'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}'
```

### Get current user

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Create an API key

```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Call a protected endpoint

```bash
curl http://localhost:8000/api/v1/data \
  -H "X-API-Key: <API_KEY>"
```

### Switch subscription plan

Assumes the target plan exists and is active (e.g. created via admin endpoints).

```bash
curl -X POST http://localhost:8000/api/v1/subscriptions/switch \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"plan_name":"PRO"}'
```

## Migrations

- Migrations live in `alembic/versions/` and can be applied with `alembic upgrade head`.
- On Docker startup, migrations are executed automatically.
- The default `FREE` plan is seeded if it does not exist.

## Code quality

```bash
poetry run ruff check .
poetry run ruff format .
```

## Tests

```bash
poetry run pytest
```

## What I learned

- Moving from a synchronous API to an async stack (FastAPI + async SQLAlchemy sessions)
- Designing two separate auth layers: user authentication (JWT) vs API access (API keys)
- Implementing per-day usage tracking and daily request limits per API key
- Handling race conditions with database constraints (partial unique index) and `IntegrityError` fallbacks
- Running background jobs using the FastAPI `lifespan` hook (usage cleanup)
- Setting up a simple CI pipeline (ruff + pytest on GitHub Actions)

## License

MIT

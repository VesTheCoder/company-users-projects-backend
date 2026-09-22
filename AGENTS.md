# AGENTS.md

## Project overview

Company Management API is a FastAPI REST API for authenticated company management. It is a feature-oriented modular monolith with Onion-style boundaries, backed by PostgreSQL and Redis.

The repository contains the backend only. There is no frontend application in this repository, and the documented 10,000,000-user target describes long-term account cardinality rather than 10,000,000 concurrent users. The local Compose deployment is a single API instance intended for development, smoke tests, and measurements.

### Runtime and tooling

- Python: CPython 3.13.12, pinned in `.python-version`
- Dependency manager: `uv`, with the committed `uv.lock` as the source of reproducibility
- API: FastAPI and Uvicorn
- Database: PostgreSQL 18.6, accessed asynchronously through SQLAlchemy 2 and asyncpg
- Migrations: Alembic
- Distributed rate limiting: Redis 8.10.2
- Password hashing: Argon2id through `argon2-cffi`
- Quality: Ruff
- Tests: pytest, pytest-asyncio, HTTPX, Polyfactory, and Testcontainers
- Load tests: k6 scripts under `load/k6`

## Existing repository guardrails

- Keep Docker and Docker Compose configuration minimal.
- Do not add fallback defaults or required-variable guards in Compose; developer-managed environment files are expected to provide valid values.
- Keep startup ordering that is required for services and migrations to run correctly.
- Keep runtime and migration/bootstrap database credentials separated; never pass privileged database credentials to the API container.
- Keep `Settings` limited to loading and typing environment values. Assume developer-managed environment values are valid; do not add configuration validators or normalizers.

## Repository map

- `app/main.py` is the application factory and composition root. Uvicorn loads `app.main:create_app` with `--factory`.
- `app/auth/` contains users, database-backed sessions, login/logout, password handling, CSRF, and account operations.
- `app/companies/` contains companies, company membership, role authorization, and ownership transfer.
- `app/employees/` contains tenant-scoped employee records and employment rules.
- `app/projects/` contains tenant-scoped projects, status transitions, and employee assignments.
- `app/handlers/` contains shared FastAPI dependencies, middleware, error mapping, OpenAPI customization, and operational endpoints.
- `app/infrastructure/` contains PostgreSQL/Redis adapters, ORM base and mixins, metrics, logging, rate limiting, and the concrete Unit of Work.
- `app/utils/` contains small reusable pure helpers such as cursor pagination, normalization, security, and version handling.
- `migrations/` contains the Alembic environment and ordered schema revisions. All schema changes must be delivered through Alembic.
- `scripts/` contains operational commands, demo seeding, OpenAPI export, benchmark data generation, and query-plan tooling.
- `tests/unit/`, `tests/api/`, `tests/integration/`, `tests/concurrency/`, and `tests/smoke/` contain tests grouped by scope.
- `docs/openapi.json` is generated from the application factory and checked by CI.
- `docs/performance.md` and `docs/benchmarks/` contain measured performance evidence and benchmark artifacts.
- `Dockerfile`, `docker-compose.yaml`, and `docker/postgres/init/` define the containerized development deployment.

## Setup and development workflow

Run commands from the repository root in PowerShell.

### Local Python environment

Create the environment only if `.venv` does not exist, then activate it before running project commands:

```powershell
uv venv --python 3.13.12
.\.venv\Scripts\Activate.ps1
uv sync --frozen --all-groups
if (-not (Test-Path .env)) { uv run python -m scripts.setup_local_env }
```

`.env` is ignored by Git. Use `.env.sample` as the development template and replace sample credentials before using any non-local environment. Pydantic settings load `.env`; JSON-valued list settings such as `CORS_ALLOWED_ORIGINS` and `TRUSTED_HOSTS` must remain valid JSON.

The preferred local workflow is Docker Compose because it supplies the required PostgreSQL and Redis services and runs migrations before the API:

```powershell
docker compose up -d --build --wait
docker compose exec api python -m scripts.seed_demo
```

The API is available at `http://localhost:8080`, and the interactive OpenAPI UI is at `http://localhost:8080/docs` when `DOCS_ENABLED=true`. Follow API logs with `docker compose logs -f api`; stop the stack without deleting its named volumes with `docker compose down`.

To run Uvicorn outside Docker, PostgreSQL and Redis must already be reachable using the values in `.env`:

```powershell
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8080
```

### Database migrations

The Compose `migrate` service runs `alembic upgrade head` with the migration database credentials. The API container uses the runtime database role and does not run migrations implicitly during application startup.

For a configured local database:

```powershell
uv run alembic upgrade head
uv run alembic check
```

When changing the schema, add a new ordered revision, review the generated SQL and constraints, and verify it against a fresh database and an already migrated database. Do not add `Base.metadata.create_all()` or other startup schema creation. Keep migrations compatible with the tenant-leading indexes, composite foreign keys, and role constraints already present in the schema.

Downgrade/re-upgrade commands are for disposable development or test databases only:

```powershell
uv run alembic downgrade -1
uv run alembic upgrade head
```

## API and domain conventions

### Authentication and authorization

- Authentication uses opaque database-backed session cookies, not JWTs.
- `Principal` in `app/handlers/dependencies.py` authenticates every business endpoint and also applies the general rate limit.
- Login requires the configured Origin and `X-CSRF-Protection: 1`. Successful login sets an HttpOnly cookie and returns a CSRF token.
- Unsafe authenticated requests (`POST`, `PUT`, `PATCH`, and `DELETE`) require a valid Origin/Referer contract and `X-CSRF-Token`.
- With `COOKIE_SECURE=false`, the development cookie is `session`; secure deployments use the `__Host-session` cookie name.
- Company roles are `owner`, `admin`, and `viewer`. Viewers are read-only. Admins and owners can perform normal company mutations. Company access administration, ownership transfer, and company deletion are owner-only.
- There is exactly one owner per company. Ownership transfer requires an existing non-owner member and must preserve the ownership invariant.
- Application accounts and employee records are separate concepts. An employee is not an authentication account merely because it has a work email.

### Resource and HTTP contracts

All resource routes are under `/api/v1` and require authentication, including reads.

| Area | Main routes |
|---|---|
| Auth | `/api/v1/auth/login`, `/logout`, `/me`, `/csrf` |
| Companies | `/api/v1/companies` and `/{company_id}` |
| Company access | `/{company_id}/access`, `/{company_id}/access/{user_id}`, and `/{company_id}/ownership-transfer` |
| Employees | `/api/v1/companies/{company_id}/employees` and `/{employee_id}` |
| Projects | `/api/v1/companies/{company_id}/projects` and `/{project_id}` |
| Assignments | `/{project_id}/employees` and `/{project_id}/employees/{employee_id}` |
| Operations | `/health/live`, `/health/ready`, and `/metrics` |

Use cursor pagination for collection endpoints. `limit` is bounded from 1 to 100; cursors are signed and scope-bound. Do not replace this with offset pagination or mandatory `COUNT(*)` queries for tenant lists.

Mutable companies, employees, and projects use optimistic versioning. Preserve `ETag` responses and `If-Match` handling when changing these resources. Assignment creation is an idempotent `PUT`; ordinary resource updates use `PATCH`.

Domain rules that must remain enforced in the service/domain layer include:

- Employee termination removes active project assignments in the same transaction.
- Completed and cancelled projects retain existing assignments but do not accept new assignments.
- Project transitions are `planned -> active|cancelled` and `active -> completed|cancelled`; terminal states are terminal, and repeating the same state is idempotent.
- Company, employee, and project deletion is physical deletion in v1.

## Architecture rules for changes

Keep the existing feature-oriented Onion boundaries:

- `domain.py` contains feature invariants and domain errors without FastAPI, SQLAlchemy, or Redis imports.
- `schemas.py` defines the HTTP wire contract through Pydantic models.
- `handlers.py` translates HTTP requests into service calls, selects status codes, and should not contain SQL or business rules.
- `services.py` contains use cases, authorization decisions, orchestration, and transaction intent; it should not depend on HTTP objects.
- `repositories.py` contains feature-specific SQL, tenant scoping, eager loading, and locking. Do not introduce a generic repository.
- `app/infrastructure/unit_of_work.py` owns the concrete `SqlAlchemyUnitOfWork`. A use case gets one `AsyncSession`; commit, rollback, and close remain explicit at this boundary.
- Pass database sessions and other dependencies explicitly. Do not create global sessions or hide database access in business logic.
- Tenant queries must scope by `company_id` and preserve the existing cross-company safety constraints.
- Keep API processes stateless: durable sessions live in PostgreSQL and rate-limit state lives in Redis.
- Do not add a worker, queue, application cache, SSO, public registration, or frontend unless the scope is explicitly expanded.

Follow the repository/workspace coding rules: write code and docstrings in English, do not add inline code comments, keep functions focused and small, prefer existing utilities, and avoid speculative abstractions. Do not log passwords, session credentials, CSRF tokens, or other secrets.

## Verification commands

Activate `.venv` before these commands. The full suite uses Testcontainers and therefore requires Docker Desktop.

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Useful focused runs:

```powershell
uv run pytest -q tests/unit
uv run pytest -q tests/api
uv run pytest -q tests/integration
uv run pytest -q tests/concurrency
uv run pytest -q tests/unit/test_pagination.py
```

API, integration, concurrency, and smoke tests commonly need Docker-managed PostgreSQL and Redis. After the Compose stack is up and the demo data is seeded, run the container smoke tests with:

```powershell
uv run pytest -q tests/smoke
```

When API routes or schemas change, regenerate and verify the checked-in OpenAPI document:

```powershell
if (-not (Test-Path .env)) { uv run python -m scripts.setup_local_env }
uv run python -m scripts.export_openapi
git diff --exit-code -- docs/openapi.json
```

The CI workflow in `.github/workflows/ci.yaml` runs the Ruff checks, the full pytest suite, OpenAPI drift verification, a Compose build/start, demo seeding, and smoke tests. Reproduce the same checks before submitting a substantial change.

## Operational scripts

Run scripts with `uv run python -m ...` after activating `.venv`.

- `scripts.setup_local_env`: creates `.env` from `.env.sample` only when `.env` is absent.
- `scripts.seed_demo`: idempotently seeds the development demo dataset. It refuses to run unless `APP_ENV=development` and `ALLOW_DEMO_SEED=true`.
- `scripts.provision_account --login ... --display-name ...`: provisions an account and prompts for a password. Use `--password-stdin` only with a secure input pipeline; never put passwords in command arguments.
- `scripts.reset_password --user-id <uuid>`: resets a password and revokes sessions.
- `scripts.set_account_status --user-id <uuid> --status activate|deactivate`: changes account status and applies session revocation rules.
- `scripts.cleanup_sessions [--batch-size 1000]`: removes expired or revoked sessions after the retention window.
- `scripts.export_openapi`: writes `docs/openapi.json`.
- `scripts.generate_load_data --profile small|functional|cardinality`: loads benchmark data into a fresh development database and writes ignored credentials under `.local/`. The `cardinality` profile is not a casual local test.
- `scripts.explain_queries`: writes PostgreSQL query plans to `docs/benchmarks/query-plans.json`.
- `scripts.summarize_benchmarks`: regenerates benchmark summary Markdown from benchmark JSON files.

## Load and performance measurements

Use a fresh migrated development database for each load-data profile. The generator intentionally refuses to load over existing benchmark IDs and does not truncate a database. Keep generated credentials in ignored `.local/` files.

```powershell
.\.venv\Scripts\Activate.ps1
uv run python -m scripts.generate_load_data --profile small
uv run python -m scripts.explain_queries
.\load\run-local.ps1 -DurationSeconds 30
uv run python -m scripts.summarize_benchmarks
```

The k6 runner uses the pinned image digest in `load/run-local.ps1`. The benchmark scripts distinguish iteration rate from HTTP request rate and record dropped iterations and failures. Treat `docs/performance.md` as local measurement evidence, not a production capacity guarantee.

## Security and configuration guardrails

- Keep `.env` local and never commit secrets. Update `.env.sample` only with safe sample values.
- Replace all sample passwords and signing keys before any shared or production-like deployment.
- Keep `COOKIE_SECURE=true` behind HTTPS and configure trusted hosts and CORS explicitly.
- Keep demo seeding disabled outside development.
- Keep metrics disabled or protected with `METRICS_BEARER_TOKEN_FILE` when the metrics endpoint is exposed.
- Do not bypass CSRF, authentication, authorization, rate limiting, optimistic concurrency, or tenant scoping to make a test pass.
- Do not treat UUIDs as authorization secrets.

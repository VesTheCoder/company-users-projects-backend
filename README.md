# Company Management API

Async FastAPI modular monolith for companies, independent employee records, projects and employee assignments. PostgreSQL enforces tenant relationships; PostgreSQL sessions and Redis rate limits support stateless API replicas. Backend scope and contracts are defined in [implementation-plan.md](implementation-plan.md).

## Run with Docker

Requires Docker Compose. Python 3.13.12 with uv is needed only for local tooling. Commands below use PowerShell.

Create `.env` from `.env.sample` and fill in the credentials before starting the containers. The API is intended to run through Docker Compose; its database and Redis endpoints use the Compose service names from `.env`.

```powershell
docker compose up -d --build
docker compose exec api python -m scripts.seed_demo
Invoke-RestMethod http://localhost:8080/health/ready
```

The environment setup command `uv run python -m scripts.setup_local_env` can generate `.env` with random local credentials and refuses to overwrite an existing file. `.env.sample` is the placeholder template, following the repository coding rules. No working credentials are committed.

The seeder asks for a password of 12–1024 characters using hidden input. Demo logins are `owner@demo.example`, `admin@demo.example`, `viewer@demo.example`, and `outsider@demo.example`. The chosen password applies to all four. Re-running the seed resets the known demo dataset and revokes demo sessions. It requires `APP_ENV=development` and `ALLOW_DEMO_SEED=true`.

- API: http://localhost:8080/api/v1
- Swagger: http://localhost:8080/docs
- OpenAPI: [docs/openapi.json](docs/openapi.json)
- Health: `/health/live`, `/health/ready`
- Metrics: `/metrics`

Compose waits for PostgreSQL and Redis health, applies Alembic migrations once, then starts the API. PostgreSQL and Redis use named volumes. The bootstrap shell script creates runtime/migration roles only on an empty PostgreSQL volume. Changing role passwords in `.env` does not update an existing database; use an operator-controlled `ALTER ROLE` for existing volumes.

## Tooling and tests

```powershell
. .venv/Scripts/Activate.ps1
uv sync --frozen --all-groups
docker compose up -d --build
```

The API and migrations run in Compose containers. The checked-in runtime pin, CI and Docker all use Python 3.13.12. Dependency versions are recorded in `uv.lock`; upgrades are explicit.

```powershell
. .venv/Scripts/Activate.ps1
uv run ruff check .
uv run ruff format --check .
uv run alembic check
uv run pytest -q
uv run python -m scripts.export_openapi
```

Integration/API/concurrency tests start disposable PostgreSQL 18.6 and Redis 8.10.2 containers through Testcontainers. They never use SQLite or modify the Compose database. Docker must be running. The live Docker smoke test is opt-in: set `SMOKE_PASSWORD` to the demo password and run `uv run pytest -q tests/smoke`. Without that variable it is skipped. Migration tests exercise every revision, downgrade/re-upgrade and metadata alignment in an isolated test schema.

## Browser API contract

All business reads and writes require a session. Login is `POST /api/v1/auth/login` with JSON `{"login":"owner@demo.example","password":"your chosen password"}`, a trusted `Origin` and `X-CSRF-Protection: 1`. Login returns a fresh HttpOnly session cookie, `csrf_token`, user and absolute eight-hour expiry.

Use `credentials: "include"` for every browser fetch. Unsafe requests also require `X-CSRF-Token` from login and a trusted Origin (Referer origin is accepted if Origin is absent). Store CSRF only in memory; restore it after reload through `GET /api/v1/auth/csrf`. Logout revokes the current session and clears the cookie. Password reset and deactivation revoke all sessions.

Local frontend origin `http://localhost:5173` is allowed explicitly. CORS preflight is public. Errors use `application/problem+json` with a stable code and request ID; CORS preflight rejection is the documented Starlette exception. Unknown/inaccessible tenant resources return 404; insufficient role within an accessible company returns 403.

Companies, employees and projects support create/list/read/patch/delete. A create returns 201, Location and ETag. PATCH/DELETE require `If-Match: "v1"`; missing tags return 428, stale tags 412. PATCH distinguishes omitted fields from explicit null and rejects unknown fields. Lists use signed cursor pagination: `limit=25` by default, maximum 100, `{items,next_cursor}` without total counts. Cursors are bound to resource, tenant, actor where applicable and filters.

| Operation | Owner | Admin | Viewer |
|---|---|---|---|
| Read business records | Yes | Yes | Yes |
| Edit company; employee/project/assignment CRUD | Yes | Yes | No |
| List/change access; ownership transfer; company delete | Yes | No | No |

Any active account can create a company and becomes its owner. Access grants accept existing active account UUIDs; no public account directory or registration exists. Employee records have no account relationship. Ownership transfer requires an existing admin/viewer and preserves exactly one owner. Account deactivation is blocked while it owns any company.

Project transitions: planned → active/cancelled; active → completed/cancelled. Terminal projects retain existing assignments and reject new ones. Repeating the current status is allowed. Assignment PUT returns 201 when added, 200 when already present; DELETE returns 204 after tenant validation even when absent. Only active employees can be newly assigned. Termination removes assignments atomically. Deletes physically cascade.

## Operations

```powershell
docker compose exec api python -m scripts.provision_account --login user@example.com --display-name "User Name"
docker compose exec api python -m scripts.reset_password --user-id <uuid>
docker compose exec api python -m scripts.set_account_status --user-id <uuid> --status deactivate
docker compose exec api python -m scripts.set_account_status --user-id <uuid> --status activate
docker compose exec api python -m scripts.cleanup_sessions --batch-size 1000
docker compose run --rm migrate
docker compose logs --tail 100 api
docker compose stop api
```

Password commands support `--password-stdin`; passwords are never command-line arguments. Restrict shell/container/database access to operators. Schedule cleanup externally, for example hourly; expired/revoked sessions are retained for 24 hours and removed in short batches. There is no background worker in v1.

Runtime database credentials have DML permissions only. Migration credentials are provided only to the migration service. Alembic is the only schema manager. Back up before deploying migrations; future schema changes should use expand/backfill/contract and forward fixes. Initial downgrades destroy data and are intended only for disposable test databases.

## Production and capacity

Compose is a local demonstration deployment. Production requires verified PostgreSQL TLS (`DB_SSLMODE=verify-full`), secure cookies, exact public HTTPS origins and trusted hosts, managed secrets and a reverse proxy that strips client forwarding headers. Publish frontend and `/api` under one HTTPS origin. Unrelated-site cookie deployment is unsupported. Set `DOCS_ENABLED=false` and `METRICS_ENABLED=false` on public ingress; protected metrics require `METRICS_BEARER_TOKEN_FILE` and a Bearer token.

Override the API command behind the proxy to include `--proxy-headers --forwarded-allow-ips <exact-proxy-CIDRs>`. Local Compose explicitly disables proxy-header trust and keeps PostgreSQL and Redis internal to the Compose network. Production should use private endpoints, Redis authentication/TLS and network restrictions.

Each API process has a 10-connection pool plus 5 overflow, 5-second checkout/statement timeouts and a 2-second lock timeout. Four replicas plus two operational connections use at most 62 of the 80-connection application budget. More replicas require smaller pools or measured adoption of PgBouncer. Writes within one company serialize through a company row lock to preserve access and lifecycle invariants; hot write-heavy tenants are a known scaling limit.

Redis enforces login IP 20/10min, login account 10/15min, authenticated 300/min and expensive lists 60/min. Keys use HMAC and expose no raw account/IP values. Redis failure returns 503, never an in-memory fallback. Metrics use route templates and exclude account/tenant labels. Logs allow only selected structured fields and never include request bodies, cookies or database URLs.

The 10-million-user figure is an account-cardinality target, not a measured concurrency guarantee. See [docs/performance.md](docs/performance.md) for reproducible load profiles, query plans and measured local limits. Frontend implementation remains the next separate stage.

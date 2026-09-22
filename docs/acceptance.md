# Backend acceptance evidence

Validated on Windows with CPython 3.13.12 and Linux Docker containers. The implementation follows the feature modules and concrete Unit of Work in the supplied plan; no SQLite, generic repository, public account directory, application cache or worker was added.

| Contract | Evidence |
|---|---|
| Reproducible environment | `uv.lock`, Python pin, frozen Docker install, Ruff checks |
| Schema and relationships | Three Alembic revisions; empty-schema upgrades, downgrade/re-upgrade, `alembic check`; PostgreSQL composite FK rejection test |
| Unit of Work | Explicit commit, rollback and close tests; shared session identity; actual rollback test |
| Authentication | Argon2id profile, generic login failures, fresh cookies, CSRF, logout/reset/deactivation revocation, two application instances sharing one session |
| Authorization | Owner/admin/viewer matrix, access revoke, hidden tenant records, owner deactivation invariant |
| Business API | Company/employee/project CRUD, field validation, status transitions, idempotent assignments, termination cleanup |
| Concurrent operations | Duplicate assignment, assignment/termination, competing ownership transfers, access revocation versus waiting mutation, stale ETags |
| Rate limits | Real Redis, exact concurrent admission across two adapters, HMAC keys and dependency-outage distinction |
| Lists | Signed scope-bound cursors, deleted-anchor independence, fixed query count across page sizes, indexed shallow/deep SQL plans |
| Operations | Readiness degradation, metrics template labels, log allowlist, session retention, protected account scripts |
| Seed | Repeated runs converge, production guard, employees remain independent of accounts |
| Container | Port 8080, UID 10001, read-only filesystem, DML-only runtime role, repeated migration, live login/CRUD/logout smoke, graceful stop exit 0 |
| Performance | Functional dataset and recorded local k6 scenarios; limitations and failing latency thresholds are reported in `performance.md` |

The template is `.env.sample`, as required by the supplied coding rules, rather than the plan's `.env.example`. Direct `email-validator` was added for the explicit email-like login/work-email contract. The employee increment includes the entire third migration so an already applied revision did not need to be rewritten when project behavior was added.

CI configuration is included. Local checks were executed; a remote GitHub Actions run is not claimed. Frontend work and a production-scale 10-million-account deployment remain outside this backend implementation.

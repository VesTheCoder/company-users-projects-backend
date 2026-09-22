import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from app.config import Settings
from app.infrastructure.database import create_engine
from app.utils.security import hash_token
from scripts.load_dataset import load_id, session_material


async def explain():
    settings = Settings()
    engine = create_engine(settings, migration=True)
    tenant, user = load_id(2, 0), load_id(1, 0)
    params = {
        "tenant": tenant,
        "user": user,
        "project": load_id(4, 0),
        "anchor": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=10000),
        "id": load_id(3, 10000),
        "token": hash_token(
            session_material(settings.cursor_signing_key.get_secret_value(), 0)[0]
        ),
    }
    queries = {
        "session": (
            "SELECT s.id, u.id FROM auth_sessions s JOIN users u ON "
            "u.id=s.user_id WHERE s.token_hash=:token AND s.revoked_at IS "
            "NULL AND s.expires_at>now() AND u.is_active"
        ),
        "companies": (
            "SELECT c.id,c.name,a.role FROM company_access a JOIN companies "
            "c ON c.id=a.company_id WHERE a.user_id=:user ORDER BY "
            "a.created_at DESC,a.company_id DESC LIMIT 26"
        ),
        "access": (
            "SELECT role FROM company_access WHERE company_id=:tenant AND user_id=:user"
        ),
        "employees": (
            "SELECT id,full_name,status FROM employees WHERE "
            "company_id=:tenant ORDER BY created_at DESC,id DESC LIMIT 26"
        ),
        "employees_status": (
            "SELECT id,full_name,status FROM employees WHERE "
            "company_id=:tenant AND status='active' ORDER BY created_at "
            "DESC,id DESC LIMIT 26"
        ),
        "employees_deep": (
            "SELECT id,full_name FROM employees WHERE company_id=:tenant "
            "AND (created_at,id)<(:anchor,:id) ORDER BY created_at DESC,id "
            "DESC LIMIT 26"
        ),
        "projects": (
            "SELECT id,name,status FROM projects WHERE company_id=:tenant "
            "ORDER BY created_at DESC,id DESC LIMIT 26"
        ),
        "projects_status": (
            "SELECT id,name FROM projects WHERE company_id=:tenant AND "
            "status='active' ORDER BY created_at DESC,id DESC LIMIT 26"
        ),
        "assignments": (
            "SELECT a.employee_id,e.full_name,a.assigned_at FROM "
            "project_employees a JOIN employees e ON e.id=a.employee_id AND "
            "e.company_id=a.company_id WHERE a.company_id=:tenant AND "
            "a.project_id=:project ORDER BY a.assigned_at "
            "DESC,a.employee_id DESC LIMIT 26"
        ),
    }
    result = {}
    try:
        async with engine.connect() as connection:
            await connection.execute(text("ANALYZE"))
            for name, query in queries.items():
                plan = await connection.scalar(
                    text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query), params
                )
                result[name] = plan
            result["postgres_settings"] = {
                key: await connection.scalar(text(f"SHOW {key}"))
                for key in [
                    "server_version",
                    "max_connections",
                    "shared_buffers",
                    "work_mem",
                    "effective_cache_size",
                ]
            }
    finally:
        await engine.dispose()
    return result


def main():
    output = Path("docs/benchmarks/query-plans.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asyncio.run(explain()), indent=2, default=str) + "\n")
    print(output)


if __name__ == "__main__":
    main()

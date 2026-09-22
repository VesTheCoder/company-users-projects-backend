import hashlib
import hmac
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from app.utils.security import encode_token, hash_token

PROFILES = {
    "small": {
        "users": 1000,
        "companies": 100,
        "access": 5000,
        "employees": 10000,
        "projects": 2500,
        "assignments": 30000,
        "sessions": 1000,
    },
    "functional": {
        "users": 100000,
        "companies": 10000,
        "access": 500000,
        "employees": 1000000,
        "projects": 250000,
        "assignments": 3000000,
        "sessions": 100000,
    },
    "cardinality": {
        "users": 10000000,
        "companies": 2000000,
        "access": 15000000,
        "employees": 50000000,
        "projects": 10000000,
        "assignments": 150000000,
        "sessions": 1000000,
    },
}


def load_id(kind: int, number: int) -> UUID:
    return UUID(int=(0xF1000000 + kind) << 96 | number, version=4)


def employee_company(index, counts):
    hot = counts["employees"] // 10
    hot_companies = counts["companies"] // 5
    if index < hot:
        return 0
    if index < counts["employees"] * 4 // 5:
        return 1 + (index - hot) % (hot_companies - 1)
    return hot_companies + (index - counts["employees"] * 4 // 5) % (
        counts["companies"] - hot_companies
    )


def session_material(secret, index):
    raw = hmac.new(
        secret.encode(), f"load-session:{index}".encode(), hashlib.sha256
    ).digest()
    csrf = hmac.new(
        secret.encode(), f"load-csrf:{index}".encode(), hashlib.sha256
    ).digest()
    return raw, csrf


def dataset_rows(table, counts, password_hash, secret, now):
    created = datetime(2026, 1, 1, tzinfo=UTC)
    if table == "users":
        for i in range(counts["users"]):
            login = f"load{i}@benchmark.example"
            yield (
                load_id(1, i),
                login,
                login,
                f"Load User {i}",
                password_hash,
                True,
                created,
                created,
                created,
            )
    elif table == "companies":
        for i in range(counts["companies"]):
            yield (load_id(2, i), f"Load Company {i}", 1, created, created)
    elif table == "company_access":
        for i in range(counts["access"]):
            company, slot = i % counts["companies"], i // counts["companies"]
            user = (company * 5 + slot) % counts["users"]
            yield (
                load_id(2, company),
                load_id(1, user),
                "owner" if slot == 0 else "admin",
                created,
                created,
            )
    elif table == "employees":
        for i in range(counts["employees"]):
            status = (
                "terminated" if i % 10 == 9 else "leave" if i % 10 == 8 else "active"
            )
            stamp = created + timedelta(seconds=i)
            yield (
                load_id(3, i),
                load_id(2, employee_company(i, counts)),
                f"Employee {i}",
                status,
                date(2025, 1, 1),
                date(2026, 1, 1) if status == "terminated" else None,
                1,
                stamp,
                stamp,
            )
    elif table == "projects":
        for i in range(counts["projects"]):
            stamp = created + timedelta(seconds=i)
            yield (
                load_id(4, i),
                load_id(2, i % counts["companies"]),
                f"Project {i}",
                "completed" if i % 17 == 0 else "active",
                1,
                stamp,
                stamp,
            )
    elif table == "project_employees":
        eligible = counts["employees"] * 9 // 10
        for i in range(counts["assignments"]):
            offset = i % eligible
            employee = offset // 9 * 10 + offset % 9
            company = employee_company(employee, counts)
            project = company + (i // eligible) * counts["companies"]
            yield (
                load_id(2, company),
                load_id(4, project),
                load_id(3, employee),
                created + timedelta(seconds=i),
                load_id(1, company * 5 % counts["users"]),
            )
    elif table == "auth_sessions":
        for i in range(counts["sessions"]):
            raw, csrf = session_material(secret, i)
            yield (
                load_id(5, i),
                load_id(1, i),
                hash_token(raw),
                csrf,
                now,
                now + timedelta(hours=8),
            )


COLUMNS = {
    "users": [
        "id",
        "login",
        "login_normalized",
        "display_name",
        "password_hash",
        "is_active",
        "password_changed_at",
        "created_at",
        "updated_at",
    ],
    "companies": ["id", "name", "version", "created_at", "updated_at"],
    "company_access": ["company_id", "user_id", "role", "created_at", "updated_at"],
    "employees": [
        "id",
        "company_id",
        "full_name",
        "status",
        "start_date",
        "end_date",
        "version",
        "created_at",
        "updated_at",
    ],
    "projects": [
        "id",
        "company_id",
        "name",
        "status",
        "version",
        "created_at",
        "updated_at",
    ],
    "project_employees": [
        "company_id",
        "project_id",
        "employee_id",
        "assigned_at",
        "assigned_by_user_id",
    ],
    "auth_sessions": [
        "id",
        "user_id",
        "token_hash",
        "csrf_token",
        "created_at",
        "expires_at",
    ],
}


def session_pool(counts, secret):
    result = []
    for i in range(min(5000, counts["sessions"], counts["companies"] * 5)):
        raw, csrf = session_material(secret, i)
        company = i // 5
        result.append(
            {
                "user_id": str(load_id(1, i)),
                "login": f"load{i}@benchmark.example",
                "cookie": encode_token(raw),
                "csrf": encode_token(csrf),
                "company_id": str(load_id(2, company)),
            }
        )
    return result

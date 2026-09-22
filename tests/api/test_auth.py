from datetime import datetime

from app.auth.accounts import reset_password
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def test_session_lifecycle_and_cookie_contract(authenticated):
    client = authenticated
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert datetime.fromisoformat(me.json()["expires_at"]).tzinfo is not None
    csrf = await client.get("/api/v1/auth/csrf")
    assert csrf.headers["cache-control"] == "no-store"
    assert csrf.json()["csrf_token"] == client.headers["X-CSRF-Token"]
    assert (await client.post("/api/v1/auth/logout")).status_code == 204
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_password_reset_revokes_sessions(
    authenticated, account, database, application
):
    hashed = await application.state.passwords.hash("replacement password")
    async with SqlAlchemyUnitOfWork(database) as uow:
        await reset_password(uow, account["id"], hashed)
    assert (await authenticated.get("/api/v1/auth/me")).status_code == 401


async def test_login_origin_and_generic_errors(client, account):
    data = {"login": account["login"], "password": "wrong"}
    assert (await client.post("/api/v1/auth/login", json=data)).status_code == 403
    headers = {"Origin": "http://localhost:5173", "X-CSRF-Protection": "1"}
    known = await client.post("/api/v1/auth/login", json=data, headers=headers)
    missing = await client.post(
        "/api/v1/auth/login",
        json=data | {"login": "missing@example.com"},
        headers=headers,
    )
    assert known.status_code == missing.status_code == 401
    assert known.json()["detail"] == missing.json()["detail"]


async def test_unsafe_request_requires_session_csrf(authenticated):
    response = await authenticated.post(
        "/api/v1/auth/logout", headers={"X-CSRF-Token": "wrong"}
    )
    assert response.status_code == 403
    assert (await authenticated.get("/api/v1/auth/me")).status_code == 200


async def test_cors_preflight_is_public(client):
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-CSRF-Protection",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-credentials"] == "true"
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 400

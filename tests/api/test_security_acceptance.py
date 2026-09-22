from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.auth.accounts import create_user, set_account_status
from app.auth.schemas import AccountCreate
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.main import create_app


async def test_session_works_across_instances(authenticated, settings):
    second = create_app(settings)
    async with second.router.lifespan_context(second.app):
        async with AsyncClient(
            transport=ASGITransport(second),
            base_url="http://localhost:8080",
            cookies=authenticated.cookies,
            headers=authenticated.headers,
        ) as client:
            assert (await client.get("/api/v1/auth/me")).status_code == 200
            assert (
                await client.post("/api/v1/companies", json={"name": "Replica"})
            ).status_code == 201


async def test_viewer_permissions_and_cross_tenant_hiding(
    authenticated, application, database
):
    company = (
        await authenticated.post("/api/v1/companies", json={"name": "Private"})
    ).headers["location"]
    other = (
        await authenticated.post("/api/v1/companies", json={"name": "Hidden"})
    ).headers["location"]
    password = str(uuid4())
    hashed = await application.state.passwords.hash(password)
    login = f"{uuid4()}@example.com"
    async with SqlAlchemyUnitOfWork(database) as uow:
        user_id = await create_user(
            uow, AccountCreate(login=login, display_name="Viewer"), hashed
        )
    assert (
        await authenticated.post(
            company + "/access", json={"user_id": str(user_id), "role": "viewer"}
        )
    ).status_code == 201
    async with AsyncClient(
        transport=ASGITransport(application, client=("127.0.0.2", 1)),
        base_url="http://localhost:8080",
    ) as viewer:
        response = await viewer.post(
            "/api/v1/auth/login",
            json={"login": login, "password": password},
            headers={"Origin": "http://localhost:8080", "X-CSRF-Protection": "1"},
        )
        viewer.headers.update(
            {
                "Origin": "http://localhost:8080",
                "X-CSRF-Token": response.json()["csrf_token"],
            }
        )
        assert (await viewer.get(company)).status_code == 200
        assert (await viewer.get(other)).status_code == 404
        assert (
            await viewer.post(company + "/projects", json={"name": "Denied"})
        ).status_code == 403
        await authenticated.delete(company + f"/access/{user_id}")
        assert (await viewer.get(company)).status_code == 404
        async with SqlAlchemyUnitOfWork(database) as uow:
            await set_account_status(uow, user_id, False)
        assert (await viewer.get("/api/v1/auth/me")).status_code == 401

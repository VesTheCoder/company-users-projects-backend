from uuid import uuid4

import pytest

from app.auth.accounts import create_user, set_account_status
from app.auth.schemas import AccountCreate
from app.exceptions.base import AppError
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def test_company_crud_versions_and_pagination(authenticated):
    client = authenticated
    created = await client.post("/api/v1/companies", json={"name": "Acme"})
    assert created.status_code == 201, created.text
    location = created.headers["location"]
    assert created.headers["etag"] == '"v1"'
    assert (await client.patch(location, json={"name": "New"})).status_code == 428
    changed = await client.patch(
        location, json={"name": "New"}, headers={"If-Match": '"v1"'}
    )
    assert changed.status_code == 200, changed.text
    assert changed.headers["etag"] == '"v2"'
    assert (
        await client.delete(location, headers={"If-Match": '"v1"'})
    ).status_code == 412
    await client.post("/api/v1/companies", json={"name": "Other"})
    page = (await client.get("/api/v1/companies?limit=1")).json()
    assert len(page["items"]) == 1 and page["next_cursor"]
    next_page = (
        await client.get("/api/v1/companies", params={"cursor": page["next_cursor"]})
    ).json()
    assert next_page["items"][0]["id"] != page["items"][0]["id"]
    assert (
        await client.delete(location, headers={"If-Match": '"v2"'})
    ).status_code == 204
    assert (await client.get(location)).status_code == 404


async def test_access_and_ownership_transfer(authenticated, account, database):
    client = authenticated
    created = await client.post("/api/v1/companies", json={"name": "Roles"})
    location = created.headers["location"]
    async with SqlAlchemyUnitOfWork(database) as uow:
        target = await create_user(
            uow,
            AccountCreate(login=f"{uuid4()}@example.com", display_name="Target"),
            "encoded",
        )
    grant = await client.post(
        location + "/access", json={"user_id": str(target), "role": "viewer"}
    )
    assert grant.status_code == 201, grant.text
    assert (
        await client.delete(location + f"/access/{account['id']}")
    ).status_code == 409
    with pytest.raises(AppError):
        async with SqlAlchemyUnitOfWork(database) as uow:
            await set_account_status(uow, account["id"], False)
    transferred = await client.post(
        location + "/ownership-transfer",
        json={"new_owner_user_id": str(target), "previous_owner_role": "viewer"},
    )
    assert transferred.status_code == 200, transferred.text
    assert (await client.get(location + "/access")).status_code == 403
    assert (
        await client.patch(
            location, json={"name": "Denied"}, headers={"If-Match": '"v1"'}
        )
    ).status_code == 403


async def test_unknown_tenant_is_hidden(authenticated):
    assert (await authenticated.get(f"/api/v1/companies/{uuid4()}")).status_code == 404

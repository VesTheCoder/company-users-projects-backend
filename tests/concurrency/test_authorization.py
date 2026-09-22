import asyncio
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.auth.accounts import create_user
from app.auth.schemas import AccountCreate
from app.companies.schemas import AccessGrant, CompanyUpdate
from app.companies.services import grant_access, update_company
from app.exceptions.base import AppError
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def test_revocation_blocks_waiting_mutation(authenticated, account, database):
    company = (
        await authenticated.post("/api/v1/companies", json={"name": "Revocation race"})
    ).json()
    company_id = UUID(company["id"])
    owner = SimpleNamespace(user_id=account["id"])
    async with SqlAlchemyUnitOfWork(database) as uow:
        target = await create_user(
            uow,
            AccountCreate(login=f"{uuid4()}@example.com", display_name="Admin"),
            "encoded",
        )
    async with SqlAlchemyUnitOfWork(database) as uow:
        await grant_access(
            uow, owner, company_id, AccessGrant(user_id=target, role="admin")
        )
    async with SqlAlchemyUnitOfWork(database) as uow:
        await uow.companies.accessible(company_id, owner.user_id, lock=True)
        access = await uow.company_access.member(company_id, target)
        await uow.session.delete(access)
        started = asyncio.Event()

        async def mutate():
            async with SqlAlchemyUnitOfWork(database) as other:
                started.set()
                return await update_company(
                    other,
                    SimpleNamespace(user_id=target),
                    company_id,
                    CompanyUpdate(name="Forbidden"),
                    1,
                )

        task = asyncio.create_task(mutate())
        await started.wait()
        await uow.commit()
    result = (await asyncio.gather(task, return_exceptions=True))[0]
    assert isinstance(result, AppError) and result.status == 404
    response = await authenticated.get(f"/api/v1/companies/{company_id}")
    assert response.json()["name"] == "Revocation race"

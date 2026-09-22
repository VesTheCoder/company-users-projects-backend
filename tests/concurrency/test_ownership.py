import asyncio
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import func, select

from app.auth.accounts import create_user
from app.auth.schemas import AccountCreate
from app.companies.models import CompanyAccess
from app.companies.schemas import AccessGrant, CompanyCreate, OwnershipTransfer
from app.companies.services import create_company, grant_access, transfer_ownership
from app.exceptions.base import AppError
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def test_concurrent_transfers_preserve_exactly_one_owner(database, account):
    principal = SimpleNamespace(user_id=account["id"])
    async with SqlAlchemyUnitOfWork(database) as uow:
        company = await create_company(uow, principal, CompanyCreate(name="Concurrent"))
    targets = []
    for _ in range(2):
        async with SqlAlchemyUnitOfWork(database) as uow:
            target = await create_user(
                uow,
                AccountCreate(login=f"{uuid4()}@example.com", display_name="Target"),
                "encoded",
            )
            targets.append(target)
        async with SqlAlchemyUnitOfWork(database) as uow:
            await grant_access(
                uow, principal, company.id, AccessGrant(user_id=target, role="admin")
            )

    async def transfer(target):
        async with SqlAlchemyUnitOfWork(database) as uow:
            return await transfer_ownership(
                uow,
                principal,
                company.id,
                OwnershipTransfer(
                    new_owner_user_id=target, previous_owner_role="admin"
                ),
            )

    results = await asyncio.gather(
        *(transfer(target) for target in targets), return_exceptions=True
    )
    assert sum(isinstance(result, list) for result in results) == 1
    assert (
        sum(
            isinstance(result, AppError) and result.code == "ownership_changed"
            for result in results
        )
        == 1
    )
    async with database() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(CompanyAccess)
                .where(
                    CompanyAccess.company_id == company.id,
                    CompanyAccess.role == "owner",
                )
            )
            == 1
        )

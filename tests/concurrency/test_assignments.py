import asyncio
from types import SimpleNamespace

from sqlalchemy import func, select

from app.companies.schemas import CompanyCreate
from app.companies.services import create_company
from app.employees.schemas import EmployeeCreate, EmployeeUpdate
from app.employees.services import create_employee, update_employee
from app.exceptions.base import AppError
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.projects.models import ProjectEmployee
from app.projects.schemas import ProjectCreate
from app.projects.services import create_project, ensure_assignment


async def test_duplicate_add_and_termination_races(database, account):
    principal = SimpleNamespace(user_id=account["id"])
    async with SqlAlchemyUnitOfWork(database) as uow:
        company = await create_company(uow, principal, CompanyCreate(name="Race"))
    async with SqlAlchemyUnitOfWork(database) as uow:
        employee = await create_employee(
            uow,
            principal,
            company.id,
            EmployeeCreate(full_name="Worker", start_date="2026-01-01"),
        )
    async with SqlAlchemyUnitOfWork(database) as uow:
        project = await create_project(
            uow, principal, company.id, ProjectCreate(name="Project")
        )

    async def assign():
        async with SqlAlchemyUnitOfWork(database) as uow:
            return await ensure_assignment(
                uow, principal, company.id, project.id, employee.id
            )

    results = await asyncio.gather(assign(), assign())
    assert sorted(result[1] for result in results) == [False, True]

    async def terminate():
        async with SqlAlchemyUnitOfWork(database) as uow:
            return await update_employee(
                uow,
                principal,
                company.id,
                employee.id,
                EmployeeUpdate(status="terminated", end_date="2026-09-01"),
                1,
            )

    results = await asyncio.gather(assign(), terminate(), return_exceptions=True)
    assert not any(
        isinstance(result, Exception) and not isinstance(result, AppError)
        for result in results
    )
    async with database() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ProjectEmployee)
                .where(ProjectEmployee.company_id == company.id)
            )
            == 0
        )

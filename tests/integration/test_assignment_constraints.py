from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.companies.schemas import CompanyCreate
from app.companies.services import create_company
from app.employees.schemas import EmployeeCreate
from app.employees.services import create_employee
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.projects.models import ProjectEmployee
from app.projects.schemas import ProjectCreate
from app.projects.services import create_project


async def test_database_rejects_cross_tenant_assignment(database, account):
    principal = SimpleNamespace(user_id=account["id"])
    async with SqlAlchemyUnitOfWork(database) as uow:
        first = await create_company(uow, principal, CompanyCreate(name="First"))
    async with SqlAlchemyUnitOfWork(database) as uow:
        second = await create_company(uow, principal, CompanyCreate(name="Second"))
    async with SqlAlchemyUnitOfWork(database) as uow:
        employee = await create_employee(
            uow,
            principal,
            first.id,
            EmployeeCreate(full_name="Worker", start_date="2026-01-01"),
        )
    async with SqlAlchemyUnitOfWork(database) as uow:
        project = await create_project(
            uow, principal, second.id, ProjectCreate(name="Project")
        )
    with pytest.raises(IntegrityError):
        async with SqlAlchemyUnitOfWork(database) as uow:
            uow.session.add(
                ProjectEmployee(
                    company_id=second.id,
                    project_id=project.id,
                    employee_id=employee.id,
                    assigned_by_user_id=account["id"],
                )
            )
            await uow.commit()

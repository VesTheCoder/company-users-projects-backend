import argparse
import asyncio
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.auth.models import User
from app.auth.passwords import PasswordHasherService
from app.companies.models import Company, CompanyAccess
from app.config import Settings
from app.employees.models import Employee
from app.projects.models import Project, ProjectEmployee
from scripts.common import operational_uow, read_password


def demo_id(number: int) -> UUID:
    return UUID(f"d0000000-0000-4000-8000-{number:012x}")


def require_demo_environment(settings):
    if settings.app_env != "development" or not settings.allow_demo_seed:
        raise ValueError("Demo seed requires development and ALLOW_DEMO_SEED=true")


async def seed_demo(settings, password_hash: str):
    require_demo_environment(settings)
    async with operational_uow(settings) as uow:
        for number, name in enumerate(["owner", "admin", "viewer", "outsider"], 1):
            values = dict(
                id=demo_id(number),
                login=f"{name}@demo.example",
                login_normalized=f"{name}@demo.example",
                display_name=name.title(),
                password_hash=password_hash,
                is_active=True,
            )
            await uow.session.execute(
                insert(User)
                .values(**values)
                .on_conflict_do_update(index_elements=[User.id], set_=values)
            )
            await uow.sessions.revoke_user(demo_id(number))
        for number, name in [(101, "Acme Demo"), (102, "Other Tenant")]:
            values = dict(
                id=demo_id(number),
                name=name,
                description="Reproducible development dataset",
                version=1,
            )
            await uow.session.execute(
                insert(Company)
                .values(**values)
                .on_conflict_do_update(index_elements=[Company.id], set_=values)
            )
        await seed_access(uow)
        await seed_business(uow)
        await uow.commit()


async def seed_access(uow):
    await uow.session.execute(
        delete(CompanyAccess).where(
            CompanyAccess.company_id.in_([demo_id(101), demo_id(102)]),
            CompanyAccess.user_id.in_([demo_id(i) for i in range(1, 5)]),
        )
    )
    for company, user, role in [
        (101, 1, "owner"),
        (101, 2, "admin"),
        (101, 3, "viewer"),
        (102, 4, "owner"),
        (102, 1, "viewer"),
    ]:
        uow.session.add(
            CompanyAccess(company_id=demo_id(company), user_id=demo_id(user), role=role)
        )


async def seed_business(uow):
    for number, company, status in [
        (201, 101, "active"),
        (202, 101, "leave"),
        (203, 101, "terminated"),
        (204, 102, "active"),
    ]:
        values = dict(
            id=demo_id(number),
            company_id=demo_id(company),
            full_name=f"Demo Employee {number}",
            status=status,
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1) if status == "terminated" else None,
            version=1,
        )
        await uow.session.execute(
            insert(Employee)
            .values(**values)
            .on_conflict_do_update(index_elements=[Employee.id], set_=values)
        )
    for number, company in [(301, 101), (302, 102)]:
        values = dict(
            id=demo_id(number),
            company_id=demo_id(company),
            name=f"Demo Project {number}",
            status="active",
            version=1,
        )
        await uow.session.execute(
            insert(Project)
            .values(**values)
            .on_conflict_do_update(index_elements=[Project.id], set_=values)
        )
    await uow.session.execute(
        delete(ProjectEmployee).where(
            ProjectEmployee.company_id.in_([demo_id(101), demo_id(102)]),
            ProjectEmployee.employee_id.in_([demo_id(i) for i in range(201, 205)]),
        )
    )
    for company, project, employee, user in [(101, 301, 201, 1), (102, 302, 204, 4)]:
        uow.session.add(
            ProjectEmployee(
                company_id=demo_id(company),
                project_id=demo_id(project),
                employee_id=demo_id(employee),
                assigned_by_user_id=demo_id(user),
            )
        )


def main():
    parser = argparse.ArgumentParser(
        description="Seed deterministic development records"
    )
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    require_demo_environment(settings)
    password = (
        Path(settings.demo_password_file).read_text().rstrip("\r\n")
        if settings.demo_password_file
        else read_password(args.password_stdin)
    )

    async def run():
        hashed = await PasswordHasherService().hash(password)
        await seed_demo(settings, hashed)

    asyncio.run(run())
    print(
        "Seeded owner/admin/viewer/outsider@demo.example; company IDs:",
        demo_id(101),
        demo_id(102),
    )


if __name__ == "__main__":
    main()

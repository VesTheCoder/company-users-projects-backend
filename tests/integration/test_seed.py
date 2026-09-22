import pytest
from sqlalchemy import func, select

from app.auth.models import User
from app.companies.models import CompanyAccess
from app.projects.models import ProjectEmployee
from scripts.seed_demo import demo_id, require_demo_environment, seed_demo


async def test_seed_is_idempotent_and_employees_have_no_accounts(settings, database):
    settings.allow_demo_seed = True
    await seed_demo(settings, "encoded")
    await seed_demo(settings, "encoded")
    async with database() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.id.in_([demo_id(i) for i in range(1, 5)]))
            )
            == 4
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(CompanyAccess)
                .where(
                    CompanyAccess.company_id == demo_id(101),
                    CompanyAccess.role == "owner",
                )
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ProjectEmployee)
                .where(ProjectEmployee.employee_id == demo_id(203))
            )
            == 0
        )


def test_seed_refuses_production(settings):
    settings.app_env = "production"
    settings.allow_demo_seed = True
    with pytest.raises(ValueError):
        require_demo_environment(settings)

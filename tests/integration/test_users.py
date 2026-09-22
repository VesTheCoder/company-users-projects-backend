from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.accounts import create_user
from app.auth.models import User
from app.auth.schemas import AccountCreate
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def test_provision_normalizes_login_and_commits(database):
    login = f"{uuid4()}@example.com"
    async with SqlAlchemyUnitOfWork(database) as uow:
        user_id = await create_user(
            uow, AccountCreate(login=login.upper(), display_name="Test"), "encoded"
        )
        assert uow.users.session is uow.sessions.session is uow.session
    async with database() as session:
        user = await session.get(User, user_id)
        assert user.login_normalized == login
    with pytest.raises(IntegrityError):
        async with SqlAlchemyUnitOfWork(database) as uow:
            await create_user(
                uow, AccountCreate(login=login, display_name="Other"), "encoded"
            )


async def test_uncommitted_use_case_rolls_back(database):
    login = f"{uuid4()}@example.com"
    async with SqlAlchemyUnitOfWork(database) as uow:
        uow.session.add(
            User(
                login=login,
                login_normalized=login,
                display_name="Rollback",
                password_hash="encoded",
            )
        )
        await uow.session.flush()
    async with database() as session:
        assert await session.scalar(select(User).where(User.login == login)) is None

from unittest.mock import AsyncMock, Mock

import pytest

from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def test_uow_commits_explicitly_and_always_closes():
    session = AsyncMock()
    async with SqlAlchemyUnitOfWork(Mock(return_value=session)) as uow:
        await uow.commit()
    session.commit.assert_awaited_once()
    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()


async def test_uow_rolls_back_failed_use_case():
    session = AsyncMock()
    with pytest.raises(ValueError):
        async with SqlAlchemyUnitOfWork(Mock(return_value=session)):
            raise ValueError("Aborted")
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()

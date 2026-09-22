import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from polyfactory.factories.sqlalchemy_factory import (
    SQLAlchemyFactory,
    SQLAlchemyPersistenceMethod,
)
from sqlalchemy import select

from app.auth.models import AuthSession, User
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def test_retention_removes_old_sessions_but_preserves_grace_period(database):
    now = datetime.now(UTC)
    async with SqlAlchemyUnitOfWork(database) as uow:

        class UserFactory(SQLAlchemyFactory[User]):
            __model__ = User
            __async_session__ = uow.session
            __persistence_method__ = SQLAlchemyPersistenceMethod.FLUSH

        login = f"{uuid4()}@example.com"
        user = await UserFactory.create_async(
            login=login,
            login_normalized=login,
            display_name="Retention",
            password_hash="encoded",
        )
        sessions = []
        for hours in [48, 12]:
            session = AuthSession(
                user_id=user.id,
                token_hash=secrets.token_bytes(32),
                csrf_token=secrets.token_bytes(32),
                created_at=now - timedelta(hours=hours + 8),
                expires_at=now - timedelta(hours=hours),
            )
            uow.session.add(session)
            sessions.append(session)
        await uow.commit()
        identifiers = [session.id for session in sessions]
    async with SqlAlchemyUnitOfWork(database) as uow:
        assert await uow.sessions.cleanup(now - timedelta(hours=24)) == 1
        await uow.commit()
    async with database() as session:
        found = (
            await session.scalars(
                select(AuthSession.id).where(AuthSession.id.in_(identifiers))
            )
        ).all()
        assert found == [identifiers[1]]

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.repositories import SessionRepository, UserRepository


class SqlAlchemyUnitOfWork:
    def __init__(self, factory: async_sessionmaker[AsyncSession]):
        self.factory = factory

    async def __aenter__(self):
        self.session = self.factory()
        self.users = UserRepository(self.session)
        self.sessions = SessionRepository(self.session)
        return self

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            await self.rollback()
        finally:
            await self.session.close()

import asyncio

from alembic import context

from app.auth.models import AuthSession, User
from app.companies.models import Company, CompanyAccess
from app.config import Settings
from app.infrastructure.database import create_engine
from app.infrastructure.orm.base import Base

target_metadata = Base.metadata
registered_models = (User, AuthSession, Company, CompanyAccess)


def run_migrations(connection):
    context.configure(
        connection=connection, target_metadata=target_metadata, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_online():
    settings = context.config.attributes.get("settings") or Settings()
    engine = create_engine(settings, migration=True)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    context.configure(
        url=Settings().migration_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    run_migrations(context.config.attributes["connection"])
else:
    asyncio.run(run_online())

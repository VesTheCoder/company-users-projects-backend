from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.infrastructure.database import create_engine


async def test_revisions_upgrade_downgrade_and_metadata_alignment(settings, database):
    engine = create_engine(settings)
    config = Config("alembic.ini")
    async with engine.begin() as connection:
        await connection.execute(text("CREATE SCHEMA migration_test"))
        await connection.execute(text("SET LOCAL search_path TO migration_test"))

        def exercise(sync):
            config.attributes["connection"] = sync
            command.upgrade(config, "0001")
            command.upgrade(config, "0002")
            command.upgrade(config, "0003")
            command.check(config)
            command.downgrade(config, "0002")
            command.upgrade(config, "head")
            command.downgrade(config, "base")

        await connection.run_sync(exercise)
        await connection.execute(text("DROP TABLE migration_test.alembic_version"))
        await connection.execute(text("DROP SCHEMA migration_test"))
    await engine.dispose()

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from app.config import Settings
from app.infrastructure.database import create_engine, create_session_factory


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        app_env="development",
        api_public_origin="http://localhost:8080",
        cors_allowed_origins=["http://localhost:5173"],
        cookie_secure=False,
        db_host="localhost",
        db_name="company_test",
        db_user="test",
        db_password="test",
        redis_rate_limit_url="redis://localhost:6379/0",
        rate_limit_key_secret="r" * 32,
        cursor_signing_key="c" * 32,
    )


@pytest.fixture(scope="session")
def postgres_container():
    container = (
        DockerContainer("postgres:18.6")
        .with_env("POSTGRES_USER", "test")
        .with_env("POSTGRES_PASSWORD", "test")
        .with_env("POSTGRES_DB", "company_test")
        .with_exposed_ports(5432)
        .waiting_for(
            LogMessageWaitStrategy(
                "database system is ready to accept connections", times=2
            )
        )
    )
    with container:
        yield container


@pytest.fixture
async def database(settings, postgres_container):
    settings.db_host = postgres_container.get_container_host_ip()
    settings.db_port = int(postgres_container.get_exposed_port(5432))
    settings.db_migration_user = "test"
    settings.db_migration_password = SecretStr("test")
    engine = create_engine(settings)
    config = Config("alembic.ini")
    async with engine.begin() as connection:

        def migrate(sync_connection):
            config.attributes["connection"] = sync_connection
            command.upgrade(config, "head")

        await connection.run_sync(migrate)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()

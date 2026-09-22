from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from app.auth.accounts import create_user
from app.auth.schemas import AccountCreate
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.main import create_app
from app.settings import Settings


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


@pytest.fixture(scope="session")
def redis_container():
    with (
        DockerContainer("redis:8.10.2")
        .with_exposed_ports(6379)
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections"))
    ) as container:
        yield container


@pytest.fixture
async def application(settings, database, redis_container):
    settings.redis_rate_limit_url = SecretStr(
        f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}/0"
    )
    settings.rate_limit_key_secret = SecretStr(str(uuid4()))
    app = create_app(settings)
    async with app.router.lifespan_context(app.app):
        yield app


@pytest.fixture
async def client(application):
    async with AsyncClient(
        transport=ASGITransport(application, client=("127.0.0.1", 1234)),
        base_url="http://localhost:8080",
    ) as value:
        yield value


@pytest.fixture
async def account(application, database):
    data = AccountCreate(login=f"{uuid4()}@example.com", display_name="Test User")
    password = str(uuid4())
    hashed = await application.state.passwords.hash(password)
    async with SqlAlchemyUnitOfWork(database) as uow:
        identifier = await create_user(uow, data, hashed)
    return {"id": identifier, "login": data.login, "password": password}


@pytest.fixture
async def authenticated(client, account):
    response = await client.post(
        "/api/v1/auth/login",
        json={"login": account["login"], "password": account["password"]},
        headers={"Origin": "http://localhost:5173", "X-CSRF-Protection": "1"},
    )
    assert response.status_code == 200, response.text
    client.headers.update(
        {
            "Origin": "http://localhost:5173",
            "X-CSRF-Token": response.json()["csrf_token"],
        }
    )
    return client

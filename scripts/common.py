import getpass
import sys
from contextlib import asynccontextmanager

from app.config import Settings
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def read_password(from_stdin: bool) -> str:
    value = (
        sys.stdin.readline().rstrip("\r\n")
        if from_stdin
        else getpass.getpass("Password: ")
    )
    if not 12 <= len(value) <= 1024:
        raise ValueError("Password must contain between 12 and 1024 characters")
    return value


@asynccontextmanager
async def operational_uow(settings=None):
    engine = create_engine(settings or Settings(), operational=True)
    try:
        async with SqlAlchemyUnitOfWork(create_session_factory(engine)) as uow:
            yield uow
    finally:
        await engine.dispose()

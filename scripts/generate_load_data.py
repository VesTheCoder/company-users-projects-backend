import argparse
import asyncio
import json
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from time import perf_counter

from sqlalchemy import select

from app.auth.models import User
from app.auth.passwords import PasswordHasherService
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.settings import Settings
from scripts.common import read_password
from scripts.load_dataset import COLUMNS, PROFILES, dataset_rows, load_id, session_pool
from scripts.seed_demo import require_demo_environment


async def copy_table(factory, table, rows):
    count = 0
    while batch := list(islice(rows, 5000)):
        async with SqlAlchemyUnitOfWork(factory) as uow:
            connection = await uow.session.connection()
            raw = await connection.get_raw_connection()
            await raw.driver_connection.copy_records_to_table(
                table, records=batch, columns=COLUMNS[table]
            )
            await uow.commit()
        count += len(batch)
    print(f"{table}: {count}", flush=True)


async def generate(settings, counts, password):
    hashed = await PasswordHasherService().hash(password)
    secret = settings.cursor_signing_key.get_secret_value()
    engine = create_engine(settings, operational=True)
    factory = create_session_factory(engine)
    started = perf_counter()
    try:
        async with SqlAlchemyUnitOfWork(factory) as uow:
            if await uow.session.scalar(
                select(User.id).where(User.id == load_id(1, 0))
            ):
                raise ValueError(
                    "Benchmark records already exist; use a fresh migrated database"
                )
        for table in COLUMNS:
            await copy_table(
                factory,
                table,
                dataset_rows(table, counts, hashed, secret, datetime.now(UTC)),
            )
    finally:
        await engine.dispose()
    return {
        "counts": counts,
        "generation_seconds": round(perf_counter() - started, 2),
        "sessions": session_pool(counts, secret),
    }


def main():
    parser = argparse.ArgumentParser(
        description="COPY benchmark data into a development database"
    )
    parser.add_argument("--profile", choices=PROFILES, default="functional")
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    require_demo_environment(settings)
    settings.db_statement_timeout_ms = 60000
    result = asyncio.run(
        generate(settings, PROFILES[args.profile], read_password(args.password_stdin))
    )
    output = Path(".local")
    output.mkdir(exist_ok=True)
    (output / "load-sessions.json").write_text(json.dumps(result.pop("sessions")))
    (output / "dataset.json").write_text(json.dumps(result, indent=2))
    print("Wrote local session credentials and dataset summary to .local")


if __name__ == "__main__":
    main()

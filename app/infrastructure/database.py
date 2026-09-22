from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.metrics import observed_pool_class
from app.settings import Settings


def create_engine(
    settings: Settings,
    *,
    operational: bool = False,
    migration: bool = False,
    metrics=None,
):
    options = (
        {"poolclass": NullPool}
        if operational or migration
        else {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout_seconds,
            "pool_recycle": 1800,
        }
    )
    if metrics is not None and not operational and not migration:
        options["poolclass"] = observed_pool_class(metrics)
    return create_async_engine(
        settings.migration_database_url if migration else settings.database_url,
        pool_pre_ping=True,
        connect_args={
            "ssl": settings.db_sslmode,
            "timeout": 5,
            "server_settings": {
                "statement_timeout": str(
                    60000 if migration else settings.db_statement_timeout_ms
                ),
                "lock_timeout": "2000",
                "idle_in_transaction_session_timeout": "15000",
            },
        },
        **options,
    )


def create_session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)

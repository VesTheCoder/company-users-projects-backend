import asyncio

from app.infrastructure.database import create_engine
from app.infrastructure.metrics import Metrics


async def test_pool_wait_metric_observes_connection_contention(settings, database):
    settings.db_pool_size = 1
    settings.db_max_overflow = 0
    metrics = Metrics()
    engine = create_engine(settings, metrics=metrics)
    acquired = asyncio.Event()
    release = asyncio.Event()

    async def hold():
        async with engine.connect():
            acquired.set()
            await release.wait()

    holder = asyncio.create_task(hold())
    await acquired.wait()

    async def wait_connection():
        async with engine.connect():
            return True

    waiter = asyncio.create_task(wait_connection())
    await asyncio.sleep(0.02)
    assert metrics.registry.get_sample_value("db_pool_acquiring") == 1
    release.set()
    await holder
    assert await waiter
    assert metrics.registry.get_sample_value("db_pool_acquiring") == 0
    assert metrics.registry.get_sample_value("db_pool_acquire_seconds_count") == 2
    await engine.dispose()

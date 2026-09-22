import asyncio
from uuid import uuid4

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from app.exceptions.base import AppError
from app.infrastructure.rate_limit import RateLimitCategory, RateLimiter


@pytest.fixture(scope="module")
def redis_url():
    with (
        DockerContainer("redis:8.10.2")
        .with_exposed_ports(6379)
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections")) as container
    ):
        yield f"redis://{container.get_container_host_ip()}:{container.get_exposed_port(6379)}/0"


async def test_concurrent_replicas_share_atomic_limit(redis_url):
    first, second = RateLimiter(redis_url, "secret"), RateLimiter(redis_url, "secret")
    subject = str(uuid4())
    try:
        results = await asyncio.gather(
            *(
                (first if i % 2 else second).check(
                    RateLimitCategory.LOGIN_ACCOUNT, subject
                )
                for i in range(30)
            ),
            return_exceptions=True,
        )
        assert sum(isinstance(r, dict) for r in results) == 10, results
        assert all(
            isinstance(r, dict) or isinstance(r, AppError) and r.status == 429
            for r in results
        )
    finally:
        await first.close()
        await second.close()


async def test_limiter_outage_is_unavailable_not_exceeded():
    limiter = RateLimiter("redis://localhost:1/0", "secret")
    try:
        with pytest.raises(AppError) as raised:
            await limiter.check(RateLimitCategory.GENERAL, str(uuid4()))
        assert raised.value.status == 503
    finally:
        await limiter.close()

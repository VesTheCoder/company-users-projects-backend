from redis.asyncio import Redis

from app.settings import Settings


def create_redis(settings: Settings) -> Redis:
    return Redis.from_url(
        settings.redis_rate_limit_url.get_secret_value(),
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )

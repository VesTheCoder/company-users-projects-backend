import math
import time
from enum import StrEnum
from ipaddress import ip_address

from limits import parse
from limits.aio.storage import RedisStorage
from limits.aio.strategies import SlidingWindowCounterRateLimiter
from redis.exceptions import RedisError

from app.exceptions.base import AppError
from app.utils.normalization import normalize_identifier
from app.utils.security import keyed_digest


class RateLimitCategory(StrEnum):
    LOGIN_IP = "login.ip"
    LOGIN_ACCOUNT = "login.account"
    GENERAL = "auth.general"
    EXPENSIVE = "list.expensive"


LIMITS = {
    RateLimitCategory.LOGIN_IP: parse("20/10 minutes"),
    RateLimitCategory.LOGIN_ACCOUNT: parse("10/15 minutes"),
    RateLimitCategory.GENERAL: parse("300/minute"),
    RateLimitCategory.EXPENSIVE: parse("60/minute"),
}


def build_rate_key(secret: str, category: RateLimitCategory, subject: str) -> str:
    if category == RateLimitCategory.LOGIN_ACCOUNT:
        subject = normalize_identifier(subject)
    elif category == RateLimitCategory.LOGIN_IP:
        subject = str(ip_address(subject))
    return f"rl:v1:{category}:{keyed_digest(secret, subject)}"


class RateLimiter:
    def __init__(self, url: str, secret: str):
        self.secret = secret
        self.storage = RedisStorage(
            "async+" + url,
            implementation="redispy",
            key_prefix="rl:v1",
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        self.strategy = SlidingWindowCounterRateLimiter(self.storage)

    async def check(self, category: RateLimitCategory, subject: str) -> dict[str, str]:
        key = build_rate_key(self.secret, category, subject)
        item = LIMITS[category]
        try:
            allowed = await self.strategy.hit(item, key)
            stats = await self.strategy.get_window_stats(item, key)
        except (RedisError, OSError, TimeoutError) as error:
            raise AppError(
                503,
                "rate_limiter_unavailable",
                "Rate limiting is temporarily unavailable.",
            ) from error
        reset = max(1, math.ceil(stats.reset_time - time.time()))
        headers = {
            "RateLimit-Limit": str(item.amount),
            "RateLimit-Remaining": str(stats.remaining),
            "RateLimit-Reset": str(reset),
        }
        if not allowed:
            raise AppError(
                429,
                "rate_limit_exceeded",
                "Too many requests.",
                headers | {"Retry-After": str(reset)},
            )
        return headers

    async def close(self):
        await self.storage.bridge.storage.aclose()

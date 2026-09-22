import secrets

from anyio import CapacityLimiter, to_thread
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError


class PasswordHasherService:
    def __init__(self, concurrency: int = 2):
        self.hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        self.limiter = CapacityLimiter(concurrency)
        self.dummy_hash: str | None = None

    async def initialize(self):
        self.dummy_hash = await self.hash(secrets.token_urlsafe(32))

    async def hash(self, password: str) -> str:
        return await to_thread.run_sync(
            self.hasher.hash, password, limiter=self.limiter
        )

    async def verify(self, password: str, encoded: str) -> bool:
        try:
            return await to_thread.run_sync(
                self.hasher.verify, encoded, password, limiter=self.limiter
            )
        except VerificationError:
            return False

    def needs_rehash(self, encoded: str) -> bool:
        return self.hasher.check_needs_rehash(encoded)

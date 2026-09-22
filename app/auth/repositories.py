from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update

from app.auth.models import AuthSession, User


class UserRepository:
    def __init__(self, session):
        self.session = session

    async def by_login(self, login: str):
        return await self.session.scalar(
            select(User).where(User.login_normalized == login)
        )

    async def lock(self, user_id: UUID):
        return await self.session.scalar(
            select(User).where(User.id == user_id).with_for_update()
        )


class SessionRepository:
    def __init__(self, session):
        self.session = session

    async def authenticate(self, token_hash: bytes):
        return (
            await self.session.execute(
                select(AuthSession, User)
                .join(User, User.id == AuthSession.user_id)
                .where(
                    AuthSession.token_hash == token_hash,
                    AuthSession.revoked_at.is_(None),
                    AuthSession.expires_at > func.now(),
                    User.is_active.is_(True),
                )
            )
        ).first()

    async def revoke_user(self, user_id: UUID):
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )

    async def cleanup(self, cutoff: datetime, batch_size: int = 1000):
        ids = (
            select(AuthSession.id)
            .where(
                or_(AuthSession.expires_at < cutoff, AuthSession.revoked_at < cutoff)
            )
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(
            delete(AuthSession).where(AuthSession.id.in_(ids))
        )
        return result.rowcount

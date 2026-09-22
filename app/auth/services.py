import secrets
from datetime import UTC, datetime, timedelta

from app.auth.domain import CurrentPrincipal
from app.auth.models import AuthSession
from app.auth.schemas import LoginResponse, UserRead
from app.exceptions.base import AppError
from app.utils.normalization import normalize_identifier
from app.utils.security import decode_token, encode_token, hash_token


class SessionAuthenticator:
    async def authenticate(self, uow, credential: str | None):
        try:
            raw = decode_token(credential or "")
            if len(raw) != 32:
                raise ValueError
        except ValueError as error:
            raise AppError(
                401, "authentication_required", "Authentication is required."
            ) from error
        row = await uow.sessions.authenticate(hash_token(raw))
        if row is None:
            raise AppError(
                401, "authentication_required", "Authentication is required."
            )
        session, user = row
        principal = CurrentPrincipal(
            user.id,
            session.id,
            session.csrf_token,
            session.expires_at,
            user.login,
            user.display_name,
        )
        await uow.rollback()
        return principal


async def login(uow, passwords, data, settings):
    user = await uow.users.by_login(normalize_identifier(data.login))
    snapshot = (user.id, user.password_hash, user.is_active) if user else None
    await uow.rollback()
    encoded = snapshot[1] if snapshot else passwords.dummy_hash
    verified = await passwords.verify(data.password, encoded)
    if not verified or not snapshot or not snapshot[2]:
        raise AppError(401, "invalid_credentials", "Invalid login or password.")
    replacement = (
        await passwords.hash(data.password) if passwords.needs_rehash(encoded) else None
    )
    user = await uow.users.lock(snapshot[0])
    if not user.is_active or user.password_hash != encoded:
        raise AppError(401, "invalid_credentials", "Invalid login or password.")
    if replacement:
        user.password_hash = replacement
    raw, csrf = secrets.token_bytes(32), secrets.token_bytes(32)
    expires = datetime.now(UTC) + timedelta(seconds=settings.session_ttl_seconds)
    uow.session.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(raw),
            csrf_token=csrf,
            expires_at=expires,
        )
    )
    result = LoginResponse(
        user=UserRead.model_validate(user),
        csrf_token=encode_token(csrf),
        expires_at=expires,
    )
    await uow.commit()
    return result, encode_token(raw)

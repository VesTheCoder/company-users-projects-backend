from sqlalchemy import func, select

from app.auth.models import User
from app.companies.models import Company, CompanyAccess
from app.exceptions.base import AppError
from app.utils.normalization import normalize_identifier


async def create_user(uow, data, password_hash: str):
    user = User(
        **data.model_dump(),
        login_normalized=normalize_identifier(data.login),
        password_hash=password_hash,
    )
    uow.session.add(user)
    await uow.commit()
    return user.id


async def reset_password(uow, user_id, password_hash):
    user = await uow.users.lock(user_id)
    if user is None:
        raise AppError(404, "target_user_not_available", "Account is unavailable.")
    user.password_hash = password_hash
    user.password_changed_at = func.now()
    await uow.sessions.revoke_user(user_id)
    await uow.commit()


async def set_account_status(uow, user_id, active: bool):
    if not active:
        owned = select(CompanyAccess.company_id).where(
            CompanyAccess.user_id == user_id, CompanyAccess.role == "owner"
        )
        await uow.session.execute(
            select(Company)
            .where(Company.id.in_(owned))
            .order_by(Company.id)
            .with_for_update()
        )
    user = await uow.users.lock(user_id)
    if user is None:
        raise AppError(404, "target_user_not_available", "Account is unavailable.")
    if not active and await uow.session.scalar(
        select(CompanyAccess.company_id)
        .where(CompanyAccess.user_id == user_id, CompanyAccess.role == "owner")
        .limit(1)
    ):
        raise AppError(
            409, "owner_requires_transfer", "Transfer ownership before deactivation."
        )
    user.is_active = active
    if not active:
        await uow.sessions.revoke_user(user_id)
    await uow.commit()

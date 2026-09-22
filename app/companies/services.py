from sqlalchemy import delete, update

from app.companies.domain import require_role
from app.companies.models import Company, CompanyAccess
from app.companies.schemas import AccessRead, CompanyRead
from app.exceptions.base import AppError
from app.infrastructure.logging import security_event
from app.utils.versions import ensure_version


def company_read(company, role):
    return CompanyRead(
        **{
            key: getattr(company, key)
            for key in [
                "id",
                "name",
                "description",
                "website",
                "version",
                "created_at",
                "updated_at",
            ]
        },
        current_role=role,
    )


def access_read(row):
    access, user = row
    return AccessRead(
        user_id=user.id,
        login=user.login,
        display_name=user.display_name,
        role=access.role,
        created_at=access.created_at,
        updated_at=access.updated_at,
    )


async def authorize(uow, company_id, principal, *, write=False, owner=False):
    company, role = await uow.companies.accessible(
        company_id, principal.user_id, lock=write
    )
    if write or owner:
        require_role(role, owner_only=owner)
    return company, role


async def create_company(uow, principal, data):
    user = await uow.users.lock(principal.user_id)
    if not user.is_active:
        raise AppError(401, "authentication_required", "Authentication is required.")
    company = Company(**data.model_dump())
    uow.session.add(company)
    await uow.session.flush()
    uow.session.add(
        CompanyAccess(company_id=company.id, user_id=principal.user_id, role="owner")
    )
    await uow.commit()
    return company_read(company, "owner")


async def update_company(uow, principal, company_id, data, version):
    company, role = await authorize(uow, company_id, principal, write=True)
    ensure_version(company.version, version)
    await uow.session.execute(
        update(Company)
        .where(Company.id == company_id, Company.version == version)
        .values(**data.model_dump(exclude_unset=True), version=version + 1)
    )
    await uow.session.refresh(company)
    result = company_read(company, role)
    await uow.commit()
    return result


async def delete_company(uow, principal, company_id, version):
    company, _ = await authorize(uow, company_id, principal, write=True, owner=True)
    ensure_version(company.version, version)
    await uow.session.execute(
        delete(Company).where(Company.id == company_id, Company.version == version)
    )
    await uow.commit()
    security_event("company.deleted", principal, company_id)


async def grant_access(uow, principal, company_id, data):
    await authorize(uow, company_id, principal, write=True, owner=True)
    user = await uow.users.lock(data.user_id)
    if user is None or not user.is_active:
        raise AppError(404, "target_user_not_available", "Account is unavailable.")
    if await uow.company_access.member(company_id, data.user_id):
        raise AppError(409, "access_exists", "Access already exists.")
    uow.session.add(CompanyAccess(company_id=company_id, **data.model_dump()))
    await uow.session.flush()
    result = access_read(await uow.company_access.read(company_id, data.user_id))
    await uow.commit()
    security_event("company_access.granted", principal, company_id)
    return result


async def change_access(uow, principal, company_id, user_id, role=None):
    await authorize(uow, company_id, principal, write=True, owner=True)
    access = await uow.company_access.member(company_id, user_id, lock=True)
    if access is None:
        raise AppError(404, "resource_not_found", "Resource not found.")
    if access.role == "owner":
        raise AppError(
            409, "owner_requires_transfer", "Use ownership transfer for the owner."
        )
    if role is None:
        await uow.session.delete(access)
        result = None
    else:
        access.role = role
        await uow.session.flush()
        await uow.session.refresh(access)
        result = access_read(await uow.company_access.read(company_id, user_id))
    await uow.commit()
    security_event(
        "company_access.changed" if role else "company_access.revoked",
        principal,
        company_id,
    )
    return result


async def transfer_ownership(uow, principal, company_id, data):
    _, role = await uow.companies.accessible(company_id, principal.user_id, lock=True)
    if role != "owner":
        raise AppError(409, "ownership_changed", "Ownership has changed.")
    previous = await uow.company_access.member(company_id, principal.user_id, lock=True)
    target = await uow.company_access.member(
        company_id, data.new_owner_user_id, lock=True
    )
    if target is None or target.role == "owner":
        raise AppError(
            409, "target_not_member", "Target must be an existing non-owner member."
        )
    user = await uow.users.lock(data.new_owner_user_id)
    if not user.is_active:
        raise AppError(404, "target_user_not_available", "Account is unavailable.")
    previous.role = data.previous_owner_role
    await uow.session.flush()
    target.role = "owner"
    await uow.session.flush()
    await uow.session.refresh(previous)
    await uow.session.refresh(target)
    result = [
        access_read(await uow.company_access.read(company_id, identifier))
        for identifier in [principal.user_id, data.new_owner_user_id]
    ]
    await uow.commit()
    security_event("company.ownership_transferred", principal, company_id)
    return result

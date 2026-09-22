from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from app.companies import services
from app.companies.domain import CompanyRole
from app.companies.schemas import (
    AccessGrant,
    AccessRead,
    AccessUpdate,
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
    OwnershipTransfer,
)
from app.handlers.dependencies import Principal, Uow, expensive_list
from app.utils.pagination import Page, page_result, pagination
from app.utils.versions import expected_version, set_entity_headers

router = APIRouter(prefix="/api/v1/companies", tags=["Companies"])
Limit = Annotated[int, Query(ge=1, le=100)]
Match = Annotated[str | None, Header(alias="If-Match")]


@router.post("", response_model=CompanyRead, status_code=201)
async def create(
    data: CompanyCreate, principal: Principal, uow: Uow, response: Response
):
    result = await services.create_company(uow, principal, data)
    set_entity_headers(response, result, f"/api/v1/companies/{result.id}")
    return result


@router.get("", response_model=Page[CompanyRead])
async def list_companies(
    request: Request,
    principal: Principal,
    uow: Uow,
    limit: Limit = 25,
    cursor: str | None = None,
    role: CompanyRole | None = None,
):
    codec, scope, after = pagination(
        request.app.state.settings,
        "companies",
        principal.user_id,
        {"role": role},
        cursor,
    )
    rows = await uow.companies.page(principal.user_id, role, after, limit)
    return page_result(
        rows,
        limit,
        codec,
        scope,
        lambda row: services.company_read(row[0], row[1].role),
        lambda row: (row[1].created_at, row[1].company_id),
    )


@router.get("/{company_id}", response_model=CompanyRead)
async def read(company_id: UUID, principal: Principal, uow: Uow, response: Response):
    company, role = await services.authorize(uow, company_id, principal)
    set_entity_headers(response, company)
    return services.company_read(company, role)


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company(
    company_id: UUID,
    data: CompanyUpdate,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Match = None,
):
    result = await services.update_company(
        uow, principal, company_id, data, expected_version(if_match)
    )
    set_entity_headers(response, result)
    return result


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: UUID, principal: Principal, uow: Uow, if_match: Match = None
):
    await services.delete_company(
        uow, principal, company_id, expected_version(if_match)
    )


@router.get(
    "/{company_id}/access",
    response_model=Page[AccessRead],
    dependencies=[Depends(expensive_list)],
)
async def list_access(
    company_id: UUID,
    request: Request,
    principal: Principal,
    uow: Uow,
    limit: Limit = 25,
    cursor: str | None = None,
    role: CompanyRole | None = None,
):
    await services.authorize(uow, company_id, principal, owner=True)
    codec, scope, after = pagination(
        request.app.state.settings, "access", company_id, {"role": role}, cursor
    )
    rows = await uow.company_access.page(company_id, role, after, limit)
    return page_result(
        rows,
        limit,
        codec,
        scope,
        services.access_read,
        lambda row: (row[0].created_at, row[0].user_id),
    )


@router.post("/{company_id}/access", response_model=AccessRead, status_code=201)
async def grant(
    company_id: UUID,
    data: AccessGrant,
    principal: Principal,
    uow: Uow,
    response: Response,
):
    result = await services.grant_access(uow, principal, company_id, data)
    response.headers["Location"] = (
        f"/api/v1/companies/{company_id}/access/{data.user_id}"
    )
    return result


@router.patch("/{company_id}/access/{user_id}", response_model=AccessRead)
async def change(
    company_id: UUID, user_id: UUID, data: AccessUpdate, principal: Principal, uow: Uow
):
    return await services.change_access(uow, principal, company_id, user_id, data.role)


@router.delete("/{company_id}/access/{user_id}", status_code=204)
async def revoke(company_id: UUID, user_id: UUID, principal: Principal, uow: Uow):
    await services.change_access(uow, principal, company_id, user_id)


@router.post("/{company_id}/ownership-transfer", response_model=list[AccessRead])
async def transfer(
    company_id: UUID, data: OwnershipTransfer, principal: Principal, uow: Uow
):
    return await services.transfer_ownership(uow, principal, company_id, data)

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.companies.handlers import Limit, Match
from app.companies.services import authorize
from app.employees import services
from app.employees.domain import EmploymentStatus
from app.employees.schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.handlers.dependencies import Principal, Uow, expensive_list
from app.utils.pagination import Page, page_result, pagination
from app.utils.versions import expected_version, set_entity_headers

router = APIRouter(
    prefix="/api/v1/companies/{company_id}/employees", tags=["Employees"]
)


@router.post("", response_model=EmployeeRead, status_code=201)
async def create(
    company_id: UUID,
    data: EmployeeCreate,
    principal: Principal,
    uow: Uow,
    response: Response,
):
    result = await services.create_employee(uow, principal, company_id, data)
    set_entity_headers(
        response, result, f"/api/v1/companies/{company_id}/employees/{result.id}"
    )
    return result


@router.get(
    "", response_model=Page[EmployeeRead], dependencies=[Depends(expensive_list)]
)
async def list_employees(
    company_id: UUID,
    request: Request,
    principal: Principal,
    uow: Uow,
    limit: Limit = 25,
    cursor: str | None = None,
    status: EmploymentStatus | None = None,
):
    await authorize(uow, company_id, principal)
    codec, scope, after = pagination(
        request.app.state.settings, "employees", company_id, {"status": status}, cursor
    )
    rows = await uow.employees.page(company_id, status, after, limit)
    return page_result(
        rows,
        limit,
        codec,
        scope,
        EmployeeRead.model_validate,
        lambda row: (row.created_at, row.id),
    )


@router.get("/{employee_id}", response_model=EmployeeRead)
async def read(
    company_id: UUID,
    employee_id: UUID,
    principal: Principal,
    uow: Uow,
    response: Response,
):
    await authorize(uow, company_id, principal)
    employee = await uow.employees.scoped(company_id, employee_id)
    set_entity_headers(response, employee)
    return EmployeeRead.model_validate(employee)


@router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    company_id: UUID,
    employee_id: UUID,
    data: EmployeeUpdate,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Match = None,
):
    result = await services.update_employee(
        uow, principal, company_id, employee_id, data, expected_version(if_match)
    )
    set_entity_headers(response, result)
    return result


@router.delete("/{employee_id}", status_code=204)
async def delete_employee(
    company_id: UUID,
    employee_id: UUID,
    principal: Principal,
    uow: Uow,
    if_match: Match = None,
):
    await services.delete_employee(
        uow, principal, company_id, employee_id, expected_version(if_match)
    )

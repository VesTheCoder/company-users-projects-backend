from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.companies.handlers import Limit, Match
from app.companies.services import authorize
from app.handlers.dependencies import Principal, Uow, expensive_list
from app.projects import services
from app.projects.domain import ProjectStatus
from app.projects.schemas import (
    AssignmentRead,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from app.utils.pagination import Page, page_result, pagination
from app.utils.versions import expected_version, set_entity_headers

router = APIRouter(prefix="/api/v1/companies/{company_id}/projects", tags=["Projects"])


@router.post("", response_model=ProjectRead, status_code=201)
async def create(
    company_id: UUID,
    data: ProjectCreate,
    principal: Principal,
    uow: Uow,
    response: Response,
):
    result = await services.create_project(uow, principal, company_id, data)
    set_entity_headers(
        response, result, f"/api/v1/companies/{company_id}/projects/{result.id}"
    )
    return result


@router.get(
    "", response_model=Page[ProjectRead], dependencies=[Depends(expensive_list)]
)
async def list_projects(
    company_id: UUID,
    request: Request,
    principal: Principal,
    uow: Uow,
    limit: Limit = 25,
    cursor: str | None = None,
    status: ProjectStatus | None = None,
):
    await authorize(uow, company_id, principal)
    codec, scope, after = pagination(
        request.app.state.settings, "projects", company_id, {"status": status}, cursor
    )
    rows = await uow.projects.page(company_id, status, after, limit)
    return page_result(
        rows,
        limit,
        codec,
        scope,
        ProjectRead.model_validate,
        lambda row: (row.created_at, row.id),
    )


@router.get("/{project_id}", response_model=ProjectRead)
async def read(
    company_id: UUID,
    project_id: UUID,
    principal: Principal,
    uow: Uow,
    response: Response,
):
    await authorize(uow, company_id, principal)
    project = await uow.projects.scoped(company_id, project_id)
    set_entity_headers(response, project)
    return ProjectRead.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    company_id: UUID,
    project_id: UUID,
    data: ProjectUpdate,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Match = None,
):
    result = await services.update_project(
        uow, principal, company_id, project_id, data, expected_version(if_match)
    )
    set_entity_headers(response, result)
    return result


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    company_id: UUID,
    project_id: UUID,
    principal: Principal,
    uow: Uow,
    if_match: Match = None,
):
    await services.delete_project(
        uow, principal, company_id, project_id, expected_version(if_match)
    )


@router.put(
    "/{project_id}/employees/{employee_id}",
    response_model=AssignmentRead,
    responses={201: {"model": AssignmentRead}},
)
async def assign(
    company_id: UUID,
    project_id: UUID,
    employee_id: UUID,
    principal: Principal,
    uow: Uow,
    response: Response,
):
    result, created = await services.ensure_assignment(
        uow, principal, company_id, project_id, employee_id
    )
    response.status_code = 201 if created else 200
    if created:
        response.headers["Location"] = (
            f"/api/v1/companies/{company_id}/projects/{project_id}/employees/{employee_id}"
        )
    return result


@router.delete("/{project_id}/employees/{employee_id}", status_code=204)
async def unassign(
    company_id: UUID,
    project_id: UUID,
    employee_id: UUID,
    principal: Principal,
    uow: Uow,
):
    await services.remove_assignment(
        uow, principal, company_id, project_id, employee_id
    )


@router.get(
    "/{project_id}/employees",
    response_model=Page[AssignmentRead],
    dependencies=[Depends(expensive_list)],
)
async def list_assignments(
    company_id: UUID,
    project_id: UUID,
    request: Request,
    principal: Principal,
    uow: Uow,
    limit: Limit = 25,
    cursor: str | None = None,
):
    await authorize(uow, company_id, principal)
    await uow.projects.scoped(company_id, project_id)
    codec, scope, after = pagination(
        request.app.state.settings,
        "assignments",
        company_id,
        {"project_id": str(project_id)},
        cursor,
    )
    rows = await uow.project_assignments.page(company_id, project_id, after, limit)
    return page_result(
        rows,
        limit,
        codec,
        scope,
        services.assignment_read,
        lambda row: (row[0].assigned_at, row[0].employee_id),
    )

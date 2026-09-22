from pydantic import ValidationError
from sqlalchemy import delete, update

from app.companies.services import authorize
from app.employees.schemas import EmployeeSummary
from app.exceptions.base import AppError
from app.projects.domain import validate_transition
from app.projects.models import Project, ProjectEmployee
from app.projects.schemas import AssignmentRead, ProjectCreate, ProjectRead
from app.utils.versions import ensure_version


async def create_project(uow, principal, company_id, data):
    await authorize(uow, company_id, principal, write=True)
    project = Project(company_id=company_id, **data.model_dump())
    uow.session.add(project)
    await uow.session.flush()
    result = ProjectRead.model_validate(project)
    await uow.commit()
    return result


async def update_project(uow, principal, company_id, project_id, data, version):
    await authorize(uow, company_id, principal, write=True)
    project = await uow.projects.scoped(company_id, project_id, lock=True)
    ensure_version(project.version, version)
    values = {key: getattr(project, key) for key in ProjectCreate.model_fields}
    try:
        validated = ProjectCreate.model_validate(
            values | data.model_dump(exclude_unset=True)
        )
    except ValidationError as error:
        raise AppError(
            422, "validation_error", "Project dates are inconsistent."
        ) from error
    validate_transition(project.status, validated.status)
    await uow.session.execute(
        update(Project)
        .where(
            Project.company_id == company_id,
            Project.id == project_id,
            Project.version == version,
        )
        .values(**validated.model_dump(), version=version + 1)
    )
    await uow.session.refresh(project)
    result = ProjectRead.model_validate(project)
    await uow.commit()
    return result


async def delete_project(uow, principal, company_id, project_id, version):
    await authorize(uow, company_id, principal, write=True)
    project = await uow.projects.scoped(company_id, project_id, lock=True)
    ensure_version(project.version, version)
    await uow.session.execute(
        delete(Project).where(
            Project.company_id == company_id,
            Project.id == project_id,
            Project.version == version,
        )
    )
    await uow.commit()


def assignment_read(row):
    assignment, employee = row
    return AssignmentRead(
        employee=EmployeeSummary.model_validate(employee),
        assigned_at=assignment.assigned_at,
        assigned_by_user_id=assignment.assigned_by_user_id,
    )


async def ensure_assignment(uow, principal, company_id, project_id, employee_id):
    await authorize(uow, company_id, principal, write=True)
    project = await uow.projects.scoped(company_id, project_id, lock=True)
    employee = await uow.employees.scoped(company_id, employee_id, lock=True)
    existing = await uow.project_assignments.existing(
        company_id, project_id, employee_id
    )
    if existing:
        result = assignment_read((existing, employee))
        await uow.commit()
        return result, False
    if employee.status != "active":
        raise AppError(
            409, "employee_not_active", "Only active employees can be assigned."
        )
    if project.status not in {"planned", "active"}:
        raise AppError(
            409, "project_not_assignable", "The project does not accept assignments."
        )
    assignment = ProjectEmployee(
        company_id=company_id,
        project_id=project_id,
        employee_id=employee_id,
        assigned_by_user_id=principal.user_id,
    )
    uow.session.add(assignment)
    await uow.session.flush()
    result = assignment_read((assignment, employee))
    await uow.commit()
    return result, True


async def remove_assignment(uow, principal, company_id, project_id, employee_id):
    await authorize(uow, company_id, principal, write=True)
    await uow.projects.scoped(company_id, project_id, lock=True)
    await uow.employees.scoped(company_id, employee_id, lock=True)
    await uow.session.execute(
        delete(ProjectEmployee).where(
            ProjectEmployee.company_id == company_id,
            ProjectEmployee.project_id == project_id,
            ProjectEmployee.employee_id == employee_id,
        )
    )
    await uow.commit()

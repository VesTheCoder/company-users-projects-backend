from contextlib import contextmanager

from pydantic import ValidationError
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError

from app.companies.services import authorize
from app.employees.models import Employee
from app.employees.schemas import EmployeeCreate, EmployeeRead
from app.exceptions.base import AppError
from app.projects.models import ProjectEmployee
from app.utils.normalization import normalize_identifier
from app.utils.versions import ensure_version


def employee_values(data):
    values = data.model_dump()
    values["work_email_normalized"] = (
        normalize_identifier(data.work_email) if data.work_email else None
    )
    return values


@contextmanager
def employee_conflicts():
    try:
        yield
    except IntegrityError as error:
        if "uq_employee_company_email" in str(error.orig):
            raise AppError(
                409, "work_email_exists", "Work email already exists in this company."
            ) from error
        raise


async def persist_employee(uow, employee):
    with employee_conflicts():
        await uow.session.flush()
    await uow.session.refresh(employee)
    result = EmployeeRead.model_validate(employee)
    await uow.commit()
    return result


async def create_employee(uow, principal, company_id, data):
    await authorize(uow, company_id, principal, write=True)
    employee = Employee(company_id=company_id, **employee_values(data))
    uow.session.add(employee)
    return await persist_employee(uow, employee)


async def update_employee(uow, principal, company_id, employee_id, data, version):
    await authorize(uow, company_id, principal, write=True)
    employee = await uow.employees.scoped(company_id, employee_id, lock=True)
    ensure_version(employee.version, version)
    values = {key: getattr(employee, key) for key in EmployeeCreate.model_fields}
    try:
        validated = EmployeeCreate.model_validate(
            values | data.model_dump(exclude_unset=True)
        )
    except ValidationError as error:
        raise AppError(
            422, "validation_error", "Employee status and dates are inconsistent."
        ) from error
    with employee_conflicts():
        await uow.session.execute(
            update(Employee)
            .where(
                Employee.company_id == company_id,
                Employee.id == employee_id,
                Employee.version == version,
            )
            .values(**employee_values(validated), version=version + 1)
        )
    if validated.status == "terminated":
        await uow.session.execute(
            delete(ProjectEmployee).where(
                ProjectEmployee.company_id == company_id,
                ProjectEmployee.employee_id == employee_id,
            )
        )
    return await persist_employee(uow, employee)


async def delete_employee(uow, principal, company_id, employee_id, version):
    await authorize(uow, company_id, principal, write=True)
    employee = await uow.employees.scoped(company_id, employee_id, lock=True)
    ensure_version(employee.version, version)
    await uow.session.execute(
        delete(Employee).where(
            Employee.company_id == company_id,
            Employee.id == employee_id,
            Employee.version == version,
        )
    )
    await uow.commit()

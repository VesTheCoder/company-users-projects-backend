from sqlalchemy import select

from app.employees.models import Employee
from app.exceptions.base import AppError
from app.utils.pagination import page_query


class EmployeeRepository:
    def __init__(self, session):
        self.session = session

    async def scoped(self, company_id, employee_id, *, lock=False):
        query = select(Employee).where(
            Employee.company_id == company_id, Employee.id == employee_id
        )
        if lock:
            query = query.with_for_update()
        employee = await self.session.scalar(query)
        if employee is None:
            raise AppError(404, "resource_not_found", "Resource not found.")
        return employee

    async def page(self, company_id, status, after, limit):
        query = select(Employee).where(Employee.company_id == company_id)
        if status:
            query = query.where(Employee.status == status)
        return (
            await self.session.scalars(
                page_query(query, Employee.created_at, Employee.id, after, limit)
            )
        ).all()

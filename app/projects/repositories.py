from sqlalchemy import select

from app.employees.models import Employee
from app.exceptions.base import AppError
from app.projects.models import Project, ProjectEmployee
from app.utils.pagination import page_query


class ProjectRepository:
    def __init__(self, session):
        self.session = session

    async def scoped(self, company_id, project_id, *, lock=False):
        query = select(Project).where(
            Project.company_id == company_id, Project.id == project_id
        )
        if lock:
            query = query.with_for_update()
        project = await self.session.scalar(query)
        if project is None:
            raise AppError(404, "resource_not_found", "Resource not found.")
        return project

    async def page(self, company_id, status, after, limit):
        query = select(Project).where(Project.company_id == company_id)
        if status:
            query = query.where(Project.status == status)
        return (
            await self.session.scalars(
                page_query(query, Project.created_at, Project.id, after, limit)
            )
        ).all()


class AssignmentRepository:
    def __init__(self, session):
        self.session = session

    async def existing(self, company_id, project_id, employee_id):
        return await self.session.get(
            ProjectEmployee, (company_id, project_id, employee_id)
        )

    async def page(self, company_id, project_id, after, limit):
        query = (
            select(ProjectEmployee, Employee)
            .join(
                Employee,
                (Employee.id == ProjectEmployee.employee_id)
                & (Employee.company_id == ProjectEmployee.company_id),
            )
            .where(
                ProjectEmployee.company_id == company_id,
                ProjectEmployee.project_id == project_id,
            )
        )
        return (
            await self.session.execute(
                page_query(
                    query,
                    ProjectEmployee.assigned_at,
                    ProjectEmployee.employee_id,
                    after,
                    limit,
                )
            )
        ).all()

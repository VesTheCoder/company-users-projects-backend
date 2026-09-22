from datetime import date, datetime
from uuid import UUID

from pydantic import ConfigDict, field_validator, model_validator

from app.auth.schemas import Name, RequestSchema
from app.companies.schemas import Description
from app.employees.schemas import EmployeeSummary
from app.projects.domain import ProjectStatus


class ProjectCreate(RequestSchema):
    name: Name
    description: Description | None = None
    status: ProjectStatus = ProjectStatus.PLANNED
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date is not None and (
            self.start_date is None or self.end_date < self.start_date
        ):
            raise ValueError("End date requires an earlier or equal start date")
        return self


class ProjectUpdate(RequestSchema):
    name: Name | None = None
    description: Description | None = None
    status: ProjectStatus | None = None
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("name", "status")
    @classmethod
    def reject_null_required(cls, value):
        if value is None:
            raise ValueError("Required fields cannot be null")
        return value


class ProjectRead(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime


class AssignmentRead(RequestSchema):
    employee: EmployeeSummary
    assigned_at: datetime
    assigned_by_user_id: UUID

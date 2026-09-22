from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.auth.schemas import Login, Name, RequestSchema
from app.employees.domain import EmploymentStatus, validate_employment_dates


class EmployeeCreate(RequestSchema):
    full_name: Name
    work_email: Login | None = None
    work_phone: Annotated[str, Field(pattern=r"^\+[1-9][0-9]{1,14}$")] | None = None
    job_title: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    status: EmploymentStatus = EmploymentStatus.ACTIVE
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        validate_employment_dates(self.status, self.start_date, self.end_date)
        return self


class EmployeeUpdate(RequestSchema):
    full_name: Name | None = None
    work_email: Login | None = None
    work_phone: Annotated[str, Field(pattern=r"^\+[1-9][0-9]{1,14}$")] | None = None
    job_title: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    status: EmploymentStatus | None = None
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("full_name", "status", "start_date")
    @classmethod
    def reject_null_required(cls, value):
        if value is None:
            raise ValueError("Required fields cannot be null")
        return value


class EmployeeRead(EmployeeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime


class EmployeeSummary(RequestSchema):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    full_name: str
    job_title: str | None
    status: EmploymentStatus

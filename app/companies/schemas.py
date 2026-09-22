from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.auth.schemas import Name, RequestSchema

Description = Annotated[str, Field(max_length=5000)]


class CompanyCreate(RequestSchema):
    name: Name
    description: Description | None = None
    website: str | None = Field(default=None, max_length=2048)

    @field_validator("website")
    @classmethod
    def validate_website(cls, value):
        return str(HttpUrl(value)) if value is not None else None


class CompanyUpdate(CompanyCreate):
    name: Name | None = None

    @field_validator("name")
    @classmethod
    def reject_null_name(cls, value):
        if value is None:
            raise ValueError("Name cannot be null")
        return value


class CompanyRead(CompanyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    current_role: str


class AccessGrant(RequestSchema):
    user_id: UUID
    role: Literal["admin", "viewer"]


class AccessUpdate(RequestSchema):
    role: Literal["admin", "viewer"]


class AccessRead(BaseModel):
    user_id: UUID
    login: str
    display_name: str
    role: str
    created_at: datetime
    updated_at: datetime


class OwnershipTransfer(RequestSchema):
    new_owner_user_id: UUID
    previous_owner_role: Literal["admin", "viewer"]

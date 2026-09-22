from datetime import datetime
from typing import Annotated
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

from app.utils.normalization import normalize_identifier, normalize_text


def validate_login(value: str) -> str:
    if len(normalize_identifier(value)) > 254:
        raise ValueError("Normalized login is too long")
    try:
        validate_email(value, check_deliverability=False, test_environment=True)
    except EmailNotValidError as error:
        raise ValueError("A valid email-like login is required") from error
    return value


Login = Annotated[
    str,
    BeforeValidator(normalize_text),
    Field(min_length=3, max_length=254),
    AfterValidator(validate_login),
]
Name = Annotated[
    str, BeforeValidator(normalize_text), Field(min_length=1, max_length=200)
]


class RequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(RequestSchema):
    login: Login
    password: str = Field(min_length=1, max_length=1024)


class AccountCreate(RequestSchema):
    login: Login
    display_name: Name


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    login: str
    display_name: str


class LoginResponse(BaseModel):
    user: UserRead
    csrf_token: str
    expires_at: datetime


class CurrentUserRead(UserRead):
    expires_at: datetime

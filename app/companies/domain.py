from enum import StrEnum

from app.exceptions.base import AppError


class CompanyRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    VIEWER = "viewer"


def require_role(role: str, *, owner_only: bool = False):
    allowed = (
        {CompanyRole.OWNER} if owner_only else {CompanyRole.OWNER, CompanyRole.ADMIN}
    )
    if role not in allowed:
        raise AppError(403, "permission_denied", "Permission denied.")

from datetime import date

import pytest

from app.companies.domain import require_role
from app.employees.domain import validate_employment_dates
from app.exceptions.base import AppError
from app.projects.domain import validate_transition


@pytest.mark.parametrize(
    "role,owner,allowed",
    [
        ("owner", True, True),
        ("admin", True, False),
        ("admin", False, True),
        ("viewer", False, False),
    ],
)
def test_permission_matrix(role, owner, allowed):
    if allowed:
        require_role(role, owner_only=owner)
    else:
        with pytest.raises(AppError):
            require_role(role, owner_only=owner)


@pytest.mark.parametrize(
    "previous,target,allowed",
    [
        ("planned", "active", True),
        ("active", "completed", True),
        ("completed", "active", False),
        ("cancelled", "planned", False),
        ("active", "active", True),
    ],
)
def test_project_transition_matrix(previous, target, allowed):
    if allowed:
        validate_transition(previous, target)
    else:
        with pytest.raises(AppError):
            validate_transition(previous, target)


def test_termination_requires_ordered_dates():
    with pytest.raises(ValueError):
        validate_employment_dates("terminated", date(2026, 1, 1), None)
    with pytest.raises(ValueError):
        validate_employment_dates("terminated", date(2026, 1, 1), date(2025, 1, 1))

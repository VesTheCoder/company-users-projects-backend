from enum import StrEnum

from app.exceptions.base import AppError


class ProjectStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def validate_transition(previous: str, target: str):
    transitions = {
        "planned": {"active", "cancelled"},
        "active": {"completed", "cancelled"},
        "completed": set(),
        "cancelled": set(),
    }
    if previous != target and target not in transitions[previous]:
        raise AppError(
            409,
            "invalid_project_transition",
            "Project status transition is not allowed.",
        )

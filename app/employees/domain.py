from enum import StrEnum


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    LEAVE = "leave"
    TERMINATED = "terminated"


def validate_employment_dates(status, start_date, end_date):
    if (status == EmploymentStatus.TERMINATED) != (end_date is not None):
        raise ValueError("Only terminated employees require an end date")
    if end_date is not None and end_date < start_date:
        raise ValueError("End date precedes start date")

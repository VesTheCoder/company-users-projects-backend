import re

from app.exceptions.base import AppError


def expected_version(header: str | None) -> int:
    if header is None:
        raise AppError(428, "precondition_required", "If-Match is required.")
    if not re.fullmatch(r'"v[1-9][0-9]*"', header):
        raise AppError(412, "precondition_failed", "Invalid entity tag.")
    return int(header[2:-1])


def ensure_version(actual: int, expected: int):
    if actual != expected:
        raise AppError(412, "precondition_failed", "The resource has changed.")


def set_entity_headers(response, record, location=None):
    response.headers["ETag"] = f'"v{record.version}"'
    if location:
        response.headers["Location"] = location

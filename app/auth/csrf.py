import hmac
from urllib.parse import urlsplit

from app.config import normalize_origin
from app.exceptions.base import AppError
from app.utils.security import decode_token


def validate_origin(headers, settings):
    origin = headers.get("origin")
    if origin is None and headers.get("referer"):
        parsed = urlsplit(headers["referer"])
        origin = f"{parsed.scheme}://{parsed.netloc}"
    try:
        origin = normalize_origin(origin or "")
    except ValueError:
        origin = None
    if origin not in {settings.api_public_origin, *settings.cors_allowed_origins}:
        raise AppError(403, "csrf_origin_invalid", "Request origin is not trusted.")


def validate_csrf(headers, expected: bytes):
    try:
        supplied = decode_token(headers.get("x-csrf-token", ""))
    except ValueError:
        supplied = b""
    if not hmac.compare_digest(supplied, expected):
        raise AppError(403, "csrf_token_invalid", "A valid CSRF token is required.")


def validate_login_csrf(headers, settings):
    validate_origin(headers, settings)
    if (
        headers.get("x-csrf-protection") != "1"
        or headers.get("content-type", "").split(";")[0].strip().lower()
        != "application/json"
    ):
        raise AppError(
            403, "login_csrf_invalid", "JSON and CSRF protection are required."
        )

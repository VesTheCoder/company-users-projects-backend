from http import HTTPStatus

from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from sqlalchemy.exc import DBAPIError, IntegrityError, TimeoutError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.exceptions.base import AppError


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    request_id: str
    errors: list[dict] = []


def problem_response(request, status, code, detail, *, headers=None, errors=None):
    settings = request.app.state.settings
    body = ProblemDetail(
        type=f"{settings.problem_type_base_uri}/{code.replace('_', '-')}",
        title=HTTPStatus(status).phrase,
        status=status,
        detail=detail,
        instance=request.url.path,
        code=code,
        request_id=getattr(request.state, "request_id", ""),
        errors=errors or [],
    )
    headers = {"X-Request-ID": body.request_id, **(headers or {})}
    return JSONResponse(
        body.model_dump(),
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
    )


def register_error_handlers(app):
    @app.exception_handler(AppError)
    async def application_error(request, error):
        if error.code == "rate_limit_exceeded":
            request.app.state.metrics.limiter_rejections.inc()
        elif error.code == "rate_limiter_unavailable":
            request.app.state.metrics.limiter_failures.inc()
        return problem_response(
            request, error.status, error.code, error.detail, headers=error.headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        errors = [
            {
                "pointer": "/" + "/".join(map(str, e["loc"][1:])),
                "code": e["type"],
                "message": "Invalid field value.",
            }
            for e in error.errors()
        ]
        return problem_response(
            request,
            422,
            "validation_error",
            "One or more fields are invalid.",
            errors=errors,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return problem_response(
            request,
            error.status_code,
            "http_error",
            HTTPStatus(error.status_code).phrase,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error(request, error):
        return problem_response(
            request,
            409,
            "resource_conflict",
            "The operation conflicts with existing data.",
        )

    @app.exception_handler(DBAPIError)
    @app.exception_handler(TimeoutError)
    async def database_error(request, error):
        if isinstance(error, TimeoutError):
            request.app.state.metrics.pool_timeouts.inc()
        return problem_response(
            request,
            503,
            "database_unavailable",
            "The database is temporarily unavailable.",
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request, error):
        return problem_response(
            request, 500, "internal_error", "An unexpected error occurred."
        )

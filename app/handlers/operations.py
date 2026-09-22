import asyncio
import hmac

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.exceptions.base import AppError

router = APIRouter(tags=["Operations"])


@router.get("/health/live")
async def live():
    return {"status": "ok"}


@router.get("/health/ready", responses={503: {"description": "Dependency unavailable"}})
async def ready(request: Request, response: Response):
    async def database_check():
        async with request.app.state.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def bounded(check):
        try:
            async with asyncio.timeout(3):
                await check()
            return "ok"
        except Exception:
            return "unavailable"

    database, redis = await asyncio.gather(
        bounded(database_check), bounded(request.app.state.redis.ping)
    )
    if database != "ok" or redis != "ok":
        response.status_code = 503
    return {
        "status": "ok" if database == redis == "ok" else "unavailable",
        "database": database,
        "rate_limiter": redis,
    }


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request):
    settings = request.app.state.settings
    if not settings.metrics_enabled:
        raise AppError(404, "resource_not_found", "Resource not found.")
    expected = request.app.state.metrics_token
    if expected and not hmac.compare_digest(
        request.headers.get("authorization", ""), f"Bearer {expected}"
    ):
        raise AppError(401, "authentication_required", "Authentication is required.")
    return Response(
        generate_latest(request.app.state.metrics.registry),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )

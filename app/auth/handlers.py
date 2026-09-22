from fastapi import APIRouter, Request, Response
from sqlalchemy import func, update

from app.auth.csrf import validate_login_csrf
from app.auth.models import AuthSession
from app.auth.schemas import CurrentUserRead, LoginRequest, LoginResponse
from app.auth.services import login
from app.exceptions.base import AppError
from app.handlers.dependencies import Principal, Uow
from app.infrastructure.logging import security_event
from app.infrastructure.rate_limit import RateLimitCategory
from app.utils.security import encode_token

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login_handler(
    data: LoginRequest, request: Request, response: Response, uow: Uow
):
    settings = request.app.state.settings
    validate_login_csrf(request.headers, settings)
    for category, subject in [
        (RateLimitCategory.LOGIN_IP, request.client.host),
        (RateLimitCategory.LOGIN_ACCOUNT, data.login),
    ]:
        response.headers.update(
            await request.app.state.limiter.check(category, subject)
        )
    try:
        result, credential = await login(
            uow, request.app.state.passwords, data, settings
        )
    except AppError:
        security_event("auth.login.failed")
        raise
    request.state.actor_user_id = result.user.id
    security_event("auth.login.succeeded")
    response.set_cookie(
        settings.cookie_name,
        credential,
        max_age=settings.session_ttl_seconds,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, uow: Uow, principal: Principal):
    await uow.session.execute(
        update(AuthSession)
        .where(AuthSession.id == principal.session_id)
        .values(revoked_at=func.now())
    )
    await uow.commit()
    security_event("auth.logout", principal)
    settings = request.app.state.settings
    response.delete_cookie(
        settings.cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.get("/me", response_model=CurrentUserRead)
async def me(principal: Principal, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return CurrentUserRead(
        id=principal.user_id,
        login=principal.login,
        display_name=principal.display_name,
        expires_at=principal.expires_at,
    )


@router.get("/csrf")
async def csrf(principal: Principal, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": encode_token(principal.csrf_token)}

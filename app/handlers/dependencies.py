from typing import Annotated

from fastapi import Depends, Request, Response

from app.auth.csrf import validate_csrf, validate_origin
from app.auth.domain import CurrentPrincipal
from app.auth.services import SessionAuthenticator
from app.infrastructure.rate_limit import RateLimitCategory
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def get_uow(request: Request):
    async with SqlAlchemyUnitOfWork(request.app.state.session_factory) as uow:
        yield uow


Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


async def current_principal(request: Request, response: Response, uow: Uow):
    settings = request.app.state.settings
    principal = await SessionAuthenticator().authenticate(
        uow, request.cookies.get(settings.cookie_name)
    )
    headers = await request.app.state.limiter.check(
        RateLimitCategory.GENERAL, str(principal.user_id)
    )
    response.headers.update(headers)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        validate_origin(request.headers, settings)
        validate_csrf(request.headers, principal.csrf_token)
    request.state.actor_user_id = principal.user_id
    return principal


Principal = Annotated[CurrentPrincipal, Depends(current_principal)]


async def expensive_list(request: Request, response: Response, principal: Principal):
    response.headers.update(
        await request.app.state.limiter.check(
            RateLimitCategory.EXPENSIVE, str(principal.user_id)
        )
    )

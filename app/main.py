from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.auth.handlers import router as auth_router
from app.auth.passwords import PasswordHasherService
from app.companies.handlers import router as company_router
from app.config import Settings
from app.employees.handlers import router as employee_router
from app.handlers.errors import register_error_handlers
from app.handlers.middleware import TransportMiddleware
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.rate_limit import RateLimiter
from app.infrastructure.redis import create_redis
from app.projects.handlers import router as project_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        engine = create_engine(settings)
        redis = create_redis(settings)
        app.state.session_factory = create_session_factory(engine)
        app.state.engine = engine
        app.state.redis = redis
        limiter = RateLimiter(
            settings.redis_rate_limit_url.get_secret_value(),
            settings.rate_limit_key_secret.get_secret_value(),
        )
        app.state.limiter = limiter
        passwords = PasswordHasherService(settings.password_hash_concurrency)
        await passwords.initialize()
        app.state.passwords = passwords
        try:
            yield
        finally:
            await limiter.close()
            await redis.aclose()
            await engine.dispose()

    app = FastAPI(
        title="Company Management API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.state.settings = settings
    app.include_router(auth_router)
    app.include_router(company_router)
    app.include_router(employee_router)
    app.include_router(project_router)
    register_error_handlers(app)
    app.add_middleware(TransportMiddleware, trusted_hosts=settings.trusted_hosts)

    @app.get("/health/live", tags=["Operations"])
    async def live():
        return {"status": "ok"}

    wrapped = CORSMiddleware(
        app,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Content-Type",
            "X-CSRF-Token",
            "X-CSRF-Protection",
            "X-Request-ID",
            "If-Match",
            "Idempotency-Key",
        ],
        expose_headers=[
            "X-Request-ID",
            "ETag",
            "Location",
            "RateLimit-Limit",
            "RateLimit-Remaining",
            "RateLimit-Reset",
            "Retry-After",
        ],
        max_age=600,
    )
    wrapped.state = app.state
    wrapped.router = app.router
    wrapped.openapi = app.openapi
    wrapped.title = app.title
    return wrapped

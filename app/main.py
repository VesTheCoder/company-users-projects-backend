from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.redis import create_redis


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        engine = create_engine(settings)
        redis = create_redis(settings)
        app.state.session_factory = create_session_factory(engine)
        app.state.engine = engine
        app.state.redis = redis
        try:
            yield
        finally:
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
    return app

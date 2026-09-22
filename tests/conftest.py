import pytest

from app.config import Settings


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        app_env="development",
        api_public_origin="http://localhost:8080",
        cors_allowed_origins=["http://localhost:5173"],
        cookie_secure=False,
        db_host="localhost",
        db_name="company_test",
        db_user="test",
        db_password="test",
        redis_rate_limit_url="redis://localhost:6379/0",
        rate_limit_key_secret="r" * 32,
        cursor_signing_key="c" * 32,
    )

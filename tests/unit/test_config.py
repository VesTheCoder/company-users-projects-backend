import pytest
from pydantic import ValidationError

from app.config import Settings, normalize_origin
from app.infrastructure.database import create_engine


@pytest.mark.parametrize(
    "origin",
    ["null", "https://*.test", "http://a/path", "http://u:p@a", "http://a?x=1"],
)
def test_invalid_origins_are_rejected(origin):
    with pytest.raises(ValueError):
        normalize_origin(origin)


def test_default_origin_ports_are_normalized():
    assert normalize_origin("https://EXAMPLE.com:443") == "https://example.com"


def test_database_password_is_escaped(settings):
    settings.db_password = type(settings.db_password)("p@ss/word")
    assert "p%40ss%2Fword" in settings.database_url.render_as_string(
        hide_password=False
    )


def test_production_rejects_insecure_configuration(settings):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **(settings.model_dump() | {"app_env": "production"}))


async def test_database_pool_is_bounded(settings):
    engine = create_engine(settings)
    assert engine.pool.size() == 10
    await engine.dispose()

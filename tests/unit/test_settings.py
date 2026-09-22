from app.infrastructure.database import create_engine


def test_database_password_is_escaped(settings):
    settings.db_password = type(settings.db_password)("p@ss/word")
    assert "p%40ss%2Fword" in settings.database_url.render_as_string(
        hide_password=False
    )


async def test_database_pool_is_bounded(settings):
    engine = create_engine(settings)
    assert engine.pool.size() == 10
    await engine.dispose()

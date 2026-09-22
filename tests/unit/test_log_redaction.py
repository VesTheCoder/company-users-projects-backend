from app.infrastructure.logging import redact_log


def test_log_allowlist_drops_secrets_and_unstructured_content():
    result = redact_log(
        None,
        "info",
        {
            "event": "auth.login.failed",
            "password": "secret",
            "cookie": "secret",
            "url": "postgres://secret",
            "headers": {"Authorization": "secret"},
        },
    )
    assert result == {"event": "auth.login.failed"}

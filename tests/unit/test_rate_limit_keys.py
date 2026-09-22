from app.infrastructure.rate_limit import RateLimitCategory, build_rate_key


def test_login_keys_normalize_and_hide_identifiers():
    first = build_rate_key(
        "secret", RateLimitCategory.LOGIN_ACCOUNT, " User@Example.COM "
    )
    second = build_rate_key(
        "secret", RateLimitCategory.LOGIN_ACCOUNT, "user@example.com"
    )
    assert first == second
    assert "example" not in first


def test_equivalent_ipv6_addresses_share_key():
    assert build_rate_key("key", RateLimitCategory.LOGIN_IP, "::1") == build_rate_key(
        "key", RateLimitCategory.LOGIN_IP, "0:0:0:0:0:0:0:1"
    )

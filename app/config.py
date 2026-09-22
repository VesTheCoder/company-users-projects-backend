from functools import cached_property
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


def normalize_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
        or "*" in value
    ):
        raise ValueError("An exact HTTP origin without a path is required")
    port = parsed.port
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    suffix = (
        f":{port}" if port and port != {"http": 80, "https": 443}[parsed.scheme] else ""
    )
    return f"{parsed.scheme}://{host}{suffix}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"]
    api_public_origin: str
    cors_allowed_origins: list[str] = []
    trusted_hosts: list[str] = ["localhost", "127.0.0.1"]
    forwarded_allow_ips: str = ""
    cookie_secure: bool = True
    session_ttl_seconds: Literal[28800] = 28800
    db_host: str
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str
    db_user: str
    db_password: SecretStr
    db_migration_user: str | None = None
    db_migration_password: SecretStr | None = None
    db_sslmode: Literal["disable", "require", "verify-full"] = "disable"
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=5, ge=0)
    db_pool_timeout_seconds: int = 5
    db_statement_timeout_ms: int = 5000
    redis_rate_limit_url: SecretStr
    rate_limit_key_secret: SecretStr
    cursor_signing_key: SecretStr
    password_hash_concurrency: int = Field(default=2, ge=1, le=8)
    docs_enabled: bool | None = None
    metrics_enabled: bool | None = None
    metrics_bearer_token_file: str | None = None
    allow_demo_seed: bool = False
    demo_password_file: str | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    problem_type_base_uri: str = "https://api.example.com/problems"

    @field_validator("api_public_origin")
    @classmethod
    def validate_origin(cls, value: str) -> str:
        return normalize_origin(value)

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        origins = [normalize_origin(value) for value in values]
        if len(set(origins)) != len(origins):
            raise ValueError("Duplicate origins are forbidden")
        return origins

    @field_validator("rate_limit_key_secret", "cursor_signing_key")
    @classmethod
    def validate_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode()) < 32:
            raise ValueError("Signing secrets must contain at least 32 bytes")
        return value

    @model_validator(mode="after")
    def validate_security(self):
        if self.rate_limit_key_secret == self.cursor_signing_key:
            raise ValueError("Signing secrets must be distinct")
        redis = urlsplit(self.redis_rate_limit_url.get_secret_value())
        if redis.scheme not in {"redis", "rediss"} or not redis.hostname:
            raise ValueError("Invalid Redis URL")
        if "*" in self.forwarded_allow_ips or any("*" in h for h in self.trusted_hosts):
            raise ValueError("Wildcard trust is forbidden")
        if not self.cookie_secure and self.app_env != "development":
            raise ValueError("Insecure cookies are development-only")
        if self.app_env == "production":
            origins = [self.api_public_origin, *self.cors_allowed_origins]
            if any(
                not o.startswith("https://")
                or urlsplit(o).hostname in {"localhost", "127.0.0.1", "::1"}
                for o in origins
            ):
                raise ValueError("Production requires public HTTPS origins")
            if self.db_sslmode != "verify-full" or not self.trusted_hosts:
                raise ValueError("Production requires verified database TLS and hosts")
            if self.metrics_enabled and not self.metrics_bearer_token_file:
                raise ValueError("Production metrics require a protected token file")
        if self.docs_enabled is None:
            self.docs_enabled = self.app_env != "production"
        if self.metrics_enabled is None:
            self.metrics_enabled = self.app_env != "production"
        return self

    @cached_property
    def database_url(self) -> URL:
        return self.build_database_url(self.db_user, self.db_password)

    @cached_property
    def migration_database_url(self) -> URL:
        if not self.db_migration_user or not self.db_migration_password:
            raise ValueError("Migration credentials are required")
        return self.build_database_url(
            self.db_migration_user, self.db_migration_password
        )

    def build_database_url(self, user: str, password: SecretStr) -> URL:
        return URL.create(
            "postgresql+asyncpg",
            username=user,
            password=password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def cookie_name(self) -> str:
        return "__Host-session" if self.cookie_secure else "session"

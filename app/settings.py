from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str
    api_public_origin: str
    cors_allowed_origins: list[str] = []
    trusted_hosts: list[str] = ["localhost", "127.0.0.1"]
    cookie_secure: bool = True
    session_ttl_seconds: int = 28800
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: SecretStr
    db_migration_user: str | None = None
    db_migration_password: SecretStr | None = None
    db_sslmode: str = "disable"
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_pool_timeout_seconds: int = 5
    db_statement_timeout_ms: int = 5000
    redis_rate_limit_url: SecretStr
    rate_limit_key_secret: SecretStr
    cursor_signing_key: SecretStr
    password_hash_concurrency: int = 2
    docs_enabled: bool = True
    metrics_enabled: bool = True
    metrics_bearer_token_file: str | None = None
    allow_demo_seed: bool = False
    demo_password_file: str | None = None
    log_level: str = "INFO"
    problem_type_base_uri: str = "https://api.example.com/problems"

    @property
    def database_url(self) -> URL:
        return self.build_database_url(self.db_user, self.db_password)

    @property
    def migration_database_url(self) -> URL:
        return self.build_database_url(
            self.db_migration_user, self.db_migration_password
        )

    def build_database_url(self, user, password) -> URL:
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

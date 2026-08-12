from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    The defaults are safe for local development. Production values should come
    from GitLab CI/CD variables, Docker secrets, or the runtime environment.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="UKB_", extra="ignore")

    app_name: str = "Unified Knowledge Base"
    environment: str = Field(default="local", description="local, dev, stage, prod")
    log_level: str = "INFO"

    # API auth is intentionally stubbed in the scaffold.
    api_token: str = "dev-token-change-me"

    # Local web UI origins. Keep explicit origins instead of wildcarding because
    # the React app will eventually carry authenticated user sessions.
    cors_allow_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173"
    )

    # Future persistence targets.
    database_url: str = "sqlite:///./ukb-dev.db"
    object_store_url: str = "file://./.ukb/object-store"

    # MCP settings.
    mcp_server_name: str = "unified-knowledge-base"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

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

    # Future persistence targets.
    database_url: str = "sqlite:///./ukb-dev.db"
    object_store_url: str = "file://./.ukb/object-store"

    # MCP settings.
    mcp_server_name: str = "unified-knowledge-base"


@lru_cache
def get_settings() -> Settings:
    return Settings()

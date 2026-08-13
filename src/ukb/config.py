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

    # AI enrichment. The default is deterministic and offline-safe. Hosted model
    # calls must be enabled explicitly through server-side environment config.
    ai_enrichment_enabled: bool = True
    ai_mode: str = "offline_no_model"
    ai_provider: str = "noop"
    ai_base_url: str = "http://localhost:11434"
    ai_chat_model: str = "deterministic"
    ai_embedding_model: str = "embeddinggemma"
    ai_max_input_chars: int = 20000
    ai_timeout_seconds: int = 45
    allow_hosted_ai_for_restricted: bool = False
    store_ai_prompts: bool = False
    store_ai_outputs: bool = True

    # Optional hosted provider settings. Never expose these to the React app.
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com"
    openai_model: str = "gpt-4o-mini"

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

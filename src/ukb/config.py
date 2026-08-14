from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    The defaults are safe for local development and intentionally route LLM
    enrichment to a local Ollama runtime. Production values should come from
    GitLab CI/CD variables, Docker secrets, or the runtime environment.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="UKB_", extra="ignore")

    app_name: str = "Unified Knowledge Base"
    environment: str = Field(default="local", description="local, dev, stage, prod")
    log_level: str = "INFO"

    # Shared-secret auth for mutating and privileged endpoints. This is a
    # single-tenant stopgap until SSO/OIDC lands; it is enforced by default so
    # the gap cannot go unnoticed. Rotate api_token away from the shipped
    # default before exposing the API beyond localhost.
    api_token: str = "dev-token-change-me"
    require_auth: bool = True
    default_api_token: str = "dev-token-change-me"

    # Access policy. The scaffold has no identity provider, so every caller gets
    # default_user_clearance unless listed in user_clearances as
    # "user:level,user2:level". Objects above the caller's clearance are dropped
    # before a context pack is composed.
    default_user_clearance: str = "internal"
    user_clearances: str = ""

    # Local web UI origins. Keep explicit origins instead of wildcarding because
    # the React app will eventually carry authenticated user sessions.
    cors_allow_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173"
    )

    # AI enrichment defaults to local Ollama. If Ollama is unavailable, the
    # AIEnrichmentService falls back to NoopProvider so review workflows still run.
    ai_enrichment_enabled: bool = True
    ai_mode: str = "local_ai"
    ai_provider: str = "ollama"
    ai_base_url: str = "http://localhost:11434"
    ai_chat_model: str = "llama3.1"
    ai_embedding_model: str = "embeddinggemma"
    ai_max_input_chars: int = 20000
    ai_timeout_seconds: int = 45
    allow_hosted_ai_for_restricted: bool = False
    store_ai_prompts: bool = False
    store_ai_outputs: bool = True

    # Hosted provider settings remain present for future/private extensions, but
    # they are not the default UKB path. Never expose these to the React app.
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com"
    openai_model: str = "gpt-4o-mini"

    # Future persistence targets.
    database_url: str = "sqlite:///./ukb-dev.db"
    object_store_url: str = "file://./.ukb/object-store"

    # MCP settings.
    mcp_server_name: str = "unified-knowledge-base"

    # MCP agents may submit and read context, but approval is a human gate.
    # Enabling this hands an LLM client the publish button; keep it off.
    mcp_allow_approval: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def api_token_is_default(self) -> bool:
        return self.api_token == self.default_api_token


@lru_cache
def get_settings() -> Settings:
    return Settings()

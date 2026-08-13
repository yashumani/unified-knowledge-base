from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Code defaults remain safe for tests. Environment files opt local and
    production runtimes into durable SQL storage, local Ollama, and Zvec.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="UKB_", extra="ignore")

    app_name: str = "Unified Knowledge Base"
    environment: str = Field(default="local", description="local, dev, stage, prod")
    log_level: str = "INFO"

    api_token: str = "dev-token-change-me"

    cors_allow_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173"
    )

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

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com"
    openai_model: str = "gpt-4o-mini"

    store_backend: str = "memory"
    database_url: str = "sqlite+pysqlite:///./.ukb/ukb.db"
    object_store_url: str = "file://./.ukb/object-store"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_extracted_chars: int = 250000

    # Zvec is a derived local index. The SQL store remains authoritative.
    search_backend: str = "memory"
    search_sync_on_query: bool = True
    zvec_path: str = "./.ukb/zvec/approved-knowledge"
    zvec_collection_name: str = "ukb_approved_knowledge"

    # Web collection is disabled until administrators configure an allowlist.
    web_connector_enabled: bool = False
    web_allowed_hosts: str = ""
    web_allowed_ports: str = "80,443"
    web_allow_private_networks: bool = False
    web_respect_robots: bool = True
    web_robots_fail_closed: bool = True
    web_user_agent: str = "UKB-Knowledge-Connector/0.1"
    web_timeout_seconds: int = 20
    web_max_response_bytes: int = 5 * 1024 * 1024
    web_max_redirects: int = 5

    mcp_server_name: str = "unified-knowledge-base"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def web_hosts(self) -> list[str]:
        return [host.strip().casefold() for host in self.web_allowed_hosts.split(",") if host.strip()]

    @property
    def web_ports(self) -> list[int]:
        return [int(port.strip()) for port in self.web_allowed_ports.split(",") if port.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Unified Knowledge Base runtime configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="UKB_", extra="ignore")

    app_name: str = "Unified Knowledge Base"
    environment: str = Field(default="local", description="local, dev, stage, prod")
    log_level: str = "INFO"

    api_token: str = "dev-token-change-me"
    api_tokens_json: str = "{}"
    require_auth: bool = True
    default_api_token: str = "dev-token-change-me"
    oidc_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_audience: str | None = None

    default_user_clearance: str = "internal"
    user_clearances: str = ""
    reviewer_roles: str = "reviewer,governance_admin"
    publisher_roles: str = "publisher,governance_admin"

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
    ai_max_input_chars: int = 100000
    ai_timeout_seconds: int = 45
    ai_schema_version: str = "2.0"
    allow_hosted_ai_for_restricted: bool = False
    store_ai_prompts: bool = False
    store_ai_outputs: bool = True

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com"
    openai_model: str = "gpt-4o-mini"

    store_backend: str = "memory"
    database_url: str = "sqlite+pysqlite:///./.ukb/ukb.db"
    object_store_url: str = "file://./.ukb/object-store"
    create_schema_on_startup: bool = True

    max_upload_bytes: int = 25 * 1024 * 1024
    max_batch_files: int = 250
    max_archive_bytes: int = 50 * 1024 * 1024
    max_archive_uncompressed_bytes: int = 250 * 1024 * 1024
    max_extracted_chars: int = 2_000_000
    evidence_chunk_chars: int = 2200
    evidence_chunk_overlap: int = 200
    require_owner_for_publish: bool = True

    search_backend: str = "memory"
    search_sync_on_query: bool = True
    zvec_path: str = "./.ukb/zvec/approved-knowledge-v2"
    zvec_collection_name: str = "ukb_approved_knowledge_v2"

    web_connector_enabled: bool = False
    web_allowed_hosts: str = ""
    web_allowed_ports: str = "80,443"
    web_allow_private_networks: bool = False
    web_respect_robots: bool = True
    web_robots_fail_closed: bool = True
    web_user_agent: str = "UKB-Knowledge-Connector/0.2"
    web_timeout_seconds: int = 20
    web_max_response_bytes: int = 5 * 1024 * 1024
    web_max_redirects: int = 5

    crawl4ai_enabled: bool = False
    crawl4ai_base_url: str = "http://crawl4ai:11235"
    crawl4ai_api_token: str | None = None
    crawl4ai_timeout_seconds: int = 90
    crawl4ai_max_pages: int = 25

    google_drive_enabled: bool = False
    google_drive_access_token: str | None = None
    google_drive_timeout_seconds: int = 30

    mcp_server_name: str = "unified-knowledge-base"
    mcp_allow_approval: bool = False
    mcp_allow_publication: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def web_hosts(self) -> list[str]:
        return [host.strip().casefold() for host in self.web_allowed_hosts.split(",") if host.strip()]

    @property
    def web_ports(self) -> list[int]:
        return [int(port.strip()) for port in self.web_allowed_ports.split(",") if port.strip()]

    @property
    def api_token_is_default(self) -> bool:
        return self.api_token == self.default_api_token

    @property
    def reviewer_role_set(self) -> set[str]:
        return {role.strip() for role in self.reviewer_roles.split(",") if role.strip()}

    @property
    def publisher_role_set(self) -> set[str]:
        return {role.strip() for role in self.publisher_roles.split(",") if role.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()

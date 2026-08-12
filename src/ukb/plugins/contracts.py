from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class PluginCapability(str, Enum):
    """Capabilities a brain plugin can provide.

    The capability list is intentionally broad so a domain brain can extend the
    platform without changing core runtime code.
    """

    source_connector = "source_connector"
    parser = "parser"
    extractor = "extractor"
    validator = "validator"
    retriever = "retriever"
    context_pack_decorator = "context_pack_decorator"
    policy = "policy"
    exporter = "exporter"


@dataclass(frozen=True)
class PluginManifest:
    """Human and machine-readable plugin metadata."""

    name: str
    version: str
    description: str
    capabilities: tuple[PluginCapability, ...]
    author: str | None = None
    homepage: str | None = None
    offline_safe: bool = True
    requires_network: bool = False
    config_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PluginResult:
    """Generic plugin return envelope.

    Plugins should preserve source evidence and confidence. They should not
    silently publish official knowledge; publication still goes through the
    review/governance services.
    """

    items: list[dict[str, Any]]
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SourceConnectorPlugin(Protocol):
    manifest: PluginManifest

    def can_handle(self, source_type: str, source_uri: str | None = None) -> bool:
        """Return True when this plugin can ingest the provided source."""

    def ingest(self, payload: dict[str, Any]) -> PluginResult:
        """Ingest source material and return normalized evidence candidates."""


@runtime_checkable
class ParserPlugin(Protocol):
    manifest: PluginManifest

    def parse(self, evidence: dict[str, Any]) -> PluginResult:
        """Parse evidence into sections, tables, SQL blocks, or other artifacts."""


@runtime_checkable
class ExtractorPlugin(Protocol):
    manifest: PluginManifest

    def extract(self, parsed_artifact: dict[str, Any]) -> PluginResult:
        """Extract candidate brain objects from a parsed artifact."""


@runtime_checkable
class ValidatorPlugin(Protocol):
    manifest: PluginManifest

    def validate(self, candidate_object: dict[str, Any]) -> PluginResult:
        """Validate candidate knowledge before human review."""

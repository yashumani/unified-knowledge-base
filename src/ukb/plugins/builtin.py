from __future__ import annotations

from typing import Any

from ukb.plugins.contracts import PluginCapability, PluginManifest, PluginResult
from ukb.plugins.registry import PluginRegistry


class ManualTextSourceConnector:
    """Offline-safe connector for manually supplied text context."""

    manifest = PluginManifest(
        name="builtin.manual_text_source",
        version="0.1.0",
        description="Accepts manually supplied text and turns it into evidence candidates.",
        capabilities=(PluginCapability.source_connector,),
        offline_safe=True,
        requires_network=False,
    )

    def can_handle(self, source_type: str, source_uri: str | None = None) -> bool:
        return source_type in {"manual", "document", "markdown", "text"} and not source_uri

    def ingest(self, payload: dict[str, Any]) -> PluginResult:
        content = str(payload.get("content", "")).strip()
        title = str(payload.get("title", "Untitled context")).strip()
        if not content:
            return PluginResult(items=[], warnings=["No content supplied."], confidence=0.0)
        return PluginResult(
            items=[
                {
                    "type": "EvidenceChunk",
                    "title": title,
                    "content": content,
                    "source_type": payload.get("source_type", "manual"),
                    "domain": payload.get("domain", "general"),
                }
            ],
            evidence=[{"title": title, "content_excerpt": content[:500]}],
            confidence=0.8,
            metadata={"connector": self.manifest.name},
        )


def register_builtin_plugins(plugin_registry: PluginRegistry) -> PluginRegistry:
    plugin_registry.register_source_connector("manual_text", ManualTextSourceConnector())
    return plugin_registry

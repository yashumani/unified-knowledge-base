"""Example local plugin for a generated brain project.

This plugin is intentionally simple and offline-safe. It shows how a brain
project can provide source behavior without changing the core platform.
"""

from ukb.plugins.contracts import PluginCapability, PluginManifest, PluginResult


class LocalContextSourcePlugin:
    manifest = PluginManifest(
        name="local.context_source",
        version="0.1.0",
        description="Example generated source connector for manual or Markdown context.",
        capabilities=(PluginCapability.source_connector,),
        offline_safe=True,
        requires_network=False,
    )

    def can_handle(self, source_type: str, source_uri: str | None = None) -> bool:
        return source_type in {"manual", "markdown", "document"}

    def ingest(self, payload: dict) -> PluginResult:
        content = str(payload.get("content", "")).strip()
        if not content:
            return PluginResult(items=[], confidence=0.0, warnings=["No content supplied."])
        return PluginResult(
            items=[{"type": "EvidenceChunk", "content": content}],
            evidence=[{"content_excerpt": content[:500]}],
            confidence=0.75,
        )

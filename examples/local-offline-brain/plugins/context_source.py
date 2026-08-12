"""Offline-safe example plugin for the local offline brain."""

from ukb.plugins.contracts import PluginCapability, PluginManifest, PluginResult


class LocalOfflineContextSource:
    manifest = PluginManifest(
        name="local.context_source",
        version="0.1.0",
        description="Example offline source plugin.",
        capabilities=(PluginCapability.source_connector,),
        offline_safe=True,
        requires_network=False,
    )

    def can_handle(self, source_type: str, source_uri: str | None = None) -> bool:
        return source_type in {"manual", "markdown", "document"}

    def ingest(self, payload: dict) -> PluginResult:
        content = str(payload.get("content", "")).strip()
        return PluginResult(
            items=[{"type": "EvidenceChunk", "content": content}] if content else [],
            evidence=[{"content_excerpt": content[:500]}] if content else [],
            confidence=0.75 if content else 0.0,
            warnings=[] if content else ["No content supplied."],
        )

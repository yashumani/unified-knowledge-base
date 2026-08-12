from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ukb.plugins.contracts import (
    ExtractorPlugin,
    ParserPlugin,
    PluginCapability,
    PluginManifest,
    SourceConnectorPlugin,
    ValidatorPlugin,
)


@dataclass
class PluginRegistry:
    """Runtime registry for domain-brain plugins.

    The registry is deliberately small: plugins are discovered and registered by
    loaders, then core services ask the registry for a capability. This lets a
    user build a custom brain by adding plugins without forking the platform.
    """

    manifests: dict[str, PluginManifest] = field(default_factory=dict)
    source_connectors: dict[str, SourceConnectorPlugin] = field(default_factory=dict)
    parsers: dict[str, ParserPlugin] = field(default_factory=dict)
    extractors: dict[str, ExtractorPlugin] = field(default_factory=dict)
    validators: dict[str, ValidatorPlugin] = field(default_factory=dict)

    def register_manifest(self, manifest: PluginManifest) -> None:
        self.manifests[manifest.name] = manifest

    def register_source_connector(self, name: str, plugin: SourceConnectorPlugin) -> None:
        self.source_connectors[name] = plugin
        self.register_manifest(plugin.manifest)

    def register_parser(self, name: str, plugin: ParserPlugin) -> None:
        self.parsers[name] = plugin
        self.register_manifest(plugin.manifest)

    def register_extractor(self, name: str, plugin: ExtractorPlugin) -> None:
        self.extractors[name] = plugin
        self.register_manifest(plugin.manifest)

    def register_validator(self, name: str, plugin: ValidatorPlugin) -> None:
        self.validators[name] = plugin
        self.register_manifest(plugin.manifest)

    def list_manifests(self, capability: PluginCapability | None = None) -> list[PluginManifest]:
        manifests = list(self.manifests.values())
        if capability is None:
            return manifests
        return [manifest for manifest in manifests if capability in manifest.capabilities]

    def find_source_connector(
        self,
        source_type: str,
        source_uri: str | None = None,
    ) -> SourceConnectorPlugin | None:
        for plugin in self.source_connectors.values():
            if plugin.can_handle(source_type=source_type, source_uri=source_uri):
                return plugin
        return None

    def describe(self) -> dict[str, Any]:
        return {
            "plugins": [
                {
                    "name": manifest.name,
                    "version": manifest.version,
                    "capabilities": [capability.value for capability in manifest.capabilities],
                    "offline_safe": manifest.offline_safe,
                    "requires_network": manifest.requires_network,
                }
                for manifest in self.manifests.values()
            ]
        }


registry = PluginRegistry()

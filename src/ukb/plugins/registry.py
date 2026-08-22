from __future__ import annotations

import logging
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any

from ukb.plugins.contracts import (
    ExtractorPlugin,
    ParserPlugin,
    PluginCapability,
    PluginManifest,
    SourceConnectorPlugin,
    ValidatorPlugin,
)

logger = logging.getLogger("ukb.plugins")


@dataclass
class PluginRegistry:
    """Runtime registry and entry-point loader for UKB extensions."""

    manifests: dict[str, PluginManifest] = field(default_factory=dict)
    source_connectors: dict[str, SourceConnectorPlugin] = field(default_factory=dict)
    parsers: dict[str, ParserPlugin] = field(default_factory=dict)
    extractors: dict[str, ExtractorPlugin] = field(default_factory=dict)
    validators: dict[str, ValidatorPlugin] = field(default_factory=dict)
    load_errors: list[str] = field(default_factory=list)

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

    def register(self, plugin: object, *, name: str | None = None) -> None:
        manifest = getattr(plugin, "manifest", None)
        if not isinstance(manifest, PluginManifest):
            raise TypeError("A UKB plugin must expose a PluginManifest as 'manifest'.")
        plugin_name = name or manifest.name
        registered = False
        if isinstance(plugin, SourceConnectorPlugin):
            self.register_source_connector(plugin_name, plugin)
            registered = True
        if isinstance(plugin, ParserPlugin):
            self.register_parser(plugin_name, plugin)
            registered = True
        if isinstance(plugin, ExtractorPlugin):
            self.register_extractor(plugin_name, plugin)
            registered = True
        if isinstance(plugin, ValidatorPlugin):
            self.register_validator(plugin_name, plugin)
            registered = True
        if not registered:
            self.register_manifest(manifest)

    def load_entry_points(self, group: str = "ukb.plugins") -> list[str]:
        """Load installed plugins without hardcoding them into the core runtime."""

        loaded: list[str] = []
        try:
            candidates = entry_points(group=group)
        except TypeError:  # pragma: no cover - older importlib.metadata compatibility
            candidates = entry_points().select(group=group)
        for entry_point in candidates:
            try:
                target = entry_point.load()
                plugin = target() if isinstance(target, type) else target
                self.register(plugin, name=entry_point.name)
                loaded.append(entry_point.name)
            except Exception as exc:  # a broken optional plugin must not take down UKB
                message = f"{entry_point.name}: {type(exc).__name__}: {exc}"
                self.load_errors.append(message)
                logger.exception("Failed to load UKB plugin %s", entry_point.name)
        return loaded

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
            ],
            "load_errors": list(self.load_errors),
        }


registry = PluginRegistry()

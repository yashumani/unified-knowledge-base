from ukb.plugins.builtin import register_builtin_plugins
from ukb.plugins.contracts import PluginCapability, PluginManifest
from ukb.plugins.registry import PluginRegistry


def test_plugin_registry_filters_by_capability():
    registry = PluginRegistry()
    registry.register_manifest(
        PluginManifest(
            name="test.extractor",
            version="0.1.0",
            description="Test extractor",
            capabilities=(PluginCapability.extractor,),
        )
    )

    extractors = registry.list_manifests(PluginCapability.extractor)

    assert len(extractors) == 1
    assert extractors[0].name == "test.extractor"


def test_builtin_manual_connector_is_offline_safe():
    registry = register_builtin_plugins(PluginRegistry())
    connector = registry.find_source_connector("manual")

    assert connector is not None
    assert connector.manifest.offline_safe is True
    assert connector.manifest.requires_network is False

    result = connector.ingest(
        {
            "title": "Metric note",
            "content": "Revenue is owned by Finance BI.",
            "domain": "finance",
        }
    )

    assert result.items
    assert result.confidence > 0.5

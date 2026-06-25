from __future__ import annotations

import pytest

from forge.plugins.base import (
    CommandRunner,
    Configurable,
    DependencyProvider,
    FileProvider,
    PluginBase,
)


class TestIntegration_MixinComposition:
    """Validates that real production plugins correctly report their
    capability mixins via isinstance checks."""

    def test_real_production_plugin_capabilities(self) -> None:
        try:
            from forge.plugins.fastapi.plugin import FastapiPlugin
        except ImportError:
            pytest.skip("FastapiPlugin not available — cannot test production plugin capabilities")

        plugin = FastapiPlugin()

        assert isinstance(plugin, PluginBase)
        assert isinstance(plugin, Configurable)
        assert isinstance(plugin, FileProvider)
        assert isinstance(plugin, CommandRunner)
        assert isinstance(plugin, DependencyProvider)

    def test_plugin_without_mixin_returns_false_for_isinstance(
        self, minimal_plugin
    ) -> None:
        from forge.plugins.base import FileProvider, PluginBase

        class FileOnlyPlugin(PluginBase, FileProvider):
            name = "file-only"
            display_name = "File Only"
            description = ""

            def files(self, spec):
                return []

            def directories(self, spec):
                return []

        fp = FileOnlyPlugin()
        assert isinstance(fp, PluginBase)
        assert isinstance(fp, FileProvider)
        assert not isinstance(fp, Configurable)
        assert not isinstance(fp, CommandRunner)
        assert not isinstance(fp, DependencyProvider)

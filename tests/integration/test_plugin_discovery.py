from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forge.generation.registry import (
    CycleDependencyError,
    DiscoveryError,
    PluginRegistry,
)
from forge.plugins.base import PluginBase

# ── Mock plugin classes for topo-sort and conflict tests ──


class MockA(PluginBase):
    name = "a"
    display_name = "A"
    description = "Plugin A"
    def files(self, spec): return []
    def directories(self, spec): return []


class MockB(PluginBase):
    name = "b"
    display_name = "B"
    description = "Plugin B"
    def files(self, spec): return []
    def directories(self, spec): return []


class MockARequiresB(PluginBase):
    name = "a"
    display_name = "A"
    description = "A requires B"
    requires = ["b"]
    def files(self, spec): return []
    def directories(self, spec): return []


class MockRunAfterB(PluginBase):
    name = "a"
    display_name = "A"
    description = "A prefers B first"
    run_after = ["b"]
    def files(self, spec): return []
    def directories(self, spec): return []


class MockCycleA(PluginBase):
    name = "cycle-a"
    display_name = "Cycle A"
    description = ""
    requires = ["cycle-b"]
    def files(self, spec): return []
    def directories(self, spec): return []


class MockCycleB(PluginBase):
    name = "cycle-b"
    display_name = "Cycle B"
    description = ""
    requires = ["cycle-a"]
    def files(self, spec): return []
    def directories(self, spec): return []


def _make_entry_point(name: str, plugin_cls: type[PluginBase]) -> MagicMock:
    ep = MagicMock()
    ep.name = name
    ep.group = "forge.plugins"
    ep.load.return_value = plugin_cls
    return ep


def _dot_plugins_source(plugin_name: str) -> str:
    return (
        "from forge.plugins.base import PluginBase\n"
        "class _UserPlugin(PluginBase):\n"
        f'    name = "{plugin_name}"\n'
        '    display_name = "User Plugin"\n'
        '    description = ""\n'
        "    def files(self, spec): return []\n"
        "    def directories(self, spec): return []\n"
        "plugin = _UserPlugin()\n"
    )


class TestIntegration_EntryPointDiscovery:
    """Canary test: loads REAL production plugins via importlib entry points."""

    def test_entry_point_discovery_loads_production_plugins(self) -> None:
        reg = PluginRegistry()
        discovered = reg.discover()
        # All 4 production plugins must be discoverable
        expected_ids = {"fastapi", "django", "react", "htmx"}
        assert expected_ids.issubset(set(discovered.keys())), (
            f"Missing production plugins. Found: {set(discovered.keys())}"
        )
        for plugin_id in expected_ids:
            plugin = discovered[plugin_id]
            assert isinstance(plugin, PluginBase)
            assert plugin.display_name


class TestIntegration_UserDirDiscovery:
    def test_discovers_both_flat_and_subdirectory_formats(
        self, user_plugin_dir: Path
    ) -> None:
        with (
            patch("importlib.metadata.entry_points", return_value=[]),
            patch("pathlib.Path.cwd", return_value=user_plugin_dir.parent),
        ):
            reg = PluginRegistry()
            discovered = reg.discover()

        assert "user-plugin" in discovered
        assert "sub-plugin" in discovered
        assert isinstance(discovered["user-plugin"], PluginBase)
        assert isinstance(discovered["sub-plugin"], PluginBase)
        assert discovered["sub-plugin"].name == "sub-plugin"


class TestIntegration_ConflictResolution:
    def test_entry_point_wins_over_user_plugin(
        self, user_plugin_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.WARNING)
        with (
            patch("importlib.metadata.entry_points") as mock_ep,
            patch("pathlib.Path.cwd", return_value=user_plugin_dir.parent),
        ):
            mock_ep.return_value = [
                _make_entry_point("user-plugin", MockA),
            ]
            reg = PluginRegistry()
            discovered = reg.discover()

        assert "user-plugin" in discovered
        assert discovered["user-plugin"].name == "user-plugin"
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("user-plugin" in r.message for r in warning_records)

    def test_strict_mode_raises_discovery_error_on_conflict(
        self, user_plugin_dir: Path
    ) -> None:
        with (
            patch("importlib.metadata.entry_points") as mock_ep,
            patch("pathlib.Path.cwd", return_value=user_plugin_dir.parent),
        ):
            mock_ep.return_value = [
                _make_entry_point("user-plugin", MockA),
            ]
            reg = PluginRegistry(strict=True)
            with pytest.raises(DiscoveryError):
                reg.discover()


class TestIntegration_TopologicalSort:
    @pytest.fixture
    def registry_with_a_and_b(self) -> PluginRegistry:
        with patch("importlib.metadata.entry_points") as mock_ep:
            mock_ep.return_value = [
                _make_entry_point("a", MockA),
                _make_entry_point("b", MockB),
            ]
            reg = PluginRegistry()
            reg.discover()
            return reg

    @pytest.fixture
    def registry_with_deps(self) -> PluginRegistry:
        with patch("importlib.metadata.entry_points") as mock_ep:
            mock_ep.return_value = [
                _make_entry_point("a", MockARequiresB),
                _make_entry_point("b", MockB),
            ]
            reg = PluginRegistry()
            reg.discover()
            return reg

    @pytest.fixture
    def registry_with_run_after(self) -> PluginRegistry:
        with patch("importlib.metadata.entry_points") as mock_ep:
            mock_ep.return_value = [
                _make_entry_point("a", MockRunAfterB),
                _make_entry_point("b", MockB),
            ]
            reg = PluginRegistry()
            reg.discover()
            return reg

    @pytest.fixture
    def registry_with_cycle(self) -> PluginRegistry:
        with patch("importlib.metadata.entry_points") as mock_ep:
            mock_ep.return_value = [
                _make_entry_point("cycle-a", MockCycleA),
                _make_entry_point("cycle-b", MockCycleB),
            ]
            reg = PluginRegistry()
            reg.discover()
            return reg

    def test_single_plugin_returns_as_is(
        self, registry_with_a_and_b: PluginRegistry
    ) -> None:
        result = registry_with_a_and_b.topological_sort(["a"])
        assert len(result) == 1
        assert result[0].name == "a"

    def test_dependency_before_dependent(
        self, registry_with_deps: PluginRegistry
    ) -> None:
        result = registry_with_deps.topological_sort(["a", "b"])
        ids = [p.name for p in result]
        assert ids.index("b") < ids.index("a")

    def test_cycle_detection_raises_error(
        self, registry_with_cycle: PluginRegistry
    ) -> None:
        with pytest.raises(CycleDependencyError) as exc:
            registry_with_cycle.topological_sort(["cycle-a", "cycle-b"])
        assert "cycle-a" in str(exc.value)
        assert "cycle-b" in str(exc.value)

    def test_run_after_creates_soft_ordering(
        self, registry_with_run_after: PluginRegistry
    ) -> None:
        result = registry_with_run_after.topological_sort(["a", "b"])
        ids = [p.name for p in result]
        assert ids.index("b") < ids.index("a")

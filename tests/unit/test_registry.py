from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forge.domain import ProjectSpec
from forge.generation.registry import (
    CycleDependencyError,
    DiscoveryError,
    PluginRegistry,
)
from forge.plugins.base import PluginBase

# ── Mock plugin classes for discovery, resolution, and topological sort ──


class MockA(PluginBase):
    name = "a"
    display_name = "A"
    description = "Plugin A"

    def files(self, spec: ProjectSpec) -> list:
        return []

    def directories(self, spec: ProjectSpec) -> list:
        return []


class MockB(PluginBase):
    name = "b"
    display_name = "B"
    description = "Plugin B"

    def files(self, spec: ProjectSpec) -> list:
        return []

    def directories(self, spec: ProjectSpec) -> list:
        return []


class MockARequiresB(PluginBase):
    name = "a"
    display_name = "A"
    description = "A requires B"
    requires = ["b"]

    def files(self, spec: ProjectSpec) -> list:
        return []

    def directories(self, spec: ProjectSpec) -> list:
        return []


class MockRunAfterB(PluginBase):
    name = "a"
    display_name = "A"
    description = "A prefers B first"
    run_after = ["b"]

    def files(self, spec: ProjectSpec) -> list:
        return []

    def directories(self, spec: ProjectSpec) -> list:
        return []


class MockCycleA(PluginBase):
    name = "cycle-a"
    display_name = "Cycle A"
    description = ""
    requires = ["cycle-b"]

    def files(self, spec: ProjectSpec) -> list:
        return []

    def directories(self, spec: ProjectSpec) -> list:
        return []


class MockCycleB(PluginBase):
    name = "cycle-b"
    display_name = "Cycle B"
    description = ""
    requires = ["cycle-a"]

    def files(self, spec: ProjectSpec) -> list:
        return []

    def directories(self, spec: ProjectSpec) -> list:
        return []


class MockMissingDep(PluginBase):
    name = "needs-c"
    display_name = "Needs C"
    description = ""
    requires = ["c"]

    def files(self, spec: ProjectSpec) -> list:
        return []

    def directories(self, spec: ProjectSpec) -> list:
        return []


def _make_entry_point(name: str, plugin_cls: type[PluginBase]) -> MagicMock:
    ep = MagicMock()
    ep.name = name
    ep.group = "forge.plugins"
    ep.load.return_value = plugin_cls
    return ep


def _dot_plugins_source(plugin_name: str) -> str:
    return f"""from forge.plugins.base import PluginBase
class _UserPlugin(PluginBase):
    name = "{plugin_name}"
    display_name = "User Plugin"
    description = ""
    def files(self, spec): return []
    def directories(self, spec): return []
plugin = _UserPlugin()
"""


# ── Fixtures ──


@pytest.fixture
def empty_registry():
    """Registry with zero entry points and no .plugins/ directory."""
    with patch("importlib.metadata.entry_points", return_value=[]):
        reg = PluginRegistry()
        reg.discover()
        return reg


@pytest.fixture
def registry_with_a_and_b():
    """Registry with plugins 'a' and 'b' discovered (no deps)."""
    with patch("importlib.metadata.entry_points") as mock_ep:
        mock_ep.return_value = [
            _make_entry_point("a", MockA),
            _make_entry_point("b", MockB),
        ]
        reg = PluginRegistry()
        reg.discover()
        return reg


@pytest.fixture
def registry_with_deps():
    """Registry where 'a' requires 'b'."""
    with patch("importlib.metadata.entry_points") as mock_ep:
        mock_ep.return_value = [
            _make_entry_point("a", MockARequiresB),
            _make_entry_point("b", MockB),
        ]
        reg = PluginRegistry()
        reg.discover()
        return reg


@pytest.fixture
def registry_with_run_after():
    """Registry where 'a' declares run_after=['b']."""
    with patch("importlib.metadata.entry_points") as mock_ep:
        mock_ep.return_value = [
            _make_entry_point("a", MockRunAfterB),
            _make_entry_point("b", MockB),
        ]
        reg = PluginRegistry()
        reg.discover()
        return reg


@pytest.fixture
def registry_with_cycle():
    """Registry with circular dependency cycle-a -> cycle-b -> cycle-a."""
    with patch("importlib.metadata.entry_points") as mock_ep:
        mock_ep.return_value = [
            _make_entry_point("cycle-a", MockCycleA),
            _make_entry_point("cycle-b", MockCycleB),
        ]
        reg = PluginRegistry()
        reg.discover()
        return reg


@pytest.fixture
def registry_with_missing_dep():
    """Registry where 'needs-c' requires 'c' but 'c' is not discovered."""
    with patch("importlib.metadata.entry_points") as mock_ep:
        mock_ep.return_value = [
            _make_entry_point("needs-c", MockMissingDep),
            _make_entry_point("b", MockB),
        ]
        reg = PluginRegistry()
        reg.discover()
        return reg


# ── Constructor (AC-1, AC-2) ──


class TestAC1_2_Constructor:
    def test_default_strict_false(self) -> None:
        reg = PluginRegistry()
        assert reg.strict is False

    def test_strict_true(self) -> None:
        reg = PluginRegistry(strict=True)
        assert reg.strict is True


# ── Discovery (AC-3, AC-4, AC-5, AC-6) ──


class TestAC3_6_Discovery:
    def test_entry_point_discovery(self) -> None:
        mock_a = MockA()
        with patch("importlib.metadata.entry_points") as mock_ep:
            mock_ep.return_value = [_make_entry_point("a", MockA)]
            reg = PluginRegistry()
            discovered = reg.discover()
        assert "a" in discovered
        plugin = discovered["a"]
        assert isinstance(plugin, PluginBase)
        assert plugin.name == mock_a.name
        assert plugin.display_name == mock_a.display_name

    def test_returned_dict_contains_plugin_id_key(self) -> None:
        with patch("importlib.metadata.entry_points") as mock_ep:
            mock_ep.return_value = [_make_entry_point("a", MockA)]
            reg = PluginRegistry()
            discovered = reg.discover()
        assert "a" in discovered
        # Ensure the plugin's name matches the dict key
        assert discovered["a"].name == "a"

    def test_conflict_entry_point_wins_and_warning_logged(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level(logging.WARNING)
        plugins_dir = tmp_path / ".plugins"
        plugins_dir.mkdir()
        (plugins_dir / "myplugin.py").write_text(_dot_plugins_source("myplugin"))

        with (
            patch("importlib.metadata.entry_points") as mock_ep,
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            mock_ep.return_value = [_make_entry_point("myplugin", MockA)]
            reg = PluginRegistry()
            discovered = reg.discover()

        assert "myplugin" in discovered
        assert discovered["myplugin"].name == "myplugin"
        # Entry point version wins (MockA)
        assert len(caplog.records) >= 1
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) >= 1
        assert any("myplugin" in r.message for r in warning_records)

    def test_strict_mode_raises_discovery_error_on_conflict(
        self,
        tmp_path: Path,
    ) -> None:
        plugins_dir = tmp_path / ".plugins"
        plugins_dir.mkdir()
        (plugins_dir / "myplugin.py").write_text(_dot_plugins_source("myplugin"))

        with (
            patch("importlib.metadata.entry_points") as mock_ep,
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            mock_ep.return_value = [_make_entry_point("myplugin", MockA)]
            reg = PluginRegistry(strict=True)
            with pytest.raises(DiscoveryError):
                reg.discover()

    def test_empty_discovery_when_no_sources(self) -> None:
        with patch("importlib.metadata.entry_points", return_value=[]):
            reg = PluginRegistry()
            discovered = reg.discover()
        assert discovered == {}


# ── Resolution (AC-7, AC-8, AC-9, AC-10, AC-11) ──


class TestAC7_11_Resolution:
    def test_resolve_existing(self, registry_with_a_and_b: PluginRegistry) -> None:
        plugin = registry_with_a_and_b.resolve("a")
        assert plugin.name == "a"
        assert isinstance(plugin, PluginBase)

    def test_resolve_missing_raises_key_error(self, registry_with_a_and_b: PluginRegistry) -> None:
        with pytest.raises(KeyError, match="unknown"):
            registry_with_a_and_b.resolve("unknown")

    def test_resolve_many_returns_in_order(self, registry_with_a_and_b: PluginRegistry) -> None:
        plugins = registry_with_a_and_b.resolve_many(["a", "b"])
        assert len(plugins) == 2
        assert plugins[0].name == "a"
        assert plugins[1].name == "b"

    def test_resolve_many_partial_raises_key_error(
        self, registry_with_a_and_b: PluginRegistry
    ) -> None:
        with pytest.raises(KeyError):
            registry_with_a_and_b.resolve_many(["a", "unknown"])

    def test_resolve_many_empty_list(self, registry_with_a_and_b: PluginRegistry) -> None:
        assert registry_with_a_and_b.resolve_many([]) == []


# ── .plugins/ Discovery (AC-12) ──


class TestAC12_DotPluginsDiscovery:
    def test_discovers_plugin_from_dot_plugins_dir(self, tmp_path: Path) -> None:
        plugins_dir = tmp_path / ".plugins"
        plugins_dir.mkdir()
        (plugins_dir / "user_plugin.py").write_text(_dot_plugins_source("user-plugin"))

        with (
            patch("importlib.metadata.entry_points", return_value=[]),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            reg = PluginRegistry()
            discovered = reg.discover()

        assert "user-plugin" in discovered
        assert isinstance(discovered["user-plugin"], PluginBase)
        assert discovered["user-plugin"].name == "user-plugin"

    def test_dot_plugins_file_without_plugin_attr_skipped(self, tmp_path: Path) -> None:
        plugins_dir = tmp_path / ".plugins"
        plugins_dir.mkdir()
        (plugins_dir / "invalid.py").write_text("# no plugin attribute\nx = 1\n")

        with (
            patch("importlib.metadata.entry_points", return_value=[]),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            reg = PluginRegistry()
            discovered = reg.discover()

        assert "user-plugin" not in discovered
        assert "invalid" not in discovered


# ── Available Plugins (AC-13, AC-14) ──


class TestAC13_14_Available:
    def test_get_available_backends(self, registry_with_a_and_b: PluginRegistry) -> None:
        backends = registry_with_a_and_b.get_available_backends()
        assert len(backends) == 2
        assert all(isinstance(p, PluginBase) for p in backends)

    def test_get_available_frontends_empty(self, registry_with_a_and_b: PluginRegistry) -> None:
        assert registry_with_a_and_b.get_available_frontends() == []


# ── Missing Dependencies (AC-15, AC-16, AC-17) ──


class TestAC15_17_MissingDeps:
    def test_all_deps_resolved_returns_empty_list(
        self,
        registry_with_deps: PluginRegistry,
    ) -> None:
        missing = registry_with_deps.get_missing_dependencies("a")
        assert missing == []

    def test_unresolved_dep_in_list(
        self,
        registry_with_missing_dep: PluginRegistry,
    ) -> None:
        missing = registry_with_missing_dep.get_missing_dependencies("needs-c")
        assert "c" in missing

    def test_unknown_plugin_id_raises_key_error(
        self,
        registry_with_a_and_b: PluginRegistry,
    ) -> None:
        with pytest.raises(KeyError):
            registry_with_a_and_b.get_missing_dependencies("unknown")


# ── Topological Sort (AC-18 through AC-23) ──


class TestAC18_23_TopologicalSort:
    def test_dependency_before_dependent(
        self,
        registry_with_deps: PluginRegistry,
    ) -> None:
        result = registry_with_deps.topological_sort(["a", "b"])
        ids = [p.name for p in result]
        assert ids.index("b") < ids.index("a")

    def test_cycle_detection_raises_cycle_dependency_error(
        self,
        registry_with_cycle: PluginRegistry,
    ) -> None:
        with pytest.raises(CycleDependencyError) as exc:
            registry_with_cycle.topological_sort(["cycle-a", "cycle-b"])
        assert "cycle-a" in str(exc.value)
        assert "cycle-b" in str(exc.value)

    def test_single_plugin_unchanged(
        self,
        registry_with_a_and_b: PluginRegistry,
    ) -> None:
        result = registry_with_a_and_b.topological_sort(["a"])
        assert len(result) == 1
        assert result[0].name == "a"

    def test_empty_list(self, registry_with_a_and_b: PluginRegistry) -> None:
        assert registry_with_a_and_b.topological_sort([]) == []

    def test_stable_sort_preserves_input_order(
        self,
        registry_with_a_and_b: PluginRegistry,
    ) -> None:
        result = registry_with_a_and_b.topological_sort(["b", "a"])
        assert result[0].name == "b"
        assert result[1].name == "a"

    def test_run_after_creates_soft_edge(
        self,
        registry_with_run_after: PluginRegistry,
    ) -> None:
        result = registry_with_run_after.topological_sort(["a", "b"])
        ids = [p.name for p in result]
        assert ids.index("b") < ids.index("a")

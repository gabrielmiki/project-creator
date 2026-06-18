from __future__ import annotations

import importlib.metadata
import logging
from pathlib import Path
from typing import Any

from forge.infrastructure import GenerationTransaction as _  # noqa: F401
from forge.plugins.base import PluginBase

logger = logging.getLogger(__name__)


class DiscoveryError(Exception):
    """Raised when strict=True and a plugin ID conflict is detected."""


class CycleDependencyError(Exception):
    """Raised when topological_sort detects a circular dependency."""


class PluginRegistry:
    strict: bool

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict
        self._discovered: dict[str, PluginBase] = {}

    def discover(self) -> dict[str, PluginBase]:
        self._discovered = {}

        # Tier 1: Entry points (priority 10)
        eps = importlib.metadata.entry_points(group="forge.plugins")
        for ep in sorted(eps, key=lambda e: e.name):
            try:
                cls = ep.load()
                plugin = cls()
                plugin_id = ep.name
                plugin.name = plugin_id
                self._discovered[plugin_id] = plugin
            except Exception:
                logger.exception(
                    "Failed to load entry point plugin %s",
                    ep.name,
                )

        # Tier 2: .plugins/ directory (priority 5)
        plugins_dir = Path.cwd() / ".plugins"
        if plugins_dir.is_dir():
            # Flat .py files
            for py_file in sorted(plugins_dir.glob("*.py")):
                self._load_dot_plugins_file(py_file)
            # Subdirectories with plugin.py
            for subdir in sorted(plugins_dir.iterdir()):
                if subdir.is_dir():
                    plugin_file = subdir / "plugin.py"
                    if plugin_file.exists():
                        self._load_dot_plugins_file(plugin_file)

        return dict(self._discovered)

    def _load_dot_plugins_file(self, py_file: Path) -> None:
        try:
            namespace: dict[str, Any] = {}
            exec(py_file.read_text(), namespace)
        except Exception:
            logger.exception(
                "Failed to execute plugin file %s",
                py_file,
            )
            return
        plugin = namespace.get("plugin")
        if not isinstance(plugin, PluginBase):
            return
        plugin_id = plugin.name
        if plugin_id in self._discovered:
            if self.strict:
                raise DiscoveryError(
                    f"Plugin '{plugin_id}' conflict between entry point and .plugins/{py_file.name}"
                )
            logger.warning(
                "Plugin '%s' conflict: entry point (%s) wins "
                "over .plugins/%s — user plugin skipped",
                plugin_id,
                self._discovered[plugin_id],
                py_file.name,
            )
            return
        self._discovered[plugin_id] = plugin

    def resolve(self, plugin_id: str) -> PluginBase:
        if plugin_id not in self._discovered:
            raise KeyError(plugin_id)
        return self._discovered[plugin_id]

    def resolve_many(self, plugin_ids: list[str]) -> list[PluginBase]:
        return [self.resolve(pid) for pid in plugin_ids]

    def get_available_backends(self) -> list[PluginBase]:
        return list(self._discovered.values())

    def get_available_frontends(self) -> list[PluginBase]:
        return []

    def get_missing_dependencies(self, plugin_id: str) -> list[str]:
        if plugin_id not in self._discovered:
            raise KeyError(plugin_id)
        plugin = self._discovered[plugin_id]
        return [dep for dep in (plugin.requires or []) if dep not in self._discovered]

    def topological_sort(self, plugin_ids: list[str]) -> list[PluginBase]:
        if not plugin_ids:
            return []

        plugins = self.resolve_many(plugin_ids)
        pid_set = set(plugin_ids)

        # Build graph from requires (hard edges)
        graph: dict[str, list[str]] = {}
        in_degree: dict[str, int] = {}
        for pid in plugin_ids:
            graph.setdefault(pid, [])
            in_degree.setdefault(pid, 0)

        # Track run_after (soft edges) — maps dependency → list of dependents
        run_after_dependents: dict[str, list[str]] = {}

        for p in plugins:
            pid = p.name
            for dep in p.requires or []:
                if dep in pid_set:
                    graph.setdefault(dep, []).append(pid)
                    in_degree[pid] = in_degree.get(pid, 0) + 1
            for dep in p.run_after or []:
                if dep in pid_set:
                    run_after_dependents.setdefault(dep, []).append(pid)

        # Cycle detection (DFS on hard edges only)
        state: dict[str, int] = {}

        def _dfs(node: str, path: list[str]) -> None:
            state[node] = 1
            path.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in state:
                    _dfs(neighbor, path)
                elif state[neighbor] == 1:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    raise CycleDependencyError(f"Circular dependency detected: {' → '.join(cycle)}")
            path.pop()
            state[node] = 2

        for pid in plugin_ids:
            if pid not in state:
                _dfs(pid, [])

        # Kahn's algorithm
        queue = [pid for pid in plugin_ids if in_degree.get(pid, 0) == 0]
        result: list[PluginBase] = []

        while queue:
            queue.sort(
                key=lambda pid: (
                    -len(run_after_dependents.get(pid, [])),
                    plugin_ids.index(pid),
                )
            )
            node = queue.pop(0)
            result.append(self._discovered[node])
            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(plugin_ids):
            raise CycleDependencyError("Circular dependency detected")

        return result

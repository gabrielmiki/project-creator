import os
from pathlib import Path
from typing import Any

from forge.domain import ProjectSpec
from forge.generation.errors import MissingDependencyError
from forge.generation.progress import ProgressReporter
from forge.infrastructure import GenerationTransaction as _  # noqa: F401
from forge.infrastructure import ProcessExecutor
from forge.plugins.base import CommandRunner, DependencyProvider, FileProvider


class PluginExecutionEngine:
    name = "plugin-execution-engine"

    def __init__(self, registry: Any, executor: ProcessExecutor | None = None) -> None:
        self._registry = registry
        self._executor = executor or ProcessExecutor()

    def run(
        self,
        spec: ProjectSpec,
        output_dir: Path,
        txn: Any,
        progress: ProgressReporter,
    ) -> None:
        plugin_ids: list[str] = [
            pid for pid in [spec.template.backend_id, spec.template.frontend_id] if pid
        ]
        if not plugin_ids:
            return

        plugins = self._registry.resolve_many(plugin_ids)

        for plugin in plugins:
            for dep in plugin.requires or []:
                if dep not in plugin_ids:
                    raise MissingDependencyError(
                        f"Missing dependency '{dep}' required by plugin '{plugin.name}'"
                    )

        ordered = self._registry.topological_sort(plugin_ids)

        for plugin in ordered:
            if progress.should_cancel():
                return

            if isinstance(plugin, FileProvider):
                for f in plugin.files(spec):
                    staged = txn.stage_file(str(f.path), f.content)
                    if f.executable and os.path.exists(staged):
                        os.chmod(staged, 0o755)
                for d in plugin.directories(spec):
                    txn.stage_directory(d)

            if isinstance(plugin, DependencyProvider):
                txn.requirements.extend(plugin.dependencies(spec))

            if isinstance(plugin, CommandRunner):
                plugin.generate(spec, txn.staging, self._executor)

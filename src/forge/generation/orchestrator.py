from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forge.domain import DurationEstimate, ProjectSpec, Question, QuestionType
from forge.generation.progress import ProgressReporter
from forge.generation.registry import PluginRegistry
from forge.generation.stages import (
    AgentSkillScaffolder,
    DirectoryInitializer,
    JustfileGenerator,
    PluginExecutionEngine,
    ProjectDocumentationWriter,
    SharedStructureScaffolder,
)
from forge.generation.validation import ValidationEngine
from forge.infrastructure import GenerationTransaction as _  # noqa: F401
from forge.plugins.base import CommandRunner, Configurable, FileProvider, PluginBase


@dataclass
class GenerationResult:
    success: bool
    error: str | None
    output_path: Path | None


class Orchestrator:
    def __init__(
        self,
        registry: PluginRegistry,
        validation: ValidationEngine,
        stages: list[Any] | None = None,
    ) -> None:
        self._registry = registry
        self._validation = validation
        if stages is not None:
            self._stages = stages
        else:
            self._stages = [
                DirectoryInitializer(),
                SharedStructureScaffolder(),
                PluginExecutionEngine(registry),
                JustfileGenerator(),
                ProjectDocumentationWriter(),
                AgentSkillScaffolder(),
            ]

    def get_available_backends(self) -> list[PluginBase]:
        return self._registry.get_available_backends()

    def get_available_frontends(self) -> list[PluginBase]:
        return self._registry.get_available_frontends()

    def get_global_questions(self) -> list[Question]:
        return [
            Question(
                key="project_description",
                label="Project Description",
                question_type=QuestionType.STRING,
                required=False,
                description="A brief description of your project",
            ),
            Question(
                key="license",
                label="License",
                question_type=QuestionType.CHOICE,
                required=True,
                default="MIT",
                description="Choose a license for your project",
                options=["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause"],
            ),
        ]

    def get_domain_questions(
        self,
        backend_id: str | None,
        frontend_id: str | None,
    ) -> dict[str, list[Question]]:
        plugin_ids = [pid for pid in [backend_id, frontend_id] if pid is not None]
        result: dict[str, list[Question]] = {}
        for pid in plugin_ids:
            plugin = self._registry.resolve(pid)
            if isinstance(plugin, Configurable):
                result[plugin.name] = plugin.questions()
        return result

    def estimate_duration(self, spec: ProjectSpec) -> DurationEstimate:
        plugin_ids = [
            pid for pid in [spec.template.backend_id, spec.template.frontend_id]
            if pid
        ]
        if not plugin_ids:
            return DurationEstimate(1, False, [])

        plugins = self._registry.topological_sort(plugin_ids)
        total = 1.0
        has_slow = False
        details: list[str] = []
        for plugin in plugins:
            if isinstance(plugin, CommandRunner):
                total += 3.0
                has_slow = True
                details.append(f"{plugin.name}: command runner")
            elif isinstance(plugin, FileProvider):
                total += 0.5
                details.append(f"{plugin.name}: file provider")

        total = max(1, min(60, int(total)))
        return DurationEstimate(total, has_slow, details)

    def generate(
        self,
        spec: ProjectSpec,
        output_dir: Path,
        txn: Any,
        progress: ProgressReporter,
        overwrite_confirmed: bool = False,
    ) -> GenerationResult:
        stages = list(self._stages)
        if overwrite_confirmed:
            stages = stages[1:]

        try:
            for stage in stages:
                stage.run(spec, output_dir, txn, progress)
        except Exception as e:
            txn.rollback()
            progress.on_error(e, False)
            return GenerationResult(False, str(e), None)

        txn.commit()
        return GenerationResult(True, None, output_dir)

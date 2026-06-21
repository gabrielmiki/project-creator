from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from forge.domain import Domain, GeneratedFile, ProjectSpec, TemplateDefinition
from forge.infrastructure import ProcessExecutor
from forge.plugins.base import (
    CommandRunner,
    DependencyProvider,
    FileProvider,
    PluginBase,
)


class MockTransaction:
    """Duck-typed replacement for GenerationTransaction used in stage + orchestrator tests."""

    def __init__(self) -> None:
        self.staging: Path = Path("/tmp/mock-staging")
        self.stage_file_calls: list[tuple[str, str]] = []
        self.stage_directory_calls: list[str] = []
        self.add_checkpoint_calls: list[list[Path]] = []
        self.requirements: list[str] = []

    def stage_file(self, path: str, content: str) -> Path:
        self.stage_file_calls.append((path, content))
        return Path(path)

    def stage_directory(self, path: str) -> Path:
        self.stage_directory_calls.append(path)
        return Path(path)

    def add_checkpoint(self, paths: list[Path]) -> None:
        self.add_checkpoint_calls.append(paths)


class MockFilePlugin(PluginBase, FileProvider):
    name = "mock-file"
    display_name = "Mock File Plugin"
    description = ""

    def __init__(
        self, files: list[GeneratedFile] | None = None, dirs: list[str] | None = None
    ) -> None:
        super().__init__()
        self._files = files or []
        self._dirs = dirs or []

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        return self._files

    def directories(self, spec: ProjectSpec) -> list[str]:
        return self._dirs


class MockCommandPlugin(PluginBase, CommandRunner):
    name = "mock-command"
    display_name = "Mock Command Plugin"
    description = ""

    def __init__(self) -> None:
        super().__init__()
        self._generate_called = False
        self._generate_target_dir: Path | None = None
        self._generate_spec: ProjectSpec | None = None

    def generate(self, spec: ProjectSpec, target_dir: Path, executor: ProcessExecutor) -> None:
        self._generate_called = True
        self._generate_target_dir = target_dir
        self._generate_spec = spec


class MockDepPlugin(PluginBase, DependencyProvider):
    name = "mock-dep"
    display_name = "Mock Dependency Plugin"
    description = ""

    def __init__(self, deps: list[str] | None = None) -> None:
        super().__init__()
        self._deps = deps or []

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        return self._deps


def make_spec(backend_id: str = "", frontend_id: str | None = None) -> ProjectSpec:
    return ProjectSpec(
        project_name="test-proj",
        template=TemplateDefinition(
            id="test",
            display_name="Test Template",
            description="",
            backend_id=backend_id,
            frontend_id=frontend_id,
        ),
        domains=[Domain(name="Web")],
        config={},
    )


def make_empty_spec() -> ProjectSpec:
    return ProjectSpec(
        project_name="empty",
        template=TemplateDefinition(id="base", display_name="Base", description="", backend_id=""),
        domains=[],
        config={},
    )


def build_registry(plugins: list[PluginBase]) -> MagicMock:
    by_name = {p.name: p for p in plugins}
    reg: MagicMock = MagicMock()
    reg.topological_sort.return_value = plugins
    reg.resolve.side_effect = lambda pid: by_name[pid]
    reg.resolve_many.return_value = plugins
    return reg

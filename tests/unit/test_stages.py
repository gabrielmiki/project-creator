from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from forge.domain import GeneratedFile, ProjectSpec
from tests.unit._shared import (
    MockCommandPlugin,
    MockDepPlugin,
    MockFilePlugin,
    MockTransaction,
    build_registry,
    make_spec,
)

# ---- Mock Progress Reporter (AC-13: cancellable) ----


class _CancellableReporter:
    def __init__(self, cancel_after: int = 1) -> None:
        self.cancel_after = cancel_after
        self.call_count = 0

    def on_stage_start(self, stage_name: str, total_steps: int) -> None:
        pass

    def on_step_complete(self, step_name: str) -> None:
        pass

    def on_stage_complete(self, stage_name: str) -> None:
        pass

    def on_log(self, message: str, level: str = "info") -> None:
        pass

    def on_error(self, error: Exception, recoverable: bool) -> None:
        pass

    def on_duration_estimate(self, estimate: object) -> None:
        pass

    def should_cancel(self) -> bool:
        self.call_count += 1
        return self.call_count > self.cancel_after


# ====================================================================
# AC-1 / AC-2: DirectoryInitializer
# ====================================================================
# AC-1 / AC-2: DirectoryInitializer
# ====================================================================


class TestDirectoryInitializer:
    """AC-1: empty dir → no exception. AC-2: non-empty → DirectoryNotEmptyError."""

    # -- AC-1: empty --

    def test_empty_directory_passes(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.directory_initializer import DirectoryInitializer

        output_dir.mkdir()
        DirectoryInitializer().run(spec, output_dir, txn, progress)

    def test_non_existent_directory_passes(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.directory_initializer import DirectoryInitializer

        DirectoryInitializer().run(spec, output_dir, txn, progress)

    def test_directory_with_dotfile_passes(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.directory_initializer import DirectoryInitializer

        output_dir.mkdir()
        (output_dir / ".gitkeep").touch()
        DirectoryInitializer().run(spec, output_dir, txn, progress)

    # -- AC-2: non-empty --

    def test_file_in_dir_raises(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.errors import DirectoryNotEmptyError
        from forge.generation.stages.directory_initializer import DirectoryInitializer

        output_dir.mkdir()
        (output_dir / "main.py").touch()
        with pytest.raises(DirectoryNotEmptyError):
            DirectoryInitializer().run(spec, output_dir, txn, progress)

    def test_subdirectory_raises(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.errors import DirectoryNotEmptyError
        from forge.generation.stages.directory_initializer import DirectoryInitializer

        output_dir.mkdir()
        (output_dir / "sub").mkdir()
        with pytest.raises(DirectoryNotEmptyError):
            DirectoryInitializer().run(spec, output_dir, txn, progress)

    def test_nested_content_raises(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.errors import DirectoryNotEmptyError
        from forge.generation.stages.directory_initializer import DirectoryInitializer

        output_dir.mkdir()
        (output_dir / "a" / "b").mkdir(parents=True)
        with pytest.raises(DirectoryNotEmptyError):
            DirectoryInitializer().run(spec, output_dir, txn, progress)


# ====================================================================
# AC-3: SharedStructureScaffolder
# ====================================================================


class TestSharedStructureScaffolder:
    """AC-3: README.md, .gitignore, .env.example, .python-version, docs/ file."""

    REQUIRED_FILES = {"README.md", ".gitignore", ".env.example", ".python-version"}

    def test_shared_files_created(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.shared_structure_scaffolder import SharedStructureScaffolder

        SharedStructureScaffolder().run(spec, output_dir, txn, progress)

        staged_paths = {call[0] for call in txn.stage_file_calls}
        assert self.REQUIRED_FILES.issubset(staged_paths)

    def test_docs_stub_created(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.shared_structure_scaffolder import SharedStructureScaffolder

        SharedStructureScaffolder().run(spec, output_dir, txn, progress)

        assert any(call[0].startswith("docs/") for call in txn.stage_file_calls)

    def test_empty_spec_still_generates(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, empty_spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.shared_structure_scaffolder import SharedStructureScaffolder

        SharedStructureScaffolder().run(empty_spec, output_dir, txn, progress)

        staged_paths = {call[0] for call in txn.stage_file_calls}
        assert self.REQUIRED_FILES.issubset(staged_paths)


# ====================================================================
# AC-4, AC-5, AC-6, AC-11, AC-12, AC-13: PluginExecutionEngine
# ====================================================================


class TestPluginExecutionEngine:
    """All PluginExecutionEngine acceptance criteria."""

    # -- AC-4: FileProvider --

    def test_file_provider_forwards_files(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="fp")
        files = [
            GeneratedFile(Path("main.py"), "print(1)"),
            GeneratedFile(Path("utils.py"), "def foo(): pass"),
        ]
        dirs = ["static", "templates"]
        plugin = MockFilePlugin(files=files, dirs=dirs)
        plugin.name = "fp"
        registry = build_registry([plugin])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

        assert ("main.py", "print(1)") in txn.stage_file_calls
        assert ("utils.py", "def foo(): pass") in txn.stage_file_calls
        assert "static" in txn.stage_directory_calls
        assert "templates" in txn.stage_directory_calls

    def test_file_provider_no_files(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="fp")
        plugin = MockFilePlugin(files=[], dirs=[])
        plugin.name = "fp"
        registry = build_registry([plugin])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

        assert txn.stage_file_calls == []
        assert txn.stage_directory_calls == []

    def test_generated_file_executable_flag(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="fp")
        files = [GeneratedFile(Path("script.sh"), "#!/bin/bash\necho hi", executable=True)]
        plugin = MockFilePlugin(files=files, dirs=[])
        plugin.name = "fp"
        registry = build_registry([plugin])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

        assert ("script.sh", "#!/bin/bash\necho hi") in txn.stage_file_calls

    # -- AC-5: CommandRunner --

    def test_command_runner_generate_called(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="cp")
        plugin = MockCommandPlugin()
        plugin.name = "cp"
        registry = build_registry([plugin])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

        assert plugin._generate_called
        assert plugin._generate_target_dir == txn.staging

    def test_command_runner_multiple_both_called(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="cp1", frontend_id="cp2")
        p1 = MockCommandPlugin()
        p1.name = "cp1"
        p2 = MockCommandPlugin()
        p2.name = "cp2"
        registry = build_registry([p1, p2])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

        assert p1._generate_called
        assert p2._generate_called

    def test_command_runner_adds_checkpoint(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="cp")
        checkpoint_paths = [output_dir / "generated" / "file.txt"]
        plugin = MockCommandPlugin()
        plugin.name = "cp"
        original_generate = plugin.generate

        def patched_generate(spec: ProjectSpec, target_dir: Path, executor: object) -> None:
            original_generate(spec, target_dir, executor)
            txn.add_checkpoint(checkpoint_paths)

        plugin.generate = patched_generate  # type: ignore[assignment]
        registry = build_registry([plugin])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

        assert checkpoint_paths in txn.add_checkpoint_calls

    # -- AC-6: MissingDependency --

    def test_missing_dep_raises(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.errors import MissingDependencyError
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="needy")
        plugin = MockFilePlugin(files=[], dirs=[])
        plugin.name = "needy"
        plugin.requires = ["missing-plugin"]
        registry = build_registry([plugin])

        with pytest.raises(MissingDependencyError) as exc:
            PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)
        assert "missing-plugin" in str(exc.value)

    def test_present_dep_passes(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="a", frontend_id="b")
        a = MockFilePlugin(files=[], dirs=[])
        a.name = "a"
        a.requires = ["b"]
        b = MockFilePlugin(files=[], dirs=[])
        b.name = "b"
        registry = build_registry([a, b])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

    def test_empty_requires_passes(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="empty")
        plugin = MockFilePlugin(files=[], dirs=[])
        plugin.name = "empty"
        plugin.requires = []
        registry = build_registry([plugin])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

    # -- AC-11: CycleDependency --

    def test_circular_dependency_raises(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.registry import CycleDependencyError
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="a", frontend_id="b")
        registry: MagicMock = MagicMock()
        registry.topological_sort.side_effect = CycleDependencyError("cycle: a -> b -> a")

        with pytest.raises(CycleDependencyError):
            PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

    def test_self_referencing_dep_raises(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.registry import CycleDependencyError
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="self")
        registry: MagicMock = MagicMock()
        registry.topological_sort.side_effect = CycleDependencyError("cycle: self -> self")

        with pytest.raises(CycleDependencyError):
            PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

    def test_no_cycle_passes(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="a", frontend_id="b")
        a = MockFilePlugin(files=[], dirs=[])
        a.name = "a"
        b = MockFilePlugin(files=[], dirs=[])
        b.name = "b"
        registry = build_registry([a, b])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

    # -- AC-12: DependencyProvider --

    def test_dep_appended_to_requirements(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="dp")
        plugin = MockDepPlugin(deps=["fastapi", "sqlalchemy"])
        plugin.name = "dp"
        registry = build_registry([plugin])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

        assert "fastapi" in txn.requirements
        assert "sqlalchemy" in txn.requirements

    def test_multiple_dep_providers_accumulate(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="d1", frontend_id="d2")
        d1 = MockDepPlugin(deps=["pydantic"])
        d1.name = "d1"
        d2 = MockDepPlugin(deps=["uvicorn"])
        d2.name = "d2"
        registry = build_registry([d1, d2])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

        assert "pydantic" in txn.requirements
        assert "uvicorn" in txn.requirements

    def test_empty_deps_appends_nothing(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="dp")
        plugin = MockDepPlugin(deps=[])
        plugin.name = "dp"
        registry = build_registry([plugin])

        PluginExecutionEngine(registry).run(spec, output_dir, txn, progress)

        assert txn.requirements == []

    # -- AC-13: Cancellation --

    def test_cancellation_stops_after_first(
        self, output_dir: Path, txn: MockTransaction, progress: _CancellableReporter
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="p1", frontend_id="p2")
        p1 = MockCommandPlugin()
        p1.name = "p1"
        p2 = MockCommandPlugin()
        p2.name = "p2"
        registry = build_registry([p1, p2])
        cancel_progress = _CancellableReporter(cancel_after=1)

        PluginExecutionEngine(registry).run(spec, output_dir, txn, cancel_progress)

        assert p1._generate_called
        assert not p2._generate_called

    def test_cancellation_before_any_plugin(
        self, output_dir: Path, txn: MockTransaction, progress: _CancellableReporter
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="p1", frontend_id="p2")
        p1 = MockCommandPlugin()
        p1.name = "p1"
        p2 = MockCommandPlugin()
        p2.name = "p2"
        registry = build_registry([p1, p2])
        cancel_progress = _CancellableReporter(cancel_after=0)

        PluginExecutionEngine(registry).run(spec, output_dir, txn, cancel_progress)

        assert not p1._generate_called
        assert not p2._generate_called

    def test_no_cancellation_runs_all(
        self, output_dir: Path, txn: MockTransaction, progress: _CancellableReporter
    ) -> None:
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine

        spec = make_spec(backend_id="p1", frontend_id="p2")
        p1 = MockDepPlugin(deps=["lib-a"])
        p1.name = "p1"
        p2 = MockDepPlugin(deps=["lib-b"])
        p2.name = "p2"
        registry = build_registry([p1, p2])
        cancel_progress = _CancellableReporter(cancel_after=999)

        PluginExecutionEngine(registry).run(spec, output_dir, txn, cancel_progress)

        assert "lib-a" in txn.requirements
        assert "lib-b" in txn.requirements


# ====================================================================
# AC-8: JustfileGenerator
# ====================================================================


class TestJustfileGenerator:
    """AC-8: justfile with setup, dev, test, lint, format, build commands."""

    COMMANDS = {"setup", "dev", "test", "lint", "format", "build"}

    def test_justfile_contains_default_commands(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.justfile_generator import JustfileGenerator

        JustfileGenerator().run(spec, output_dir, txn, progress)

        justfile_content = next(c[1] for c in txn.stage_file_calls if c[0] == "justfile")
        for cmd in self.COMMANDS:
            assert cmd in justfile_content

    def test_justfile_called_via_stage_file(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.justfile_generator import JustfileGenerator

        JustfileGenerator().run(spec, output_dir, txn, progress)

        staged_paths = {c[0] for c in txn.stage_file_calls}
        assert "justfile" in staged_paths

    def test_justfile_no_domains_still_has_commands(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, empty_spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.justfile_generator import JustfileGenerator

        JustfileGenerator().run(empty_spec, output_dir, txn, progress)

        justfile_content = next(c[1] for c in txn.stage_file_calls if c[0] == "justfile")
        for cmd in self.COMMANDS:
            assert cmd in justfile_content


# ====================================================================
# AC-9: ProjectDocumentationWriter
# ====================================================================


class TestProjectDocumentationWriter:
    """AC-9: AGENTS.md + .claude/CLAUDE.md with project name."""

    def test_agents_md_contains_project_name(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.project_documentation_writer import ProjectDocumentationWriter

        ProjectDocumentationWriter().run(spec, output_dir, txn, progress)

        agents_content = next(c[1] for c in txn.stage_file_calls if c[0] == "AGENTS.md")
        assert spec.project_name in agents_content

    def test_claude_md_exists(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.project_documentation_writer import ProjectDocumentationWriter

        ProjectDocumentationWriter().run(spec, output_dir, txn, progress)

        staged_paths = {c[0] for c in txn.stage_file_calls}
        assert ".claude/CLAUDE.md" in staged_paths

    def test_empty_spec_still_generates_both_files(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, empty_spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.project_documentation_writer import ProjectDocumentationWriter

        ProjectDocumentationWriter().run(empty_spec, output_dir, txn, progress)

        staged_paths = {c[0] for c in txn.stage_file_calls}
        assert "AGENTS.md" in staged_paths
        assert ".claude/CLAUDE.md" in staged_paths


# ====================================================================
# AC-10: AgentSkillScaffolder
# ====================================================================


class TestAgentSkillScaffolder:
    """AC-10: .opencode/skills/, .opencode/agents/, .opencode/handoffs/."""

    EXPECTED_DIRS = {".opencode/skills/", ".opencode/agents/", ".opencode/handoffs/"}

    def test_all_three_directories_created(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.agent_skill_scaffolder import AgentSkillScaffolder

        AgentSkillScaffolder().run(spec, output_dir, txn, progress)

        for dir_path in self.EXPECTED_DIRS:
            assert dir_path in txn.stage_directory_calls or any(
                c[0].startswith(dir_path.rstrip("/")) for c in txn.stage_file_calls
            )

    def test_directories_created_via_stage_directory(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.agent_skill_scaffolder import AgentSkillScaffolder

        AgentSkillScaffolder().run(spec, output_dir, txn, progress)

        for dir_path in self.EXPECTED_DIRS:
            assert dir_path in txn.stage_directory_calls

    def test_no_plugins_creates_default_stubs(
        self, output_dir: Path, txn: MockTransaction, progress: MagicMock, empty_spec: ProjectSpec
    ) -> None:
        from forge.generation.stages.agent_skill_scaffolder import AgentSkillScaffolder

        AgentSkillScaffolder().run(empty_spec, output_dir, txn, progress)

        for dir_path in self.EXPECTED_DIRS:
            assert dir_path in txn.stage_directory_calls

from __future__ import annotations

from pathlib import Path

import pytest

from forge.domain import GeneratedFile, ProjectSpec
from forge.plugins.base import (
    CommandRunner,
    Configurable,
    DependencyProvider,
    FileProvider,
    PluginBase,
)


class TestMultiPluginPipeline:
    def test_backend_plus_frontend_generation(
        self,
        orchestrator,
        full_spec: ProjectSpec,
        tmp_path: Path,
    ) -> None:
        from forge.generation.progress import MockProgressReporter
        from forge.infrastructure.transaction import GenerationTransaction

        output_dir = tmp_path / "output"
        txn = GenerationTransaction(output_dir)
        progress = MockProgressReporter()

        result = orchestrator.generate(full_spec, output_dir, txn, progress)

        assert result.success is True
        assert result.output_path == output_dir
        # FastAPI files
        assert (output_dir / "app/main.py").exists()
        assert (output_dir / "requirements.txt").exists()
        assert (output_dir / "app/__init__.py").exists()
        # React files (from files() — scaffold's package.json requires mock_executor to be unmocked)
        assert (output_dir / "src/App.tsx").exists()
        assert (output_dir / "src/main.tsx").exists()
        assert (output_dir / "vite.config.ts").exists()
        assert (output_dir / "tsconfig.json").exists()
        assert (output_dir / "public/index.html").exists()
        assert (output_dir / "src/index.css").exists()
        # Shared structure
        assert (output_dir / "README.md").exists()
        assert (output_dir / "justfile").exists()
        assert (output_dir / "AGENTS.md").exists()
        assert not (output_dir / ".forge-staging").exists()

    def test_plugin_directory_coexistence(
        self,
        orchestrator,
        django_htmx_spec: ProjectSpec,
        tmp_path: Path,
    ) -> None:
        from forge.generation.progress import MockProgressReporter
        from forge.infrastructure.transaction import GenerationTransaction

        output_dir = tmp_path / "output"
        txn = GenerationTransaction(output_dir)
        progress = MockProgressReporter()

        result = orchestrator.generate(django_htmx_spec, output_dir, txn, progress)

        assert result.success is True
        # Both plugins produce templates/ — verify coexistence
        assert (output_dir / "templates").is_dir()
        # Django files
        assert (output_dir / "config/settings.py").exists()
        assert (output_dir / "manage.py").exists()
        # HTMX file
        assert (output_dir / "templates/base.html").exists()
        assert not (output_dir / ".forge-staging").exists()

    def test_django_with_htmx(
        self,
        orchestrator,
        django_htmx_spec: ProjectSpec,
        tmp_path: Path,
    ) -> None:
        from forge.generation.progress import MockProgressReporter
        from forge.infrastructure.transaction import GenerationTransaction

        output_dir = tmp_path / "output"
        txn = GenerationTransaction(output_dir)
        progress = MockProgressReporter()

        result = orchestrator.generate(django_htmx_spec, output_dir, txn, progress)

        assert result.success is True
        # Django-specific files
        assert (output_dir / "config/settings.py").exists()
        assert (output_dir / "manage.py").exists()
        assert (output_dir / "requirements.txt").exists()
        reqs = (output_dir / "requirements.txt").read_text()
        assert "django" in reqs
        # HTMX files
        assert (output_dir / "templates/base.html").exists()
        base_content = (output_dir / "templates/base.html").read_text()
        assert "htmx" in base_content
        assert not (output_dir / ".forge-staging").exists()

    def test_plugin_dependency_ordering(
        self,
        pipeline_registry,
    ) -> None:
        class PluginA(PluginBase, FileProvider, CommandRunner):
            name = "plugin-a"
            display_name = "Plugin A"
            description = ""
            requires = ["plugin-b"]

            def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
                return []

            def directories(self, spec: ProjectSpec) -> list[str]:
                return []

            def generate(self, spec: ProjectSpec, target_dir: Path, executor: object) -> None:
                pass

        class PluginB(PluginBase, FileProvider, CommandRunner):
            name = "plugin-b"
            display_name = "Plugin B"
            description = ""
            requires = []

            def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
                return []

            def directories(self, spec: ProjectSpec) -> list[str]:
                return []

            def generate(self, spec: ProjectSpec, target_dir: Path, executor: object) -> None:
                pass

        pipeline_registry._discovered["plugin-a"] = PluginA()
        pipeline_registry._discovered["plugin-b"] = PluginB()

        ordered_names = [p.name for p in pipeline_registry.topological_sort(["plugin-a", "plugin-b"])]
        assert ordered_names == ["plugin-b", "plugin-a"]

from __future__ import annotations

from pathlib import Path

from forge.domain import Domain, ProjectSpec, TemplateDefinition
from forge.generation.progress import MockProgressReporter
from forge.infrastructure.transaction import GenerationTransaction

# ====================================================================
# Orchestrator Pipeline — Integration Tests
# ====================================================================
# Uses real PluginRegistry (via pipeline_registry), real 6 stages,
# real GenerationTransaction, and real MockProgressReporter.
# ProcessExecutor is mocked via the orchestrator fixture.
# ====================================================================


class TestOrchestratorPipeline:
    def test_orchestrator_full_pipeline(
        self,
        orchestrator,
        fastapi_spec: ProjectSpec,
        tmp_path: Path,
    ) -> None:
        output_dir = tmp_path / "output"
        txn = GenerationTransaction(output_dir)
        progress = MockProgressReporter()

        result = orchestrator.generate(fastapi_spec, output_dir, txn, progress)

        assert result.success is True
        assert result.output_path == output_dir
        assert (output_dir / "app/main.py").exists()
        assert (output_dir / "requirements.txt").exists()
        assert (output_dir / "app/__init__.py").exists()
        assert (output_dir / "README.md").exists()
        assert (output_dir / "justfile").exists()
        assert (output_dir / "AGENTS.md").exists()
        assert not (output_dir / ".forge-staging").exists()

    def test_orchestrator_empty_project(
        self,
        orchestrator,
        tmp_path: Path,
        spec_factory,
    ) -> None:
        spec = spec_factory(backend_id="")
        output_dir = tmp_path / "output"
        txn = GenerationTransaction(output_dir)
        progress = MockProgressReporter()

        result = orchestrator.generate(spec, output_dir, txn, progress)

        assert result.success is True
        # Shared structure files — produced by stages 1-2, 4-6
        assert (output_dir / "README.md").exists()
        assert (output_dir / ".gitignore").exists()
        assert (output_dir / "justfile").exists()
        assert (output_dir / "AGENTS.md").exists()
        # No plugin-specific files
        assert not (output_dir / "app").exists()
        assert not (output_dir / "requirements.txt").exists()
        assert not (output_dir / ".forge-staging").exists()

    def test_orchestrator_rollback_on_failure(
        self,
        orchestrator,
        tmp_path: Path,
        spec_factory,
    ) -> None:
        spec = spec_factory(backend_id="nonexistent")
        spec.config = {}
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        txn = GenerationTransaction(output_dir)
        progress = MockProgressReporter()

        result = orchestrator.generate(spec, output_dir, txn, progress)

        assert result.success is False
        assert not (output_dir / ".forge-staging").exists()
        # No committed files
        committed = list(output_dir.iterdir())
        assert all(e.name.startswith(".") or e.name == ".forge-staging" for e in committed)

    def test_orchestrator_get_questions_using_real_registry(
        self,
        pipeline_registry,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator
        from forge.generation.validation import ValidationEngine

        validation = ValidationEngine(pipeline_registry)
        orch = Orchestrator(pipeline_registry, validation)

        questions = orch.get_domain_questions("fastapi", None)

        assert "fastapi" in questions
        fastapi_qs = questions["fastapi"]
        assert len(fastapi_qs) > 0
        keys = {q.key for q in fastapi_qs}
        assert "orm" in keys
        assert "auth" in keys
        assert "include_alembic" in keys

    def test_orchestrator_unresolvable_backend_id(
        self,
        pipeline_registry,
    ) -> None:
        from forge.generation.validation import ValidationEngine

        validation = ValidationEngine(pipeline_registry)
        spec = ProjectSpec(
            project_name="test-proj",
            template=TemplateDefinition(
                id="test",
                display_name="Test",
                description="",
                backend_id="nonexistent",
                frontend_id=None,
            ),
            domains=[Domain(name="Web")],
            config={},
        )

        errors = validation.validate_spec(spec)

        error_errors = [e for e in errors if e.severity == "error"]
        assert any("backend_id" in e.field for e in error_errors)

    def test_orchestrator_overwrite_confirmed_real_stages(
        self,
        orchestrator,
        fastapi_spec: ProjectSpec,
        tmp_path: Path,
    ) -> None:
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "pre_existing.txt").write_text("keep me")
        txn = GenerationTransaction(output_dir)
        progress = MockProgressReporter()

        result = orchestrator.generate(
            fastapi_spec, output_dir, txn, progress, overwrite_confirmed=True
        )

        assert result.success is True
        assert (output_dir / "pre_existing.txt").read_text() == "keep me"
        assert (output_dir / "app/main.py").exists()
        assert (output_dir / "README.md").exists()
        assert not (output_dir / ".forge-staging").exists()

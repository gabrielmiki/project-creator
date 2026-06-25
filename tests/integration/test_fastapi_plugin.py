from __future__ import annotations

from pathlib import Path

from forge.domain import ProjectSpec

# ====================================================================
# FastAPI Plugin — Integration Tests
# ====================================================================
# Uses real PluginRegistry, real FastapiPlugin, real PluginExecutionEngine,
# and real GenerationTransaction on temp_dir filesystem.
# ProcessExecutor is mocked via the orchestrator fixture.
# ====================================================================


class TestFastAPIPlugin:
    def test_fastapi_generates_correct_files(
        self,
        orchestrator,
        fastapi_spec: ProjectSpec,
        tmp_path: Path,
    ) -> None:
        from forge.generation.progress import MockProgressReporter
        from forge.infrastructure.transaction import GenerationTransaction

        output_dir = tmp_path / "output"
        txn = GenerationTransaction(output_dir)
        progress = MockProgressReporter()

        result = orchestrator.generate(fastapi_spec, output_dir, txn, progress)

        assert result.success is True
        assert (output_dir / "app/main.py").exists()
        assert (output_dir / "app/__init__.py").exists()
        assert (output_dir / "app/schemas.py").exists()
        assert (output_dir / "app/routes/__init__.py").exists()
        assert (output_dir / "app/routes/health.py").exists()
        assert (output_dir / "app/models.py").exists()
        assert (output_dir / "app/database.py").exists()
        assert (output_dir / "requirements.txt").exists()

        reqs = (output_dir / "requirements.txt").read_text()
        assert "fastapi" in reqs
        assert "sqlalchemy" in reqs
        assert "aiosqlite" in reqs

    def test_fastapi_config_variations(
        self,
        orchestrator,
        spec_factory,
        tmp_path: Path,
    ) -> None:
        from forge.generation.progress import MockProgressReporter
        from forge.infrastructure.transaction import GenerationTransaction

        spec = spec_factory(backend_id="fastapi")
        spec.config = {"fastapi": {"orm": "none", "auth": True, "include_alembic": False}}

        output_dir = tmp_path / "output"
        txn = GenerationTransaction(output_dir)
        progress = MockProgressReporter()

        result = orchestrator.generate(spec, output_dir, txn, progress)

        assert result.success is True
        assert (output_dir / "app/main.py").exists()
        assert (output_dir / "app/middleware/__init__.py").exists()
        assert (output_dir / "app/middleware/auth.py").exists()
        assert (output_dir / "app/routes/auth.py").exists()
        # ORM=none → no models or database files
        assert not (output_dir / "app/models.py").exists()
        assert not (output_dir / "app/database.py").exists()
        assert not (output_dir / "alembic").exists()

        reqs = (output_dir / "requirements.txt").read_text()
        assert "sqlalchemy" not in reqs
        assert "jose" in reqs
        assert "passlib" in reqs

    def test_fastapi_plugin_execution_engine_real_plugin(
        self,
        pipeline_registry,
        temp_dir: Path,
        spec_factory,
        mock_executor,
    ) -> None:
        from forge.generation.progress import MockProgressReporter
        from forge.generation.stages.plugin_execution_engine import PluginExecutionEngine
        from forge.infrastructure.transaction import GenerationTransaction

        spec = spec_factory(backend_id="fastapi")
        spec.config = {"fastapi": {"orm": "sqlalchemy", "auth": False, "include_alembic": True}}

        output_dir = temp_dir / "output"
        txn = GenerationTransaction(output_dir)
        progress = MockProgressReporter()

        engine = PluginExecutionEngine(pipeline_registry, executor=mock_executor)
        engine.run(spec, output_dir, txn, progress)

        staged = txn.staging
        assert (staged / "app/main.py").exists()
        assert (staged / "app/models.py").exists()
        assert (staged / "app/database.py").exists()
        assert (staged / "requirements.txt").exists()
        assert (staged / "alembic").is_dir()

        reqs = (staged / "requirements.txt").read_text()
        assert "sqlalchemy" in reqs
        assert "aiosqlite" in reqs

        assert "fastapi>=0.115" in txn.requirements
        assert "sqlalchemy>=2.0" in txn.requirements

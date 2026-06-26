from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QThread
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from forge.domain import Domain, ProjectSpec, TemplateDefinition


class TestErrorScenarios:
    def test_error_mid_stage_rollback(
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

        orchestrator._executor.run.side_effect = RuntimeError("mid-stage failure")

        result = orchestrator.generate(full_spec, output_dir, txn, progress)

        assert result.success is False
        assert "mid-stage failure" in result.error
        assert not (output_dir / ".forge-staging").exists()

    def test_error_scaffold_command_failure(
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

        orchestrator._executor.run.side_effect = RuntimeError("scaffold failed")

        result = orchestrator.generate(fastapi_spec, output_dir, txn, progress)

        assert result.success is False
        assert "scaffold failed" in result.error
        assert not (output_dir / ".forge-staging").exists()

    def test_error_scaffold_timeout(
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

        orchestrator._executor.run.side_effect = TimeoutError("timed out")

        result = orchestrator.generate(fastapi_spec, output_dir, txn, progress)

        assert result.success is False
        assert "timed out" in result.error
        assert not (output_dir / ".forge-staging").exists()

    def test_error_missing_plugin_id_cli(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        import json

        spec = {
            "project_name": "test-proj",
            "template": {
                "id": "invalid",
                "display_name": "Invalid",
                "description": "",
                "backend_id": "nonexistent",
                "frontend_id": None,
            },
            "domains": [{"name": "web"}],
            "config": {},
        }
        spec_path = tmp_path / "spec.json"
        spec_path.write_text(json.dumps(spec))
        output_dir = tmp_path / "output"
        args = ["forge", "--headless", str(spec_path), str(output_dir)]

        with patch.object(sys, "argv", args):
            with patch("forge.generation.orchestrator.ProcessExecutor") as mock_exec_cls:
                mock_exec_cls.return_value = MagicMock()
                from forge.app import main as app_main

                with pytest.raises(SystemExit) as exc_info:
                    app_main()

        assert exc_info.value.code == 1
        out, _ = capsys.readouterr()
        assert "not found" in out

    def test_error_missing_plugin_id_api(
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

    def test_error_empty_project_name(
        self,
        pipeline_registry,
    ) -> None:
        from forge.generation.validation import ValidationEngine

        validation = ValidationEngine(pipeline_registry)
        spec = ProjectSpec(
            project_name="",
            template=TemplateDefinition(
                id="test",
                display_name="Test",
                description="",
                backend_id="fastapi",
                frontend_id=None,
            ),
            domains=[Domain(name="Web")],
            config={},
        )

        errors = validation.validate_spec(spec)

        error_errors = [e for e in errors if e.severity == "error"]
        assert any(e.field == "project_name" for e in error_errors)

    @pytest.mark.skip(reason="not implemented — requires sanitization")
    def test_error_special_chars_in_name(self) -> None:
        pass


@pytest.mark.gui
class TestScaffoldOverlap:
    def test_react_scaffold_files_overlap(
        self,
        qapp: object,
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
        # Files produced by React.files() — these would overlap with
        # create-vite scaffold output if executor were not mocked.
        # With mock executor, only files() side is verifiable.
        assert (output_dir / "vite.config.ts").exists()
        assert (output_dir / "src/App.tsx").exists()
        assert (output_dir / "src/main.tsx").exists()
        assert (output_dir / "tsconfig.json").exists()
        assert (output_dir / "public/index.html").exists()
        assert (output_dir / "src/index.css").exists()
        # Verify staging handled duplication idempotently
        assert not (output_dir / ".forge-staging").exists()

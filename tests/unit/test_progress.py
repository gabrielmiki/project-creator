from __future__ import annotations

import ast
import pathlib

import pytest

from forge.domain import DurationEstimate
from forge.generation.progress import (
    MockProgressReporter,
    ProgressReporter,
    StdoutProgressReporter,
)


class TestAC1_StdoutReporter:

    def test_stdout_contains_stage_name_and_step_messages_in_order(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        reporter = StdoutProgressReporter()
        reporter.on_stage_start("DirectoryInitializer", 3)
        reporter.on_step_complete("mkdir")
        reporter.on_stage_complete("DirectoryInitializer")
        captured = capsys.readouterr()
        assert "DirectoryInitializer" in captured.out
        assert "mkdir" in captured.out


class TestAC2_MockReporterCalls:

    def test_calls_tracked_in_order(self) -> None:
        reporter = MockProgressReporter()
        reporter.on_stage_start("init", 1)
        reporter.on_step_complete("mkdir")
        assert reporter.calls == [
            ("on_stage_start", "init", 1),
            ("on_step_complete", "mkdir"),
        ]

    def test_empty_calls_before_any_method(self) -> None:
        reporter = MockProgressReporter()
        assert reporter.calls == []


class TestAC3_ProtocolIsInstance:

    def test_isinstance_returns_true_for_stdout_reporter(self) -> None:
        assert isinstance(StdoutProgressReporter(), ProgressReporter)

    def test_isinstance_false_when_method_missing(self) -> None:
        class IncompleteReporter:
            def on_stage_start(self, stage_name: str, total_steps: int) -> None:
                pass

        assert not isinstance(IncompleteReporter(), ProgressReporter)


class TestAC4_ErrorTracking:

    def test_errors_tracked_with_recoverable_flag(self) -> None:
        reporter = MockProgressReporter()
        reporter.on_error(ValueError("config err"), True)
        reporter.on_error(RuntimeError("crash"), False)
        assert len(reporter.calls) == 2
        assert reporter.calls[0][0] == "on_error"
        assert isinstance(reporter.calls[0][1], ValueError)
        assert str(reporter.calls[0][1]) == "config err"
        assert reporter.calls[0][2] is True
        assert reporter.calls[1][0] == "on_error"
        assert isinstance(reporter.calls[1][1], RuntimeError)
        assert str(reporter.calls[1][1]) == "crash"
        assert reporter.calls[1][2] is False


class TestAC5_LogLevels:

    def test_warning_level_shows_prefix(self, capsys: pytest.CaptureFixture[str]) -> None:
        reporter = StdoutProgressReporter()
        reporter.on_log("message", "warning")
        captured = capsys.readouterr()
        assert "warning" in captured.out
        assert "message" in captured.out

    def test_default_info_level_shows_prefix(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        reporter = StdoutProgressReporter()
        reporter.on_log("info message")
        captured = capsys.readouterr()
        assert "info" in captured.out
        assert "info message" in captured.out


class TestAC6_DurationEstimate:

    def test_duration_estimate_tracked_in_calls(self) -> None:
        reporter = MockProgressReporter()
        de = DurationEstimate(estimated_seconds=30, has_slow_steps=True, slow_step_details=["npm install"])
        reporter.on_duration_estimate(de)
        assert len(reporter.calls) == 1
        assert reporter.calls[0][0] == "on_duration_estimate"
        assert reporter.calls[0][1] == de

    def test_duration_estimate_with_empty_slow_step_details(self) -> None:
        reporter = MockProgressReporter()
        de = DurationEstimate(estimated_seconds=10, has_slow_steps=False, slow_step_details=[])
        reporter.on_duration_estimate(de)
        assert reporter.calls[0][1].slow_step_details == []


class TestAC7_EmptyInputs:

    def test_no_crash_on_empty_stage_name_and_zero_steps(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        reporter = StdoutProgressReporter()
        reporter.on_stage_start("", 0)
        captured = capsys.readouterr()
        assert captured.out


class TestAC8_NoCrossLayerImports:
    FORBIDDEN_PREFIXES = ("forge.ui",)

    def _generation_source_files(self) -> list[pathlib.Path]:
        here = pathlib.Path(__file__).resolve().parent.parent.parent
        gen_dir = here / "src" / "forge" / "generation"
        files = sorted(gen_dir.rglob("*.py"))
        assert files, (
            f"No source files found in {gen_dir}. "
            f"Expected at least progress.py and __init__.py."
        )
        return files

    def test_forbidden_ui_imports(self) -> None:
        for source_file in self._generation_source_files():
            tree = ast.parse(source_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._check_forbidden(alias.name, source_file.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self._check_forbidden(node.module, source_file.name)

    def test_infrastructure_imports_allowed(self) -> None:
        for source_file in self._generation_source_files():
            tree = ast.parse(source_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("forge.infrastructure"):
                        break
            else:
                pytest.fail(
                    f"{source_file.name} does not import from forge.infrastructure "
                    f"— generation layer is expected to use infrastructure services"
                )

    def _check_forbidden(self, module_name: str, filename: str) -> None:
        for prefix in self.FORBIDDEN_PREFIXES:
            if module_name == prefix or module_name.startswith(prefix + "."):
                pytest.fail(f"{filename} imports forbidden module: {module_name}")


class TestAC9_ShouldCancel:

    def test_should_cancel_returns_false_by_default(self) -> None:
        reporter = MockProgressReporter()
        assert reporter.should_cancel() is False

    def test_should_cancel_tracked_in_calls(self) -> None:
        reporter = MockProgressReporter()
        reporter.should_cancel()
        assert reporter.calls == [("should_cancel",)]

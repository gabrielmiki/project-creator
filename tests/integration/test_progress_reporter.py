from __future__ import annotations

import pytest

from forge.generation.progress import (
    MockProgressReporter,
    StdoutProgressReporter,
)


class TestIntegration_MockProgressReporter:
    """Deferred from T-003 post-mortem: verifies typed call records
    with consistent tuple lengths."""

    def test_mock_reporter_records_typed_calls(self) -> None:
        reporter = MockProgressReporter()
        assert reporter.calls == []

        reporter.on_stage_start("init", 1)
        reporter.on_step_complete("mkdir")
        reporter.on_stage_complete("init")

        assert len(reporter.calls) == 3
        assert reporter.calls[0] == ("on_stage_start", "init", 1)
        assert reporter.calls[1] == ("on_step_complete", "mkdir")
        assert reporter.calls[2] == ("on_stage_complete", "init")


class TestIntegration_StdoutProgressReporter:
    def test_stdout_prints_expected_text(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reporter = StdoutProgressReporter()
        reporter.on_stage_start("GenStage", 3)
        reporter.on_step_complete("step1")
        captured = capsys.readouterr()
        assert "GenStage" in captured.out
        assert "step1" in captured.out

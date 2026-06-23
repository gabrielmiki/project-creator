from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt, QThread
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from forge.domain import DurationEstimate
from forge.generation.orchestrator import GenerationResult
from forge.generation.progress import ProgressReporter

# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    orch: MagicMock = MagicMock()
    orch.generate.return_value = GenerationResult(
        success=True, error=None, output_path=Path("/tmp/test"),
    )
    return orch


@pytest.fixture
def mock_txn() -> MagicMock:
    txn: MagicMock = MagicMock(spec=["rollback", "commit", "stage_file", "stage_directory"])
    return txn


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    return tmp_path / "output"


@pytest.fixture
def spec() -> MagicMock:
    return MagicMock()


@pytest.fixture
def reporter() -> object:
    from forge.ui.workers import QtProgressReporter

    return QtProgressReporter()


@pytest.fixture
def worker(
    mock_orchestrator: MagicMock,
    spec: MagicMock,
    output_dir: Path,
    mock_txn: MagicMock,
    reporter: object,
) -> object:
    from forge.ui.workers import GenerationWorker

    return GenerationWorker(
        orchestrator=mock_orchestrator,
        spec=spec,
        output_dir=output_dir,
        txn=mock_txn,
        progress=reporter,
    )


# ====================================================================
# Helpers
# ====================================================================


def _make_polling_side_effect(
    mock_txn: MagicMock, output_dir: Path,
) -> object:
    def _generate_with_polling(
        _spec: object, _output_dir: object, _txn: object, progress: object, **kw: object,
    ) -> GenerationResult:
        for _ in range(10):
            time.sleep(0.005)
            if progress.should_cancel():  # type: ignore[attr-defined]
                mock_txn.rollback()
                return GenerationResult(False, "Cancelled", None)
        return GenerationResult(True, None, output_dir)
    return _generate_with_polling


# ====================================================================
# AC-1: Success → finished(success=True) + output_path
# ====================================================================


class TestAC1_SuccessEmitsFinished:
    def test_success_emits_finished(self, worker: object) -> None:
        result = GenerationResult(success=True, error=None, output_path=Path("/out"))
        worker._orchestrator.generate.return_value = result  # type: ignore[attr-defined]
        spy = QSignalSpy(worker.finished)  # type: ignore[attr-defined]
        worker.run()  # type: ignore[attr-defined]
        assert spy.count() == 1
        assert spy.at(0)[0].success is True
        assert spy.at(0)[0].output_path == Path("/out")


# ====================================================================
# AC-2: on_stage_start("stages", 3) → stage_started signal
# ====================================================================


class TestAC2_OnStageStartSignal:
    def test_on_stage_start_signal(self, reporter: object) -> None:
        spy = QSignalSpy(reporter.stage_started)  # type: ignore[attr-defined]
        reporter.on_stage_start("stages", 3)  # type: ignore[attr-defined]
        assert spy.count() == 1
        assert spy.at(0)[0] == "stages"
        assert spy.at(0)[1] == 3


# ====================================================================
# AC-3: on_step_complete("init") → step_completed signal
# ====================================================================


class TestAC3_OnStepCompleteSignal:
    def test_on_step_complete_signal(self, reporter: object) -> None:
        spy = QSignalSpy(reporter.step_completed)  # type: ignore[attr-defined]
        reporter.on_step_complete("init")  # type: ignore[attr-defined]
        assert spy.count() == 1
        assert spy.at(0)[0] == "init"


# ====================================================================
# AC-4: on_stage_complete("init") → stage_completed signal
# ====================================================================


class TestAC4_OnStageCompleteSignal:
    def test_on_stage_complete_signal(self, reporter: object) -> None:
        spy = QSignalSpy(reporter.stage_completed)  # type: ignore[attr-defined]
        reporter.on_stage_complete("init")  # type: ignore[attr-defined]
        assert spy.count() == 1
        assert spy.at(0)[0] == "init"


# ====================================================================
# AC-5: on_log("building...", "info") → log_message signal
# ====================================================================


class TestAC5_OnLogSignal:
    def test_on_log_signal(self, reporter: object) -> None:
        spy = QSignalSpy(reporter.log_message)  # type: ignore[attr-defined]
        reporter.on_log("building...", "info")  # type: ignore[attr-defined]
        assert spy.count() == 1
        assert spy.at(0)[0] == "building..."
        assert spy.at(0)[1] == "info"


# ====================================================================
# AC-6: on_duration_estimate → duration_estimated signal
# ====================================================================


class TestAC6_OnDurationEstimateSignal:
    def test_on_duration_estimate_signal(self, reporter: object) -> None:
        spy = QSignalSpy(reporter.duration_estimated)  # type: ignore[attr-defined]
        estimate = DurationEstimate(30, True, ["npm install"])
        reporter.on_duration_estimate(estimate)  # type: ignore[attr-defined]
        assert spy.count() == 1
        assert spy.at(0)[0].estimated_seconds == 30


# ====================================================================
# AC-7: isinstance(reporter, ProgressReporter) → True
# ====================================================================


class TestAC7_IsInstanceProtocol:
    def test_isinstance_protocol(self, reporter: object) -> None:
        assert isinstance(reporter, ProgressReporter)


# ====================================================================
# AC-8: Cancel during generation → finished(success=False) + rollback
# ====================================================================


@pytest.mark.gui
class TestAC8_CancelDuringGeneration:
    def test_cancel_during_generation(
        self, qapp: object, mock_orchestrator: MagicMock,
        mock_txn: MagicMock, spec: MagicMock, output_dir: Path,
    ) -> None:
        from forge.ui.workers import GenerationWorker

        mock_orchestrator.generate.side_effect = _make_polling_side_effect(mock_txn, output_dir)
        worker = GenerationWorker(mock_orchestrator, spec, output_dir, txn=mock_txn)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)  # type: ignore[attr-defined]
        worker.finished.connect(thread.quit, Qt.DirectConnection)  # type: ignore[attr-defined]

        spy = QSignalSpy(worker.finished)  # type: ignore[attr-defined]
        thread.start()
        time.sleep(0.02)
        worker.cancel()  # type: ignore[attr-defined]
        thread.wait(3000)
        QApplication.processEvents()

        assert spy.count() == 1
        assert spy.at(0)[0].success is False
        assert spy.at(0)[0].error == "Cancelled"
        mock_txn.rollback.assert_called_once()


# ====================================================================
# AC-9: on_error → error_occurred signal with str conversion
# ====================================================================


class TestAC9_OnErrorSignal:
    def test_on_error_signal(self, reporter: object) -> None:
        spy = QSignalSpy(reporter.error_occurred)  # type: ignore[attr-defined]
        reporter.on_error(ValueError("config err"), True)  # type: ignore[attr-defined]
        assert spy.count() == 1
        assert spy.at(0)[0] == "config err"
        assert spy.at(0)[1] is True


# ====================================================================
# AC-10: Exception in run() → finished(success=False) + rollback
# ====================================================================


class TestAC10_RunExceptionRollback:
    def test_run_exception_triggers_rollback(self, worker: object, mock_txn: MagicMock) -> None:
        worker._orchestrator.generate.side_effect = RuntimeError("boom")  # type: ignore[attr-defined]
        spy = QSignalSpy(worker.finished)  # type: ignore[attr-defined]
        worker.run()  # type: ignore[attr-defined]
        assert spy.count() == 1
        assert spy.at(0)[0].success is False
        assert "boom" in spy.at(0)[0].error
        mock_txn.rollback.assert_called_once()


# ====================================================================
# AC-11: cancel() before run() → finished NOT emitted
# ====================================================================


class TestAC11_CancelBeforeRun:
    def test_cancel_before_run_no_finished(self, worker: object) -> None:
        spy = QSignalSpy(worker.finished)  # type: ignore[attr-defined]
        worker.cancel()  # type: ignore[attr-defined]
        worker.run()  # type: ignore[attr-defined]
        assert spy.count() == 0


# ====================================================================
# AC-12: cancel() after finished → idempotent (no re-emission)
# ====================================================================


class TestAC12_CancelAfterFinished:
    def test_cancel_after_finished_idempotent(self, worker: object) -> None:
        result = GenerationResult(success=True, error=None, output_path=Path("/out"))
        worker._orchestrator.generate.return_value = result  # type: ignore[attr-defined]
        spy = QSignalSpy(worker.finished)  # type: ignore[attr-defined]
        worker.run()  # type: ignore[attr-defined]
        assert spy.count() == 1
        worker.cancel()  # type: ignore[attr-defined]
        assert spy.count() == 1


# ====================================================================
# AC-13: Multiple cancel() calls → finished emitted exactly once
# ====================================================================


@pytest.mark.gui
class TestAC13_MultipleCancel:
    def test_multiple_cancel_emits_finished_once(
        self, qapp: object, mock_orchestrator: MagicMock,
        mock_txn: MagicMock, spec: MagicMock, output_dir: Path,
    ) -> None:
        from forge.ui.workers import GenerationWorker

        mock_orchestrator.generate.side_effect = _make_polling_side_effect(mock_txn, output_dir)
        worker = GenerationWorker(mock_orchestrator, spec, output_dir, txn=mock_txn)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)  # type: ignore[attr-defined]
        worker.finished.connect(thread.quit, Qt.DirectConnection)  # type: ignore[attr-defined]

        spy = QSignalSpy(worker.finished)  # type: ignore[attr-defined]
        thread.start()
        time.sleep(0.02)
        for _ in range(3):
            worker.cancel()  # type: ignore[attr-defined]
        thread.wait(3000)
        QApplication.processEvents()

        assert spy.count() == 1


# ====================================================================
# AC-14: on_stage_start("", 0) → no exception, signal emitted
# ====================================================================


class TestAC14_EmptyInput:
    def test_on_stage_start_empty_input(self, reporter: object) -> None:
        spy = QSignalSpy(reporter.stage_started)  # type: ignore[attr-defined]
        reporter.on_stage_start("", 0)  # type: ignore[attr-defined]
        assert spy.count() == 1
        assert spy.at(0)[0] == ""
        assert spy.at(0)[1] == 0


# ====================================================================
# AC-15: should_cancel() before/after cancel()
# ====================================================================


class TestAC15_ShouldCancelLifecycle:
    def test_should_cancel_before_cancel_returns_false(self, reporter: object) -> None:
        assert reporter.should_cancel() is False  # type: ignore[attr-defined]

    def test_should_cancel_after_cancel_returns_true(
        self, worker: object, reporter: object,
    ) -> None:
        worker.cancel()  # type: ignore[attr-defined]
        assert reporter.should_cancel() is True  # type: ignore[attr-defined]

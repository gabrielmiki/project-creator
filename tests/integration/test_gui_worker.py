from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt, QThread
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from forge.domain import ProjectSpec
from forge.generation.orchestrator import GenerationResult


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    orch: MagicMock = MagicMock()
    orch.generate.return_value = GenerationResult(
        success=True, error=None, output_path=Path("/tmp/test"),
    )
    return orch


def _make_polling_fn(
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


def _make_raise_fn(error: str) -> object:
    def _generate_raise(
        _spec: object, _output_dir: object, _txn: object, _progress: object, **kw: object,
    ) -> GenerationResult:
        raise RuntimeError(error)
    return _generate_raise


@pytest.mark.gui
class TestGUIWorker:
    def test_worker_generates_on_thread(
        self, qapp: object, orchestrator, full_spec: ProjectSpec, tmp_path: Path,
    ) -> None:
        from forge.ui.workers import GenerationWorker

        output_dir = tmp_path / "output"
        worker = GenerationWorker(orchestrator, full_spec, output_dir)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit, Qt.DirectConnection)

        spy = QSignalSpy(worker.finished)
        thread.start()
        thread.wait(5000)
        QApplication.processEvents()

        assert spy.count() == 1
        assert spy.at(0)[0].success is True
        assert spy.at(0)[0].output_path == output_dir

    def test_worker_cancel_during_generation(
        self, monkeypatch, qapp: object, orchestrator, full_spec: ProjectSpec, tmp_path: Path,
    ) -> None:
        from forge.infrastructure.transaction import GenerationTransaction
        from forge.ui.workers import GenerationWorker

        mock_txn = MagicMock(spec=["rollback", "commit"])
        output_dir = tmp_path / "output"
        monkeypatch.setattr(
            orchestrator, "generate", _make_polling_fn(mock_txn, output_dir),
        )

        worker = GenerationWorker(
            orchestrator, full_spec, output_dir, txn=mock_txn,
        )
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit, Qt.DirectConnection)

        spy = QSignalSpy(worker.finished)
        thread.start()
        time.sleep(0.02)
        worker.cancel()
        thread.wait(5000)
        QApplication.processEvents()

        assert spy.count() == 1
        assert spy.at(0)[0].success is False
        assert spy.at(0)[0].error == "Cancelled"
        mock_txn.rollback.assert_called_once()

    def test_worker_signals_connected(
        self, qapp: object, orchestrator, tmp_path: Path, monkeypatch,
    ) -> None:
        from forge.domain import DurationEstimate
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.ui.screens.generation_screen import GenerationScreen
        from PySide6.QtWidgets import QWidget, QApplication

        mock_orch = MagicMock(wraps=orchestrator)
        mock_orch.estimate_duration.return_value = DurationEstimate(5, False, [])
        screens = [QWidget(), QWidget(), QWidget(), ReviewScreen(mock_orch), GenerationScreen()]
        screens[0].can_proceed = True  # type: ignore[attr-defined]

        window = MainWindow(orchestrator=mock_orch, screens=screens)
        window.show()
        QApplication.processEvents()

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(Path, "exists", lambda _: False)
        monkeypatch.setattr(QThread, "start", lambda self: None)

        window.navigate_to(3)
        spy = QSignalSpy(window.generation_requested)
        window.next_screen()

        assert spy.count() == 1
        assert isinstance(spy.at(0)[0], ProjectSpec)
        window.close()

    def test_worker_finished_signal_on_failure(
        self, monkeypatch, qapp: object, orchestrator, full_spec: ProjectSpec, tmp_path: Path,
    ) -> None:
        from forge.infrastructure.transaction import GenerationTransaction
        from forge.ui.workers import GenerationWorker

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        txn = GenerationTransaction(output_dir)

        monkeypatch.setattr(
            orchestrator, "generate", _make_raise_fn("boom"),
        )

        worker = GenerationWorker(orchestrator, full_spec, output_dir, txn=txn)
        spy = QSignalSpy(worker.finished)
        worker.run()

        assert spy.count() == 1
        assert spy.at(0)[0].success is False
        assert "boom" in spy.at(0)[0].error

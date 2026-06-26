from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QThread
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication, QMessageBox


@pytest.mark.gui
class TestOverwriteFlow:
    def test_overwrite_confirm_dialog_shown(
        self, qapp: object, orchestrator, monkeypatch, tmp_path: Path,
    ) -> None:
        from forge.domain import DurationEstimate
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.ui.screens.generation_screen import GenerationScreen
        from PySide6.QtWidgets import QWidget

        mock_orch = MagicMock(wraps=orchestrator)
        mock_orch.estimate_duration.return_value = DurationEstimate(5, False, [])

        screens = [QWidget(), QWidget(), QWidget(), ReviewScreen(mock_orch), GenerationScreen()]
        screens[0].can_proceed = True  # type: ignore[attr-defined]

        window = MainWindow(orchestrator=mock_orch, screens=screens)
        window.show()
        QApplication.processEvents()

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(Path, "exists", lambda _: True)
        monkeypatch.setattr(QThread, "start", lambda self: None)

        question_called = False

        def fake_question(*a, **kw):
            nonlocal question_called
            question_called = True
            return QMessageBox.StandardButton.No

        monkeypatch.setattr(QMessageBox, "question", fake_question)

        window.navigate_to(3)
        spy = QSignalSpy(window.generation_requested)
        window.next_screen()

        assert question_called, "show_confirm was not triggered"
        assert spy.count() == 0
        window.close()

    def test_overwrite_yes_continues(
        self, qapp: object, orchestrator, mock_executor, monkeypatch, tmp_path: Path,
    ) -> None:
        from forge.domain import DurationEstimate
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.ui.screens.generation_screen import GenerationScreen
        from PySide6.QtWidgets import QWidget

        mock_orch = MagicMock(wraps=orchestrator)
        mock_orch.estimate_duration.return_value = DurationEstimate(5, False, [])

        screens = [QWidget(), QWidget(), QWidget(), ReviewScreen(mock_orch), GenerationScreen()]
        screens[0].can_proceed = True  # type: ignore[attr-defined]

        window = MainWindow(orchestrator=mock_orch, screens=screens)
        window.show()
        QApplication.processEvents()

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(Path, "exists", lambda _: True)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Yes,
        )
        # Prevent real thread start — worker will be created but not run
        monkeypatch.setattr(QThread, "start", lambda self: None)

        window.navigate_to(3)
        window.next_screen()

        assert window._worker is not None
        assert window._stacked.currentIndex() == 4
        window.close()

    def test_overwrite_no_returns_to_review(
        self, qapp: object, orchestrator, monkeypatch, tmp_path: Path,
    ) -> None:
        from forge.domain import DurationEstimate
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.ui.screens.generation_screen import GenerationScreen
        from PySide6.QtWidgets import QWidget

        mock_orch = MagicMock(wraps=orchestrator)
        mock_orch.estimate_duration.return_value = DurationEstimate(5, False, [])

        screens = [QWidget(), QWidget(), QWidget(), ReviewScreen(mock_orch), GenerationScreen()]
        screens[0].can_proceed = True  # type: ignore[attr-defined]

        window = MainWindow(orchestrator=mock_orch, screens=screens)
        window.show()
        QApplication.processEvents()

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(Path, "exists", lambda _: True)
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.No,
        )

        window.navigate_to(3)
        window.next_screen()

        stacked = window.findChild(object, "")
        assert window._stacked.currentIndex() == 3
        assert window._worker is None
        window.close()

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QStackedWidget

from forge.domain import ProjectSpec
from forge.generation.orchestrator import GenerationResult

# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def main_window(qapp: QApplication, mock_orchestrator: MagicMock) -> object:
    from forge.ui.main_window import MainWindow
    from forge.ui.screens.welcome_screen import WelcomeScreen
    from PySide6.QtWidgets import QWidget

    screens = [WelcomeScreen()]
    for _ in range(4):
        screens.append(QWidget())

    screens[0].can_proceed = True

    window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
    window.show()
    yield window
    window.close()


# ====================================================================
# AC-1: Window creation — title, QStackedWidget, 5 screens
# ====================================================================


@pytest.mark.gui
class TestAC1_WindowCreation:
    def test_window_title_and_stacked_widget(self, main_window: object) -> None:
        assert main_window.windowTitle() == "Forge"
        stacked = main_window.findChild(QStackedWidget)
        assert stacked is not None
        assert stacked.count() == 5
        for i in range(5):
            assert stacked.widget(i) is not None


# ====================================================================
# AC-2: Screen 0 — Previous disabled, Next enabled
# ====================================================================


@pytest.mark.gui
class TestAC2_Screen0ButtonStates:
    def test_previous_disabled_next_enabled_at_screen_0(self, main_window: object) -> None:
        main_window.navigate_to(0)
        prev = main_window.findChild(QPushButton, "previous_button")
        next_btn = main_window.findChild(QPushButton, "next_button")
        assert prev is not None
        assert next_btn is not None
        assert prev.isEnabled() is False
        assert next_btn.isEnabled() is True


# ====================================================================
# AC-3: Screen 4 — Previous/Next hidden, Cancel shown
# ====================================================================


@pytest.mark.gui
class TestAC3_Screen4ButtonStates:
    def test_previous_next_hidden_cancel_shown(self, main_window: object) -> None:
        main_window.navigate_to(4)
        prev = main_window.findChild(QPushButton, "previous_button")
        next_btn = main_window.findChild(QPushButton, "next_button")
        cancel = main_window.findChild(QPushButton, "cancel_button")
        assert prev is not None
        assert next_btn is not None
        assert cancel is not None
        assert prev.isVisible() is False
        assert next_btn.isVisible() is False
        assert cancel.isVisible() is True


# ====================================================================
# AC-4: show_error — monitors QMessageBox.critical
# ====================================================================


@pytest.mark.gui
class TestAC4_ShowError:
    def test_show_error_calls_critical(
        self, monkeypatch: pytest.MonkeyPatch, main_window: object,
    ) -> None:
        captured: dict[str, str] = {}

        def fake_critical(parent: object, title: str, text: str) -> QMessageBox.StandardButton:
            captured["title"] = title
            captured["text"] = text
            return QMessageBox.StandardButton.Ok

        monkeypatch.setattr(QMessageBox, "critical", fake_critical)
        main_window.show_error("Error", "Something failed")
        assert captured == {"title": "Error", "text": "Something failed"}


# ====================================================================
# AC-5: show_confirm — Yes → True, No → False
# ====================================================================


@pytest.mark.gui
class TestAC5_ShowConfirm:
    def test_confirm_yes_returns_true(
        self, monkeypatch: pytest.MonkeyPatch, main_window: object,
    ) -> None:
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Yes,
        )
        assert main_window.show_confirm("Confirm", "Proceed?") is True

    def test_confirm_no_returns_false(
        self, monkeypatch: pytest.MonkeyPatch, main_window: object,
    ) -> None:
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.No,
        )
        assert main_window.show_confirm("Confirm", "Proceed?") is False


# ====================================================================
# AC-6: generation_requested signal on 3→4 transition
# ====================================================================


@pytest.mark.gui
class TestAC6_GenerationRequestedSignal:
    def test_generation_requested_emitted_on_next_from_screen_3(self, main_window: object) -> None:
        main_window.navigate_to(3)
        spy = QSignalSpy(main_window.generation_requested)
        main_window.next_screen()
        assert spy.count() == 1
        assert isinstance(spy.at(0)[0], ProjectSpec)


# ====================================================================
# AC-7: generation_completed signal received with GenerationResult
# ====================================================================


@pytest.mark.gui
class TestAC7_GenerationCompletedSignal:
    def test_generation_completed_signal_received(self, main_window: object) -> None:
        spy = QSignalSpy(main_window.generation_completed)
        result = GenerationResult(success=True, error=None, output_path=Path("/tmp/out"))
        main_window.generation_completed.emit(result)
        assert spy.count() == 1
        assert isinstance(spy.at(0)[0], GenerationResult)
        assert spy.at(0)[0].success is True
        assert spy.at(0)[0].output_path == Path("/tmp/out")


# ====================================================================
# AC-8: navigate_to out-of-bounds clamping
# ====================================================================


@pytest.mark.gui
class TestAC8_NavigateToClamping:
    def test_navigate_to_negative_one_clamped_to_zero(self, main_window: object) -> None:
        main_window.navigate_to(0)
        stacked = main_window.findChild(QStackedWidget)
        assert stacked is not None
        main_window.navigate_to(-1)
        assert stacked.currentIndex() == 0

    def test_navigate_to_ten_clamped_to_four(self, main_window: object) -> None:
        main_window.navigate_to(0)
        stacked = main_window.findChild(QStackedWidget)
        assert stacked is not None
        main_window.navigate_to(10)
        assert stacked.currentIndex() == 4


# ====================================================================
# AC-9: previous_screen at screen 0 is no-op
# ====================================================================


@pytest.mark.gui
class TestAC9_PreviousScreenBoundary:
    def test_previous_screen_at_zero_is_noop(self, main_window: object) -> None:
        main_window.navigate_to(0)
        stacked = main_window.findChild(QStackedWidget)
        assert stacked is not None
        main_window.previous_screen()
        assert stacked.currentIndex() == 0


# ====================================================================
# AC-10: next_screen at screen 4 is no-op
# ====================================================================


@pytest.mark.gui
class TestAC10_NextScreenBoundary:
    def test_next_screen_at_four_is_noop(self, main_window: object) -> None:
        main_window.navigate_to(4)
        stacked = main_window.findChild(QStackedWidget)
        assert stacked is not None
        main_window.next_screen()
        assert stacked.currentIndex() == 4


# ====================================================================
# AC-11: show_confirm with Escape returns False
# ====================================================================


@pytest.mark.gui
class TestAC11_ConfirmEscape:
    def test_confirm_escape_returns_false(
        self, monkeypatch: pytest.MonkeyPatch, main_window: object,
    ) -> None:
        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Escape,
        )
        assert main_window.show_confirm("Confirm", "Proceed?") is False


# ====================================================================
# AC-12: Cancel button emits cancelled signal
# ====================================================================


@pytest.mark.gui
class TestAC12_CancelSignal:
    def test_cancel_button_emits_cancelled(self, main_window: object) -> None:
        main_window.navigate_to(4)
        cancel = main_window.findChild(QPushButton, "cancel_button")
        assert cancel is not None
        spy = QSignalSpy(main_window.cancelled)
        QTest.mouseClick(cancel, Qt.LeftButton)
        assert spy.count() == 1

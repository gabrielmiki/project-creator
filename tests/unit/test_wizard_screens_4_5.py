from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTreeWidget,
)

from forge.domain import DurationEstimate, ProjectSpec
from forge.generation.orchestrator import GenerationResult
from forge.plugins.base import PluginBase


def _mock_plugin(display_name: str, name: str, description: str = "") -> MagicMock:
    p: MagicMock = MagicMock(spec=PluginBase)
    p.display_name = display_name
    p.name = name
    p.description = description
    return p


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    from forge.generation.orchestrator import Orchestrator

    orch: MagicMock = MagicMock(spec=Orchestrator)
    orch.get_available_backends.return_value = []
    orch.get_available_frontends.return_value = []
    orch.estimate_duration.return_value = DurationEstimate(
        estimated_seconds=5, has_slow_steps=False, slow_step_details=[],
    )
    return orch


@pytest.fixture
def review_screen(qapp: QApplication, mock_orchestrator: MagicMock) -> object:
    from forge.ui.screens.review_screen import ReviewScreen

    screen = ReviewScreen(mock_orchestrator)
    screen.show()
    yield screen
    screen.close()


@pytest.fixture
def generation_screen(qapp: QApplication) -> object:
    from forge.ui.screens.generation_screen import GenerationScreen

    screen = GenerationScreen()
    screen.show()
    yield screen
    screen.close()


@pytest.fixture
def main_window_with_screens(
    qapp: QApplication, mock_orchestrator: MagicMock,
) -> object:
    from forge.ui.main_window import MainWindow
    from forge.ui.screens.welcome_screen import WelcomeScreen

    from forge.ui.screens.review_screen import ReviewScreen
    from forge.ui.screens.generation_screen import GenerationScreen

    screens = [
        WelcomeScreen(),
        QStackedWidget(),
        QStackedWidget(),
        ReviewScreen(mock_orchestrator),
        GenerationScreen(),
    ]
    screens[0].can_proceed = True

    window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
    window.show()
    yield window
    window.close()


# ====================================================================
# ReviewScreen (AC-01, AC-02)
# ====================================================================


@pytest.mark.gui
class TestReviewScreen:
    def test_tree_displays_backend_frontend_estimate(
        self, qapp: QApplication, mock_orchestrator: MagicMock,
    ) -> None:
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.domain import Domain, TemplateDefinition

        mock_orchestrator.get_available_backends.return_value = [
            _mock_plugin("FastAPI", "fastapi"),
        ]
        mock_orchestrator.get_available_frontends.return_value = [
            _mock_plugin("React", "react"),
        ]
        mock_orchestrator.estimate_duration.return_value = DurationEstimate(
            estimated_seconds=5, has_slow_steps=False, slow_step_details=[],
        )

        screen = ReviewScreen(mock_orchestrator)
        screen.show()

        spec = ProjectSpec(
            project_name="my-app",
            template=TemplateDefinition(
                id="custom", display_name="Custom", description="",
                backend_id="fastapi", frontend_id="react",
            ),
            domains=[],
            config={},
        )
        screen.set_spec(spec)
        screen.on_enter()

        tree = screen.findChild(QTreeWidget, "review_tree")
        assert tree is not None
        found_texts = []
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            found_texts.append(item.text(0))
        assert "FastAPI" in found_texts
        assert "React" in found_texts

        screen.close()

    def test_tree_displays_backend_only(
        self, qapp: QApplication, mock_orchestrator: MagicMock,
    ) -> None:
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.domain import Domain, TemplateDefinition

        mock_orchestrator.get_available_backends.return_value = [
            _mock_plugin("FastAPI", "fastapi"),
        ]
        mock_orchestrator.get_available_frontends.return_value = []
        mock_orchestrator.estimate_duration.return_value = DurationEstimate(
            estimated_seconds=3, has_slow_steps=False, slow_step_details=[],
        )

        screen = ReviewScreen(mock_orchestrator)
        screen.show()

        spec = ProjectSpec(
            project_name="backend-only",
            template=TemplateDefinition(
                id="custom", display_name="Custom", description="",
                backend_id="fastapi", frontend_id=None,
            ),
            domains=[],
            config={},
        )
        screen.set_spec(spec)
        screen.on_enter()

        tree = screen.findChild(QTreeWidget, "review_tree")
        assert tree is not None
        found_texts = []
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            found_texts.append(item.text(0))
        assert "FastAPI" in found_texts
        assert "React" not in found_texts

        screen.close()

    def test_no_plugins_shows_minimal(
        self, qapp: QApplication, mock_orchestrator: MagicMock,
    ) -> None:
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.domain import Domain, TemplateDefinition

        mock_orchestrator.get_available_backends.return_value = []
        mock_orchestrator.get_available_frontends.return_value = []
        mock_orchestrator.estimate_duration.return_value = DurationEstimate(
            estimated_seconds=1, has_slow_steps=False, slow_step_details=[],
        )

        screen = ReviewScreen(mock_orchestrator)
        screen.show()

        spec = ProjectSpec(
            project_name="minimal",
            template=TemplateDefinition(
                id="minimal", display_name="Minimal", description="",
                backend_id="", frontend_id=None,
            ),
            domains=[],
            config={},
        )
        screen.set_spec(spec)
        screen.on_enter()

        tree = screen.findChild(QTreeWidget, "review_tree")
        assert tree is not None
        assert tree.topLevelItemCount() >= 1

        screen.close()

    def test_slow_step_warning_label(
        self, qapp: QApplication, mock_orchestrator: MagicMock,
    ) -> None:
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.domain import Domain, TemplateDefinition

        mock_orchestrator.estimate_duration.return_value = DurationEstimate(
            estimated_seconds=15, has_slow_steps=True,
            slow_step_details=["npm install"],
        )

        screen = ReviewScreen(mock_orchestrator)
        screen.show()

        spec = ProjectSpec(
            project_name="slow-proj",
            template=TemplateDefinition(
                id="custom", display_name="Custom", description="",
                backend_id="", frontend_id=None,
            ),
            domains=[],
            config={},
        )
        screen.set_spec(spec)
        screen.on_enter()

        warning_label = screen.findChild(QLabel, "warning_label")
        assert warning_label is not None
        assert warning_label.isVisible()
        text = warning_label.text()
        assert "Warning" in text
        assert "npm install" in text

        screen.close()

    def test_no_warning_for_fast_estimate(
        self, qapp: QApplication, mock_orchestrator: MagicMock,
    ) -> None:
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.domain import Domain, TemplateDefinition

        mock_orchestrator.estimate_duration.return_value = DurationEstimate(
            estimated_seconds=3, has_slow_steps=False, slow_step_details=[],
        )

        screen = ReviewScreen(mock_orchestrator)
        screen.show()

        spec = ProjectSpec(
            project_name="fast-proj",
            template=TemplateDefinition(
                id="custom", display_name="Custom", description="",
                backend_id="", frontend_id=None,
            ),
            domains=[],
            config={},
        )
        screen.set_spec(spec)
        screen.on_enter()

        warning_label = screen.findChild(QLabel, "warning_label")
        assert warning_label is not None
        assert not warning_label.isVisible()

        screen.close()

    def test_get_spec_update_returns_empty_dict(
        self, review_screen: object,
    ) -> None:
        assert review_screen.get_spec_update() == {}

    def test_can_proceed_is_always_true(
        self, review_screen: object,
    ) -> None:
        assert review_screen.can_proceed is True


# ====================================================================
# GenerationScreen — passive methods (AC-03, AC-04)
# ====================================================================


@pytest.mark.gui
class TestGenerationScreen:
    def test_on_progress_updates_stage_and_bar(
        self, generation_screen: object,
    ) -> None:
        from unittest.mock import MagicMock
        from forge.ui.workers import GenerationWorker

        worker: MagicMock = MagicMock(spec=GenerationWorker)
        generation_screen.set_worker(worker)

        generation_screen.on_progress("PluginExecution", 3)

        stage_label = generation_screen.findChild(QLabel, "stage_label")
        assert stage_label is not None
        assert stage_label.text() == "PluginExecution"

        progress_bar = generation_screen.findChild(QProgressBar, "progress_bar")
        assert progress_bar is not None
        assert progress_bar.maximum() == 3

    def test_on_progress_multiple_calls(
        self, generation_screen: object,
    ) -> None:
        from unittest.mock import MagicMock
        from forge.ui.workers import GenerationWorker

        worker: MagicMock = MagicMock(spec=GenerationWorker)
        generation_screen.set_worker(worker)

        generation_screen.on_progress("StageA", 2)
        generation_screen.on_progress("StageB", 5)

        stage_label = generation_screen.findChild(QLabel, "stage_label")
        assert stage_label is not None
        assert stage_label.text() == "StageB"

        progress_bar = generation_screen.findChild(QProgressBar, "progress_bar")
        assert progress_bar is not None
        assert progress_bar.maximum() == 5

    def test_on_log_appends_message(
        self, generation_screen: object,
    ) -> None:
        from unittest.mock import MagicMock
        from forge.ui.workers import GenerationWorker

        worker: MagicMock = MagicMock(spec=GenerationWorker)
        generation_screen.set_worker(worker)

        generation_screen.on_log("Creating output dir", "info")

        log_widget = generation_screen.findChild(QPlainTextEdit, "log_widget")
        assert log_widget is not None
        assert "Creating output dir" in log_widget.toPlainText()

    def test_on_log_multiple_messages(
        self, generation_screen: object,
    ) -> None:
        from unittest.mock import MagicMock
        from forge.ui.workers import GenerationWorker

        worker: MagicMock = MagicMock(spec=GenerationWorker)
        generation_screen.set_worker(worker)

        generation_screen.on_log("First message", "info")
        generation_screen.on_log("Second message", "info")

        log_widget = generation_screen.findChild(QPlainTextEdit, "log_widget")
        assert log_widget is not None
        text = log_widget.toPlainText()
        assert "First message" in text
        assert "Second message" in text

    def test_on_error_appends_and_resets_generating(
        self, generation_screen: object,
    ) -> None:
        from unittest.mock import MagicMock
        from forge.ui.workers import GenerationWorker

        worker: MagicMock = MagicMock(spec=GenerationWorker)
        generation_screen.set_worker(worker)

        assert generation_screen.is_generating is True
        generation_screen.on_error("Failed at stage X")

        log_widget = generation_screen.findChild(QPlainTextEdit, "log_widget")
        assert log_widget is not None
        assert "Failed" in log_widget.toPlainText()

        assert generation_screen.is_generating is False

    def test_on_finished_resets_generating(
        self, generation_screen: object,
    ) -> None:
        from unittest.mock import MagicMock
        from forge.ui.workers import GenerationWorker
        from forge.generation.orchestrator import GenerationResult

        worker: MagicMock = MagicMock(spec=GenerationWorker)
        generation_screen.set_worker(worker)

        assert generation_screen.is_generating is True
        result = GenerationResult(success=True, error=None, output_path=Path("/tmp/out"))
        generation_screen.on_finished(result)

        assert generation_screen.is_generating is False

    def test_on_exit_cancels_worker_when_generating(
        self, generation_screen: object,
    ) -> None:
        from unittest.mock import MagicMock
        from forge.ui.workers import GenerationWorker

        worker: MagicMock = MagicMock(spec=GenerationWorker)
        generation_screen.set_worker(worker)
        generation_screen.on_enter()

        assert generation_screen.is_generating is True
        generation_screen.on_exit()

        worker.cancel.assert_called_once()
        assert generation_screen.is_generating is False

    def test_on_exit_no_worker_is_noop(
        self, generation_screen: object,
    ) -> None:
        # No worker set — on_exit should not raise
        generation_screen.on_enter()
        generation_screen.on_exit()
        assert generation_screen.is_generating is False

    def test_idle_state_on_enter_without_worker(
        self, generation_screen: object,
    ) -> None:
        generation_screen.on_enter()

        stage_label = generation_screen.findChild(QLabel, "stage_label")
        assert stage_label is not None
        assert stage_label.text() == "Ready"

        progress_bar = generation_screen.findChild(QProgressBar, "progress_bar")
        assert progress_bar is not None
        assert progress_bar.value() == 0

        log_widget = generation_screen.findChild(QPlainTextEdit, "log_widget")
        assert log_widget is not None
        assert log_widget.toPlainText() == ""

    def test_set_worker_sets_is_generating(
        self, generation_screen: object,
    ) -> None:
        from unittest.mock import MagicMock
        from forge.ui.workers import GenerationWorker

        assert generation_screen.is_generating is False
        worker: MagicMock = MagicMock(spec=GenerationWorker)
        generation_screen.set_worker(worker)
        assert generation_screen.is_generating is True

    def test_set_worker_none_resets_is_generating(
        self, generation_screen: object,
    ) -> None:
        from unittest.mock import MagicMock
        from forge.ui.workers import GenerationWorker

        worker: MagicMock = MagicMock(spec=GenerationWorker)
        generation_screen.set_worker(worker)
        assert generation_screen.is_generating is True

        generation_screen.set_worker(None)
        assert generation_screen.is_generating is False


# ====================================================================
# MainWindow integration — generation lifecycle (AC-05, AC-06)
# ====================================================================


@pytest.mark.gui
class TestGenerationLifecycleMainWindow:
    @pytest.fixture
    def main_window(self, qapp: QApplication, mock_orchestrator: MagicMock) -> object:
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.welcome_screen import WelcomeScreen
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.ui.screens.generation_screen import GenerationScreen

        screens = [
            WelcomeScreen(),
            QStackedWidget(),
            QStackedWidget(),
            ReviewScreen(mock_orchestrator),
            GenerationScreen(),
        ]
        screens[0].can_proceed = True
        window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
        window.show()
        yield window
        window.close()

    def test_finished_shows_open_close_hides_cancel(
        self, main_window: object,
    ) -> None:
        main_window.navigate_to(4)
        result = GenerationResult(success=True, error=None, output_path=Path("/tmp/out"))
        main_window._on_generation_finished(result)

        cancel_btn = main_window.findChild(QPushButton, "cancel_button")
        open_btn = main_window.findChild(QPushButton, "open_button")
        close_btn = main_window.findChild(QPushButton, "close_button")

        assert cancel_btn is not None
        assert open_btn is not None
        assert close_btn is not None

        assert cancel_btn.isVisible() is False
        assert open_btn.isVisible() is True
        assert open_btn.isEnabled() is True
        assert close_btn.isVisible() is True
        assert close_btn.isEnabled() is True

    def test_finished_success_sets_output_path(
        self, main_window: object,
    ) -> None:
        main_window.navigate_to(4)
        result = GenerationResult(success=True, error=None, output_path=Path("/tmp/out"))
        main_window._on_generation_finished(result)

        assert main_window._generation_output_path == Path("/tmp/out")
        assert main_window._generation_finished is True

    def test_finished_error_hides_open_shows_close(
        self, main_window: object,
    ) -> None:
        main_window.navigate_to(4)
        result = GenerationResult(success=False, error="Something failed", output_path=None)
        main_window._on_generation_finished(result)

        cancel_btn = main_window.findChild(QPushButton, "cancel_button")
        open_btn = main_window.findChild(QPushButton, "open_button")
        close_btn = main_window.findChild(QPushButton, "close_button")

        assert cancel_btn is not None
        assert open_btn is not None
        assert close_btn is not None

        assert cancel_btn.isVisible() is False
        assert open_btn.isVisible() is False
        assert close_btn.isVisible() is True

    def test_generation_error_shows_close_hides_cancel(
        self, main_window: object,
    ) -> None:
        main_window.navigate_to(4)
        main_window._on_generation_error("Failed at stage PluginExecution")

        cancel_btn = main_window.findChild(QPushButton, "cancel_button")
        open_btn = main_window.findChild(QPushButton, "open_button")
        close_btn = main_window.findChild(QPushButton, "close_button")

        assert cancel_btn is not None
        assert open_btn is not None
        assert close_btn is not None

        assert cancel_btn.isVisible() is False
        assert open_btn.isVisible() is False
        assert close_btn.isVisible() is True

    def test_generation_error_clears_output_path(
        self, main_window: object,
    ) -> None:
        main_window.navigate_to(4)
        main_window._on_generation_error("Failed")

        assert main_window._generation_finished is True
        # output_path should remain None since error does not set it
        assert main_window._generation_output_path is None


# ====================================================================
# Overwrite confirm flow (AC-07, AC-08, AC-09, AC-10)
# ====================================================================


@pytest.mark.gui
class TestOverwriteConfirmFlow:
    @pytest.fixture
    def main_window(self, qapp: QApplication, mock_orchestrator: MagicMock) -> object:
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.welcome_screen import WelcomeScreen
        from forge.ui.screens.domain_selection_screen import DomainSelectionScreen
        from forge.ui.screens.configuration_screen import ConfigurationScreen
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.ui.screens.generation_screen import GenerationScreen

        screens = [
            WelcomeScreen(),
            DomainSelectionScreen(mock_orchestrator),
            ConfigurationScreen(mock_orchestrator),
            ReviewScreen(mock_orchestrator),
            GenerationScreen(),
        ]
        screens[0].can_proceed = True
        screens[1].can_proceed = True
        screens[2].can_proceed = True

        window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
        window.show()
        # Fill in project name so _build_spec produces a valid spec
        name_edit = window.findChild(QLineEdit)
        if name_edit is not None:
            name_edit.setText("test-project")
        yield window
        window.close()

    def test_no_overwrite_dialog_when_dir_does_not_exist(
        self, main_window: object, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/test"))
        monkeypatch.setattr(Path, "exists", lambda _: False)
        monkeypatch.setattr("PySide6.QtCore.QThread.start", lambda self: None)

        main_window.navigate_to(3)
        stacked = main_window.findChild(QStackedWidget)
        assert stacked is not None
        assert stacked.currentIndex() == 3

        question_called = False

        def fake_question(*args: object, **kwargs: object) -> QMessageBox.StandardButton:
            nonlocal question_called
            question_called = True
            return QMessageBox.StandardButton.No

        monkeypatch.setattr(QMessageBox, "question", fake_question)
        main_window.next_screen()

        assert question_called is False, "confirm dialog should not appear"
        assert stacked.currentIndex() == 4

    def test_overwrite_yes_proceeds(
        self, main_window: object, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/test"))
        monkeypatch.setattr(Path, "exists", lambda _: True)

        # Mock the thread so start doesn't fail
        monkeypatch.setattr("PySide6.QtCore.QThread.start", lambda self: None)

        main_window.navigate_to(3)
        stacked = main_window.findChild(QStackedWidget)
        assert stacked is not None
        assert stacked.currentIndex() == 3

        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.Yes,
        )

        spy = QSignalSpy(main_window.generation_requested)
        main_window.next_screen()

        assert stacked.currentIndex() == 4
        assert spy.count() >= 1

    def test_overwrite_no_stays(
        self, main_window: object, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/test"))
        monkeypatch.setattr(Path, "exists", lambda _: True)

        main_window.navigate_to(3)
        stacked = main_window.findChild(QStackedWidget)
        assert stacked is not None
        assert stacked.currentIndex() == 3

        monkeypatch.setattr(
            QMessageBox, "question",
            lambda *a, **kw: QMessageBox.StandardButton.No,
        )

        main_window.next_screen()

        assert stacked.currentIndex() == 3, "should stay on review screen"

    def test_overwrite_exception_shows_error(
        self, main_window: object, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/test"))

        def raise_error(_: object) -> bool:
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path, "exists", raise_error)

        main_window.navigate_to(3)
        stacked = main_window.findChild(QStackedWidget)
        assert stacked is not None
        assert stacked.currentIndex() == 3

        error_captured: dict[str, str] = {}

        def fake_critical(
            parent: object, title: str, text: str,
        ) -> QMessageBox.StandardButton:
            error_captured["title"] = title
            error_captured["text"] = text
            return QMessageBox.StandardButton.Ok

        monkeypatch.setattr(QMessageBox, "critical", fake_critical)
        main_window.next_screen()

        assert error_captured.get("title") == "Error"
        assert "Permission denied" in error_captured.get("text", "")
        assert stacked.currentIndex() == 3, "should stay on review screen"


# ====================================================================
# Cancellation (AC-14, AC-15)
# ====================================================================


@pytest.mark.gui
class TestCancellation:
    @pytest.fixture
    def main_window(self, qapp: QApplication, mock_orchestrator: MagicMock) -> object:
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.welcome_screen import WelcomeScreen
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.ui.screens.generation_screen import GenerationScreen
        from PySide6.QtCore import QThread

        screens = [
            WelcomeScreen(),
            QStackedWidget(),
            QStackedWidget(),
            ReviewScreen(mock_orchestrator),
            GenerationScreen(),
        ]
        screens[0].can_proceed = True
        window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
        window.show()
        yield window
        window.close()

    def test_cancel_calls_worker_cancel_and_disables_button(
        self, main_window: object,
    ) -> None:
        from unittest.mock import MagicMock
        from forge.ui.workers import GenerationWorker

        worker: MagicMock = MagicMock(spec=GenerationWorker)
        main_window._worker = worker
        main_window._thread = MagicMock()
        main_window.navigate_to(4)

        cancel_btn = main_window.findChild(QPushButton, "cancel_button")
        assert cancel_btn is not None
        assert cancel_btn.isVisible()

        QTest.mouseClick(cancel_btn, Qt.LeftButton)

        worker.cancel.assert_called_once()
        assert cancel_btn.isEnabled() is False

    def test_cancel_idempotent_after_finished(
        self, main_window: object,
    ) -> None:
        main_window._generation_finished = True
        main_window._worker = None

        # Should not raise
        main_window.cancel_generation()


# ====================================================================
# Open Project button (AC-16)
# ====================================================================


@pytest.mark.gui
class TestOpenProjectButton:
    @pytest.fixture
    def main_window(self, qapp: QApplication, mock_orchestrator: MagicMock) -> object:
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.welcome_screen import WelcomeScreen
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.ui.screens.generation_screen import GenerationScreen

        screens = [
            WelcomeScreen(),
            QStackedWidget(),
            QStackedWidget(),
            ReviewScreen(mock_orchestrator),
            GenerationScreen(),
        ]
        screens[0].can_proceed = True
        window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
        window.show()
        yield window
        window.close()

    def test_open_project_calls_desktop_services(
        self, main_window: object, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from PySide6.QtCore import QUrl

        main_window.navigate_to(4)
        result = GenerationResult(success=True, error=None, output_path=Path("/tmp/test-proj"))
        main_window._on_generation_finished(result)

        open_url_called: list[object] = []

        def fake_open_url(url: object) -> None:
            open_url_called.append(url)

        monkeypatch.setattr(QDesktopServices, "openUrl", fake_open_url)

        open_btn = main_window.findChild(QPushButton, "open_button")
        assert open_btn is not None
        assert open_btn.isVisible()

        QTest.mouseClick(open_btn, Qt.LeftButton)

        assert len(open_url_called) == 1
        expected_url = QUrl.fromLocalFile(str(Path("/tmp/test-proj")))
        assert open_url_called[0] == expected_url

    def test_open_project_noop_when_no_output_path(
        self, main_window: object, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # When generation failed (no output_path), Open should not fire
        main_window._generation_output_path = None

        open_url_called: list[object] = []

        def fake_open_url(url: object) -> None:
            open_url_called.append(url)

        monkeypatch.setattr(QDesktopServices, "openUrl", fake_open_url)
        main_window._on_open_project()

        assert len(open_url_called) == 0

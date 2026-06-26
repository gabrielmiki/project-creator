from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTreeWidget,
)

from forge.domain import DurationEstimate, ProjectSpec


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
def welcome_screen(qapp: QApplication) -> object:
    from forge.ui.screens.welcome_screen import WelcomeScreen

    screen = WelcomeScreen()
    screen.show()
    yield screen
    screen.close()


@pytest.fixture
def review_screen(qapp: QApplication, mock_orchestrator: MagicMock) -> object:
    from forge.ui.screens.review_screen import ReviewScreen

    screen = ReviewScreen(mock_orchestrator)
    screen.show()
    yield screen
    screen.close()


@pytest.fixture
def main_window(qapp: QApplication, mock_orchestrator: MagicMock) -> object:
    from forge.ui.main_window import MainWindow
    from forge.ui.screens.welcome_screen import WelcomeScreen
    from forge.ui.screens.review_screen import ReviewScreen
    from forge.ui.screens.generation_screen import GenerationScreen
    from PySide6.QtWidgets import QWidget

    screens = [
        WelcomeScreen(),
        QWidget(),
        QWidget(),
        ReviewScreen(mock_orchestrator),
        GenerationScreen(),
    ]
    screens[0].can_proceed = True

    window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
    window.show()
    # Fill in project name so _build_spec produces a valid spec
    name_edit = window.findChild(QLineEdit)
    if name_edit is not None:
        name_edit.setText("my-app")
    yield window
    window.close()


# ====================================================================
# WelcomeScreen — Browse button and path label (AC-1, AC-2, AC-3, AC-4, AC-7)
# ====================================================================


@pytest.mark.gui
class TestWelcomeScreenBrowse:
    def test_browse_button_calls_qfiledialog(self, welcome_screen: object, monkeypatch: pytest.MonkeyPatch) -> None:
        call_args: dict[str, object] = {}

        def fake_get_existing_directory(parent: object = None, title: str = "", **kwargs: object) -> str:
            call_args["parent"] = parent
            call_args["title"] = title
            return "/selected/path"

        monkeypatch.setattr(QFileDialog, "getExistingDirectory", fake_get_existing_directory)

        browse_btn = welcome_screen.findChild(QPushButton, "browse_button")
        assert browse_btn is not None
        QTest.mouseClick(browse_btn, Qt.LeftButton)

        assert call_args.get("parent") is welcome_screen
        assert call_args.get("title") == "Select Output Directory"

    def test_browse_button_text_label(self, welcome_screen: object) -> None:
        browse_btn = welcome_screen.findChild(QPushButton, "browse_button")
        assert browse_btn is not None
        assert browse_btn.text() == "Browse\u2026"

    def test_browse_updates_label_text_and_tooltip(self, welcome_screen: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **kw: "/Users/me/projects")

        browse_btn = welcome_screen.findChild(QPushButton, "browse_button")
        assert browse_btn is not None
        QTest.mouseClick(browse_btn, Qt.LeftButton)

        path_label = welcome_screen.findChild(QLabel, "output_dir_path")
        assert path_label is not None
        assert path_label.text() == "/Users/me/projects"
        assert path_label.toolTip() == "/Users/me/projects"

    def test_browse_updates_label_with_trailing_slash(self, welcome_screen: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **kw: "/Users/me/projects/")

        browse_btn = welcome_screen.findChild(QPushButton, "browse_button")
        assert browse_btn is not None
        QTest.mouseClick(browse_btn, Qt.LeftButton)

        path_label = welcome_screen.findChild(QLabel, "output_dir_path")
        assert path_label is not None
        assert path_label.text() == "/Users/me/projects/"

    def test_get_spec_update_defaults_cwd(self, welcome_screen: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/fake_cwd"))

        update = welcome_screen.get_spec_update()
        assert update["output_parent_dir"] == "/tmp/fake_cwd"
        assert update["project_name"] == ""

    def test_get_spec_update_after_browse(self, welcome_screen: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/fake_cwd"))
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **kw: "/chosen/path")

        browse_btn = welcome_screen.findChild(QPushButton, "browse_button")
        assert browse_btn is not None
        QTest.mouseClick(browse_btn, Qt.LeftButton)

        update = welcome_screen.get_spec_update()
        assert update["output_parent_dir"] == "/chosen/path"

    def test_browse_cancel_keeps_label_and_dir_unchanged(self, welcome_screen: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/default_cwd"))
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **kw: "")

        browse_btn = welcome_screen.findChild(QPushButton, "browse_button")
        assert browse_btn is not None
        QTest.mouseClick(browse_btn, Qt.LeftButton)

        path_label = welcome_screen.findChild(QLabel, "output_dir_path")
        assert path_label is not None
        assert path_label.text() == "/tmp/default_cwd"

        update = welcome_screen.get_spec_update()
        assert update["output_parent_dir"] == "/tmp/default_cwd"

    def test_browse_cancel_after_previous_selection_preserves_prior(self, welcome_screen: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/default_cwd"))
        call_count: list[int] = []
        monkeypatch.setattr(
            QFileDialog, "getExistingDirectory",
            lambda *a, **kw: "/first/path" if not call_count else "",
        )

        browse_btn = welcome_screen.findChild(QPushButton, "browse_button")
        assert browse_btn is not None

        # First click — select a directory
        QTest.mouseClick(browse_btn, Qt.LeftButton)
        call_count.append(1)

        # Second click — cancel
        QTest.mouseClick(browse_btn, Qt.LeftButton)

        update = welcome_screen.get_spec_update()
        assert update["output_parent_dir"] == "/first/path"


# ====================================================================
# MainWindow — Output path resolution (AC-5, AC-6, AC-10, AC-11)
# ====================================================================


@pytest.mark.gui
class TestMainWindowOutputDir:
    def test_get_output_dir_with_parent_dir(self, main_window: object) -> None:
        main_window._output_parent_dir = Path("/Users/me/projects")
        result = main_window._get_output_dir("my-app")
        assert result == Path("/Users/me/projects/my-app")

    def test_get_output_dir_with_relative_project_name(self, main_window: object) -> None:
        main_window._output_parent_dir = Path("/base")
        result = main_window._get_output_dir("my/deep/app")
        assert result == Path("/base/my/deep/app")

    def test_get_output_dir_backward_compat(self, main_window: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/cwd"))
        assert main_window._output_parent_dir == Path("/tmp/cwd")
        result = main_window._get_output_dir("my-app")
        assert result == Path("/tmp/cwd/my-app")

    def test_generation_worker_receives_custom_output_dir(self, main_window: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/cwd"))
        monkeypatch.setattr(Path, "exists", lambda self: self == Path("/custom/path"))
        monkeypatch.setattr("PySide6.QtCore.QThread.start", lambda self: None)

        main_window._stacked.widget(0)._parent_dir = "/custom/path"
        main_window.navigate_to(3)

        captured: dict[str, object] = {}

        def fake_create_worker(spec: object, output_dir: Path) -> None:
            captured["output_dir"] = output_dir
            # Must also call the original — or at least set the worker so navigate_to(4) doesn't crash
            from unittest.mock import MagicMock
            from forge.ui.workers import GenerationWorker
            from forge.infrastructure.transaction import GenerationTransaction

            txn = GenerationTransaction(output_dir)
            main_window._worker = MagicMock(spec=GenerationWorker)
            main_window._thread = MagicMock()

        monkeypatch.setattr(main_window, "_create_generation_worker", fake_create_worker)

        main_window.next_screen()

        assert "output_dir" in captured
        assert captured["output_dir"] == Path("/custom/path/my-app")

    def test_generation_worker_receives_default_output_dir(self, main_window: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/cwd"))
        monkeypatch.setattr(Path, "exists", lambda self: self == Path("/tmp/cwd"))
        monkeypatch.setattr("PySide6.QtCore.QThread.start", lambda self: None)

        main_window.navigate_to(3)

        captured: dict[str, object] = {}

        def fake_create_worker(spec: object, output_dir: Path) -> None:
            captured["output_dir"] = output_dir
            from unittest.mock import MagicMock
            from forge.ui.workers import GenerationWorker

            main_window._worker = MagicMock(spec=GenerationWorker)
            main_window._thread = MagicMock()

        monkeypatch.setattr(main_window, "_create_generation_worker", fake_create_worker)

        main_window.next_screen()

        assert "output_dir" in captured
        assert captured["output_dir"] == Path("/tmp/cwd/my-app")

    def test_nonexistent_parent_shows_error_and_does_not_generate(self, main_window: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/cwd"))
        monkeypatch.setattr(Path, "exists", lambda self: self != Path("/nonexistent/parent"))
        main_window._stacked.widget(0)._parent_dir = "/nonexistent/parent"

        error_captured: dict[str, str] = {}

        def fake_critical(parent: object, title: str, text: str) -> QMessageBox.StandardButton:
            error_captured["title"] = title
            error_captured["text"] = text
            return QMessageBox.StandardButton.Ok

        monkeypatch.setattr(QMessageBox, "critical", fake_critical)

        main_window.navigate_to(3)
        stacked = main_window.findChild(QStackedWidget)
        assert stacked is not None
        assert stacked.currentIndex() == 3

        spy = QSignalSpy(main_window.generation_requested)
        main_window.next_screen()

        assert error_captured.get("title") == "Invalid Directory"
        assert "does not exist" in error_captured.get("text", "")
        assert stacked.currentIndex() == 3, "should stay on review screen"
        assert spy.count() == 0, "generation_requested should not be emitted"


# ====================================================================
# ReviewScreen — Output directory display and back-navigation (AC-8, AC-9)
# ====================================================================


@pytest.mark.gui
class TestReviewScreenOutputDir:
    def test_set_output_dir_displays_in_tree(self, review_screen: object, monkeypatch: pytest.MonkeyPatch) -> None:
        from forge.domain import TemplateDefinition

        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/cwd"))

        spec = ProjectSpec(
            project_name="my-app",
            template=TemplateDefinition(
                id="custom", display_name="Custom", description="",
                backend_id="", frontend_id=None,
            ),
            domains=[],
            config={},
        )
        review_screen.set_spec(spec)
        review_screen.set_output_dir(Path("/Users/me/projects/my-app"))
        review_screen.on_enter()

        tree = review_screen.findChild(QTreeWidget, "review_tree")
        assert tree is not None

        found = False
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if item.text(0) == "Output Directory":
                assert item.text(1) == "/Users/me/projects/my-app"
                found = True
                break
        assert found, "Output Directory item not found in review tree"

    def test_no_set_output_dir_falls_back_to_cwd(self, review_screen: object, monkeypatch: pytest.MonkeyPatch) -> None:
        from forge.domain import TemplateDefinition

        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/cwd"))

        spec = ProjectSpec(
            project_name="fallback-app",
            template=TemplateDefinition(
                id="custom", display_name="Custom", description="",
                backend_id="", frontend_id=None,
            ),
            domains=[],
            config={},
        )
        review_screen.set_spec(spec)
        # Intentionally NOT calling set_output_dir — tests backward compat
        review_screen.on_enter()

        tree = review_screen.findChild(QTreeWidget, "review_tree")
        assert tree is not None

        found = False
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if item.text(0) == "Output Directory":
                assert item.text(1) == "/tmp/cwd/fallback-app"
                found = True
                break
        assert found, "Output Directory item not found in review tree"

    def test_back_navigation_shows_new_directory(self, main_window: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/cwd"))
        monkeypatch.setattr(Path, "exists", lambda self: self == Path("/second/path"))
        monkeypatch.setattr("PySide6.QtCore.QThread.start", lambda self: None)

        call_log: list[Path] = []

        def fake_create_worker(spec: object, output_dir: Path) -> None:
            call_log.append(output_dir)
            from unittest.mock import MagicMock
            from forge.ui.workers import GenerationWorker

            main_window._worker = MagicMock(spec=GenerationWorker)
            main_window._thread = MagicMock()

        monkeypatch.setattr(main_window, "_create_generation_worker", fake_create_worker)

        # Navigate to Welcome and set first directory
        welcome = main_window._stacked.widget(0)
        welcome._parent_dir = "/first/path"

        # Go to Review
        main_window.navigate_to(3)

        # Go back to Welcome
        main_window.navigate_to(0)

        # Change directory
        welcome._parent_dir = "/second/path"

        # Go to Review again
        main_window.navigate_to(3)

        # Trigger generation
        main_window.next_screen()

        assert len(call_log) == 1
        assert call_log[0] == Path("/second/path/my-app")

    def test_back_navigation_preserves_directory_on_no_change(self, main_window: object, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/cwd"))
        monkeypatch.setattr(Path, "exists", lambda self: self == Path("/chosen/path"))
        monkeypatch.setattr("PySide6.QtCore.QThread.start", lambda self: None)

        call_log: list[Path] = []

        def fake_create_worker(spec: object, output_dir: Path) -> None:
            call_log.append(output_dir)
            from unittest.mock import MagicMock
            from forge.ui.workers import GenerationWorker

            main_window._worker = MagicMock(spec=GenerationWorker)
            main_window._thread = MagicMock()

        monkeypatch.setattr(main_window, "_create_generation_worker", fake_create_worker)

        # Set directory once
        welcome = main_window._stacked.widget(0)
        welcome._parent_dir = "/chosen/path"

        # Navigate to Review
        main_window.navigate_to(3)
        # Navigate back to Welcome (without changing dir)
        main_window.navigate_to(0)
        # Navigate to Review again
        main_window.navigate_to(3)

        # Trigger generation
        main_window.next_screen()

        assert len(call_log) == 1
        assert call_log[0] == Path("/chosen/path/my-app")

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from forge.domain import ProjectSpec, TemplateDefinition
from forge.generation.orchestrator import GenerationResult, Orchestrator
from forge.infrastructure.transaction import GenerationTransaction
from forge.ui.workers import GenerationWorker

if TYPE_CHECKING:
    from forge.ui.screens.base import WizardScreen


class MainWindow(QMainWindow):
    generation_requested = Signal(ProjectSpec)
    generation_completed = Signal(GenerationResult)
    cancelled = Signal()

    def __init__(
        self,
        orchestrator: Orchestrator,
        screens: list[WizardScreen] | None = None,
    ) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self._current_index = 0
        self._generation_finished: bool = False
        self._generation_output_path: Path | None = None
        self._worker: GenerationWorker | None = None
        self._thread: QThread | None = None

        self.setWindowTitle("Forge")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self._stacked = QStackedWidget()
        layout.addWidget(self._stacked)

        if screens is None:
            from forge.ui.screens.welcome_screen import WelcomeScreen
            from forge.ui.screens.domain_selection_screen import DomainSelectionScreen
            from forge.ui.screens.configuration_screen import ConfigurationScreen
            from forge.ui.screens.review_screen import ReviewScreen
            from forge.ui.screens.generation_screen import GenerationScreen

            screens = [
                WelcomeScreen(),
                DomainSelectionScreen(orchestrator),
                ConfigurationScreen(orchestrator),
                ReviewScreen(orchestrator),
                GenerationScreen(),
            ]

        for screen in screens:
            self._stacked.addWidget(screen)

        for screen in screens:
            if hasattr(screen, "proceed_changed"):
                screen.proceed_changed.connect(self._update_navigation_buttons)

        footer = QHBoxLayout()
        self._prev_btn = QPushButton("Previous")
        self._prev_btn.setObjectName("previous_button")
        self._next_btn = QPushButton("Next")
        self._next_btn.setObjectName("next_button")
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancel_button")
        self._open_btn = QPushButton("Open Project")
        self._open_btn.setObjectName("open_button")
        self._close_btn = QPushButton("Close")
        self._close_btn.setObjectName("close_button")

        footer.addStretch()
        footer.addWidget(self._prev_btn)
        footer.addWidget(self._next_btn)
        footer.addWidget(self._cancel_btn)
        footer.addWidget(self._open_btn)
        footer.addWidget(self._close_btn)
        layout.addLayout(footer)

        self._prev_btn.clicked.connect(self.previous_screen)
        self._next_btn.clicked.connect(self.next_screen)
        self._cancel_btn.clicked.connect(self.cancelled.emit)
        self._open_btn.clicked.connect(self._on_open_project)
        self._close_btn.clicked.connect(self._on_close)

        self.navigate_to(0)

    def _build_spec(self) -> ProjectSpec:
        updates: dict[str, Any] = {}
        for i in range(self._stacked.count()):
            screen = self._stacked.widget(i)
            if hasattr(screen, "get_spec_update"):
                updates.update(screen.get_spec_update())

        config = updates.get("config", {})
        return ProjectSpec(
            project_name=updates.get("project_name", ""),
            template=TemplateDefinition(
                id="custom",
                display_name="Custom",
                description="",
                backend_id=updates.get("backend_id") or "",
                frontend_id=updates.get("frontend_id"),
            ),
            domains=[],
            config=config,
        )

    def _get_output_dir(self, project_name: str) -> Path:
        return Path.cwd() / project_name

    def navigate_to(self, screen_index: int) -> None:
        current = self._stacked.currentWidget()
        if hasattr(current, "on_exit"):
            current.on_exit()

        index = max(0, min(4, screen_index))
        self._current_index = index
        self._stacked.setCurrentIndex(index)

        if index == 2:
            domain_updates = self._stacked.widget(1).get_spec_update()
            config_screen = self._stacked.widget(2)
            config_screen.backend_id = domain_updates.get("backend_id") or ""
            config_screen.frontend_id = domain_updates.get("frontend_id")

        if index == 3:
            spec = self._build_spec()
            review_screen = self._stacked.widget(3)
            if hasattr(review_screen, "set_spec"):
                review_screen.set_spec(spec)

        if index == 4:
            gen_screen = self._stacked.widget(4)
            if hasattr(gen_screen, "set_worker"):
                worker = getattr(self, "_worker", None)
                gen_screen.set_worker(worker)
            try:
                self._cancel_btn.clicked.disconnect()
            except TypeError:
                pass
            if hasattr(gen_screen, "is_generating") and gen_screen.is_generating:
                self._cancel_btn.clicked.connect(self.cancel_generation)
            else:
                self._cancel_btn.clicked.connect(self.cancelled.emit)

        target = self._stacked.currentWidget()
        if hasattr(target, "on_enter"):
            target.on_enter()

        self._update_navigation_buttons()

    def next_screen(self) -> None:
        if self._current_index >= 4:
            return
        current = self._stacked.currentWidget()
        if hasattr(current, "can_proceed") and not current.can_proceed:
            return

        if self._current_index == 3:
            spec = self._build_spec()
            output_dir = self._get_output_dir(spec.project_name)
            try:
                dir_exists = output_dir.exists()
            except Exception as e:
                self.show_error("Error", f"Cannot check output directory: {e}")
                return
            if dir_exists:
                if not self.show_confirm(
                    "Directory exists",
                    f"The directory {output_dir} already exists. Overwrite?",
                ):
                    return
            self._create_generation_worker(spec, output_dir)
            self.generation_requested.emit(spec)
            self.navigate_to(self._current_index + 1)
            self._thread.start()
            return

        self.navigate_to(self._current_index + 1)

    def previous_screen(self) -> None:
        if self._current_index <= 0:
            return
        self.navigate_to(self._current_index - 1)

    def show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    def show_confirm(self, title: str, message: str) -> bool:
        result = QMessageBox.question(self, title, message)
        return result == QMessageBox.StandardButton.Yes

    def _update_navigation_buttons(self) -> None:
        index = self._current_index

        if index == 4:
            self._prev_btn.setVisible(False)
            self._next_btn.setVisible(False)
            if self._generation_finished:
                self._cancel_btn.setVisible(False)
                self._open_btn.setVisible(self._generation_output_path is not None)
                self._close_btn.setVisible(True)
            else:
                self._cancel_btn.setVisible(True)
                self._cancel_btn.setEnabled(True)
                self._open_btn.setVisible(False)
                self._close_btn.setVisible(False)
            return

        for name, btn in {
            "previous": self._prev_btn,
            "next": self._next_btn,
            "cancel": self._cancel_btn,
            "open": self._open_btn,
            "close": self._close_btn,
        }.items():
            if index == 0 and name == "previous":
                visible, enabled = True, False
            elif name in ("cancel", "open", "close"):
                visible, enabled = False, True
            else:
                visible, enabled = True, True

            if name == "next" and 0 <= index <= 3:
                current = self._stacked.currentWidget()
                if hasattr(current, "can_proceed"):
                    enabled = current.can_proceed

            btn.setVisible(visible)
            btn.setEnabled(enabled)

    def _create_generation_worker(
        self, spec: ProjectSpec, output_dir: Path,
    ) -> None:
        txn = GenerationTransaction(output_dir)
        self._worker = GenerationWorker(
            orchestrator=self._orchestrator,
            spec=spec,
            output_dir=output_dir,
            txn=txn,
            overwrite_confirmed=output_dir.exists(),
        )
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._on_generation_finished)
        self._worker.progress.connect(self._on_generation_progress)
        self._worker.log.connect(self._on_generation_log)
        self._worker.error.connect(self._on_generation_error)

    def _on_generation_finished(self, result: GenerationResult) -> None:
        gen_screen = self._stacked.widget(4)
        if hasattr(gen_screen, "on_finished"):
            gen_screen.on_finished(result)
        self._generation_finished = True
        self._generation_output_path = result.output_path
        self.generation_completed.emit(result)
        self._update_navigation_buttons()

    def _on_generation_progress(self, stage: str, total: int) -> None:
        gen_screen = self._stacked.widget(4)
        if hasattr(gen_screen, "on_progress"):
            gen_screen.on_progress(stage, total)

    def _on_generation_log(self, message: str, level: str) -> None:
        gen_screen = self._stacked.widget(4)
        if hasattr(gen_screen, "on_log"):
            gen_screen.on_log(message, level)

    def _on_generation_error(self, message: str) -> None:
        gen_screen = self._stacked.widget(4)
        if hasattr(gen_screen, "on_error"):
            gen_screen.on_error(message)
        self._generation_finished = True
        self._update_navigation_buttons()

    def cancel_generation(self) -> None:
        if hasattr(self, "_worker") and self._worker is not None:
            self._worker.cancel()
            self._cancel_btn.setEnabled(False)

    def _on_open_project(self) -> None:
        if self._generation_output_path is not None:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self._generation_output_path))
            )

    def _on_close(self) -> None:
        self.close()

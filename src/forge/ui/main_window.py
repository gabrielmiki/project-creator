from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Signal
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

            screens = [
                WelcomeScreen(),
                DomainSelectionScreen(orchestrator),
                ConfigurationScreen(orchestrator),
                QWidget(),
                QWidget(),
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
            self.generation_requested.emit(spec)
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

        for name, btn in {
            "previous": self._prev_btn,
            "next": self._next_btn,
            "cancel": self._cancel_btn,
            "open": self._open_btn,
            "close": self._close_btn,
        }.items():
            if index == 0 and name == "previous":
                visible, enabled = True, False
            elif index == 4 and name in ("previous", "next"):
                visible, enabled = False, True
            elif name in ("cancel", "open", "close"):
                visible, enabled = (index == 4), True
            else:
                visible, enabled = True, True

            if name == "next" and 0 <= index <= 3:
                current = self._stacked.currentWidget()
                if hasattr(current, "can_proceed"):
                    enabled = current.can_proceed

            btn.setVisible(visible)
            btn.setEnabled(enabled)

from __future__ import annotations

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


class MainWindow(QMainWindow):
    generation_requested = Signal(ProjectSpec)
    generation_completed = Signal(GenerationResult)
    cancelled = Signal()

    def __init__(self, orchestrator: Orchestrator) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self._current_index = 0

        self.setWindowTitle("Forge")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self._stacked = QStackedWidget()
        layout.addWidget(self._stacked)

        for _ in range(5):
            page = QWidget()
            self._stacked.addWidget(page)

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

    def navigate_to(self, screen_index: int) -> None:
        index = max(0, min(4, screen_index))
        self._current_index = index
        self._stacked.setCurrentIndex(index)
        self._update_navigation_buttons()

    def next_screen(self) -> None:
        if self._current_index >= 4:
            return
        if self._current_index == 3:
            spec = ProjectSpec(
                project_name="",
                template=TemplateDefinition(
                    id="",
                    display_name="",
                    description="",
                    backend_id="",
                ),
                domains=[],
                config={},
            )
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
            btn.setVisible(visible)
            btn.setEnabled(enabled)

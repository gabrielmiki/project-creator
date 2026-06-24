from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
)

from forge.ui.screens.base import WizardScreen

if TYPE_CHECKING:
    from forge.generation.orchestrator import GenerationResult
    from forge.ui.workers import GenerationWorker


class GenerationScreen(WizardScreen):
    can_proceed = True
    can_go_back = False

    def __init__(self) -> None:
        super().__init__()
        self._worker: GenerationWorker | None = None
        self._is_generating: bool = False

        layout = QVBoxLayout(self)

        self._stage_label = QLabel("Ready")
        self._stage_label.setObjectName("stage_label")
        layout.addWidget(self._stage_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("progress_bar")
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        self._duration_label = QLabel()
        self._duration_label.setObjectName("duration_label")
        self._duration_label.setVisible(False)
        layout.addWidget(self._duration_label)

        self._log_widget = QPlainTextEdit()
        self._log_widget.setObjectName("log_widget")
        self._log_widget.setReadOnly(True)
        font = QFont("monospace")
        self._log_widget.setFont(font)
        layout.addWidget(self._log_widget, 1)

    @property
    def is_generating(self) -> bool:
        return self._is_generating

    def set_worker(self, worker: GenerationWorker | None) -> None:
        self._worker = worker
        self._is_generating = worker is not None

    def on_enter(self) -> None:
        super().on_enter()
        self._stage_label.setText("Ready")
        self._progress_bar.setValue(0)
        self._log_widget.clear()
        self._duration_label.setVisible(False)
        if self._worker is None:
            self._is_generating = False

    def on_progress(self, stage: str, total: int) -> None:
        self._stage_label.setText(stage)
        self._progress_bar.setMaximum(total)

    def on_log(self, message: str, level: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_widget.appendPlainText(f"[{timestamp}] {message}")

    def on_error(self, message: str) -> None:
        self._log_widget.appendHtml(
            f'<span style="color:red;">[ERROR] {message}</span>'
        )
        self._is_generating = False

    def on_finished(self, result: GenerationResult) -> None:
        self._is_generating = False

    def on_exit(self) -> None:
        super().on_exit()
        if self._worker is not None and self._is_generating:
            self._worker.cancel()
            self._is_generating = False

    def get_spec_update(self) -> dict:
        return {}

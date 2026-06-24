from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout

from forge.ui.screens.base import WizardScreen

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from forge.generation.orchestrator import Orchestrator
    from forge.plugins.base import PluginBase


class DomainSelectionScreen(WizardScreen):
    def __init__(self, orchestrator: Orchestrator) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self._selected_backend_id: str = ""
        self._selected_frontend_id: str | None = None

        layout = QVBoxLayout(self)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setVisible(False)
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)

        lists_layout = QHBoxLayout()

        backend_layout = QVBoxLayout()
        backend_label = QLabel("Backend")
        backend_layout.addWidget(backend_label)
        self._backend_list = QListWidget()
        backend_layout.addWidget(self._backend_list)
        lists_layout.addLayout(backend_layout)

        frontend_layout = QVBoxLayout()
        frontend_label = QLabel("Frontend")
        frontend_layout.addWidget(frontend_label)
        self._frontend_list = QListWidget()
        frontend_layout.addWidget(self._frontend_list)
        lists_layout.addLayout(frontend_layout)

        layout.addLayout(lists_layout)

        self._backend_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._frontend_list.itemSelectionChanged.connect(self._on_selection_changed)

    def _populate_list(self, list_widget: QListWidget, plugins: list[PluginBase]) -> None:
        list_widget.clear()
        for plugin in plugins:
            item = QListWidgetItem(plugin.display_name)
            item.setData(Qt.UserRole, plugin.name)
            list_widget.addItem(item)

    def _on_selection_changed(self) -> None:
        selected_backend = self._backend_list.selectedItems()
        selected_frontend = self._frontend_list.selectedItems()

        self._selected_backend_id = selected_backend[0].data(Qt.UserRole) if selected_backend else ""
        self._selected_frontend_id = selected_frontend[0].data(Qt.UserRole) if selected_frontend else None

        has_available = (
            self._backend_list.count() > 0 or self._frontend_list.count() > 0
        )
        if not has_available:
            self.can_proceed = True
        else:
            self.can_proceed = bool(self._selected_backend_id)

        self.proceed_changed.emit(self.can_proceed)

    def on_enter(self) -> None:
        backends: list[PluginBase] = []
        frontends: list[PluginBase] = []
        try:
            backends = self._orchestrator.get_available_backends()
            frontends = self._orchestrator.get_available_frontends()
            self._error_label.setVisible(False)
        except Exception:
            logger.exception("Failed to load available plugins")
            self._error_label.setText("Failed to load available templates")
            self._error_label.setVisible(True)

        self._populate_list(self._backend_list, backends)
        self._populate_list(self._frontend_list, frontends)

        self._on_selection_changed()

    def get_spec_update(self) -> dict:
        return {
            "backend_id": self._selected_backend_id or "",
            "frontend_id": self._selected_frontend_id,
        }

    def validate(self) -> list[str]:
        errors: list[str] = []
        has_available = (
            self._backend_list.count() > 0 or self._frontend_list.count() > 0
        )
        if has_available and not self._selected_backend_id:
            errors.append("Please select a backend template")
        return errors




from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from forge.domain import DurationEstimate
from forge.ui.screens.base import WizardScreen

if TYPE_CHECKING:
    from forge.domain.project_spec import ProjectSpec
    from forge.generation.orchestrator import Orchestrator
    from forge.plugins.base import PluginBase


class ReviewScreen(WizardScreen):
    can_proceed = True
    can_go_back = True

    def __init__(self, orchestrator: Orchestrator) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self._spec: ProjectSpec | None = None

        layout = QVBoxLayout(self)

        self._tree = QTreeWidget()
        self._tree.setObjectName("review_tree")
        self._tree.setHeaderLabels(["Setting", "Value"])
        layout.addWidget(self._tree)

        self._warning_label = QLabel()
        self._warning_label.setObjectName("warning_label")
        self._warning_label.setVisible(False)
        self._warning_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self._warning_label)

    def set_spec(self, spec: ProjectSpec) -> None:
        self._spec = spec

    def _resolve_display_name(self, plugin_id: str, is_backend: bool) -> str:
        plugins = (
            self._orchestrator.get_available_backends()
            if is_backend
            else self._orchestrator.get_available_frontends()
        )
        for p in plugins:
            if p.name == plugin_id:
                return p.display_name
        return plugin_id

    def on_enter(self) -> None:
        super().on_enter()
        self._tree.clear()
        self._warning_label.setVisible(False)

        spec = self._spec
        if spec is None:
            return

        project_item = QTreeWidgetItem(self._tree, ["Project", spec.project_name])
        project_item.setExpanded(True)

        backend_id = spec.template.backend_id
        if backend_id:
            display = self._resolve_display_name(backend_id, is_backend=True)
            backend_item = QTreeWidgetItem(self._tree, [display])
            backend_item.setExpanded(True)
            backend_config = spec.config.get(backend_id, {})
            for key, value in backend_config.items():
                QTreeWidgetItem(backend_item, [f"{key}: {value}"])

        frontend_id = spec.template.frontend_id
        if frontend_id:
            display = self._resolve_display_name(frontend_id, is_backend=False)
            frontend_item = QTreeWidgetItem(self._tree, [display])
            frontend_item.setExpanded(True)
            frontend_config = spec.config.get(frontend_id, {})
            for key, value in frontend_config.items():
                QTreeWidgetItem(frontend_item, [f"{key}: {value}"])

        if spec.domains:
            domains_item = QTreeWidgetItem(self._tree, ["Domains", ""])
            domains_item.setExpanded(True)
            for domain in spec.domains:
                QTreeWidgetItem(domains_item, ["", domain.name])

        output_dir = Path.cwd() / spec.project_name
        QTreeWidgetItem(self._tree, ["Output Directory", str(output_dir)])

        estimate = self._orchestrator.estimate_duration(spec)
        duration_text = f"{estimate.estimated_seconds}s"
        if estimate.has_slow_steps:
            duration_text += " (includes slow steps)"
        QTreeWidgetItem(self._tree, ["Estimated Duration", duration_text])

        if estimate.estimated_seconds > 10:
            warning_text = f"Warning: Estimated duration exceeds 10s"
            if estimate.slow_step_details:
                warning_text += " — " + ", ".join(estimate.slow_step_details)
            self._warning_label.setText(warning_text)
            self._warning_label.setVisible(True)

    def get_spec_update(self) -> dict:
        return {}

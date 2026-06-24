from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout

from forge.ui.screens.base import WizardScreen


class WelcomeScreen(WizardScreen):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.addStretch()

        label = QLabel("Project Name")
        layout.addWidget(label)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Enter your project name")
        layout.addWidget(self._name_edit)

        layout.addStretch()

        self._name_edit.textChanged.connect(self._on_name_changed)

    def _on_name_changed(self, text: str) -> None:
        self.can_proceed = bool(text.strip())
        self.proceed_changed.emit(self.can_proceed)

    def get_spec_update(self) -> dict:
        return {"project_name": self._name_edit.text().strip()}

    def validate(self) -> list[str]:
        if not self._name_edit.text().strip():
            return ["Project name is required"]
        return []

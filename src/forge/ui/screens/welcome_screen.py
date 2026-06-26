from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from forge.ui.screens.base import WizardScreen


class WelcomeScreen(WizardScreen):
    def __init__(self) -> None:
        super().__init__()

        self._parent_dir: str = ""

        layout = QVBoxLayout(self)
        layout.addStretch()

        label = QLabel("Project Name")
        layout.addWidget(label)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Enter your project name")
        layout.addWidget(self._name_edit)

        layout.addSpacing(20)

        dir_label = QLabel("Output Directory")
        layout.addWidget(dir_label)

        dir_layout = QHBoxLayout()
        self._path_label = QLabel()
        self._path_label.setObjectName("output_dir_path")
        dir_layout.addWidget(self._path_label)

        self._browse_btn = QPushButton("Browse\u2026")
        self._browse_btn.setObjectName("browse_button")
        dir_layout.addWidget(self._browse_btn)

        layout.addLayout(dir_layout)

        layout.addStretch()

        self._name_edit.textChanged.connect(self._on_name_changed)
        self._browse_btn.clicked.connect(self._on_browse)

        self._update_path_label()

    def _update_path_label(self) -> None:
        text = self._parent_dir if self._parent_dir else str(Path.cwd())
        self._path_label.setText(text)
        self._path_label.setToolTip(text)

    def _on_name_changed(self, text: str) -> None:
        self.can_proceed = bool(text.strip())
        self.proceed_changed.emit(self.can_proceed)

    def _on_browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if selected:
            self._parent_dir = selected
        self._update_path_label()

    def get_spec_update(self) -> dict:
        parent = self._parent_dir if self._parent_dir else str(Path.cwd())
        return {
            "project_name": self._name_edit.text().strip(),
            "output_parent_dir": parent,
        }

    def validate(self) -> list[str]:
        if not self._name_edit.text().strip():
            return ["Project name is required"]
        return []

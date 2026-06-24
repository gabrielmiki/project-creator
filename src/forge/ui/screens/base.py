from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class WizardScreen(QWidget):
    can_proceed = False
    can_go_back = True

    proceed_changed = Signal(bool)

    def get_spec_update(self) -> dict:
        return {}

    def validate(self) -> list[str]:
        return []

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

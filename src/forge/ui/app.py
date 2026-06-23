from __future__ import annotations

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from forge.generation.orchestrator import Orchestrator
from forge.ui.main_window import MainWindow


def create_application(orchestrator: Orchestrator) -> QApplication:
    instance = QCoreApplication.instance()
    if isinstance(instance, QApplication):
        app = instance
    else:
        app = QApplication([])
    app.setApplicationName("Forge")

    window = MainWindow(orchestrator)
    window.show()

    return app

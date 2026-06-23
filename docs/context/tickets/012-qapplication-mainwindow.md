# T-012: QApplication Bootstrap + MainWindow Shell

- **type**: task
- **complexity**: medium
- **layer**: `ui/`
- **dependencies**: T-001, T-007 (implicit — `Orchestrator` type in constructor)
- **phase**: 3 — GUI Layer
- **estimated_context**: ~25% of window
- **tdd_review**: ✅ Complete (2026-06-22)

## Description

Create the PySide6 QApplication bootstrap and the MainWindow shell with a QStackedWidget for wizard screens. Refactors the `_launch_gui()` stub from `src/forge/app.py` (created in T-007) into real bootstrap code in `src/forge/ui/app.py`.

This ticket is the **first Qt/UI ticket** in the project. It must establish the UI test infrastructure (QApplication lifecycle, widget identification conventions, modal dialog testing patterns) that all subsequent UI tickets (T-013+) will depend on.

## Role Boundary

The existing `src/forge/app.py` has a `_launch_gui()` stub (T-007) that currently prints "GUI mode not yet implemented" and exits. This ticket replaces that stub with real bootstrap logic:

```
__main__.py  →  forge.app.main()  →  _launch_gui()  →  forge.ui.app.create_application()
                                                          →  forge.ui.main_window.MainWindow(orchestrator)
```

- `forge.app._launch_gui()` — constructs `PluginRegistry`, `ValidationEngine`, `Orchestrator`, then delegates to `forge.ui`
- `forge.ui.app.create_application()` — creates `QApplication`, sets style/icon, instantiates and shows `MainWindow`, starts event loop
- `forge.ui.main_window.MainWindow` — the window shell with `QStackedWidget` + navigation footer

## Files to create

- `src/forge/ui/__init__.py`
- `src/forge/ui/app.py` — QApplication setup, style, icon; `create_application()` function
- `src/forge/ui/main_window.py` — MainWindow with QStackedWidget + navigation controls + modal dialog helpers
- `src/forge/ui/screens/__init__.py`
- `tests/unit/test_main_window.py` — unit tests for all ACs

## API Spec

```python
from PySide6.QtCore import QObject, Signal


class MainWindow(QMainWindow):
    def __init__(self, orchestrator: Orchestrator) -> None: ...

    # Screen navigation
    def navigate_to(self, screen_index: int) -> None: ...
    def next_screen(self) -> None: ...
    def previous_screen(self) -> None: ...

    # Signals
    generation_requested = Signal(ProjectSpec)        # emitted on 3→4 transition
    generation_completed = Signal(GenerationResult)   # received from GenerationWorker
    cancelled = Signal()                              # emitted on Cancel click (screen 4)

    def show_error(self, title: str, message: str) -> None: ...
    def show_confirm(self, title: str, message: str) -> bool: ...
```

### Navigation button object names

All navigation buttons MUST be assigned `setObjectName()` for testability:

| Widget | Object name |
|--------|-------------|
| Previous button | `"previous_button"` |
| Next button | `"next_button"` |
| Cancel button | `"cancel_button"` |
| Open Project button | `"open_button"` |
| Close button | `"close_button"` |

### Signal type safety

`generation_completed = Signal(GenerationResult)` requires `GenerationResult` to be a type registered with PySide6's meta-object system. Since `GenerationResult` is a `@dataclass` in `forge.generation.orchestrator`, it may need `qRegisterMetaType(GenerationResult)` to work across threads (used by T-013 `GenerationWorker`). Add this registration in `forge.ui.app.create_application()` or `MainWindow.__init__()` if cross-thread signal emission is needed.

## Navigation button visibility rules

| Screen index | Previous | Next | Cancel | Open Project | Close |
|---|---|---|---|---|---|---|
| 0 (Welcome) | Disabled (`isEnabled() == False`) | Enabled (`isVisible() == True`) | Hidden | Hidden | Hidden |
| 1–3 | Enabled | Enabled | Hidden | Hidden | Hidden |
| 4 (Generation) | Hidden (`isVisible() == False`) | Hidden | Shown | Shown (`isVisible() == True`) | Shown (`isVisible() == True`) |
| 4 (after success) | Hidden | Hidden | Hidden | Shown | Shown |

`Disabled` means `setEnabled(False)` (button remains visible but non-interactive).
`Hidden` means `setVisible(False)` (button removed from layout).
`Shown` means `setVisible(True)` (button visible and interactive).

## Screen registry

Screens are registered by index in `MainWindow.__init__()`:

| Index | Screen Class | Purpose |
|---|---|---|
| 0 | `WelcomeScreen` | Welcome + project name/author input |
| 1 | `DomainSelectionScreen` | Select backend + frontend |
| 2 | `ConfigurationScreen` | Global + per-plugin config |
| 3 | `ReviewScreen` | Summary tree view |
| 4 | `GenerationScreen` | Progress bar + status log |

The shell provides `Previous`/`Next` buttons in a footer. The `GenerationScreen` hides these and shows `Cancel` / `Open Project` / `Close`.

### Navigation boundary behavior

| Call | Screen 0 | Screen 1–3 | Screen 4 |
|------|----------|------------|-----------|
| `previous_screen()` | No-op (index stays 0) | Decrements index by 1 | No-op (index stays 4) |
| `next_screen()` | Increments index to 1 | Increments index by 1 | No-op (index stays 4) |
| `navigate_to(target)` | Sets index to target | Sets index to target | Clamped to [0, 4] |

### Signal emission triggers

| Signal | Trigger | Payload |
|--------|---------|---------|
| `generation_requested` | "Generate" clicked on review screen (index 3→4 transition) | `ProjectSpec` (current spec) |
| `generation_completed` | Received from `GenerationWorker.finished` | `GenerationResult` (outcome) |
| `cancelled` | Cancel button clicked on screen 4 | None |

The `cancelled` signal contract is declared here for T-013 (GenerationWorker) but not acceptance-tested in this ticket — the Cancel button's click-to-signal wiring is tested by T-013.

## Testing Infrastructure

This ticket establishes the Qt test infrastructure for all subsequent UI tickets.

### pytest-qt

Add `pytest-qt` to dev dependencies. The `qtbot` fixture from pytest-qt provides:
- `qtbot.addWidget(widget)` — registers widget for cleanup
- `qtbot.mouseClick(widget, Qt.LeftButton)` — simulates clicks
- `qtbot.waitSignal(signal, timeout=1000)` — waits for signal emission
- `qtbot.keyClick(widget, Qt.Key_Enter)` — simulates keyboard events

### QApplication fixture

A session-scoped `qapp` fixture. Place it in `tests/unit/conftest.py` for initial setup or consider `tests/unit/ui/conftest.py` for future isolation (avoids importing PySide6 for non-UI unit tests):

```python
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app
```

### Mock Orchestrator fixture

A module-level `mock_orchestrator` fixture following the `MagicMock` pattern from `test_orchestrator.py`:

```python
@pytest.fixture
def mock_orchestrator():
    orch = MagicMock(spec=Orchestrator)
    orch.get_available_backends.return_value = []
    orch.get_available_frontends.return_value = []
    orch.get_global_questions.return_value = []
    orch.get_domain_questions.return_value = {}
    return orch
```

### Modal dialog testing pattern

`QMessageBox.exec()` blocks the calling thread. Tests MUST monkey-patch static methods:

```python
def test_show_error(monkeypatch, main_window):
    captured: dict = {}
    def fake_critical(parent, title, text):
        captured["title"] = title
        captured["text"] = text
        return QMessageBox.Ok
    monkeypatch.setattr(QMessageBox, "critical", fake_critical)
    main_window.show_error("Error", "Something failed")
    assert captured == {"title": "Error", "text": "Something failed"}

def test_show_confirm_yes(monkeypatch, main_window):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.Yes)
    assert main_window.show_confirm("Confirm", "Proceed?") is True

def test_show_confirm_no(monkeypatch, main_window):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.No)
    assert main_window.show_confirm("Confirm", "Proceed?") is False
```

### Headless/CI display

Qt widget tests require a display. For headless CI environments, set:
```
QT_QPA_PLATFORM=offscreen
```
Document in `pyproject.toml` test configuration:
```toml
[tool.pytest.ini_options]
markers = [
    "gui: tests that require a QApplication and display"
]
```
All UI tests SHOULD be marked with `@pytest.mark.gui`.

## Acceptance Criteria

### Happy Path

1. **Given** a running `QApplication`, **when** `MainWindow(orchestrator=mock_orchestrator)` is constructed and `show()` is called, **then** `windowTitle()` returns `"Forge"`, `findChild(QStackedWidget).count()` returns `5`, and screen indices 0–4 are registered as child widgets of the stacked widget.

2. **Given** `MainWindow` is shown with `navigate_to(0)` called, **then** `findChild(QPushButton, "previous_button").isEnabled()` is `False` and `findChild(QPushButton, "next_button").isEnabled()` is `True`.

3. **Given** `MainWindow` is shown with `navigate_to(4)` called, **then** `findChild(QPushButton, "previous_button").isVisible()` is `False`, `findChild(QPushButton, "next_button").isVisible()` is `False`, and `findChild(QPushButton, "cancel_button").isVisible()` is `True`.

4. **Given** `MainWindow` is shown, **when** `show_error("Error", "Something failed")` is called and `QMessageBox.critical` is monkey-patched to capture arguments, **then** `title` is `"Error"` and `text` is `"Something failed"`.

5. **Given** `MainWindow` is shown, **when** `show_confirm("Confirm", "Proceed?")` is called and `QMessageBox.question` is monkey-patched to return `QMessageBox.Yes`, **then** return value is `True`. **When** patched to return `QMessageBox.No`, **then** return value is `False`.

6. **Given** `MainWindow` is shown with `navigate_to(3)` called, **when** `next_screen()` is called, **then** the `generation_requested` signal is emitted with a `ProjectSpec` instance (no assertion on specific field values).

7. **Given** `MainWindow` is shown, **when** `generation_completed` signal is emitted with `GenerationResult(success=True, error=None, output_path=Path("/tmp/out"))`, **then** the signal is received within 1000ms (no exception raised on `emit()`).

### Error Cases

8. **Given** `MainWindow` is shown, **when** `navigate_to(-1)` is called, **then** the `QStackedWidget` index remains at `0` (clamped). **When** `navigate_to(10)` is called, **then** the index is clamped to `4`.

9. **Given** `MainWindow` is shown with `navigate_to(0)` called, **when** `previous_screen()` is called, **then** the `QStackedWidget` current index remains `0` (no-op, not decremented to -1).

### Edge Cases

10. **Given** `MainWindow` is shown with `navigate_to(4)` called, **when** `next_screen()` is called, **then** the `QStackedWidget` current index remains `4` (no-op).

11. **Given** `MainWindow` is shown, **when** `show_confirm("Confirm", "Proceed?")` is called and `QMessageBox.question` is monkey-patched to return `QMessageBox.Escape` (the dialog close button / Escape key result), **then** return value is `False`.

12. **Given** `MainWindow` is shown with `navigate_to(4)` called, **when** the Cancel button (`"cancel_button"`) is clicked, **then** the `cancelled` signal is emitted within 1000ms.

    > This AC depends on the Cancel button's `clicked` signal being wired to the `cancelled` signal in `MainWindow`. The Cancel button's visibility is tested in AC-3; the signal emission is tested here.

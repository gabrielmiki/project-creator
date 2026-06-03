# T-012: QApplication Bootstrap + MainWindow Shell

- **type**: task
- **complexity**: medium
- **layer**: `ui/`
- **dependencies**: T-001
- **phase**: 3 — GUI Layer
- **estimated_context**: ~25% of window

## Description

Create the PySide6 QApplication bootstrap and the MainWindow shell with a QStackedWidget for wizard screens. Includes the app entry point refactored from the skeleton in T-007.

## Files to create

- `src/forge/ui/__init__.py`
- `src/forge/ui/app.py` — QApplication setup, style, icon
- `src/forge/ui/main_window.py` — MainWindow with QStackedWidget + navigation controls
- `src/forge/ui/screens/__init__.py`

## API Spec

```python
class MainWindow(QMainWindow):
    def __init__(self, orchestrator: Orchestrator): ...

    # Screen navigation
    def navigate_to(self, screen_index: int) -> None: ...
    def next_screen(self) -> None: ...
    def previous_screen(self) -> None: ...

    # Signals
    generation_requested = Signal(ProjectSpec)
    generation_completed = Signal(GenerationResult)
    cancelled = Signal()

    def show_error(self, title: str, message: str) -> None: ...
    def show_confirm(self, title: str, message: str) -> bool: ...
```

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

## Acceptance Criteria

1. **Given** QApplication runs, **when** `MainWindow` is instantiated, **then** a window appears with title "Forge" and QStackedWidget with 5 screens.
2. **Given** MainWindow is displayed, **when** screen index 0 is shown, **then** `Previous` button is disabled and `Next` button is enabled.
3. **Given** screen index 4 (Generation), **when** displayed, **then** `Previous`/`Next` are hidden and `Cancel` button is shown.
4. **Given** `show_error()` is called, **then** a QMessageBox with the error text appears.
5. **Given** `show_confirm()` is called, **then** a QMessageBox with Yes/No buttons appears and returns the user's choice.

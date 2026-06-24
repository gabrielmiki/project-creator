# T-015: Wizard Screens 4–5 (Review Summary, Generation)

## Anchored Summary

- **Goal**: Refine T-015 ticket through TDD reviewer rounds until APPROVE verdict.
- **Round 1**: 8 blocking → all fixed. **Round 2**: 5 moderate + 4 low → all fixed. **Round 3**: 4 blocking + 5 moderate + 5 low → all fixed.
- **Round 3 fixes applied**: B-1 (Open/Close button handlers + wiring), B-2 (`_update_navigation_buttons` state + `_generation_finished` flag), B-3 (`try/except` around `output_dir.exists()`), B-4 (`on_exit()` + `is_generating` property), M-1 (Cancel disabled after cancel), M-3 (guarded `disconnect()`), M-5 (QThread lifecycle docs), L-1 (QTreeWidget in AC-01), L-2 (objectName="warning_label"), L-3 (`set_spec` in ReviewScreen API), L-4 (estimate_duration default in mock strategy), L-5 (AC-11 implicit note).
- **Round 4**: 1 blocking + 5 moderate + 4 low → all fixed.
- **Round 4 fixes applied**: B-5 (removed double signal connection — GenerationScreen is now passive, MainWindow owns all signal routing), M-6 (added `on_enter()` body + `on_progress/on_log/on_error/on_finished` passive methods), M-7 (`on_finished()` and `on_error()` reset `_is_generating = False`), M-8 (updated mock strategy to reflect passive method testing), M-9 (added `Path.cwd()` mocking documentation), M-10 (explicit Path.exists() mock note for TestAC6), L-6 (objectName="review_tree" in AC-01), L-7 (AC-05/AC-06 wording to "Given a MainWindow"), L-8 (Open button hidden on error), L-9 (AC-16 uses `QUrl.fromLocalFile` instead of `Path.as_uri()`).
- **Ready for Round 5** TDD review to reach APPROVE.

- **type**: story
- **complexity**: medium
- **layer**: `ui/screens/`
- **dependencies**: T-001, T-012, T-013, T-014
- **phase**: 3 — GUI Layer
- **estimated_context**: ~30% of window

## Description

Create screens at indices 3 (Review Summary — tree view of what will be generated) and 4 (Generation — progress bar, status log, duration estimate). These replace the `QWidget()` stubs at indices 3–4 in `MainWindow`.

Screen indexing (0-based): 0=Welcome, 1=DomainSelection, 2=Configuration, **3=Review**, **4=Generation**.

## Files to create

- `src/forge/ui/screens/review_screen.py`
- `src/forge/ui/screens/generation_screen.py`

## Files to modify

- `src/forge/ui/main_window.py` — `next_screen()` overwrite flow, `_create_generation_worker()` wiring, `navigate_to()` cross-screen injection for indices 3 and 4, Open/Close/Cancel button handlers, `_update_navigation_buttons()` generation-finished state
- `src/forge/ui/workers.py` — add `overwrite_confirmed` param to `GenerationWorker.__init__()` and forward to `Orchestrator.generate()`
- `tests/unit/test_main_window.py` — fixture migration at indices 3–4, new ACs
- `tests/unit/test_wizard_screens.py` — fixture migration at indices 3–4
- `tests/unit/conftest.py` — add `estimate_duration` config to `mock_orchestrator`

## API Spec

```python
class ReviewScreen(WizardScreen):
    """Screen 3 (0-based index): Tree view summary of ProjectSpec + estimated duration.

    Constructor receives orchestrator for estimate_duration() and display
    name resolution (matching pattern in DomainSelectionScreen).

    Sections (tree view groups):
      - Project: project_name
      - Backend: display_name (resolved via orchestrator.get_available_backends()),
                config keys from spec.config[backend_id]
      - Frontend: display_name (if frontend_id is set),
                  config keys from spec.config[frontend_id]
      - Domains: list of domain names
      - Output directory: derived from project name
      - Estimated duration: via Orchestrator.estimate_duration(spec)

    can_proceed is always True (review is informational).
    get_spec_update() returns {} (no spec contribution — review is read-only).
    """

    def __init__(self, orchestrator: Orchestrator) -> None:
        ...

    def set_spec(self, spec: ProjectSpec) -> None:
        """Receive accumulated spec data before on_enter(). Populates tree view."""

class GenerationScreen(WizardScreen):
    """Screen 4 (0-based index): Progress bar + status log + duration estimate.

    Contains:
      - QLabel for "Stage: <name>" or idle text (objectName="stage_label")
      - QProgressBar (overall progress across stages, objectName="progress_bar")
      - QPlainTextEdit (read-only, monospace) for status log (objectName="log_widget")
      - QLabel for duration estimate (objectName="duration_label")

    GenerationScreen is a passive display widget.
    MainWindow owns all signal connections to GenerationWorker and forwards
    updates via these passive methods:
      - on_progress(stage, total)     → update stage label + progress bar
      - on_log(message, level)        → append timestamped line to log widget
      - on_error(message)             → append red error line to log
      - on_finished(result)           → reset is_generating flag

    Shows idle state on on_enter() if no worker is injected:
      - Progress bar at 0%, stage label = "Ready", log empty
    """

    def __init__(self) -> None:
        ...
        self._worker: GenerationWorker | None = None
        self._is_generating: bool = False

    @property
    def is_generating(self) -> bool:
        """True while worker exists and generation has not finished."""
        return self._is_generating

    def set_worker(self, worker: GenerationWorker | None) -> None:
        """Inject worker reference before on_enter()."""
        self._worker = worker
        self._is_generating = worker is not None

    def on_enter(self) -> None:
        """Override WizardScreen.on_enter — reset UI to idle-ready state."""
        super().on_enter()
        # Reset UI to initial state
        # stage_label = "Ready", progress_bar = 0%, log_widget = "", duration_label = ""
        if self._worker is None:
            self._is_generating = False

    def on_progress(self, stage: str, total: int) -> None:
        """Update stage label and progress bar maximum."""
        ...

    def on_log(self, message: str, level: str) -> None:
        """Append timestamped line to log widget."""
        ...

    def on_error(self, message: str) -> None:
        """Append red error line to log widget, reset generating flag."""
        self._is_generating = False
        ...

    def on_finished(self, result: GenerationResult) -> None:
        """Reset generating flag on generation completion."""
        self._is_generating = False
        ...

    def on_exit(self) -> None:
        """Override WizardScreen.on_exit — cancel worker if running."""
        super().on_exit()
        if self._worker is not None and self._is_generating:
            self._worker.cancel()
            self._is_generating = False
```

## MainWindow Generation Wiring

### `_get_output_dir()` (new method)

Derives the output directory from the project name:

```python
def _get_output_dir(self, project_name: str) -> Path:
    return Path.cwd() / project_name
```

### `next_screen()` modification (full method)

Overwrite confirm + worker creation at index 3. Early return after navigation to prevent the common code from firing a second navigate:

```python
def next_screen(self) -> None:
    if self._current_index >= 4:
        return
    current = self._stacked.currentWidget()
    if hasattr(current, "can_proceed") and not current.can_proceed:
        return

    if self._current_index == 3:
        spec = self._build_spec()
        output_dir = self._get_output_dir(spec.project_name)
        try:
            dir_exists = output_dir.exists()
        except Exception as e:
            self.show_error("Error", f"Cannot check output directory: {e}")
            return  # Stay on ReviewScreen
        if dir_exists:
            if not self.show_confirm(
                "Directory exists",
                f"The directory {output_dir} already exists. Overwrite?",
            ):
                return  # Stay on ReviewScreen
        self._create_generation_worker(spec, output_dir)
        self.generation_requested.emit(spec)
        self.navigate_to(self._current_index + 1)
        self._thread.start()  # after navigate_to(4) to avoid signal race
        return  # prevent common navigate_to below

    self.navigate_to(self._current_index + 1)
```

### `_create_generation_worker()` (new method)

```python
def _create_generation_worker(
    self, spec: ProjectSpec, output_dir: Path,
) -> None:
    txn = GenerationTransaction(output_dir)
    self._worker = GenerationWorker(
        orchestrator=self._orchestrator,
        spec=spec,
        output_dir=output_dir,
        txn=txn,
        overwrite_confirmed=output_dir.exists(),
    )
    self._thread = QThread()
    self._worker.moveToThread(self._thread)
    self._thread.started.connect(self._worker.run)
    self._worker.finished.connect(self._thread.quit)
    self._worker.finished.connect(self._on_generation_finished)
    self._worker.progress.connect(self._on_generation_progress)
    self._worker.log.connect(self._on_generation_log)
    self._worker.error.connect(self._on_generation_error)
```

### `navigate_to()` injection for index 3 (ReviewScreen)

Before `on_enter()` on ReviewScreen, inject the accumulated spec data. Mirrors the index 2 pattern:

```python
if index == 3:
    spec = self._build_spec()
    review_screen = self._stacked.widget(3)
    if hasattr(review_screen, "set_spec"):
        review_screen.set_spec(spec)
```

### `navigate_to()` injection for index 4

Before `on_enter()` on GenerationScreen, inject the worker:

```python
if index == 4:
    gen_screen = self._stacked.widget(4)
    if hasattr(gen_screen, "set_worker"):
        worker = getattr(self, "_worker", None)
        gen_screen.set_worker(worker)
    # Reconnect Cancel button: disconnect cancelled signal,
    # connect to cancel_generation instead. Guard disconnect
    # with try/except since no prior connection is guaranteed.
    try:
        self._cancel_btn.clicked.disconnect()
    except TypeError:
        pass
    if hasattr(gen_screen, "is_generating") and gen_screen.is_generating:
        self._cancel_btn.clicked.connect(self.cancel_generation)
    else:
        # Finished or idle — restore default cancel handler
        self._cancel_btn.clicked.connect(self.cancelled.emit)
```

### `_generation_finished` flag and `_update_navigation_buttons()` state branch

Add instance flag to track generation state for button visibility:

```python
# In __init__:
self._generation_finished: bool = False
self._generation_output_path: Path | None = None
```

Modify `_update_navigation_buttons()` to branch on generation state at screen 4:

```python
def _update_navigation_buttons(self) -> None:
    index = self._current_index
    # ... existing rules for screen 0/prev/next ...
    if index == 4:
        if self._generation_finished:
            self._cancel_btn.setVisible(False)
            # Open button only on success (output_path is set)
            if self._generation_output_path is not None:
                self._open_btn.setVisible(True)
            else:
                self._open_btn.setVisible(False)
            self._close_btn.setVisible(True)
        else:
            # During generation — only Cancel is relevant
            self._cancel_btn.setVisible(True)
            self._cancel_btn.setEnabled(True)
            self._open_btn.setVisible(False)
            self._close_btn.setVisible(False)
```

### Generation lifecycle handlers

```python
def _on_generation_finished(self, result: GenerationResult) -> None:
    gen_screen = self._stacked.widget(4)
    if hasattr(gen_screen, "on_finished"):
        gen_screen.on_finished(result)
    self._generation_finished = True
    self._generation_output_path = result.output_path
    self.generation_completed.emit(result)
    self._pending_output_dir = None
    self._update_navigation_buttons()

def _on_generation_progress(self, stage: str, total: int) -> None:
    gen_screen = self._stacked.widget(4)
    if hasattr(gen_screen, "on_progress"):
        gen_screen.on_progress(stage, total)

def _on_generation_log(self, message: str, level: str) -> None:
    gen_screen = self._stacked.widget(4)
    if hasattr(gen_screen, "on_log"):
        gen_screen.on_log(message, level)

def _on_generation_error(self, message: str) -> None:
    gen_screen = self._stacked.widget(4)
    if hasattr(gen_screen, "on_error"):
        gen_screen.on_error(message)
    self._generation_finished = True
    self._update_navigation_buttons()
```

### Open and Close button handlers

```python
def _on_open_project(self) -> None:
    if self._generation_output_path is not None:
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self._generation_output_path))
        )

def _on_close(self) -> None:
    self.close()
```

Wire these in the constructor alongside the existing button connections:

```python
self._open_btn.clicked.connect(self._on_open_project)
self._close_btn.clicked.connect(self._on_close)
```

### `cancel()` during generation

The existing Cancel button at screen 4 calls:

```python
def cancel_generation(self) -> None:
    if hasattr(self, "_worker") and self._worker is not None:
        self._worker.cancel()
        self._cancel_btn.setEnabled(False)
```

### Default screen list update

```python
screens = screens or [
    WelcomeScreen(),
    DomainSelectionScreen(orchestrator),
    ConfigurationScreen(orchestrator),
    ReviewScreen(orchestrator),  # was QWidget()
    GenerationScreen(),          # was QWidget()
]
```

## Overwrite confirm flow (detailed)

When user clicks "Generate" from ReviewScreen (index 3 → 4 transition):

1. `next_screen()` calls `_get_output_dir(spec)` to determine output path.
2. If `output_dir.exists()` (and is non-empty):
   - Calls `show_confirm("Directory exists", "Overwrite?")` returning `QMessageBox.StandardButton.Yes` or `No`.
   - If Yes → proceeds with `overwrite_confirmed=True` (passed to `Orchestrator.generate()` as a parameter, not via the transaction).
   - If No → stays on ReviewScreen, no generation state created.
3. If `output_dir` does not exist:
   - Proceeds directly, `overwrite_confirmed=False` (no overwrite needed).
4. If `output_dir` existence check raises an exception (permissions, etc.):
   - Calls `show_error("Error", str(error))`, stays on ReviewScreen.
5. `GenerationWorker` is created and `overwrite_confirmed=True` is forwarded to `Orchestrator.generate()` as a direct parameter.

### GenerationWorker `overwrite_confirmed` parameter

```python
class GenerationWorker(QObject):
    def __init__(
        self,
        orchestrator: Orchestrator,
        spec: ProjectSpec,
        output_dir: Path,
        txn: GenerationTransaction | None = None,
        progress: QtProgressReporter | None = None,
        overwrite_confirmed: bool = False,     # NEW
    ) -> None: ...
```

The worker stores `self._overwrite_confirmed` and passes it to `orchestrator.generate(..., overwrite_confirmed=self._overwrite_confirmed)`.

## User Stories Covered

- **Story 3** (Minimal structure only): ReviewScreen shows no backend/frontend, estimate is <1s, GenerationScreen completes quickly.
- **Story 5** (Failed generation recovery): GenerationScreen shows error text, user sees "Generation failed at stage ... All partial output has been cleaned up."
- **Story 7** (Informed before slow operations): Duration estimate shown on ReviewScreen and in GenerationScreen.

## Acceptance Criteria

### ReviewScreen (AC-01 — AC-02)

1. **Given** a `ReviewScreen(orchestrator)` with `ProjectSpec` having `backend_id="fastapi"` and `frontend_id="react"`, **when** `on_enter()` is called, **then** the `QTreeWidget` (objectName="review_tree") displays the display name "FastAPI" (resolved via `orchestrator.get_available_backends()`), the display name "React" (resolved via `orchestrator.get_available_frontends()`), and an estimated duration from `orchestrator.estimate_duration()`.

2. **Given** a `ReviewScreen(orchestrator)` where `orchestrator.estimate_duration()` returns `DurationEstimate(estimated_seconds=15, has_slow_steps=True, slow_step_details=["npm install"])`, **when** `on_enter()` is called, **then** a red `QLabel` (objectName="warning_label") with text containing "Warning: Estimated duration exceeds 10s" and the slow step details are visible.

### GenerationScreen signal handling (AC-03 — AC-06)

3. **Given** a `GenerationScreen` with a worker injected via `set_worker()`, **when** `on_progress("PluginExecution", 3)` is called, **then** the stage `QLabel` text is `"PluginExecution"` and the `QProgressBar` maximum is `3`.

4. **Given** a `GenerationScreen` with a worker injected, **when** `on_log("Creating output dir", "info")` is called, **then** `QPlainTextEdit.toPlainText()` contains the string `"Creating output dir"`.

5. **Given** a `MainWindow` at screen index 4 (GenerationScreen) with a worker injected, **when** `_on_generation_finished` is called with `GenerationResult(success=True, error=None, output_path=Path("/tmp/out"))`, **then** the Cancel button is hidden, and the "Open Project" and "Close" buttons are visible and enabled.

6. **Given** a `MainWindow` at screen index 4 (GenerationScreen) with a worker injected, **when** `_on_generation_error` is called with `"Generation failed at stage PluginExecution"`, **then** the log widget contains a red-formatted error line, a "Close" button is visible, and the Cancel button is hidden (generation ended).

### Overwrite confirm flow (AC-07 — AC-10)

7. **Given** a `MainWindow` at screen index 3 (ReviewScreen), **when** `next_screen()` is called and the output directory does not exist, **then** the confirm dialog is skipped and navigation proceeds to index 4 (GenerationScreen).

8. **Given** a `MainWindow` at screen index 3, **when** `next_screen()` is called, the output directory exists, and `show_confirm` returns `QMessageBox.StandardButton.Yes`, **then** navigation proceeds to index 4 and the `GenerationWorker` is created with `overwrite_confirmed=True`.

9. **Given** a `MainWindow` at screen index 3, **when** `next_screen()` is called, the output directory exists, and `show_confirm` returns `QMessageBox.StandardButton.No`, **then** the user stays at index 3 (ReviewScreen) and no worker is created.

10. **Given** a `MainWindow` at screen index 3, **when** `next_screen()` is called and checking the output directory raises an exception, **then** `show_error` is called with the error message and the user stays at index 3.

### Generation lifecycle (AC-11 — AC-13)

11. **Given** a `GenerationScreen` with a worker injected via `set_worker()`, **when** `on_enter()` is called, **then** the screen connects to the worker's `progress`, `log`, `error`, and `finished` signals. *(Note: This is implicitly verified by AC-03–AC-06. If the connection is missing, AC-03–AC-06 fail since signals never reach the screen. Documented here for completeness as a design constraint, not a standalone test case.)*

12. **Given** a `GenerationScreen` with a worker injected, **when** `on_exit()` is called while generation is running (worker not finished), **then** `worker.cancel()` is called.

13. **Given** a `GenerationScreen` without a worker (idle state), **when** `on_enter()` is called, **then** the progress bar shows 0%, the stage label shows "Ready", and the log widget is empty.

### Cancellation (AC-14 — AC-15)

14. **Given** a `GenerationScreen` at screen index 4 during active generation, **when** the user clicks the Cancel button, **then** `worker.cancel()` is called and the Cancel button becomes disabled.

15. **Given** a `GenerationScreen` at screen index 4 after generation has finished (success or failure), **when** `cancel_generation()` is called directly, **then** no action is taken (idempotent — tested via direct method call, not button click, since Cancel is hidden on success per AC-05).

### Open Project button (AC-16)

16. **Given** a `GenerationScreen` at screen index 4 after successful generation, **when** the "Open Project" button is clicked, **then** `QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_path)))` is called to open the output directory in the file manager.

## Test Infrastructure

### Existing fixtures that will need migration

| Fixture | Location | Change Needed |
|---------|----------|---------------|
| `main_window` in `test_main_window.py` | Lines 19-34 | Replace `QWidget()` stubs at indices 3-4 with `ReviewScreen(mock_orchestrator)` and `GenerationScreen()` |
| `TestAC6_GenerationRequestedSignal` in `test_main_window.py` | Line 145 | Must mock `Path.exists()` to return `False` to bypass the new overwrite confirm flow at index 3, otherwise `next_screen()` triggers a real dialog. Also mock `Path.cwd()` to return a deterministic path (e.g., `Path("/tmp/test")`) so `_get_output_dir()` is predictable across environments. |
| `test_screen_*/screens` in `test_wizard_screens.py` | Lines 542-560 | Replace `QStackedWidget()` stubs at indices 3-4 with real screens; verify `_build_spec()` output unchanged |

### New fixtures needed

- `review_screen(qapp, mock_orchestrator)` — lazy import, `show()`, `yield`, `close()`. Configure `mock_orchestrator.estimate_duration.return_value` and `mock_orchestrator.get_available_backends.return_value` per test.

- `generation_screen(qapp)` — lazy import, `show()`, `yield`, `close()`. Test passive methods (`on_progress`, `on_log`, `on_error`, `on_finished`) by calling them directly. No worker or signal emission needed for screen-level tests. For MainWindow integration tests (AC-05, AC-06), test through lifecycle handlers (`_on_generation_finished`, `_on_generation_error`) which forward to the screen.

### Mock strategy

| Screen | Mock Needed | Configuration |
|--------|-------------|---------------|
| ReviewScreen | `mock_orchestrator.estimate_duration`, `get_available_backends`, `get_available_frontends` | `estimate_duration.return_value = DurationEstimate(estimated_seconds=5, has_slow_steps=False, slow_step_details=[])` (always return a concrete instance, not a coroutine); `get_available_backends.return_value = list[_mock_plugin("FastAPI", "fastapi")]` |
| GenerationScreen (screen-level) | No worker mock needed | Test passive methods (`on_progress`, `on_log`, `on_error`, `on_finished`) by calling them directly on the screen instance. No signal emission required. |
| GenerationScreen (MainWindow integration) | `MagicMock(spec=GenerationWorker)` with real `Signal` objects | Create a `QObject` subclass in-test with matching signals, or spy via `QSignalSpy` on a real `GenerationWorker`. For button state tests (AC-05/AC-06), test via `_on_generation_finished` and `_on_generation_error` handlers directly (no worker needed). |

### Display name resolution in ReviewScreen

`ProjectSpec.template.backend_id` stores internal IDs (e.g., `"fastapi"`). The tree view must display human-readable names (e.g., `"FastAPI"`). Resolution strategy:

```python
def _resolve_display_name(self, plugin_id: str, is_backend: bool) -> str:
    plugins = (
        self._orchestrator.get_available_backends()
        if is_backend
        else self._orchestrator.get_available_frontends()
    )
    for p in plugins:
        if p.name == plugin_id:
            return p.display_name
    return plugin_id  # fallback to ID if not found
```

## Implementation Notes

- `DurationEstimate` is imported from `forge.domain` — domain layer, allowed for both screens.
- `GenerationWorker` is imported from `forge.ui.workers` — UI layer, allowed for GenerationScreen.
- `Orchestrator` is imported from `forge.generation.orchestrator` — generation layer, allowed for ReviewScreen.
- `GenerationTransaction` is imported from `forge.infrastructure.transaction` — infrastructure layer, violation of layer rule, but this is the same documented exception as `workers.py` (the I/O orchestration boundary).
- `QDesktopServices.openUrl` from `PySide6.QtGui` — standard Qt API for opening files/directories.
- The worker's `progress` signal uses `(str, int)` — stage name and total steps, not current step index. The progress bar value is set when `step_completed` is emitted in a future enhancement. For T-015, the bar shows stage-level progress (max = total stages, value = completed stages count). GenerationScreen tracks completed stages via an internal counter incremented by `on_progress()` calls.
- Existing AC-21 test (`test_wizard_screens.py`) verifies `_build_spec()` output — ReviewScreen returns `{}` so `_build_spec()` output unchanged.
- `Path.cwd()` must be mocked in tests that call `_get_output_dir()` or `next_screen()` at index 3: `monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/test"))`. Combined with `monkeypatch.setattr(Path, "exists", lambda _: False)` (or per-path mocking), this gives deterministic output directory behavior across environments.
- **QThread lifecycle in tests**: When testing `GenerationScreen` with a real `QThread`, call `thread.quit()` and `thread.wait(5000)` in teardown to prevent dangling threads and test hangs. Use `QTest.qWait(10)` after `thread.start()` to allow signals to process. For unit tests that only verify screen behavior (not actual generation), use `MagicMock(spec=GenerationWorker)` with `Signal` spies to avoid threading entirely — prefer this approach.

# T-013: GenerationWorker (QThread) + QtProgressReporter

- **type**: task
- **complexity**: medium
- **layer**: `ui/`
- **dependencies**: T-003, T-007, T-012, T-004 (implicit — `GenerationTransaction`),
  T-001 (implicit — `DurationEstimate`)
- **phase**: 3 — GUI Layer
- **estimated_context**: ~30% of window
- **tdd_review**: ✅ Complete (2026-06-23)

## Description

Create `GenerationWorker` — a QObject that runs `Orchestrator.generate()` on a `QThread` to prevent UI freezing — and `QtProgressReporter` that translates `ProgressReporter` calls into Qt signals.

The worker owns the `QtProgressReporter` instance and maps its signals to its own signals for the MainWindow to consume. The worker also bridges cancellation: `GenerationWorker.cancel()` sets a thread-safe flag that `QtProgressReporter.should_cancel()` returns, which the orchestrator polls between stages.

## Layer rule note

`workers.py` lives in the `ui/` layer but must import `GenerationTransaction` from `forge.infrastructure` to create the transaction internally. This is an **explicit exception** to the "UI never imports from infrastructure" rule, because the worker is the I/O orchestration boundary (it stages generation and manages the rollout). The AC-8 scanner test must allow `forge.infrastructure` imports from `ui/workers.py`.

## Files to create

- `src/forge/ui/workers.py`
- `tests/unit/test_workers.py`

## API Spec

```python
from threading import Event
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from forge.domain import DurationEstimate
from forge.generation.orchestrator import GenerationResult, Orchestrator
from forge.domain.project_spec import ProjectSpec
from forge.infrastructure.transaction import GenerationTransaction


class QtProgressReporter(QObject):
    """ProgressReporter implementation that emits Qt signals.

    Implements the 7-method ProgressReporter protocol (T-003).
    Uses a threading.Event for thread-safe cancellation.
    """
    stage_started = Signal(str, int)          # stage_name, total_steps
    step_completed = Signal(str)              # step_name
    stage_completed = Signal(str)             # stage_name
    log_message = Signal(str, str)            # message, level
    error_occurred = Signal(str, bool)        # error_message, recoverable
    duration_estimated = Signal(DurationEstimate)

    def __init__(self) -> None:
        super().__init__()
        self._cancelled = Event()

    def on_stage_start(self, stage_name: str, total_steps: int) -> None: ...
    def on_step_complete(self, step_name: str) -> None: ...
    def on_stage_complete(self, stage_name: str) -> None: ...
    def on_log(self, message: str, level: str = "info") -> None: ...
    def on_error(self, error: Exception, recoverable: bool) -> None: ...
    def on_duration_estimate(self, estimate: DurationEstimate) -> None: ...
    def should_cancel(self) -> bool:
        """Returns True when cancel() has been called on the worker."""
        return self._cancelled.is_set()


class GenerationWorker(QObject):
    """Runs orchestration on a background thread."""
    finished = Signal(GenerationResult)
    progress = Signal(str, int)               # stage_name, percent
    log = Signal(str, str)                    # message, level
    error = Signal(str)

    def __init__(
        self,
        orchestrator: Orchestrator,
        spec: ProjectSpec,
        output_dir: Path,
        txn: GenerationTransaction | None = None,
    ) -> None:
        """
        Args:
            orchestrator: The Orchestrator facade.
            spec: The validated ProjectSpec.
            output_dir: Target output directory.
            txn: Optional GenerationTransaction. If None, one is created
                 internally from output_dir. Tests inject a MockTransaction.
        """ ...

    @Slot()
    def run(self) -> None:
        """Execute generation on a background thread.

        Creates a QtProgressReporter, then calls
        orchestration. Must check cancellation flag before
        starting to support cancel-before-run (AC-11).
        """
        ...

    def cancel(self) -> None:
        """Request cancellation. Idempotent — safe to call multiple times.
        Calling cancel() when already finished is a no-op.
        Sets the flag that should_cancel() polls."""
        ...

    def _create_progress(self) -> QtProgressReporter:
        """Factory so tests can inject a custom reporter (e.g. sync reporter
        avoiding cross-thread registration). Created in __init__ so that
        cancel() before run() has a target for the cancellation flag."""
        return QtProgressReporter()
```

## Cross-thread signal safety

`GenerationResult` and `DurationEstimate` are custom `@dataclass` types used as `Signal()` payloads across threads. PySide6 requires custom meta-types to be registered for cross-thread emission. Registration MUST happen at module level in `workers.py` using the PySide6 `QMetaType` API:

```python
# NOTE: The exact QMetaType API call must be verified against PySide6 6.7.3
# during implementation. T-012 found that qRegisterMetaType (PyQt5 API) does
# not exist in PySide6. This example uses QMetaType.registerType() as a
# starting point — adjust based on actual PySide6 6.7.3 introspection.

# from PySide6.QtCore import QMetaType
# QMetaType.registerType("GenerationResult")   # verify API signature
# QMetaType.registerType("DurationEstimate")   # verify API signature
```

## Threading model

```
UI Thread:     MainWindow (responsive during generation)
                   │ connects signals from worker
                   │ worker.moveToThread(worker_thread)
                   │ worker_thread.started → worker.run()
Worker thread:  GenerationWorker.run()
                   │ creates QtProgressReporter
                   │ Orchestrator.generate(spec, output_dir, txn, reporter)
                   │     polls reporter.should_cancel() between stages
                   │     → GenerationResult
                   │ emits finished(GenerationResult)
```

The worker owns the `QtProgressReporter` instance and uses it as the `progress` argument to `Orchestrator.generate()`. The worker maps `QtProgressReporter` signals to its own `progress`/`log`/`error` signals for the MainWindow to consume.

### Cancellation flow

```
UI Thread call:  worker.cancel()
                     │ sets QtProgressReporter._cancelled Event
                     │
Worker thread:   orchestrator.generate()
                     │ for each stage:
                     │     if progress.should_cancel() → True:
                     │         txn.rollback()
                     │         return GenerationResult(success=False, error="Cancelled")
```

**Important**: The orchestrator's `generate()` method MUST poll `progress.should_cancel()` between stages to make cancellation responsive. This requires a small modification to `src/forge/generation/orchestrator.py` — add a `should_cancel()` check between each stage iteration in the `generate()` loop. Without this, cancellation only works within `PluginExecutionEngine` (stage 3).

## Orchestrator modification

Add a `should_cancel()` check in `Orchestrator.generate()` in `src/forge/generation/orchestrator.py` between each stage:

```python
for stage in self._stages:
    if progress.should_cancel():
        txn.rollback()
        return GenerationResult(success=False, error="Cancelled", output_path=None)
    stage.run(spec, output_dir, txn, progress)
```

This is the only orchestrator change needed. The cancellation check is placed before each stage's `run()` call. Stages that are already executing are not interrupted — the check is cooperative polling at stage boundaries.

## Testing Infrastructure

### Test markers

Tests that require a `QThread` and `QApplication` MUST use the existing `@pytest.mark.gui` marker. Tests that only test `QtProgressReporter` signal emission (same-thread, no QThread needed) may omit the marker.

### Threaded worker fixture

AC-8 (cancellation) requires a `QThread` lifecycle. Use this fixture pattern:

```python
@pytest.fixture
def threaded_worker(qapp, mock_orchestrator, txn, output_dir, spec):
    worker = GenerationWorker(mock_orchestrator, spec, output_dir, txn=txn)
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    yield worker, thread
    if thread.isRunning():
        thread.quit()
        thread.wait(2000)
```

The `mock_orchestrator` must have its `generate()` configured with a `side_effect` that
simulates stage execution and polls `should_cancel()`. Two patterns:

```python
# Success path (AC-1):
mock_orchestrator.generate.return_value = GenerationResult(
    success=True, error=None, output_path=output_dir,
)

# Cancellation test (AC-8): simulate stage execution with polling
def _generate_with_polling(spec, output_dir, txn, progress, **kw):
    for _ in range(3):
        time.sleep(0.01)
        if progress.should_cancel():
            if hasattr(txn, 'rollback'):
                txn.rollback()
            return GenerationResult(False, "Cancelled", None)
    return GenerationResult(True, None, output_dir)

mock_orchestrator.generate.side_effect = _generate_with_polling
```

### Existing infrastructure

**Fixture scope note**: `mock_orchestrator` is currently defined in `tests/unit/test_main_window.py:19-26` — it is NOT accessible from `test_workers.py`. Either:
- Move it to `tests/unit/conftest.py` (recommended — will be needed by all future UI test files)
- Or define an equivalent fixture at the top of `test_workers.py`

**MockTransaction gap**: `MockTransaction` in `_shared.py` provides `stage_file()`, `stage_directory()`, and `add_checkpoint()` but lacks `rollback()` and `commit()`. AC-1 and AC-10 require `txn.rollback()`. Either:
- Add `rollback()` and `commit()` stub methods to `MockTransaction` (recommended — 3-minute change, needed for all future orchestration tests)
- Or use `MagicMock(spec=GenerationTransaction)` in cancellation tests

| Resource | Location | Status |
|----------|----------|--------|
| `qapp` fixture | `tests/unit/conftest.py:28-32` | ✅ Session-scoped QApplication |
| `QSignalSpy` / `QTest` | PySide6 built-ins | ✅ `spy.count()` / `spy.at(i)` pattern |
| `mock_orchestrator` | Test-file-local (`test_main_window.py`) | ⚠️ Move to conftest.py for cross-file access |
| `MockTransaction` | `tests/unit/_shared.py:16-35` | ⚠️ Needs `rollback()` / `commit()` stubs |
| `gui` marker | `pyproject.toml:44-46` | ✅ `@pytest.mark.gui` |
| `ProgressReporter` protocol | `src/forge/generation/progress.py:7-15` | ✅ `@runtime_checkable` |
| `GenerationResult` | `src/forge/generation/orchestrator.py:24-28` | ✅ `@dataclass` |
| `DurationEstimate` | `src/forge/domain/generated_file.py` | ✅ `@dataclass` |

## Acceptance Criteria

### Happy Path

1. **Given** generation completes successfully, **when** `run()` returns, **then** `finished` signal is emitted with `success=True` and `output_path` matches the target directory.

2. **Given** `QtProgressReporter.on_stage_start("stages", 3)` is called (same-thread, no QThread needed), **when** the signal is emitted, **then** a connected slot receives `("stages", 3)`.

3. **Given** `QtProgressReporter.on_step_complete("init")` is called, **when** the signal is emitted, **then** `step_completed` signal is received with `("init",)`.

4. **Given** `QtProgressReporter.on_stage_complete("init")` is called, **when** the signal is emitted, **then** `stage_completed` signal is received with `("init",)`.

5. **Given** `QtProgressReporter.on_log("building...", "info")` is called, **when** the signal is emitted, **then** `log_message` signal is received with `("building...", "info")`.

6. **Given** `QtProgressReporter.on_duration_estimate(DurationEstimate(30, True, ["npm"]))` is called, **when** the signal is emitted, **then** `duration_estimated` signal is received with a `DurationEstimate` matching `estimated_seconds=30`.

7. **Given** a `QtProgressReporter` instance, **when** checked with `isinstance(reporter, ProgressReporter)`, **then** the result is `True` (confirming structural protocol conformance, requires `@runtime_checkable`).

### Error Cases

8. **Given** a `GenerationWorker` running on a QThread, **when** the UI thread calls `.cancel()` and the orchestrator polls `should_cancel()` between stages, **then** the worker stops, `finished` signal is emitted with `success=False`, and `txn.rollback()` is called.

9. **Given** `QtProgressReporter.on_error(ValueError("config err"), True)` is called, **when** the signal is emitted, **then** `error_occurred` signal is received with `("config err", True)` (verify `str(error)` conversion, not `==` on Exception objects).

10. **Given** generation fails mid-stage with an exception, **when** `run()` catches it, **then** `finished` signal is emitted with `success=False`, `error` contains the exception message, and `txn.rollback()` is called.

11. **Given** `cancel()` is called **before** `run()` is invoked, **then** `finished` signal is NOT emitted (no-op; worker was never started).

### Edge Cases

12. **Given** `cancel()` is called **after** `finished` is already emitted, **then** `finished` is not emitted again (idempotent no-op).

13. **Given** `cancel()` is called **multiple times** during generation, **then** `finished` is emitted exactly once.

14. **Given** `QtProgressReporter.on_stage_start("", 0)` is called (empty name, zero steps), **then** no exception is raised and the signal is emitted correctly.

15. **Given** a `QtProgressReporter` instance, **when** `should_cancel()` is called **before** any `cancel()`, **then** it returns `False`. **When** called **after** `cancel()`, **then** it returns `True`.

### Protocol Completeness

| Protocol Method | AC(s) | Covered |
|----------------|-------|---------|
| `on_stage_start` | 2, 14 | ✅ |
| `on_step_complete` | 3 | ✅ |
| `on_stage_complete` | 4 | ✅ |
| `on_log` | 5 | ✅ |
| `on_error` | 9 | ✅ |
| `on_duration_estimate` | 6 | ✅ |
| `should_cancel` | 8, 15 | ✅ |
| `isinstance(Protocol)` | 7 | ✅ |

All 7 protocol methods have AC coverage plus missing-method detection via `isinstance` (AC-7). Coverage spans happy path (1–7), error cases (8–11), edge cases (12–15), and structural conformance (7).

## Implementation Deviations

The following deviations from the spec were discovered during implementation:

1. **`progress` parameter added to `GenerationWorker.__init__`** — Required by AC-15 test to share the same `_cancelled` Event between worker and reporter fixture. Spec had `txn` only; implementation added `progress: QtProgressReporter | None = None`.

2. **No `QMetaType` registration needed** — PySide6 6.7.3 auto-registers custom dataclass types (`DurationEstimate`, `GenerationResult`) for cross-thread signals. Manual `QMetaType.registerType()` is not required — signals work without it.

3. **`Qt.DirectConnection` for `thread.quit()`** — Threaded tests (AC-8, AC-13) must use `Qt.DirectConnection` when connecting `worker.finished → thread.quit`. `AutoConnection` (default) deadlocks because `QThread.wait()` blocks the calling thread's event loop, preventing delivery of queued signals.

4. **`set_cancelled()` public method added to `QtProgressReporter`** — Added to avoid direct private-attribute access (`_cancelled.set()`) from `GenerationWorker.cancel()`. Not in the original spec but recommended by code review for encapsulation.

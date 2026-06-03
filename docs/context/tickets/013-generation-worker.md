# T-013: GenerationWorker (QThread) + QtProgressReporter

- **type**: task
- **complexity**: medium
- **layer**: `ui/`
- **dependencies**: T-003, T-007, T-012
- **phase**: 3 — GUI Layer
- **estimated_context**: ~30% of window

## Description

Create `GenerationWorker` — a QObject that runs `Orchestrator.generate()` on a `QThread` to prevent UI freezing — and `QtProgressReporter` that translates `ProgressReporter` calls into Qt signals.

## Files to create

- `src/forge/ui/workers.py`

## API Spec

```python
class QtProgressReporter(QObject):
    """ProgressReporter implementation that emits Qt signals."""
    stage_started = Signal(str, int)          # stage_name, total_steps
    step_completed = Signal(str)              # step_name
    stage_completed = Signal(str)             # stage_name
    log_message = Signal(str, str)            # message, level
    error_occurred = Signal(str, bool)        # error_message, recoverable
    duration_estimated = Signal(DurationEstimate)

    def on_stage_start(self, stage_name: str, total_steps: int) -> None: ...
    def on_step_complete(self, step_name: str) -> None: ...
    def on_stage_complete(self, stage_name: str) -> None: ...
    def on_log(self, message: str, level: str = "info") -> None: ...
    def on_error(self, error: Exception, recoverable: bool) -> None: ...
    def on_duration_estimate(self, estimate: DurationEstimate) -> None: ...

class GenerationWorker(QObject):
    """Runs orchestration on a background thread."""
    finished = Signal(GenerationResult)
    progress = Signal(str, int)               # stage_name, percent
    log = Signal(str, str)                    # message, level
    error = Signal(str)

    def __init__(self, orchestrator: Orchestrator, spec: ProjectSpec, output_dir: Path): ...
    def run(self) -> None: ...
    def cancel(self) -> None: ...
```

## Threading model

```
UI Thread:     MainWindow (responsive during generation)
                   │ connects signals from worker
QThread:       GenerationWorker.run()
                   │ Orchestrator.generate(spec, output_dir, QtProgressReporter)
```

The worker owns the `QtProgressReporter` instance and maps its signals to its own signals for the MainWindow to consume.

## Acceptance Criteria

1. **Given** a `GenerationWorker` running on a QThread, **when** the UI thread calls `.cancel()`, **then** the worker stops and `finished` signal is emitted with `success=False`.
2. **Given** generation completes successfully, **when** `run()` returns, **then** `finished` signal is emitted with `success=True` and the `output_path`.
3. **Given** `QtProgressReporter.on_stage_start("stages", 3)` is called, **when** the signal is emitted, **then** a connected slot receives `("stages", 3)`.
4. **Given** generation fails mid-stage, **when** `on_error()` is called, **then** `error_occurred` signal is emitted with the exception message.

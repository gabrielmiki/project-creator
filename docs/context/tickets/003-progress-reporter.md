# T-003: ProgressReporter Protocol + Implementations

- **type**: task
- **complexity**: simple
- **layer**: `generation/`
- **dependencies**: None
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~15% of window

## Description

Create the `ProgressReporter` abstract protocol and two initial implementations: `StdoutProgressReporter` (CLI) and `MockProgressReporter` (tests). The Qt implementation comes later in T-013.

## Files to create

- `src/forge/generation/progress.py`

## API Spec

```python
class ProgressReporter(Protocol):
    def on_stage_start(self, stage_name: str, total_steps: int) -> None: ...
    def on_step_complete(self, step_name: str) -> None: ...
    def on_stage_complete(self, stage_name: str) -> None: ...
    def on_log(self, message: str, level: str = "info") -> None: ...
    def on_error(self, error: Exception, recoverable: bool) -> None: ...
    def on_duration_estimate(self, estimate: DurationEstimate) -> None: ...

class StdoutProgressReporter:
    """Writes progress to terminal. Used in CLI/headless mode."""
    ...

class MockProgressReporter:
    """Collects calls for test assertions.
    Provides: .calls: list[tuple[str, ...]] for asserting on call order.
    """
    ...
```

## Acceptance Criteria

1. **Given** `StdoutProgressReporter`, **when** `generate()` runs through 3 stages, **then** each `on_stage_start` / `on_step_complete` pair is printed to stdout with the stage name.
2. **Given** `MockProgressReporter`, **when** a generation sequence calls `on_stage_start("init",1)`, `on_step_complete("mkdir")`, **then** `.calls` contains `[("on_stage_start", "init", 1), ("on_step_complete", "mkdir")]`.
3. **Given** `ProgressReporter` is a `Protocol`, **when** checked with `isinstance(stdout_reporter, ProgressReporter)`, **then** it returns `True` (structural subtyping).

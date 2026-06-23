# Post-Mortem: T-013 GenerationWorker (QThread) + QtProgressReporter

**Date:** June 23, 2026
**Status:** ✅ IMPLEMENTED (all 15 ACs passing — 377/377 tests green)
**Review Status:** APPROVE (code review — 0 blocking, 4 non-blocking action items)

---

## 1. Overview

### Original Ticket

**Title:** GenerationWorker + QtProgressReporter — Create `GenerationWorker` — a QObject that runs `Orchestrator.generate()` on a `QThread` to prevent UI freezing — and `QtProgressReporter` that translates `ProgressReporter` calls into Qt signals.

**Original Acceptance Criteria (4 ACs, well-intentioned but incomplete):**

```
AC-01: Cancel → finished(success=False)
AC-02: Success → finished(success=True)
AC-03: on_stage_start("stages", 3) → signal received
AC-04: on_error() → error_occurred signal emitted
```

**Original API Spec:**

```python
class QtProgressReporter(QObject):
    stage_started = Signal(str, int)
    step_completed = Signal(str)
    stage_completed = Signal(str)
    log_message = Signal(str, str)
    error_occurred = Signal(str, bool)
    duration_estimated = Signal(DurationEstimate)

    def on_stage_start(...): ...
    def on_step_complete(...): ...
    def on_stage_complete(...): ...
    def on_log(...): ...
    def on_error(...): ...
    def on_duration_estimate(...): ...

class GenerationWorker(QObject):
    finished = Signal(GenerationResult)
    progress = Signal(str, int)
    log = Signal(str, str)
    error = Signal(str)

    def __init__(self, orchestrator, spec, output_dir): ...
    def run(self): ...
    def cancel(self): ...
```

**Files specified:**
- `src/forge/ui/workers.py`

### Refined Acceptance Criteria (15 ACs after 2 TDD review rounds)

```
Happy path:
  AC-01: Success → finished(success=True) + output_path
  AC-02: on_stage_start("stages", 3) → stage_started("stages", 3)
  AC-03: on_step_complete("init") → step_completed("init")
  AC-04: on_stage_complete("init") → stage_completed("init")
  AC-05: on_log("building...", "info") → log_message("building...", "info")
  AC-06: on_duration_estimate → duration_estimated with estimated_seconds=30
  AC-07: isinstance(reporter, ProgressReporter) → True

Error cases:
  AC-08: Cancel during generation → finished(success=False) + rollback
  AC-09: on_error → error_occurred with str(error) conversion
  AC-10: Exception in run() → finished(success=False) + rollback
  AC-11: cancel() before run() → finished NOT emitted

Edge cases:
  AC-12: cancel() after finished → idempotent (no re-emission)
  AC-13: Multiple cancel() → finished emitted exactly once
  AC-14: on_stage_start("", 0) → no exception, signal emitted
  AC-15: should_cancel() before/after cancel() → False/True
```

### What Happened

The ticket went through 2 TDD review rounds. Round 1 (NEEDS_REVISION) identified 4 blocking issues — the primary problems were: `should_cancel()` missing from QtProgressReporter (protocol contract violation), `txn` parameter absent from generation flow (would crash at runtime), cancellation semantics unrealistic (orchestrator doesn't poll `should_cancel()`), and cross-thread signal safety unspecified (would silently fail in production). Round 2 (PASS_WITH_MINOR_FIXES) confirmed all 4 blocking issues resolved, with 2 moderate and 5 low remaining issues. A fully-detailed specification with 15 acceptance criteria, protocol completeness matrix, API spec with imports and docstrings, threading model, cancellation flow, and testing infrastructure was produced. The ticket grew from 65 lines to 316 lines.

---

## 2. Problems Identified

### TDD Review Round 1 — NEEDS REVISION (4 blocking + 5 moderate + 4 low issues)

The initial 4 ACs assumed Qt threading and signal mechanics were straightforward, missing several critical architectural constraints from prior tickets.

#### Blocking Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| `should_cancel()` missing from QtProgressReporter | **Blocking** | ProgressReporter protocol has 7 methods; API spec defined only 6. Structural subtyping (`isinstance`) would return False at runtime. Protocol contract violation — the handoff from T-003 explicitly warned: "Qt inheritance prevents common ABC, all 7 methods must be implemented." |
| `txn` (GenerationTransaction) absent from threading model and worker spec | **Blocking** | `Orchestrator.generate()` signature requires `txn` as a required positional parameter between `output_dir` and `progress` (T-007 implementation). The threading diagram showed `Orchestrator.generate(spec, output_dir, QtProgressReporter)` — missing `txn`. Worker had no mechanism to create or receive a transaction. |
| AC-1 cancellation semantics unrealistic | **Blocking** | T-007 handoff explicitly states: "orchestrator does NOT handle cancellation between stages" and "there is no orchestrator-level should_cancel() check between stages — cancellation deferred." Calling `.cancel()` would not interrupt stage execution. |
| Cross-thread signal meta-type registration unspecified | **Blocking** | Two signals use custom dataclass types (`DurationEstimate`, `GenerationResult`) across threads. T-012 post-mortem explicitly says: "qRegisterMetaType is PyQt5 API — absent in PySide6 6.7.3. Cross-thread registration deferred to T-013 using QMetaType API." Without registration, signals silently fail in production. |

#### Moderate Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| 4 of 7 protocol methods have zero AC coverage | **Moderate** | Only `on_stage_start` (AC-3) and `on_error` (AC-4) were covered. `on_step_complete`, `on_stage_complete`, `on_log`, `on_duration_estimate`, and `should_cancel` had no tests. |
| No AC for `should_cancel()` thread-safety or behavior | **Moderate** | Cancellation is central to AC-1, but there's no AC verifying that `should_cancel()` returns `True` after `cancel()` is called. |
| No edge cases for cancellation lifecycle | **Moderate** | Missing: cancel-before-run, cancel-after-finished, multiple-cancel. |
| `GenerationWorker.run()` needs `@Slot()` decoration | **Moderate** | While PySide6 doesn't strictly require `@Slot()` for this pattern, T-012 establishes following PySide6 best practices. Missing `@Slot()` may produce warnings. |
| No test marker strategy specified | **Moderate** | Workers tests may or may not need a display; the existing `@pytest.mark.gui` marker needs guidance on when to apply. |

#### Low Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| Threading diagram imprecise | **Low** | "QThread: GenerationWorker.run()" implies QThread subclassing, not the `moveToThread()` pattern. |
| `cancel()` return type / idempotency undocumented | **Low** | No documentation on whether cancel is idempotent or what happens when called after finished. |
| `DurationEstimate` import path missing from API spec | **Low** | `DurationEstimate` used in `Signal(DurationEstimate)` without showing import. |
| No AC for protocol structural subtyping (isinstance) | **Low** | T-003's AC-3 tests `isinstance(reporter, ProgressReporter)` — the Qt variant should have the same test. |

---

### TDD Review Round 2 — PASS_WITH_MINOR_FIXES (0 blocking + 2 moderate + 5 low issues)

After fixing all Round 1 issues, the re-review confirmed all 4 blocking issues resolved. 15 ACs are individually testable. The protocol matrix is complete.

#### Moderate Issues (remaining)

| Issue | Severity | Problem | Resolution |
|-------|----------|---------|------------|
| `mock_orchestrator` fixture is test-file-local | **Moderate** | Defined in `test_main_window.py`, not in conftest — `test_workers.py` cannot access it. Will get `FixtureLookupError` at collection. | Move to conftest.py or document that test_workers.py must define its own. |
| `MockTransaction` lacks `rollback()` and `commit()` | **Moderate** | `_shared.py:16-35` provides `stage_file()`/`stage_directory()`/`add_checkpoint()` but no `rollback()`/`commit()`. AC-8 and AC-10 require `txn.rollback()`. | Add stub methods or use `MagicMock(spec=GenerationTransaction)`. |

#### Low Issues (remaining)

| Issue | Severity | Problem | Resolution |
|-------|----------|---------|------------|
| AC-11 cancel-before-run mechanism underspecified | **Low** | If `QtProgressReporter` is created inside `run()`, a `cancel()` before `run()` has no flag to set. | Added `_create_progress()` factory + note in `run()` docstring. |
| `threaded_worker` fixture references non-existent `mock_txn` | **Low** | Fixture parameter `mock_txn` doesn't exist — conftest has `txn`. | Renamed to `txn` in final fixture. |
| AC-8 testing strategy not documented | **Low** | `mock_orchestrator` needs `side_effect` to simulate stage polling — not obvious. | Added `side_effect` example patterns. |
| `QMetaType.registerType()` API unverified | **Low** | Example code hardcodes syntax that may not exist in PySide6 6.7.3. | Changed to commented-out starting point with verification note. |
| AC-1 categorized under "Happy Path" but describes `success=False` | **Low** | Cancellation is an error case, not happy path. | Moved to Error Cases section. |

---

## 3. Fixes Applied

### A. Added `should_cancel()` to QtProgressReporter (B-001)

**Before:** 6 methods defined — missing `should_cancel()`. `isinstance(reporter, ProgressReporter)` would return `False`.

**After (FIXED):** Full 7-method implementation with `threading.Event`:

```python
def __init__(self) -> None:
    super().__init__()
    self._cancelled = Event()

def should_cancel(self) -> bool:
    """Returns True when cancel() has been called on the worker."""
    return self._cancelled.is_set()
```

The `Worker.cancel()` method sets this event, and the orchestrator polls it between stages. This provides thread-safe cancellation without Qt primitives.

### B. Added `txn` Parameter to GenerationWorker Constructor (B-002)

**Before:** `__init__(self, orchestrator, spec, output_dir)` — no way to inject `GenerationTransaction`. Threading diagram showed `Orchestrator.generate(spec, output_dir, QtProgressReporter)` — missing `txn` parameter.

**After (FIXED):**

```python
def __init__(
    self,
    orchestrator: Orchestrator,
    spec: ProjectSpec,
    output_dir: Path,
    txn: GenerationTransaction | None = None,
) -> None: ...
```

When `txn` is `None`, the worker creates `GenerationTransaction(output_dir)` internally. Tests inject `MockTransaction` or `MagicMock(spec=GenerationTransaction)`. Added a Layer Rule Note section documenting the explicit exception to "UI never imports from infrastructure" — the worker is the I/O orchestration boundary.

### C. Added Orchestrator `should_cancel()` Polling Between Stages (B-003)

**Before:** AC-1 assumed cancellation was instantaneous — but the orchestrator never polls `should_cancel()` between stages. Cancellation only worked within `PluginExecutionEngine` (stage 3).

**After (FIXED):** Added "Orchestrator modification" section specifying a small change to `src/forge/generation/orchestrator.py`:

```python
for stage in self._stages:
    if progress.should_cancel():
        txn.rollback()
        return GenerationResult(success=False, error="Cancelled", output_path=None)
    stage.run(spec, output_dir, txn, progress)
```

This is backward-compatible with all 361 existing tests because the `progress` fixture in `conftest.py` returns a `MagicMock` with `should_cancel.return_value = False`. The polling check is a no-op in all existing tests.

### D. Added Cross-Thread Signal Safety Section (B-004)

**Before:** No meta-type registration specified. `DurationEstimate` and `GenerationResult` signals would silently fail across threads.

**After (FIXED):** Added "Cross-thread signal safety" section with `QMetaType` registration guidance. The code example uses commented-out starting-point syntax pending PySide6 6.7.3 verification, noting that T-012 found `qRegisterMetaType` is a PyQt5 API absent in PySide6.

### E. Expanded AC Coverage from 4 → 15 (M-001, M-002, M-003, L-004)

**Before (4 ACs):** Only 2 of 7 protocol methods tested. Zero error cases beyond cancellation. Zero edge cases.

**After (15 ACs):**

| Category | ACs | What's tested |
|----------|-----|---------------|
| Happy Path | 1–7 | Success emission, all 6 signal types (stage_start, step_complete, stage_complete, log, duration_estimate), isinstance protocol check |
| Error Cases | 8–11 | Cancel during generation, on_error with str conversion, exception rollback, cancel-before-run |
| Edge Cases | 12–15 | Cancel-after-finished idempotency, multiple-cancel, empty/zero inputs, should_cancel lifecycle |

Protocol completeness matrix added:

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

### F. Added `@Slot()` Decorator and `_create_progress()` Factory (M-004, L-001)

**Before:** `def run(self) -> None: ...` — no `@Slot()`. No factory method for progress reporter. Cancel-before-run mechanism underspecified.

**After (FIXED):** `@Slot()` decorator on `run()`. Added `_create_progress()` factory method so tests can inject a custom reporter (e.g., a sync reporter avoiding cross-thread registration). `run()` docstring explicitly states: "Must check cancellation flag before starting to support cancel-before-run (AC-11)."

### G. Specified Test Marker Strategy (M-005)

**Before:** No guidance on which tests need `@pytest.mark.gui`.

**After (FIXED):** Tests requiring `QThread` + `QApplication` (AC-8, AC-13) use `@pytest.mark.gui`. Same-thread signal tests (AC-2 through AC-7, AC-9, AC-14, AC-15) omit the marker.

### H. Fixed Threading Diagram Language (L-001)

**Before:** `QThread: GenerationWorker.run()` — implied QThread subclassing.

**After (FIXED):** `Worker thread: GenerationWorker.run()` with explicit `worker.moveToThread(worker_thread)` and `worker_thread.started → worker.run()` in the diagram.

### I. Documented `cancel()` Idempotency (L-002)

**Before:** `def cancel(self) -> None: ...` — no documentation.

**After (FIXED):** Docstring: "Request cancellation. Idempotent — safe to call multiple times. Calling cancel() when already finished is a no-op. Sets the flag that should_cancel() polls."

### J. Added Full Imports to API Spec (L-003)

**Before:** `DurationEstimate` used without import. `Orchestrator` import path unknown.

**After (FIXED):** Complete imports shown:
```python
from forge.domain import DurationEstimate
from forge.generation.orchestrator import GenerationResult, Orchestrator
from forge.domain.project_spec import ProjectSpec
from forge.infrastructure.transaction import GenerationTransaction
```

### K. Updated Infrastructure Table with Notes (Round 2 M-001, M-002)

**Before:** Table claimed `mock_orchestrator` location as `tests/unit/test_main_window.py:19-26` with ✅ and `MockTransaction` status as ✅ for txn injection.

**After (FIXED):** Table updated with ⚠️ status for both resources. Fixture scope note documents the conftest.py relocation need. MockTransaction gap note documents missing `rollback()`/`commit()` with recommended fix (add stub methods).

### L. Fixed `threaded_worker` Fixture Parameter (Round 2 L-002)

**Before:** `def threaded_worker(qapp, mock_orchestrator, mock_txn, output_dir, spec):` — `mock_txn` doesn't exist.

**After (FIXED):** `def threaded_worker(qapp, mock_orchestrator, txn, output_dir, spec):` — matches conftest.py's `txn` fixture.

### M. Added `side_effect` Example Patterns (Round 2 L-003)

**Before:** No guidance on how to simulate orchestrator stage execution for cancellation testing. `mock_orchestrator` is a `MagicMock` — it doesn't run stages or poll `should_cancel()`.

**After (FIXED):** Two complete `side_effect` patterns in the fixture section:
- Success path: `mock_orchestrator.generate.return_value = GenerationResult(success=True, ...)`
- Cancellation: `_generate_with_polling()` function that loops, polls `should_cancel()`, and returns accordingly

### N. Softened `QMetaType.registerType()` Example (Round 2 L-004)

**Before:** Hardcoded `QMetaType.registerType("GenerationResult")` as if the API is confirmed.

**After (FIXED):** Changed to commented-out starting-point syntax with verification note: "The exact QMetaType API call must be verified against PySide6 6.7.3 during implementation. T-012 found that qRegisterMetaType (PyQt5 API) does not exist in PySide6. This example uses QMetaType.registerType() as a starting point."

### O. Moved AC-1 to Error Cases (Round 2 L-005)

**Before:** AC-1 (cancel → success=False) listed under "Happy Path."

**After (FIXED):** AC-1 moved from Happy Path to Error Cases (renumbered as AC-8). All subsequent ACs renumbered accordingly. Protocol completeness table updated to match new numbering.

---

## 4. Technical Issues Found During Review & Implementation

### Dependency Analysis Discoveries (Pre-Implementation)

| Finding | Discovery Method |
|---------|-----------------|
| `should_cancel()` missing from QtProgressReporter | Cross-referencing API spec against `ProgressReporter` protocol in `progress.py:15` — 7 required methods, only 6 defined |
| `txn` parameter position between `output_dir` and `progress` | Reading `src/forge/generation/orchestrator.py:118-125` — `generate(spec, output_dir, txn, progress)` |
| Orchestrator does not poll `should_cancel()` | Reading `orchestrator.py` generate loop — no `should_cancel()` check between stages |
| `qRegisterMetaType` absent in PySide6 | T-012 post-mortem page 557: "qRegisterMetaType is PyQt5 API, not PySide6 6.7.3" |
| `mock_orchestrator` fixture is test-file-local | Reading `tests/unit/test_main_window.py:19-26` — defined inside test module, not conftest |
| `MockTransaction` lacks `rollback()`/`commit()` | Reading `tests/unit/_shared.py:16-35` — only stage_file, stage_directory, add_checkpoint |

### Implementation-Phase Discoveries

| Finding | Impact |
|---------|--------|
| PySide6 6.7.3 auto-registers custom dataclass types for cross-thread signals | `QMetaType.registerType()` not needed — omitted from production code. No regressions. |
| `QThread.wait()` blocks calling thread's event loop | `Qt.DirectConnection` required for `worker.finished → thread.quit` in threaded tests — `AutoConnection` deadlocks. |
| AC-15 requires same `_cancelled` Event in worker and reporter | Added `progress: QtProgressReporter | None = None` to `__init__` — not in original spec but required for testability. |
| Code review found `_cancelled.set()` via private attribute | Added `set_cancelled()` public method to `QtProgressReporter`. |
| Code review found `GenerationTransaction()` constructed before `try` | Moved inside `try` block to prevent orphan transaction on construction exception. |
| Duplicated `_generate_with_polling` in AC-8 and AC-13 | Extracted to `_make_polling_side_effect()` module-level factory. |

### Spec-Phase Only Achievement

- **4 blocking issues in Round 1** — all structural: protocol compliance, API signature mismatch, missing orchestrator mechanism, cross-thread safety
- **7 issues resolved in Round 2** — all 4 blocking cleared, 2 moderate + 5 low remaining
- **Zero structural issues in the original intent** — the QtProgressReporter concept, GenerationWorker design, and threading model were architecturally sound; the gaps were in completeness and cross-referencing against existing code
- **All 15 ACs independently testable** — no AC depends on infrastructure that doesn't exist yet

---

## 5. Final Specification

### Files Created

```
src/forge/ui/workers.py              # GenerationWorker + QtProgressReporter (99 lines)
tests/unit/test_workers.py           # 16 tests covering all 15 ACs (336 lines)
```

### Files Modified

```
src/forge/generation/orchestrator.py # Add should_cancel() polling between stages
tests/unit/conftest.py               # mock_orchestrator fixture moved here from test_main_window.py
tests/unit/_shared.py                # MockTransaction: added rollback() + commit() stubs
tests/unit/test_main_window.py       # Removed local mock_orchestrator fixture definition
```

### Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| `threading.Event` for cancellation | Thread-safe, no Qt primitives needed; `should_cancel()` is polled from worker thread, `cancel()` is called from UI thread |
| `txn` as optional constructor parameter | Tests inject `MockTransaction`/`MagicMock`; production creates real `GenerationTransaction(output_dir)` when None |
| `_create_progress()` factory method | Allows tests to inject a same-thread reporter avoiding cross-thread registration; created in `__init__` so `cancel()` before `run()` has a target |
| `QMetaType` registration NOT needed | PySide6 6.7.3 auto-registers custom dataclass types — verified during implementation, no code needed |
| `Qt.DirectConnection` for thread quit | `AutoConnection` deadlocks because `QThread.wait()` blocks the calling thread's event loop |
| AC-8 scanner exception documented | `ui/workers.py` must import `GenerationTransaction` from infrastructure — explicit documented exception to layer rule |
| Cooperative cancellation at stage boundaries | Stages already executing are not interrupted; `should_cancel()` is polled before each stage's `run()` call |

### Implementation Deviations from Spec

| Spec Item | Implemented As | Reason |
|-----------|---------------|--------|
| `__init__(orchestrator, spec, output_dir, txn=None)` | Added `progress: QtProgressReporter | None = None` | AC-15 requires shared `_cancelled` Event between worker and reporter |
| `QMetaType.registerType()` at module level | Omitted entirely | PySide6 6.7.3 auto-registers dataclass types; verified working without |
| `auto` connection for `finished → thread.quit` | `Qt.DirectConnection` required | `AutoConnection` deadlocks in threaded tests |
| `_cancelled.set()` in `cancel()` | `set_cancelled()` public method | Code review: avoid private-attribute access across classes |
| `GenerationTransaction()` outside `try` | Inside `try` block | Code review: prevent orphan transaction on construction exception |
| Inline `_generate_with_polling` in AC-8, AC-13 | `_make_polling_side_effect()` factory | Code review: eliminate duplicated code |

---

## 6. Test Coverage

### Test File

`tests/unit/test_workers.py` — **16 tests** across **14 test classes**:

| Class | Tests | Focus | AC Coverage |
|-------|-------|-------|-------------|
| `TestAC1_SuccessEmitsFinished` | 1 | finished(success=True, output_path) | AC-1 |
| `TestAC2_OnStageStartSignal` | 1 | stage_started("stages", 3) | AC-2 |
| `TestAC3_OnStepCompleteSignal` | 1 | step_completed("init") | AC-3 |
| `TestAC4_OnStageCompleteSignal` | 1 | stage_completed("init") | AC-4 |
| `TestAC5_OnLogSignal` | 1 | log_message("building...", "info") | AC-5 |
| `TestAC6_OnDurationEstimateSignal` | 1 | duration_estimated(estimated_seconds=30) | AC-6 |
| `TestAC7_IsInstanceProtocol` | 1 | isinstance(reporter, ProgressReporter) | AC-7 |
| `TestAC8_CancelDuringGeneration` | 1 | finished(success=False) + rollback | AC-8 |
| `TestAC9_OnErrorSignal` | 1 | error_occurred("config err", True) | AC-9 |
| `TestAC10_RunExceptionRollback` | 1 | finished(success=False, error) + rollback | AC-10 |
| `TestAC11_CancelBeforeRun` | 1 | finished NOT emitted | AC-11 |
| `TestAC12_CancelAfterFinished` | 1 | finished count unchanged | AC-12 |
| `TestAC13_MultipleCancel` | 1 | finished emitted exactly once | AC-13 |
| `TestAC14_EmptyInput` | 1 | on_stage_start("", 0) → no exception | AC-14 |
| `TestAC15_ShouldCancelLifecycle` | 2 | should_cancel() False/True | AC-15 |

### Test Helpers

| Helper | Purpose |
|--------|---------|
| `_make_polling_side_effect(mock_txn, output_dir)` | Factory for orchestrator `side_effect` simulating stage execution with `should_cancel()` polling |

### Test Infrastructure

- **Fixtures** (6 in test file + qapp from conftest.py):
  - `mock_orchestrator` — `MagicMock` with canned `generate.return_value` (moved from `test_main_window.py` to `tests/unit/conftest.py`)
  - `mock_txn` — `MagicMock(spec=["rollback", "commit", "stage_file", "stage_directory"])`
  - `output_dir` — `tmp_path / "output"`
  - `spec` — `MagicMock()`
  - `reporter` — `QtProgressReporter()` (lazy import from `forge.ui.workers`)
  - `worker` — `GenerationWorker(mock_orch, spec, output_dir, txn=mock_txn, progress=reporter)` (lazy import)

- **Markers**: `@pytest.mark.gui` on AC-8 and AC-13 (thread tests); no marker on same-thread signal tests

### Edge Case Coverage

| Edge Case | Test | AC |
|-----------|------|-----|
| `cancel()` before `run()` | `test_cancel_before_run_no_finished` | AC-11 |
| `cancel()` after finished | `test_cancel_after_finished_idempotent` | AC-12 |
| Multiple `cancel()` calls | `test_multiple_cancel_emits_finished_once` | AC-13 |
| Empty stage name + zero steps | `test_on_stage_start_empty_input` | AC-14 |
| `should_cancel()` lifecycle | `test_should_cancel_before/after` | AC-15 |
| Exception in `run()` | `test_run_exception_triggers_rollback` | AC-10 |

### Import Purity

Tests import from:
- `forge.domain.DurationEstimate` (domain layer — allowed)
- `forge.generation.orchestrator.GenerationResult` (generation layer — allowed for dataclass)
- `forge.generation.progress.ProgressReporter` (generation layer — allowed for isinstance check)

Tests do NOT import from:
- `forge.plugins` (plugin layer — not used)
- `forge.infrastructure` (infrastructure layer — mocked via MagicMock)
- `forge.ui.workers` (UI layer — this is the code under test, imported via lazy fixture)

---

## 7. Outstanding Issues

### Remaining

- [ ] LOW: No integration tests for this ticket — AC-8/AC-13 use `QThread` + `MagicMock` which validates the worker contract but not end-to-end generation
- [ ] LOW: `_make_polling_side_effect` hardcodes `10` iterations and `0.005` sleep — brittle against timing-sensitive failures on slower CI

### Resolved During Implementation

- [x] `mock_orchestrator` fixture moved from `test_main_window.py` to `tests/unit/conftest.py` ✅
- [x] `MockTransaction` in `_shared.py`: `rollback()` and `commit()` stub methods added ✅
- [x] `QMetaType.registerType()` verified against PySide6 6.7.3 — NOT needed, auto-registration works ✅
- [x] Orchestrator `should_cancel()` polling added to `orchestrator.py` — backward-compatible with 377 tests ✅

### Resolved During TDD Review

- [x] `should_cancel()` missing from QtProgressReporter → added with `threading.Event`
- [x] `txn` parameter missing from constructor → `txn: GenerationTransaction | None = None`
- [x] Orchestrator doesn't poll `should_cancel()` → orchestrator modification section added
- [x] Cross-thread signal safety unspecified → `QMetaType` registration section added
- [x] 4 of 7 protocol methods zero AC coverage → AC-4 through AC-7 added
- [x] No `should_cancel()` AC → AC-15 added
- [x] No cancellation edge cases → AC-11, AC-12, AC-13 added
- [x] `run()` missing `@Slot()` decorator → added
- [x] No test marker strategy → documented
- [x] Threading diagram imprecise → fixed `moveToThread` language
- [x] `cancel()` idempotency undocumented → docstring added
- [x] `DurationEstimate` import missing → added to API spec
- [x] No isinstance protocol AC → AC-7 added
- [x] `mock_orchestrator` fixture scope → documented as gap
- [x] `MockTransaction` lacks rollback/commit → documented as gap
- [x] `threaded_worker` fixture uses non-existent `mock_txn` → fixed to `txn`
- [x] No `side_effect` testing pattern → added fixture section
- [x] `QMetaType` hardcoded → softened to commented-out starting point
- [x] AC-1 categorized as "Happy Path" → moved to Error Cases

---

## 8. Lessons Learned

### What Went Well

1. **Cross-referencing against actual code caught all 4 blocking issues** — `should_cancel()` missing was found by reading `progress.py:15` (the protocol definition), `txn` parameter was found by reading `orchestrator.py:118-125`, cancellation deferral was found in the T-007 handoff, and `qRegisterMetaType` absence was documented in T-012's post-mortem. Every blocking issue was discovered by verifying the ticket against actual existing code, not by abstract reasoning.

2. **Two-pass TDD review found different issue depths** — Round 1 caught structural gaps (protocol compliance, API signatures, missing orchestrator mechanism, cross-thread safety). Round 2 caught integration gaps (fixture scope, mock completeness, test strategy, categorization). Each pass validated a different dimension.

3. **Protocol contract enforcement via structural subtyping worked as designed** — The `@runtime_checkable` ProgressReporter protocol forced `QtProgressReporter` to implement all 7 methods exactly. The absence of `should_cancel()` was immediately detectable as a protocol violation. This validates the T-003 decision to use `@runtime_checkable` over ABC.

4. **Prior ticket handoffs provided critical context** — The T-007 handoff explicitly documented "there is no orchestrator-level should_cancel() check between stages — cancellation deferred," and the T-012 post-mortem explicitly deferred `qRegisterMetaType` to this ticket. Reading the handoffs before the review would have caught these issues immediately.

5. **Layer rule exception documented upfront** — The "UI never imports from infrastructure" rule has an explicit exception for `workers.py` (the I/O orchestration boundary). Documenting this in the ticket prevents review confusion and ensures the AC-8 scanner test can be updated accordingly.

6. **15 ACs for 16 tests is clean density** — Each AC maps to 1-2 tests with no redundancy. The protocol completeness matrix (8 rows × 15 ACs) makes coverage gaps immediately visible. This is the cleanest AC-to-test mapping in the project so far.

7. **Cooperative cancellation design avoids thread-safety complexity** — Using `threading.Event` instead of `QAtomicInt` or `QMutex` keeps the cancellation mechanism simple and framework-agnostic. The `should_cancel()` protocol method was designed for this exact use case (T-003 post-mortem explicitly discussed thread-safety).

### What Could Improve

1. **First threading ticket should explicitly document QThread lifecycle** — The original ticket assumed "GenerationWorker runs on QThread" was sufficient. It should have documented `moveToThread()`, `started.connect()`, `finished.connect(thread.quit)`, and thread cleanup. The "Threading model" section was largely rewritten in Round 2.

2. **Cross-thread signal requirements should be part of the UI ticket template** — Any ticket that creates `Signal(CustomType)` where `CustomType` is a dataclass must address meta-type registration. This is a PySide6-specific constraint that's easy to miss. Consider adding a "Cross-thread signal safety" checkbox to the UI ticket template.

3. **Fixture scope should be verified during spec review** — The `mock_orchestrator` fixture scope issue (test-file-local, not in conftest) was discovered in Round 2. Any spec that references a fixture from another test file should verify that fixture is importable. This is a cross-file dependency that spec review often misses.

4. **Cancellation semantics need explicit lifecycle states** — The original AC-1 assumed `cancel()` immediately stops generation. Real cancellation is cooperative (polling at stage boundaries). The ticket should define three states: (a) not started — cancel before `run()` starts, (b) running — polled at next stage boundary, (c) finished — idempotent no-op. Round 2 added AC-11 through AC-13 to cover these states.

5. **The `txn` parameter discovery was late** — The `Orchestrator.generate()` signature with `txn` was documented in T-007's handoff and post-mortem. If the T-007 handoff had been read before drafting T-013, the `txn` requirement would have been caught before the first review round.

6. **`QMetaType` API verification must happen during implementation, not spec** — The exact PySide6 6.7.3 API for custom type registration cannot be safely documented without running code against the installed version. The spec phase can only flag that it's needed and note the risk (as T-012's post-mortem did). Consider adding a "verify against installed PySide6" step to the implementation checklist.

7. **Cooperative cancellation means UI responsiveness is bounded** — Long-running stages (e.g., `npm install` via `CommandRunner`) cannot be interrupted mid-execution. Cancellation only takes effect at stage boundaries. The ticket doesn't document this latency bound — users may see a delay between clicking Cancel and the UI updating.

### Key Metrics

| Metric | Value |
|--------|-------|
| Original ACs | 4 |
| Refined ACs | 15 |
| TDD review rounds | 2 |
| Tests created | 16 |
| Blocking issues in Round 1 | 4 |
| Moderate + low in Round 1 | 9 |
| Moderate in Round 2 | 2 |
| Low in Round 2 | 5 |
| Issues requiring code changes | 0 (all spec-level) |
| Files to create (source) | 1 (`workers.py`) |
| Files to create (test) | 1 (`test_workers.py`) |
| Files to modify | 1 (`orchestrator.py`) |
| Protocol method coverage | 7/7 (100%) |
| New dependencies | 0 |
| Infrastructure changes needed | 2 (mock fixture move + MockTransaction stubs) |

---

## 9. Acceptance Criteria Verification

| AC | Test(s) | Verification Method | Spec Status | Impl Status |
|----|---------|---------------------|-------------|-------------|
| AC-1 | `test_success_emits_finished` | QSignalSpy on finished: count=1, success=True, output_path matches | ✅ Spec | ✅ 377/377 |
| AC-2 | `test_on_stage_start_signal` | QSignalSpy on stage_started: count=1, args ("stages", 3) | ✅ Spec | ✅ 377/377 |
| AC-3 | `test_on_step_complete_signal` | QSignalSpy on step_completed: count=1, args ("init",) | ✅ Spec | ✅ 377/377 |
| AC-4 | `test_on_stage_complete_signal` | QSignalSpy on stage_completed: count=1, args ("init",) | ✅ Spec | ✅ 377/377 |
| AC-5 | `test_on_log_signal` | QSignalSpy on log_message: count=1, args ("building...", "info") | ✅ Spec | ✅ 377/377 |
| AC-6 | `test_on_duration_estimate_signal` | QSignalSpy on duration_estimated: count=1, estimated_seconds=30 | ✅ Spec | ✅ 377/377 |
| AC-7 | `test_isinstance_protocol` | isinstance(reporter, ProgressReporter) → True | ✅ Spec | ✅ 377/377 |
| AC-8 | `test_cancel_during_generation` | QSignalSpy on finished: count=1, success=False, error="Cancelled", rollback called | ✅ Spec | ✅ 377/377 |
| AC-9 | `test_on_error_signal` | QSignalSpy on error_occurred: count=1, args ("config err", True) via str() | ✅ Spec | ✅ 377/377 |
| AC-10 | `test_run_exception_triggers_rollback` | QSignalSpy on finished: count=1, success=False, "boom" in error, rollback called | ✅ Spec | ✅ 377/377 |
| AC-11 | `test_cancel_before_run_no_finished` | QSignalSpy on finished: count=0; generate.assert_not_called() | ✅ Spec | ✅ 377/377 |
| AC-12 | `test_cancel_after_finished_idempotent` | QSignalSpy on finished: count=1 (unchanged after cancel) | ✅ Spec | ✅ 377/377 |
| AC-13 | `test_multiple_cancel_emits_finished_once` | QSignalSpy on finished: count=1 after 3× cancel | ✅ Spec | ✅ 377/377 |
| AC-14 | `test_on_stage_start_empty_input` | QSignalSpy on stage_started: count=1, args ("", 0), no exception | ✅ Spec | ✅ 377/377 |
| AC-15 | `test_should_cancel_lifecycle` | should_cancel() → False before cancel, True after cancel | ✅ Spec | ✅ 377/377 |

---

## 10. Timeline

| Date | Activity |
|------|----------|
| June 23, 2026 | Original ticket loaded (4 ACs, missing should_cancel, missing txn, no cross-thread safety) |
| June 23, 2026 | TDD review round 1 (NEEDS REVISION — 4 blocking + 5 moderate + 4 low issues) |
| June 23, 2026 | Fixed R1: added should_cancel() with threading.Event, added txn parameter, added orchestrator modification section, added cross-thread signal safety section, expanded to 15 ACs, added @Slot(), fixed threading diagram, added imports, added isinstance AC |
| June 23, 2026 | TDD review round 2 (PASS_WITH_MINOR_FIXES — 0 blocking + 2 moderate + 5 low issues) |
| June 23, 2026 | Fixed R2: documented fixture scope gap, documented MockTransaction gap, fixed fixture parameter, added side_effect patterns, softened QMetaType example, moved AC-1 to Error Cases |
| June 23, 2026 | Test file created: `tests/unit/test_workers.py` (16 tests, all fail with ModuleNotFoundError) |
| June 23, 2026 | Test-First Gate confirmed: 16/16 fail with "No module named 'forge.ui.workers'" (expected) |
| June 23, 2026 | Post-mortem written (spec phase) |
| June 23, 2026 | Implementation: workers.py + orchestrator.py changes + conftest/shared changes + test_workers.py passing |
| June 23, 2026 | Code review: APPROVE — 0 blocking, 4 non-blocking action items (3 code + 1 doc) |
| June 23, 2026 | Post-mortem updated (implementation phase) |

## 11. Final State

### Verification Summary

| Check | Result |
|-------|--------|
| Test-First Gate | ✅ 16/16 fail with expected ModuleNotFoundError |
| 16 workers tests | ✅ 16/16 passing |
| Full test suite | ✅ 377/377 passing (0 regressions) |
| ruff lint | ✅ clean on changed files |
| mypy typecheck | ✅ no issues in 40 source files |
| Code review verdict | ✅ APPROVE |
| Action items resolved | ✅ 3 code fixes (set_cancelled, txn in try, factory extraction) + 1 doc update (ticket + post-mortem) |

### T-013 is COMPLETE.

The GenerationWorker QThread implementation is done: all 15 acceptance criteria are passing, all code review action items are applied, and the post-mortem captures the full journey from 4 ACs → 15 ACs → 16 tests → 377/377 green.

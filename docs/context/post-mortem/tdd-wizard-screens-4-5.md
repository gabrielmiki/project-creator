# Post-Mortem: T-015 Wizard Screens 4–5 (Review Summary, Generation)

**Date:** June 24, 2026  
**Status:** ✅ COMPLETE  
**Review Status:** APPROVE (after 5 TDD review rounds + 2 implementation rounds + 1 bugfix round)

---

## 1. Overview

### Original Ticket

**Title:** Wizard Screens 4–5 (Review Summary, Generation)

**Original Acceptance Criteria (6 ACs, screen-level only):**

```
AC-01: ReviewScreen → tree view with display names + estimated duration
AC-02: ReviewScreen → warning label when estimate exceeds 10s
AC-03: GenerationScreen → on_progress updates stage label + progress bar
AC-04: GenerationScreen → on_log appends to log widget
AC-05: GenerationScreen → on_finished shows Open/Close, hides Cancel
AC-06: GenerationScreen → on_error shows Close, hides Cancel
```

**Files specified:**
- `src/forge/ui/screens/review_screen.py` — QTreeWidget summary of ProjectSpec
- `src/forge/ui/screens/generation_screen.py` — progress bar + log + duration
- `src/forge/ui/main_window.py` — overwrite confirm, worker wiring, button handlers
- `src/forge/ui/workers.py` — overwrite_confirmed param on GenerationWorker

**Implementation status:** All source files implemented, 31/31 tests passing, 436/436 full suite passing.

**Dependencies:** T-001, T-012, T-013, T-014

### Refined Acceptance Criteria (16 ACs after 5 TDD review rounds)

```
AC-01:  ReviewScreen QTreeWidget displays backend/frontend display names + estimate
AC-02:  ReviewScreen warning QLabel visible when estimate has slow steps
AC-03:  GenerationScreen on_progress updates stage label text + progress bar max
AC-04:  GenerationScreen on_log appends message to log widget
AC-05:  MainWindow _on_generation_finished → Cancel hidden, Open+Close visible (success)
AC-06:  MainWindow _on_generation_error → Close visible, Cancel+Open hidden
AC-07:  next_screen at index 3 skips dialog when output_dir does not exist
AC-08:  next_screen at index 3 proceeds when output_dir exists and user clicks Yes
AC-09:  next_screen at index 3 stays when user clicks No
AC-10:  next_screen at index 3 shows error on exception and stays
AC-11:  (implicit — verified by AC-03–AC-06 signal delivery)
AC-12:  GenerationScreen on_exit cancels worker when generating
AC-13:  GenerationScreen idle state shows Ready + 0% + empty log
AC-14:  Cancel button calls worker.cancel() and disables self
AC-15:  cancel_generation is idempotent after finished
AC-16:  Open Project calls QDesktopServices.openUrl(QUrl.fromLocalFile(...))
```

---

## 2. Problems Identified

### TDD Review Round 1 — NEEDS REVISION (8 blocking issues)

The initial ticket assumed screen-specific fields that don't exist in the domain model and provided no mechanism for assembling a ProjectSpec across the wizard's multi-screen workflow:

#### Blocking Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| `author` / `python_version` fields don't exist on `ProjectSpec` | **Blocking** | WelcomeScreen was spec'd to return `{"author": ..., "python_version": ...}` but `ProjectSpec` has only `project_name`, `template`, `domains`, `config` |
| No spec-assembly mechanism | **Blocking** | Ticket described collecting `get_spec_update()` from each screen but didn't specify how MainWindow assembles these into a ProjectSpec |
| No orchestrator reference in ReviewScreen | **Blocking** | ReviewScreen needs `estimate_duration()` but constructor had no orchestrator param |
| Missing navigation button wiring | **Blocking** | Open/Close buttons existed in footer but had no click handlers or visibility control |
| No generation worker creation flow | **Blocking** | next_screen() at index 3 had no mechanism to create GenerationWorker and start generation |
| No overwrite confirm dialog | **Blocking** | If output_dir exists, no confirm dialog was shown before overwriting |
| Missing lifecycle ACs | **Blocking** | No AC for on_exit cancellation, idle state, or proceed guard |
| Missing cancellation ACs | **Blocking** | No AC for Cancel button behavior during or after generation |

---

### TDD Review Round 2 — NEEDS REVISION (5 moderate + 4 low issues)

After fixing Round 1, the re-review found several wiring and implementation gaps:

#### Moderate Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| `_get_output_dir` type mismatch | **Moderate** | Method returned `Path` but code sample showed string concatenation |
| Missing spec injection at index 3 | **Moderate** | `navigate_to()` injected data at index 2 but not at index 3 for ReviewScreen |
| Retry button out of scope | **Moderate** | AC-06 mentioned a "Retry" button that is not in the MainWindow spec |
| `thread.start` never called | **Moderate** | Worker was created and wired but thread never started in `next_screen()` code |
| Cancel button never reconnected | **Moderate** | When navigating back to screen 4 after generation, Cancel reverted to `cancelled.emit` |

#### Low Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| AC-15 button limitation | **Low** | AC-15 says "Cancel is hidden on success per AC-05" — should clarify tested via direct call, not button click |
| `set_worker` docstring | **Low** | `"on_enter() connects signals"` — but screen is passive after Round 4 fix |
| GenerationTransaction text | **Low** | Overwrite flow referenced "forwarded to `Orchestrator.generate()` as a parameter, not via the transaction" — clear but verbose |
| TestAC6 migration | **Low** | Existing test must mock `Path.exists()` to bypass overwrite dialog |

---

### TDD Review Round 3 — NEEDS REVISION (4 blocking + 5 moderate + 5 low issues)

After fixing Round 2, the third review found deeper architectural gaps:

#### Blocking Issues

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| Open/Close buttons have no click handlers | **Blocking** | AC-16 requires Open Project → `QDesktopServices.openUrl`. Both `_open_btn` and `_close_btn` have zero signal connections | Add `_on_open_project()` and `_on_close()` handlers, wire in constructor |
| No button state transition for finished/error | **Blocking** | `_update_navigation_buttons()` unconditionally shows Cancel/Open/Close at index 4. AC-05/06 require Cancel hidden on success/error | Add `_generation_finished` flag, branch on gen state in `_update_navigation_buttons()` |
| AC-10 try/except not implemented in code sample | **Blocking** | Overwrite flow describes exception handling but `next_screen()` code doesn't wrap `output_dir.exists()` in try/except | Wrap `exists()` in try/except, call `show_error()` on failure |
| GenerationScreen `on_exit()` override missing | **Blocking** | AC-12 requires `worker.cancel()` on exit during generation, but no override documented | Add `on_exit()` that calls `worker.cancel()` when `_is_generating` |

#### Moderate Issues

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| Cancel button not disabled in `cancel_generation()` | **Moderate** | AC-14 requires Cancel disabled after click | Add `self._cancel_btn.setEnabled(False)` |
| `is_generating` undefined | **Moderate** | `navigate_to()` injection references `is_generating` but it's not defined | Add `_is_generating` flag + `@property` |
| Unguarded `disconnect()` | **Moderate** | `_cancel_btn.clicked.disconnect()` raises TypeError if no prior connection | Wrap in try/except TypeError |
| `overwrite_confirmed` param absent from workers.py | **Moderate** | Ticket specifies the param but code sample doesn't show it | Add `overwrite_confirmed: bool = False` to `GenerationWorker.__init__` |
| Thread lifecycle not documented for tests | **Moderate** | No guidance on QThread teardown in tests | Add QThread lifecycle note (quit/wait, prefer mock) |

#### Low Issues

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| Tree view widget type unspecified | **Low** | AC-01 says "tree view" — not clear if QTreeWidget or QTreeView | Specify `QTreeWidget` |
| Warning QLabel lacks objectName | **Low** | AC-02 references a QLabel but no objectName for test selection | Add `objectName="warning_label"` |
| `set_spec()` vs attribute injection inconsistent | **Low** | ReviewScreen uses `set_spec()` but ConfigurationScreen uses direct attribute set | Keep `set_spec()` for consistency |
| `estimate_duration` default missing | **Low** | Mock strategy doesn't specify default return value for `estimate_duration` | Add `DurationEstimate(5, False, [])` as default |
| AC-11 redundancy | **Low** | AC-11 tests signal connection but AC-03–AC-06 implicitly cover it | Annotate as implicit, not a standalone test |

---

### TDD Review Round 4 — NEEDS REVISION (1 blocking + 5 moderate + 4 low issues)

After fixing all Round 3 issues, the fourth review found one new architectural issue that required a design change:

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| **B-5: Double signal connection** | **Blocking** | GenerationScreen API spec says "connects to worker signals in `on_enter()`" BUT `_create_generation_worker()` also connects the same signals to MainWindow handlers which forward to `gen_screen.on_*()`. Every signal fires twice — progress counter doubles, log entries duplicate | Remove direct signal connections from GenerationScreen. MainWindow owns all signal routing. GenerationScreen provides passive `on_progress/on_log/on_error/on_finished` methods |

#### Moderate Issues

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| M-6: `on_enter()` body not shown | **Moderate** | API spec never shows the `on_enter()` implementation | Add full `on_enter()` with reset logic + passive method signatures |
| M-7: `_is_generating` lifecycle incomplete | **Moderate** | `_is_generating` is set in `set_worker()` but never reset on finished/error | Reset in both `on_finished()` and `on_error()` |
| M-8: Mock worker strategy contradictory | **Moderate** | `MagicMock(spec=GenerationWorker)` doesn't create real Signal objects for `.emit()` | Update strategy: test passive methods directly, no worker needed for screen-level tests |
| M-9: `Path.cwd()` environment-dependent | **Moderate** | `_get_output_dir()` uses `Path.cwd()` which varies by test runner | Document `monkeypatch.setattr(Path, "cwd", ...)` for tests |
| M-10: TestAC6 needs explicit migration | **Moderate** | Existing test needs Path.exists() mock — noted but easy to miss during implementation | Add both `Path.exists()` and `Path.cwd()` to migration note |

#### Low Issues

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| L-6: QTreeWidget lacks objectName | **Low** | Widget type is specified but no objectName for unambiguous test selection | Add `objectName="review_tree"` |
| L-7: AC-05/06 wording | **Low** | "Given a GenerationScreen" but assertions check MainWindow buttons | Fix to "Given a MainWindow at screen index 4" |
| L-8: Error state shows Open button | **Low** | On error, Open button is shown but is a no-op (output_path is None) | Hide Open when `_generation_output_path is None` |
| L-9: AC-16 uses `Path.as_uri()` but handler uses `QUrl.fromLocalFile()` | **Low** | AC text doesn't match handler implementation | Fix AC to say `QUrl.fromLocalFile(str(output_path))` |

---

### TDD Review Round 5 — NEEDS REVISION (3 moderate + 6 low issues)

After fixing all Round 4 issues and the passive-method redesign, the fifth review found remaining production-code concerns:

#### Moderate Issues

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| M-1: Dead error signal path | **Moderate** | `GenerationWorker.error = Signal(str)` is defined in workers.py but never emitted in `GenerationWorker.run()`. The wire in `_create_generation_worker()` will never fire | Either emit `error` from `run()` or document the dead wiring |
| M-2: Worker/thread resource leak | **Moderate** | `_on_generation_finished` and `_on_generation_error` never null out `self._worker`/`self._thread`. Repeated generation accumulates QObject references | Add cleanup in both handlers, or document as known limitation |
| M-3: Cancel button re-enable race | **Moderate** | `cancel_generation()` disables Cancel, but `_update_navigation_buttons()` during-gen branch unconditionally sets `setEnabled(True)`. Race condition if button state recalculates between cancel and termination | Guard `setEnabled(True)` with cancel-state check |

#### Low Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| L-1/L-2: Unspecified styling mechanisms | **Low** | AC-02 "red QLabel" — no mechanism specified (styleSheet? palette?); AC-06 "red-formatted error line" — no mechanism for QPlainTextEdit |
| L-3: `_pending_output_dir` without initialization | **Low** | `_on_generation_finished` sets `self._pending_output_dir = None` but attribute is never initialized |
| L-4: AC-05/06 "worker injected" wording vs mock strategy | **Low** | ACs say "with a worker injected" but mock strategy explicitly says "no worker needed" for direct handler tests |
| L-5: Cancel button disconnect only removes one slot | **Low** | `disconnect()` only removes one connection; multiple `navigate_to(4)` calls could accumulate slots |
| L-6: AC-11 contradicts passive pattern | **Low** | AC-11 says "screen connects to signals" but design says MainWindow owns connections |

---

## 3. Fixes Applied

### A. Removed Non-Existent Fields from WelcomeScreen (v1 B1)

**Before:** `WelcomeScreen.get_spec_update()` returned `{"project_name": ..., "author": ..., "python_version": ...}` — but `ProjectSpec` has no `author` or `python_version` fields.

**After (FIXED):** `WelcomeScreen` returns only `{"project_name": str}`. Confirmed via reading `src/forge/domain/project_spec.py`.

### B. Added `_build_spec()` Spec-Assembly Mechanism (v1 B2)

**Before:** `next_screen()` at index 3→4 created a hardcoded empty `ProjectSpec`.

**After (FIXED):** Introduced `_build_spec()` that iterates all 5 `QStackedWidget` pages, collects `get_spec_update()` from each `WizardScreen`, and merges them into a `ProjectSpec`.

### C. Added Orchestrator to ReviewScreen Constructor (v1 B3)

**Before:** `ReviewScreen.__init__()` took no arguments — couldn't call `estimate_duration()`.

**After (FIXED):** `ReviewScreen(orchestrator: Orchestrator)` — same pattern as `DomainSelectionScreen` and `ConfigurationScreen`.

### D. Wired Navigation Buttons + Generation Flow (v1 B4-B8)

Multiple blockages resolved in a single pass:
- Added `_on_open_project()` handler calling `QDesktopServices.openUrl(QUrl.fromLocalFile(...))`
- Added `_on_close()` handler calling `self.close()`
- Added `_create_generation_worker()` method creating `GenerationWorker` + `QThread` + signal plumbing
- Added overwrite confirm dialog in `next_screen()` at index 3
- Added ACs for cancellation, idle state, lifecycle, and button states (expanded from 6 to 16 ACs)

### E. Added Cross-Screen Injection at Index 3 (v2 M2)

**Before:** `navigate_to()` only injected data at index 2 (ConfigurationScreen).

**After (FIXED):**
```python
if index == 3:
    spec = self._build_spec()
    review_screen = self._stacked.widget(3)
    if hasattr(review_screen, "set_spec"):
        review_screen.set_spec(spec)
```

### F. Added `thread.start()` After Navigation (v2 M4)

**Before:** Worker was created and wired but `self._thread.start()` was missing.

**After (FIXED):** `self._thread.start()` called after `navigate_to(4)` to avoid signal race between worker completion and screen initialization.

### G. Cancel Button Reconnection in `navigate_to(index 4)` (v2 M5)

**Before:** Navigating to index 4 left Cancel connected to `cancelled.emit`.

**After (FIXED):** `navigate_to()` disconnects Cancel, then connects to `cancel_generation` if generating, or reconnects to `cancelled.emit` if idle/finished. Guarded with `try/except TypeError`.

### H. Full Signal Wiring for Open/Close Buttons (v3 B1)

**Before:** `_open_btn` and `_close_btn` existed in MainWindow footer but had no `clicked.connect()` calls.

**After (FIXED):**
```python
self._open_btn.clicked.connect(self._on_open_project)
self._close_btn.clicked.connect(self._on_close)
```

### I. Button State Matrix for Screen 4 (v3 B2)

**Before:** `_update_navigation_buttons()` showed Cancel/Open/Close unconditionally at index 4.

**After (FIXED):**
- During generation: Cancel visible+enabled, Open/Close hidden
- After success (output_path set): Cancel hidden, Open+Close visible+enabled
- After error (output_path None): Cancel hidden, Open hidden, Close visible

### J. try/except on `output_dir.exists()` (v3 B3)

**Before:** `next_screen()` called `output_dir.exists()` with no error handling.

**After (FIXED):**
```python
try:
    dir_exists = output_dir.exists()
except Exception as e:
    self.show_error("Error", f"Cannot check output directory: {e}")
    return
```

### K. GenerationScreen `on_exit()` + `is_generating` Property (v3 B4)

**Before:** `GenerationScreen` had no `on_exit()` override — base class `on_exit()` is a no-op.

**After (FIXED):**
```python
def on_exit(self) -> None:
    super().on_exit()
    if self._worker is not None and self._is_generating:
        self._worker.cancel()
        self._is_generating = False
```
Added `_is_generating` flag and `is_generating` property.

### L. Cancel Button Disabled After Cancel (v3 M1)

**Before:** `cancel_generation()` called `worker.cancel()` but didn't disable the button.

**After (FIXED):** `self._cancel_btn.setEnabled(False)` added after `worker.cancel()`.

### M. Guarded `disconnect()` with try/except (v3 M3)

**Before:** `_cancel_btn.clicked.disconnect()` raised `TypeError` on first call (no prior connection).

**After (FIXED):**
```python
try:
    self._cancel_btn.clicked.disconnect()
except TypeError:
    pass
```

### N. Added `overwrite_confirmed` Param to GenerationWorker (v3 M4)

**Before:** `GenerationWorker.__init__` had no `overwrite_confirmed` parameter.

**After (FIXED):** `overwrite_confirmed: bool = False` added to constructor, forwarded to `Orchestrator.generate()`.

### O. Added QThread Lifecycle Documentation (v3 M5)

**Before:** No guidance on how to clean up QThread in tests.

**After (FIXED):** Added documentation: call `thread.quit()` + `thread.wait(5000)` in teardown; prefer `MagicMock(spec=GenerationWorker)` for unit tests.

### P. Redesigned GenerationScreen as Passive Widget (v4 B5)

**Before (double signal routing):** GenerationScreen connected to worker signals in `on_enter()` AND MainWindow connected the same signals in `_create_generation_worker()` AND MainWindow forwarded to `gen_screen.on_*()` — triple processing.

**After (FIXED):** Removed all signal connections from GenerationScreen. It is now a passive display widget with methods:
- `on_progress(stage, total)` — called by MainWindow's progress handler
- `on_log(message, level)` — called by MainWindow's log handler
- `on_error(message)` — called by MainWindow's error handler, resets `_is_generating`
- `on_finished(result)` — called by MainWindow's finished handler, resets `_is_generating`

MainWindow owns all signal connections in `_create_generation_worker()` and forwards to the screen via `hasattr`-guarded calls.

### Q. Added `on_enter()` Body (v4 M6)

**Before:** `on_enter()` never shown in API spec.

**After (FIXED):** Full `on_enter()` documented — resets UI to idle state, resets `_is_generating` if no worker.

### R. Fixed `_is_generating` Lifecycle (v4 M7)

**Before:** `_is_generating` set in `set_worker()` but never reset on finished/error.

**After (FIXED):** Both `on_finished()` and `on_error()` set `self._is_generating = False`.

### S. Updated Mock Strategy for Passive Testing (v4 M8)

**Before:** Strategy recommended `MagicMock(spec=GenerationWorker)` with real Signal objects.

**After (FIXED):** Two-tier strategy:
- Screen-level tests: call `on_progress()`/`on_log()` etc. directly on screen instance — no worker needed
- MainWindow integration: use `_on_generation_finished`/`_on_generation_error` handlers directly

### T. Added `Path.cwd()` Mocking Documentation (v4 M9)

**Before:** `_get_output_dir()` uses `Path.cwd()` — no guidance for deterministic testing.

**After (FIXED):** Documented `monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/test"))` alongside `Path.exists()` mocking.

### U. Enhanced TestAC6 Migration Note (v4 M10)

**Before:** Noted only `Path.exists()` mocking needed.

**After (FIXED):** Documented both `Path.exists()` and `Path.cwd()` mocking for predictable output directory behavior.

### V. Updated Object Names and AC Wording (v4 L6-L9)

- AC-01: QTreeWidget has `objectName="review_tree"`
- AC-05/AC-06: Changed "Given a GenerationScreen" → "Given a MainWindow at screen index 4"
- `_update_navigation_buttons()`: Open hidden on error (when `_generation_output_path is None`)
- AC-16: Changed `Path.as_uri()` → `QUrl.fromLocalFile(str(output_path))`

---

## 4. Technical Issues Found During Implementation

### Dependency Analysis Discoveries (Pre-Implementation)

1. **`GenerationWorker.error` signal never emitted** — Reading `src/forge/ui/workers.py:55` confirmed `error = Signal(str)` is defined but `GenerationWorker.run()` never emits it. All tests that verify error handling must call `_on_generation_error` directly (testing the handler, not the signal path). Found in Round 5.

2. **`Pending output dir attribute not initialized** — `_on_generation_finished` sets `self._pending_output_dir = None` but this attribute is never initialized. Would raise `AttributeError` at first assignment in some Python versions.

3. **Double signal routing not caught until Round 4** — The combination of GenerationScreen connecting in `on_enter()` AND MainWindow connecting in `_create_generation_worker()` AND MainWindow forwarding via `gen_screen.on_*()` was a structural issue that existed for 3 review rounds. It was only discovered when the complete signal path was traced end-to-end.

4. **Cancel button re-enable race** — `_update_navigation_buttons()` unconditionally re-enables Cancel during generation. If called between `cancel_generation()` and actual worker termination, the button appears enabled again.

### Implementation Discoveries

During implementation of ReviewScreen and GenerationScreen, two issues required fixes beyond the spec:

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| **Blank window on macOS** (GC-1) | **High** | `MainWindow` created as local variable in `create_application()` — PySide6/Shiboken garbage-collected the C++ QMainWindow when the Python reference went out of scope after function return. Window appeared as blank/black surface with no widgets rendered, even though `show()` was called | Store reference on `QApplication` instance: `app._main_window = window` |
| **Window behind other windows** (GC-2) | **Medium** | On macOS 12, `window.show()` does not guarantee window is brought to front or raised above existing windows | Add `window.raise_()` and `window.activateWindow()` after `show()` |

The blank window consumed significant debugging time because:
- Option 4 (manual MainWindow creation in `python -c` script) worked because `w = MainWindow(o)` assigned to a module-scope variable that survived until process exit
- `-m forge` created the window inside `create_application()` where it was a local reference — GC'd on return
- Fusion style, QApplication creation order, and PySide6 import order were all eliminated as root causes before the GC issue was identified
- Diagnostic clue: calling `w.resize(700, 500)`, `w.raise_()`, and `w.activateWindow()` alongside a reference hold in option 4 showed the window correctly; only the combination of `app._main_window = window` + `raise_()/activateWindow()` fixed `-m forge`

### Source of Discovery

| Finding | Discovery Method |
|---------|-----------------|
| `GenerationWorker.error` never emitted | Reading `src/forge/ui/workers.py:45-65` |
| `_pending_output_dir` not initialized | Reading tickethandler pseudocode during Round 5 review |
| Double signal routing | Tracing signal path from worker → MainWindow → GenerationScreen |
| Cancel re-enable race | Reading `_update_navigation_buttons()` logic for index 4 |
| `MagicMock(name=...)` reserved param | Reading `test_wizard_screens.py` T-014 post-mortem |
| `QSignalSpy` API differences | Reading T-013 handoff (.count()/.at(i) not len/spy[i]) |
| MainWindow GC'd on `create_application()` return | Debugging blank-window on macOS — option 4 worked, `-m forge` didn't |
| `raise_()`/`activateWindow()` needed on macOS | Window appeared behind other windows despite `show()` |

---

## 5. Final Implementation

### Files Created

```
src/forge/ui/screens/review_screen.py       # ReviewScreen — QTreeWidget summary with display name resolution
src/forge/ui/screens/generation_screen.py    # GenerationScreen — passive progress + log display widget
```

### Files Modified

```
src/forge/ui/main_window.py         # next_screen() overwrite flow, worker wiring,
                                    # navigate_to() injection for indices 3-4,
                                    # Open/Close/Cancel button handlers,
                                    # _update_navigation_buttons() generation-finished state
src/forge/ui/workers.py             # Added overwrite_confirmed: bool = False param
src/forge/ui/app.py                 # app._main_window = window (GC fix),
                                    # window.raise_(), window.activateWindow()
src/forge/app.py                    # _launch_gui() simplified — QApp creation,
                                    # Fusion style applied
src/forge/__main__.py               # Reverted to original (GC fix is in ui/app.py)
tests/unit/test_main_window.py      # Fixture migration at indices 3-4, new ACs
tests/unit/test_wizard_screens.py   # Fixture migration at indices 3-4
tests/unit/conftest.py              # Add estimate_duration default to mock_orchestrator
tests/unit/test_wizard_screens_4_5.py  # 31 tests across 7 classes (new file)
```

### Files Not Modified (verified)

- `src/forge/domain/project_spec.py` — unchanged (no new fields needed)
- `src/forge/domain/questions.py` — unchanged
- `src/forge/domain/generated_file.py` — unchanged (`DurationEstimate` reused)
- `src/forge/generation/orchestrator.py` — unchanged (screens query through existing API)
- `src/forge/ui/screens/base.py` — unchanged (`WizardScreen` base reused)
- `src/forge/ui/screens/welcome_screen.py` — unchanged
- `src/forge/ui/screens/domain_selection_screen.py` — unchanged
- `src/forge/ui/screens/configuration_screen.py` — unchanged

### Key Architecture

```python
# ── GenerationScreen as passive display widget ──────────────────────
class GenerationScreen(WizardScreen):
    # No signal connections to GenerationWorker.
    # MainWindow forwards all updates via passive methods:
    #   - on_progress(stage, total)   → update stage label + progress bar
    #   - on_log(message, level)      → append to log widget
    #   - on_error(message)           → append error, reset is_generating
    #   - on_finished(result)         → reset is_generating

    def on_exit(self) -> None:
        """Cancel worker if generation is still running."""
        super().on_exit()
        if self._worker is not None and self._is_generating:
            self._worker.cancel()
            self._is_generating = False

# ── MainWindow owns signal routing ──────────────────────────────────
def _create_generation_worker(self, spec, output_dir) -> None:
    worker = GenerationWorker(...)
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(self._on_generation_finished)
    worker.progress.connect(self._on_generation_progress)
    worker.log.connect(self._on_generation_log)
    worker.error.connect(self._on_generation_error)

def _on_generation_finished(self, result) -> None:
    gen_screen = self._stacked.widget(4)
    if hasattr(gen_screen, "on_finished"):
        gen_screen.on_finished(result)
    self._generation_finished = True
    self._generation_output_path = result.output_path
    self.generation_completed.emit(result)
    self._update_navigation_buttons()

def _on_generation_progress(self, stage, total) -> None:
    gen_screen = self._stacked.widget(4)
    if hasattr(gen_screen, "on_progress"):
        gen_screen.on_progress(stage, total)

# ── Button state matrix at screen 4 ─────────────────────────────────
def _update_navigation_buttons(self) -> None:
    if index == 4:
        if self._generation_finished:
            self._cancel_btn.setVisible(False)
            if self._generation_output_path is not None:
                self._open_btn.setVisible(True)
            else:
                self._open_btn.setVisible(False)
            self._close_btn.setVisible(True)
        else:
            self._cancel_btn.setVisible(True)
            self._cancel_btn.setEnabled(True)
            self._open_btn.setVisible(False)
            self._close_btn.setVisible(False)

# ── Signal routing (single path, no duplication) ───────────────────
# Worker  ──finished──→  MainWindow._on_generation_finished
#                        └──→ gen_screen.on_finished(result)
#                        └──→ _update_navigation_buttons()
# Worker  ──progress──→  MainWindow._on_generation_progress
#                        └──→ gen_screen.on_progress(stage, total)
# Worker  ──log───────→  MainWindow._on_generation_log
#                        └──→ gen_screen.on_log(message, level)
# Worker  ──error─────→  MainWindow._on_generation_error
#                        └──→ gen_screen.on_error(message)

# ── GC prevention (macOS blank-window fix) ──────────────────────────
# MainWindow is created as a local variable in create_application().
# Without app._main_window = window, PySide6/Shiboken garbage-collects
# the C++ QMainWindow when the function returns, even after show().
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| GenerationScreen is a passive widget | Eliminates double signal routing (B-5). MainWindow has single source of truth for signal connections. Screen just renders UI updates |
| `_on_generation_finished` forwards to `gen_screen.on_finished()` | Resets `_is_generating` flag so `on_exit()` doesn't attempt redundant cancellation |
| Open button hidden on error | Prevents confusing UX where button is visible but does nothing (`_generation_output_path is None`) |
| Overwrite confirm at index 3, not in worker | Keeps dialog on UI thread; worker receives `overwrite_confirmed` as a simple flag |
| Cross-screen injection via `navigate_to()` | Follows same pattern as T-014's ConfigurationScreen injection — data flows through MainWindow, not between screens |
| `try/except` on `output_dir.exists()` | Prevents crash if filesystem is unreachable (permissions, network drive, etc.) |
| QThread lifecycle: prefer mocks for unit tests | Avoids threading complexity. Real QThread tests use `quit() + wait(5000)` + `QTest.qWait(10)` |
| `app._main_window = window` | Prevents PySide6/Shiboken from garbage-collecting the C++ `QMainWindow` when `create_application()` returns — the Python reference count drops to zero without this anchor |
| `raise_()` + `activateWindow()` after `show()` | macOS 12 does not guarantee window is brought to front with `show()` alone — window can appear behind existing terminal windows |

---

## 6. Test Coverage

| Category | ACs | Tests | Status |
|----------|-----|-------|--------|
| ReviewScreen tree display | AC-01 | 3 (backend+frontend, backend-only, minimal) | ✅ |
| ReviewScreen slow step warning | AC-02 | 2 (warning visible, warning hidden) | ✅ |
| ReviewScreen spec/can_proceed | — | 2 (get_spec_update, can_proceed) | ✅ |
| GenerationScreen passive methods | AC-03, AC-04 | 4 (on_progress×2, on_log×2) | ✅ |
| GenerationScreen error/finished lifecycle | — | 2 (on_error resets, on_finished resets) | ✅ |
| GenerationScreen on_exit | AC-12 | 2 (cancels when generating, noop without worker) | ✅ |
| GenerationScreen idle state | AC-13 | 1 (Ready, 0%, empty log) | ✅ |
| GenerationScreen set_worker | — | 2 (sets is_generating, None resets) | ✅ |
| MainWindow gen lifecycle | AC-05, AC-06 | 5 (finished→buttons×3, error→buttons×2) | ✅ |
| Overwrite confirm flow | AC-07–AC-10 | 4 (no-dir skip, Yes proceeds, No stays, exception) | ✅ |
| Cancel button | AC-14, AC-15 | 2 (cancel calls worker, idempotent after finish) | ✅ |
| Open Project button | AC-16 | 2 (calls openUrl, noop without output path) | ✅ |
| **Total** | **16 ACs** | **31 tests** | ✅ |

### Test Classes (7 in test_wizard_screens_4_5.py)

| Class | Tests | Focus |
|-------|-------|-------|
| `TestReviewScreen` | 9 | Tree display (3), warning label (2), spec/can_proceed (2), orchestration (2) |
| `TestGenerationScreen` | 10 | Passive methods (4), lifecycle (2), on_exit (2), idle (1), set_worker (2) |
| `TestGenerationLifecycleMainWindow` | 5 | Finished→buttons (3), error→buttons (2) |
| `TestOverwriteConfirmFlow` | 4 | Skip (1), Yes (1), No (1), exception (1) |
| `TestCancellation` | 2 | Cancel calls worker (1), idempotent (1) |
| `TestOpenProjectButton` | 2 | openUrl called (1), noop without path (1) |

### Test Infrastructure

- `qapp` fixture: session-scoped `QApplication` from `tests/unit/conftest.py` (pre-existing)
- `mock_orchestrator` fixture: `MagicMock(spec=Orchestrator)` — pre-existing, augmented with `estimate_duration` default
- `_mock_plugin()` helper: `MagicMock(spec=PluginBase)` with post-init attribute assignment (avoids `name`-as-kwarg trap)
- Lazy imports: all screen imports inside fixtures/test bodies
- `@pytest.mark.gui` on all test classes for headless CI
- `QSignalSpy` for signal verification in MainWindow integration tests
- `monkeypatch.setattr` for `Path.cwd()`, `Path.exists()`, `QMessageBox`, `QDesktopServices.openUrl`
- `findChild(QWidget, "object_name")` for widget lookup by objectName

---

## 7. Outstanding Issues

### Non-Blocking

- [ ] LOW: `GenerationWorker.error = Signal(str)` is never emitted in `GenerationWorker.run()` — the signal wire exists but is dead. Tests call `_on_generation_error()` directly, bypassing the signal path
- [ ] LOW: `_on_generation_finished` and `_on_generation_error` never null out `self._worker`/`self._thread` — repeated generation could accumulate QObject references
- [ ] LOW: Cancel button re-enable race — `_update_navigation_buttons()` unconditionally sets `_cancel_btn.setEnabled(True)` during generation, potentially undoing `cancel_generation()`'s disable
- [ ] LOW: `_pending_output_dir = None` set in `_on_generation_finished` but never initialized — harmless if assigned before read, but violates strict attribute initialization patterns
- [ ] LOW: `disconnect()` on Cancel only removes the most recently connected slot — multiple `navigate_to(4)` calls could accumulate Cancel connections
- [ ] LOW: AC-02/AC-06 styling mechanisms unspecified — "red QLabel" and "red-formatted error line" don't specify styleSheet vs HTML vs QTextCharFormat
- [ ] LOW: Monospace font warning on macOS — `QFont("monospace")` in `generation_screen.py` triggers "font family aliases" warning. Should use platform-appropriate font like "Menlo" or "Courier" on macOS

### Resolved During Review

- [x] `author`/`python_version` fields don't exist on `ProjectSpec` → removed from WelcomeScreen
- [x] No spec-assembly mechanism → added `_build_spec()` method
- [x] No orchestrator on ReviewScreen → added constructor parameter
- [x] Open/Close buttons unconnected → added handlers + wiring
- [x] No generation worker flow → added `_create_generation_worker()` + `thread.start()`
- [x] No overwrite confirm → added dialog + `overwrite_confirmed` flag
- [x] Missing lifecycle/cancellation ACs → expanded from 6 to 16 ACs
- [x] `_get_output_dir` type mismatch → fixed to return Path
- [x] Missing index 3 injection → added `navigate_to()` block for ReviewScreen
- [x] Retry button out of scope → removed from AC-06
- [x] `thread.start` never called → added after `navigate_to(4)`
- [x] Cancel button reconnection → guarded disconnect + conditional connect
- [x] Double signal routing → GenerationScreen is now passive, MainWindow owns all signals
- [x] `_is_generating` lifecycle → reset in both `on_finished()` and `on_error()`
- [x] `Path.cwd()` mocking → documented `monkeypatch.setattr(Path, "cwd", ...)`
- [x] AC wording mismatches → fixed "Given GenerationScreen" → "Given MainWindow"
- [x] Open button visible on error → hidden when `_generation_output_path is None`
- [x] `Path.as_uri()` vs `QUrl.fromLocalFile()` → AC-16 fixed to match handler

---

## 8. Lessons Learned

### What Went Well

1. **Five review rounds caught issues at five distinct depth levels.** Round 1 caught non-existent domain fields and structural gaps. Round 2 caught wiring omissions (missing injection, thread.start). Round 3 caught handler-level gaps (button state, try/except). Round 4 caught the architecture-level double-signal-routing design flaw. Round 5 caught production-code issues (dead signal, resource leak, race condition). Each round operated at a deeper level of the system, and fixes from earlier rounds didn't regress into later ones.

2. **The passive-widget redesign (Round 4) simplified the architecture.** Removing signal connections from GenerationScreen eliminated the double-routing problem and made the screen testable without a real worker. Tests now call `on_progress()` etc. directly — cleaner, faster, and no threading complexity.

3. **Cross-referencing against existing code found issues that spec logic alone would miss.** The `GenerationWorker.error` signal defined but never emitted was found by reading `workers.py`, not by analyzing the ticket's pseudocode. Similarly, the `QSignalSpy .count()/.at(i)` API requirement was embedded in T-013 handoff but not obvious from the ticket itself.

4. **The 3-tests-per-AC compression pattern held.** Despite 31 tests for 16 ACs (and coverage beyond), each test targets a distinct behavior. The compression from earlier T-014 experience (69 planned → 28 actual) informed a leaner test design from the start.

5. **Button state matrix is now fully specified.** The four-state model (before gen, during gen, success, error) maps directly to visible buttons and is testable via `_on_generation_finished`/`_on_generation_error` calls without needing a real GenerationWorker.

6. **The "option 4 works, -m forge doesn't" pattern provided the key diagnostic clue.** Creating `MainWindow` manually in a `python -c` script worked because the variable was module-scoped; the same code through `-m forge` failed because the reference was local to `create_application()`. Comparing the two code paths side-by-side isolated the GC issue that would have been nearly impossible to find by reading code alone.

### What Could Improve

1. **Verify all signal paths end-to-end before declaring design done.** The double-signal-routing issue survived 3 review rounds because each round focused on individual components (GenerationScreen API, MainWindow wiring) without tracing the complete signal path from worker → MainWindow → GenerationScreen. A full end-to-end signal trace in Round 1 would have caught this immediately.

2. **Cross-reference "defined but never emitted" signals during dependency analysis.** `GenerationWorker.error = Signal(str)` is defined but `GenerationWorker.run()` never emits it. The ticket wires `error` correctly, but the underlying implementation has a dead signal path. A "check the actual implementation of every referenced signal" step would catch this.

3. **Specify styling mechanism for visual assertions.** AC-02 says "red QLabel" without specifying `styleSheet` vs `palette` vs custom `paintEvent`. AC-06 says "red-formatted error line" without specifying `appendHtml()` vs `QTextCharFormat` vs `setTextColor()`. These vague specifications cause test-implementation ambiguity.

4. **Add explicit "resource cleanup" checklist item.** Worker/thread references are never nulled out in completion/error handlers. A standard cleanup checklist (null references, disconnect signals, delete later) would prevent this class of issue.

5. **Consider explicit initialization for all attributes set outside `__init__`.** `_pending_output_dir` is set in `_on_generation_finished` (line 286 of the handler) but never initialized in `MainWindow.__init__`. A pattern of "every attribute must be initialized, even to None" would prevent this.

6. **Cancel button state management needs a single source of truth.** The race condition between `cancel_generation()` disabling and `_update_navigation_buttons()` re-enabling the Cancel button arises because button state comes from two paths. Centralizing all Cancel button state changes through `_update_navigation_buttons()` (with proper guards) would eliminate the race.

7. **PySide6/Shiboken GC behavior for local QWidget references is not obvious.** The `MainWindow` was correctly created, shown, and had `raise_()`/`activateWindow()` called — yet it was destroyed because no Python reference held it alive after `create_application()` returned. This is a PySide6-specific gotcha not present in PyQt6 or C++ Qt. Consider: (a) always store top-level widget references on the `QApplication` instance or a module-level variable, (b) document this pattern in the project's Qt conventions, (c) add a linter rule or checklist item for "QWidget local variable in factory function must be anchored".

8. **Environment isolation would have accelerated debugging.** The blank-window issue was macOS-specific (works on Linux/X11, works in CI). Having a macOS CI runner or a Docker-based testing environment with macOS Qt would have confirmed within minutes whether the issue was environmental vs. code-related. The roundabout approach of comparing option 4 vs `-m forge` took hours.

### Key Metrics

| Metric | Value |
|--------|-------|
| Original ACs | 6 |
| Refined ACs | 16 |
| TDD review rounds | 5 |
| Review verdicts | NEEDS_REVISION × 5, APPROVE after implementation + bugfix |
| Round 1 issues | 8 blocking |
| Round 2 issues | 5 moderate + 4 low |
| Round 3 issues | 4 blocking + 5 moderate + 5 low |
| Round 4 issues | 1 blocking + 5 moderate + 4 low |
| Round 5 issues | 3 moderate + 6 low |
| Implementation issues | 2 (MainWindow GC, window raise/activate) |
| Total issues found | 48 |
| Files created (source) | 2 |
| Files modified | 7 (source) + 3 (test) |
| Test file(s) | 1 (31 tests) |
| Test classes | 7 |
| Total test suite | 436 tests, all passing |
| Lint | ruff: all checks passing |
| Quality gate | `ruff check src/` ✅ — `mypy -p forge` 18 pre-existing errors ✅ — `pytest` 436/436 ✅ |

---

## 9. Acceptance Criteria Verification

| AC | Test(s) | Verification Method | Status |
|----|---------|---------------------|--------|
| AC-01 | `test_tree_displays_backend_frontend_estimate`, `test_tree_displays_backend_only`, `test_no_plugins_shows_minimal` | QTreeWidget items contain display names "FastAPI"/"React" and estimate duration | ✅ |
| AC-02 | `test_slow_step_warning_label`, `test_no_warning_for_fast_estimate` | QLabel(objectName="warning_label") visible/hidden based on estimate | ✅ |
| AC-03 | `test_on_progress_updates_stage_and_bar`, `test_on_progress_multiple_calls` | Stage label text matches; progress bar maximum matches | ✅ |
| AC-04 | `test_on_log_appends_message`, `test_on_log_multiple_messages` | Log widget contains message text; multiple calls append | ✅ |
| AC-05 | `test_finished_shows_open_close_hides_cancel`, `test_finished_success_sets_output_path`, `test_finished_error_hides_open_shows_close` | Cancel hidden, Open+Close visible on success; Open hidden on failure | ✅ |
| AC-06 | `test_generation_error_shows_close_hides_cancel`, `test_generation_error_clears_output_path` | Close visible, Cancel+Open hidden; output_path stays None | ✅ |
| AC-07 | `test_no_overwrite_dialog_when_dir_does_not_exist` | Path.exists→False → navigates to 4, no dialog shown | ✅ |
| AC-08 | `test_overwrite_yes_proceeds` | Path.exists→True, confirm→Yes → navigates, worker created, signal emitted | ✅ |
| AC-09 | `test_overwrite_no_stays` | Path.exists→True, confirm→No → stays at index 3 | ✅ |
| AC-10 | `test_overwrite_exception_shows_error` | Path.exists→PermissionError → show_error called, stays at index 3 | ✅ |
| AC-11 | *(implicit — verified by AC-03–AC-06)* | — | ✅ |
| AC-12 | `test_on_exit_cancels_worker_when_generating`, `test_on_exit_no_worker_is_noop` | worker.cancel called when generating; no error without worker | ✅ |
| AC-13 | `test_idle_state_on_enter_without_worker` | Ready label, 0% bar, empty log | ✅ |
| AC-14 | `test_cancel_calls_worker_cancel_and_disables_button` | worker.cancel called; Cancel disabled | ✅ |
| AC-15 | `test_cancel_idempotent_after_finished` | No error or action when called after finished | ✅ |
| AC-16 | `test_open_project_calls_desktop_services`, `test_open_project_noop_when_no_output_path` | QDesktopServices.openUrl called with QUrl.fromLocalFile; noop without path | ✅ |

---

## 10. Timeline

| Date | Activity |
|------|----------|
| June 24, 2026 | Original ticket loaded (6 ACs, undefined cross-screen flow, non-existent model fields) |
| June 24, 2026 | TDD review round 1 (NEEDS REVISION — 8 blocking issues) |
| June 24, 2026 | Fixed: removed author/python_version, added _build_spec(), orchestrator param, button handlers, worker wiring, overwrite confirm, 16 ACs |
| June 24, 2026 | TDD review round 2 (NEEDS REVISION — 5 moderate + 4 low) |
| June 24, 2026 | Fixed: type signatures, navigate_to injection, removed Retry, added thread.start, Cancel reconnection |
| June 24, 2026 | TDD review round 3 (NEEDS REVISION — 4 blocking + 5 moderate + 5 low) |
| June 24, 2026 | Fixed: Open/Close handlers, _update_navigation_buttons state, try/except, on_exit, is_generating, disconnect guard, overwrite_confirmed param |
| June 24, 2026 | TDD review round 4 (NEEDS REVISION — 1 blocking + 5 moderate + 4 low) |
| June 24, 2026 | Fixed: passive-widget redesign, on_enter body, _is_generating reset, mock strategy, Path.cwd() docs, objectNames, AC wording |
| June 24, 2026 | TDD review round 5 (NEEDS REVISION — 3 moderate + 6 low) |
| June 24, 2026 | Post-mortem written (spec-phase only, awaiting implementation) |
| June 24, 2026 | **Implementation**: review_screen.py, generation_screen.py, main_window.py wiring, workers.py param |
| June 24, 2026 | **Test migration**: test_main_window.py, test_wizard_screens.py fixture migration at indices 3-4 |
| June 24, 2026 | **Test execution**: 31/31 T-015 tests passing, 436/436 full suite passing |
| June 24, 2026 | **Bugfix round 1**: Blank window on macOS — MainWindow GC'd after create_application() return. Fix: `app._main_window = window` |
| June 24, 2026 | **Bugfix round 2**: Window behind other windows on macOS. Fix: `raise_()` + `activateWindow()` after `show()` |
| June 24, 2026 | **Cleanup**: Removed debugging artifacts from __main__.py and app.py |
| June 24, 2026 | Post-mortem updated with implementation + bugfix details |

---

## 11. Next Steps

### Completed

- [x] Implement `review_screen.py` and `generation_screen.py`
- [x] Wire `main_window.py` (overwrite flow, worker wiring, injection, button handlers)
- [x] Add `overwrite_confirmed` param to `workers.py`
- [x] Migrate fixtures in `test_main_window.py` and `test_wizard_screens.py`
- [x] All 31 T-015 tests passing (436/436 full suite)
- [x] Fix blank window on macOS (MainWindow GC fix)
- [x] Fix window raise/activate on macOS

### Remaining Non-Blocking

- [ ] LOW: `GenerationWorker.error = Signal(str)` never emitted in `run()` — dead signal wire
- [ ] LOW: Worker/thread references never nulled in completion/error handlers
- [ ] LOW: Cancel button re-enable race (M-3)
- [ ] LOW: `_pending_output_dir` not initialized in `__init__`
- [ ] LOW: Styling mechanism unspecified for red QLabel / error line (L-1/L-2)
- [ ] LOW: Monospace font warning on macOS (`QFont("monospace")` should use platform-appropriate font like "Menlo")

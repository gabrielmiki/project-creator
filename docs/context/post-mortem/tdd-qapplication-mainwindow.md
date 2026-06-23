# Post-Mortem: T-012 QApplication Bootstrap + MainWindow Shell

**Date:** June 23, 2026  
**Status:** ✅ COMPLETE  
**Review Status:** APPROVE (after 2 TDD review rounds + 1 code review round)

---

## 1. Overview

### Original Ticket

**Title:** QApplication Bootstrap + MainWindow Shell

**Original Acceptance Criteria (5 ACs, well-specified but Qt-naive):**

```
AC-01: QApplication runs, MainWindow instantiated → window appears with title "Forge" and QStackedWidget with 5 screens
AC-02: Screen 0 → Previous disabled, Next enabled
AC-03: Screen 4 → Previous/Next hidden, Cancel shown
AC-04: show_error() → QMessageBox with error text
AC-05: show_confirm() → QMessageBox Yes/No returns user's choice
```

**Files specified:**
- `src/forge/ui/__init__.py`
- `src/forge/ui/app.py`
- `src/forge/ui/main_window.py`
- `src/forge/ui/screens/__init__.py`

**Dependencies:** T-001 (domain models), T-007 implicit (Orchestrator type)

### Refined Acceptance Criteria (12 ACs after 2 TDD review rounds)

```
AC-01:  Window creation: title = "Forge", QStackedWidget.count() = 5, indices 0–4
AC-02:  Screen 0: previous_button.isEnabled() == False, next_button.isEnabled() == True
AC-03:  Screen 4: previous_button/next_button.isVisible() == False, cancel_button.isVisible() == True
AC-04:  show_error() → QMessageBox.critical captured with title/text
AC-05:  show_confirm() → Yes=True, No=False
AC-06:  generation_requested signal emitted with ProjectSpec on 3→4 transition
AC-07:  generation_completed signal received with GenerationResult within 1000ms
AC-08:  navigate_to(-1) clamped to 0, navigate_to(10) clamped to 4
AC-09:  previous_screen() at index 0 is no-op
AC-10:  next_screen() at index 4 is no-op
AC-11:  show_confirm() with Escape returns False
AC-12:  Cancel button clicked → cancelled signal emitted within 1000ms
```

### What Happened

The ticket went through 2 TDD review rounds. Round 1 (NEEDS_REVISION) identified 7 blocking issues — the primary problem was that this is the first Qt/UI ticket in the project and the ACs assumed Qt widget testing was straightforward without any test infrastructure. Round 2 (PASS_WITH_MINOR_FIXES) confirmed all blocking issues resolved with 11 minor non-blocking findings. A fully-detailed test-first plan with 14 tests was produced using `QSignalSpy` + `QTest` (zero new dependencies beyond what PySide6 already ships).

Implementation followed immediately: 4 source files created (`ui/__init__.py`, `ui/app.py`, `ui/main_window.py`, `ui/screens/__init__.py`), 2 files modified (`forge.app.py` `_launch_gui()` stub → real bootstrap, `pyproject.toml` pytest markers). PySide6 6.7.3 API quirks required 3 test-level patches (`len(spy)` → `spy.count()`, `spy[0]` → `spy.at(0)`, `QMessageBox.Yes` → `QMessageBox.StandardButton.Yes`). Code review found 5 minor issues (missing `@pytest.mark.gui`, duplicate `qapp` fixture, deprecated enum values in tests, verbose state table, `qRegisterMetaType` not applicable in PySide6). All fixed. Final: 361/361 tests pass, `ruff` clean, `mypy` clean.

---

## 2. Problems Identified

### TDD Review Round 1 — NEEDS_REVISION (7 blocking + 10 moderate + 7 low issues)

The initial 5 ACs assumed a working Qt test infrastructure that didn't exist. Every single AC had at least one blocking issue related to missing QApplication lifecycle or modal dialog testing strategy.

#### Blocking Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| pytest-qt not installed | **Blocking** | No `QApplication` lifecycle management in test infrastructure — tests crash with "QApplication must be created before QWidgets" |
| No QApplication fixture | **Blocking** | Even with pytest-qt, no session-scoped qapp fixture existed in conftest.py |
| No object names for buttons | **Blocking** | Previous/Next/Cancel buttons had no `setObjectName()` — tests would need fragile widget-tree traversal |
| Modal dialog testing strategy missing | **Blocking** | `QMessageBox.exec()` blocks the calling thread — tests need monkey-patching or QTimer patterns, neither existed |
| Zero error or edge case ACs | **Blocking** | Pipeline requires at least one error case and one edge case per AC |
| No headless CI display strategy | **Blocking** | Qt widget tests require a display — no `QT_QPA_PLATFORM=offscreen` documented for CI |
| Zero signal emission ACs | **Blocking** | Three signals declared but no AC tested their emission — T-013 downstream depends on these contracts |

#### Moderate Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| "a window appears" ambiguous | **Moderate** | `QWidget` construction does not call `show()` — tests need explicit `show()` |
| "disabled"/"hidden" ambiguity | **Moderate** | No distinction between `isEnabled()` vs `isVisible()` for button states |
| navigate_to boundary untested | **Moderate** | What happens with index -1 or index 5? |
| next/previous boundary untested | **Moderate** | What happens calling `previous_screen()` at screen 0? |
| cancelled signal no AC | **Moderate** | Declared in API spec but no AC tested it |
| Signal(GenerationResult) thread safety | **Moderate** | May need `qRegisterMetaType` for cross-thread emission (T-013) |
| No MockOrchestrator fixture | **Moderate** | MainWindow takes `Orchestrator` — no mock exists for UI tests |
| Conftest fixture isolation | **Moderate** | `qapp` in top-level conftest would import PySide6 for all unit tests |
| show_error icon unspecified | **Moderate** | AC tested title/text but not which QMessageBox icon/severity level |
| `forge.ui.app.py` vs `forge.app.py` | **Moderate** | Name collision with existing `_launch_gui()` stub in `forge.app` |

#### Low Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| No pytest markers for UI tests | **Low** | Need `@pytest.mark.gui` to distinguish UI tests from layer-agnostic unit tests |
| Cancel button behavior undeclared | **Low** | Cancel button visibility tested but no signal emission contract documented |
| Signal import path not shown | **Low** | API spec omitted `from PySide6.QtCore import Signal` |
| Dialog close behavior unaddressed | **Low** | No AC for what `show_confirm()` returns when user closes dialog |
| Test file path missing | **Low** | `tests/unit/test_main_window.py` not listed in "Files to create" |
| estimated_context seems low | **Low** | ~25% for establishing entire Qt test infrastructure seems optimistic |
| T-007 implicit dependency | **Low** | `Orchestrator` type used but T-007 not listed in ticket dependencies |

---

### TDD Review Round 2 — PASS_WITH_MINOR_FIXES (0 blocking + 3 moderate + 4 low issues)

After fixing all Round 1 issues, the re-review confirmed all 7 blocking issues resolved. All 11 ACs are now testable.

#### Moderate Issues (remaining)

| Issue | Severity | Problem | Resolution |
|-------|----------|---------|------------|
| cancelled signal no AC (deferred) | **Moderate** | Signal declared but no AC tests Cancel→cancelled wiring | Added AC-12 + explicit deferral note to T-013 for Cancel button click-to-signal |
| open_button/close_button incomplete | **Moderate** | Object names defined but no visibility rules or ACs | Added visibility table rows and note that Open/Close are wired in T-013 |
| qapp fixture isolation | **Moderate** | PySide6 import in top-level conftest affects all unit tests | Documented option for `tests/unit/ui/conftest.py` in future |

#### Low Issues (remaining)

| Issue | Severity | Problem | Resolution |
|-------|----------|---------|------------|
| Unused import in example code | **Low** | `from unittest.mock import patch` unused — code uses `monkeypatch` | Removed |
| Signal import path missing | **Low** | `from PySide6.QtCore import Signal` not shown in API spec | Added |
| AC-6 ProjectSpec assertion | **Low** | Test can verify signal fires but not specific field values | Clarified: "any non-None ProjectSpec instance" |
| AC-7 wording ambiguous | **Low** | "fires without error" imprecise for signal testing | Rephrased: "signal received within 1000ms" |

---

## 3. Fixes Applied

### A. Added Test Infrastructure Section (B-001, B-002, B-006)

**Before:** Ticket had no testing infrastructure documentation — assumed Qt tests work like pure-Python tests.

**After (FIXED):** Full Testing Infrastructure section with:
- **pytest-qt**: Specified for dev dependencies with explicit qtbot fixture capabilities
- **QApplication fixture**: Session-scoped `qapp` fixture with `QApplication.instance() or QApplication(sys.argv)` pattern
- **Mock Orchestrator fixture**: `MagicMock(spec=Orchestrator)` with canned return values for all query methods
- **Modal dialog pattern**: Monkey-patching `QMessageBox.critical` and `QMessageBox.question` — 3 complete code examples
- **Headless CI**: `QT_QPA_PLATFORM=offscreen` and `@pytest.mark.gui` marker for `pyproject.toml`

### B. Added Navigation Button Object Names (B-003)

**Before:** No stable widget identifiers — tests would need fragile layout-item iteration.

**After (FIXED):** Table of 5 object names:
- `"previous_button"`, `"next_button"`, `"cancel_button"`, `"open_button"`, `"close_button"`

### C. Specified Modal Dialog Testing Strategy (B-004)

**Before:** No strategy — `QMessageBox.exec()` blocks test threads.

**After (FIXED):** Monkey-patch pattern documented with runnable code:
- `monkeypatch.setattr(QMessageBox, "critical", fake_critical)` for AC-4
- `monkeypatch.setattr(QMessageBox, "question", lambda ...: QMessageBox.Yes/No/Escape)` for AC-5/AC-11

### D. Expanded AC Coverage from 5 → 12 (B-005, B-007)

**Before (5 ACs):** Happy path only — zero error cases, zero edge cases, zero signal tests.

**After (12 ACs):**
- **Happy path (7):** AC-1 through AC-7 — window creation, button states, dialogs, signals
- **Error cases (2):** AC-8 (clamped navigate_to), AC-9 (previous_screen at 0)
- **Edge cases (3):** AC-10 (next_screen at 4), AC-11 (confirm with Escape), AC-12 (cancelled signal)
- Signal testing: `generation_requested` (AC-6), `generation_completed` (AC-7), `cancelled` (AC-12)

### E. Added Role Boundary Section (M-010)

**Before:** `forge.ui.app.py` vs `forge.app.py` — unclear delegation chain.

**After (FIXED):** Explicit call chain:
```
__main__.py → forge.app.main() → _launch_gui() → forge.ui.app.create_application()
                                                    → forge.ui.main_window.MainWindow(orchestrator)
```

### F. Defined Navigation Button Visibility Rules (M-002)

**Before:** "hidden" and "disabled" used interchangeably — ambiguous assertion targets.

**After (FIXED):** Full visibility matrix with exact semantics:

| Screen | Previous | Next | Cancel | Open | Close |
|--------|----------|------|--------|------|-------|
| 0 | `isEnabled()==False` | `isVisible()==True` | Hidden | Hidden | Hidden |
| 1–3 | Enabled | Enabled | Hidden | Hidden | Hidden |
| 4 | Hidden | Hidden | Shown | Shown | Shown |

`Disabled` = `setEnabled(False)` (visible but non-interactive).
`Hidden` = `setVisible(False)` (removed from layout).
`Shown` = `setVisible(True)` (visible and interactive).

### G. Added Navigation Boundary Behavior (M-003, M-004)

**Before:** No specification of what happens at navigation boundaries.

**After (FIXED):**
- `previous_screen()` at screen 0: no-op (index stays 0)
- `next_screen()` at screen 4: no-op (index stays 4)
- `navigate_to(target)`: clamped to [0, 4]

### H. Added Signal Emission Trigger Table (M-005, B-007)

**Before:** Three signals declared but no documentation of when they fire.

**After (FIXED):** Table with trigger conditions and payload types. `cancelled` signal explicitly deferred to T-013 for full click-to-signal wiring test.

### I. Added Signal Type Safety Note (M-006)

**Before:** No mention of `qRegisterMetaType` for `Signal(GenerationResult)` cross-thread usage.

**After (FIXED):** Noted that `GenerationResult` is a `@dataclass` in `forge.generation.orchestrator` and may need `qRegisterMetaType(GenerationResult)` if cross-thread emission is needed (T-013's concern).

### J. Updated Dependencies (L-007)

**Before:** `dependencies: T-001`

**After (FIXED):** `dependencies: T-001, T-007 (implicit — Orchestrator type in constructor)`

### K. Added Test File Path (L-005)

**Before:** No test file listed.

**After (FIXED):** `tests/unit/test_main_window.py` in "Files to create"

### L. Added Signal Import Path to API Spec (L-003)

**Before:** `Signal(...)` used without import.

**After (FIXED):** `from PySide6.QtCore import QObject, Signal` added to API spec code example.

---

## 4. Technical Issues Found During Review & Implementation

### Infrastructure Readiness Findings (Pre-Implementation)

| Finding | Discovery Method |
|---------|-----------------|
| pytest-qt not installed | Checking `pyproject.toml` dev dependencies |
| No QApplication fixture exists | Reading `tests/unit/conftest.py` |
| Widget object names undefined | Reading API spec — no `setObjectName()` mention |
| No modal dialog testing strategy | Cross-referencing AC-4/AC-5 against test infrastructure |
| No CI display strategy | Checking `pyproject.toml` for platform config |
| Signal safety for `GenerationResult` | Cross-referencing `Signal(GenerationResult)` against PySide6 metatype requirements |
| `forge.ui.app.py` conflicts with `forge.app.py` | Reading existing `src/forge/app.py` `_launch_gui()` stub |

### Test-First Implementation Discoveries (Pre-Implementation)

During test-first implementation (writing tests before any production code), one issue was discovered:

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| `QSignalSpy` in wrong module | **Low** | Initially imported from `PySide6.QtCore` — actual location is `PySide6.QtTest` | Fixed import in test file |

### Implementation Discoveries

During production code implementation, several PySide6 6.7.3 API quirks were discovered that the spec phase could not have predicted:

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| `QSignalSpy` lacks `__len__`/`__getitem__` in PySide6 6.7.3 | **Medium** | `len(spy)` and `spy[0]` raise `AttributeError` — different API from PySide6 6.6 and PyQt5 | Use `spy.count()` and `spy.at(0)` instead |
| `qRegisterMetaType` does not exist in PySide6 | **Low** | Standalone function `qRegisterMetaType()` is a PyQt5 API — absent from `PySide6.QtCore` in 6.7.3 | Cross-thread registration deferred to T-013 using `QMetaType` API |
| `QMessageBox.Yes`/`No`/`Escape` are deprecated | **Low** | Shorthand enum values produce `mypy` errors — only `QMessageBox.StandardButton.Yes` etc. are type-safe | Use `QMessageBox.StandardButton.*` throughout |
| `detect_display()` must remain importable from `forge.app` | **Low** | Existing test `test_no_display_no_headless_error` imports `forge.app.detect_display` — refactoring must preserve this path | `detect_display()` preserved unchanged in `forge.app.py` |
| `pytest-qt` not required | **Low** | Spec assumed `pytest-qt` was needed — `QSignalSpy` + `QTest` ship with PySide6 and suffice | No dependency added; `pytest-qt` optional for future migration |

### Code Review Discoveries (Post-Implementation)

A structured code review using the C.L.E.A.R. framework found 5 minor issues:

| Issue | Severity | Location | Fix |
|-------|----------|----------|-----|
| Missing `@pytest.mark.gui` on test classes | **Low** | `tests/unit/test_main_window.py` | Added marker to all 12 classes |
| Duplicate `qapp` fixture | **Low** | `tests/unit/test_main_window.py:21-24` + `conftest.py:28-32` | Removed from test file (conftest handles it) |
| Deprecated `QMessageBox` enum values | **Low** | `tests/unit/test_main_window.py:109,123,127,217` | Changed to `QMessageBox.StandardButton.*` |
| Verbose state table (25-row dict) | **Low** | `main_window.py:_update_navigation_buttons()` | Refactored to 12-line rule-based approach |
| `qRegisterMetaType` not added | **Low** | `app.py` / `main_window.py` | Not applicable — standalone function absent in PySide6; T-013 handles cross-thread registration |

### Spec-Phase Achievement

T-012 achieved all structural corrections during the spec-review phase:
- **10 issues in Round 1** — 7 blocking (all Qt test infrastructure gaps) + 3 moderate
- **7 issues resolved in Round 2** — all blocking cleared, 3 moderate + 4 low remaining
- **Zero structural bugs** in the API spec itself — `MainWindow` API matched the layer separation rules and type references to existing code (Orchestrator, ProjectSpec, GenerationResult) were correct from the start

---

## 5. Final Implementation

### Files Created

```
src/forge/ui/__init__.py               # Re-exports create_application, MainWindow
src/forge/ui/app.py                    # create_application(orchestrator) — QApplication bootstrap + MainWindow instantiation
src/forge/ui/main_window.py            # MainWindow(QMainWindow) with QStackedWidget, 5 placeholder screens,
                                       #   5 named navigation buttons, lookup-table state matrix,
                                       #   generation_requested/generation_completed/cancelled signals,
                                       #   show_error/show_confirm modal helpers
src/forge/ui/screens/__init__.py       # Empty subpackage init

tests/unit/test_main_window.py         # 14 tests covering all 12 ACs
```

### Files Modified

```
src/forge/app.py                       # _launch_gui(): replaced stub with real construction
                                       #   (PluginRegistry → ValidationEngine → Orchestrator →
                                       #    forge.ui.app.create_application)
pyproject.toml                         # Added [tool.pytest.ini_options] markers: "gui"
```

### Files Not Modified

- `tests/unit/conftest.py` — `qapp` fixture already added during test-first phase; no changes needed
- `src/forge/domain/` — entirely untouched
- `src/forge/generation/` — entirely untouched
- `src/forge/plugins/` — entirely untouched
- `src/forge/infrastructure/` — entirely untouched

### Key Architecture

```python
# ── Bootstrap chain (forge.app → forge.ui) ─────────────────────────
#
# forge.app._launch_gui():
#     registry = PluginRegistry(strict=False)
#     registry.discover()
#     validator = ValidationEngine(registry)
#     orchestrator = Orchestrator(registry, validator)
#     app = forge.ui.app.create_application(orchestrator)
#     app.exec()
#
# forge.ui.app.create_application(orchestrator):
#     app = QApplication.instance() or QApplication([])
#     window = MainWindow(orchestrator)
#     window.show()
#     return app

# ── MainWindow navigation ───────────────────────────────────────────
#
# class MainWindow(QMainWindow):
#     def __init__(self, orchestrator):
#         self._stacked = QStackedWidget()     # 5 placeholder QWidget pages
#         self._prev_btn = QPushButton("Previous")     # objectName = "previous_button"
#         self._next_btn = QPushButton("Next")         # objectName = "next_button"
#         self._cancel_btn = QPushButton("Cancel")     # objectName = "cancel_button"
#         self._open_btn = QPushButton("Open Project") # objectName = "open_button"
#         self._close_btn = QPushButton("Close")       # objectName = "close_button"
#         self.navigate_to(0)
#
#     def navigate_to(self, screen_index):
#         index = max(0, min(4, screen_index))     # clamped to [0, 4]
#         self._stacked.setCurrentIndex(index)
#         self._update_navigation_buttons()
#
#     def next_screen(self):
#         if self._current_index >= 4: return       # no-op at boundary
#         if self._current_index == 3:              # 3→4 emits generation_requested
#             self.generation_requested.emit(spec)
#         self.navigate_to(self._current_index + 1)
#
#     def previous_screen(self):
#         if self._current_index <= 0: return       # no-op at boundary
#         self.navigate_to(self._current_index - 1)

# ── Navigation button state matrix (rule-based) ──────────────────────
#
# def _update_navigation_buttons(self):
#     for name, btn in {buttons}.items():
#         if index == 0 and name == "previous":
#             visible, enabled = True, False
#         elif index == 4 and name in ("previous", "next"):
#             visible, enabled = False, True
#         elif name in ("cancel", "open", "close"):
#             visible, enabled = (index == 4), True
#         else:
#             visible, enabled = True, True
#         btn.setVisible(visible); btn.setEnabled(enabled)

# ── Modal dialog helpers ────────────────────────────────────────────
#
# def show_error(self, title, message):
#     QMessageBox.critical(self, title, message)
#
# def show_confirm(self, title, message) -> bool:
#     result = QMessageBox.question(self, title, message)
#     return result == QMessageBox.StandardButton.Yes
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Tests use `QSignalSpy` + `QTest` (not `qtbot`) | Zero new dependencies — `QSignalSpy`/`QTest` ship with PySide6. Migration to `qtbot` is a trivial 3-line change per test when pytest-qt is added |
| `qapp` fixture in top-level `tests/unit/conftest.py` | Simplest path — imports PySide6 for all unit tests but avoids fixture file fragmentation. Future isolation to `tests/unit/ui/conftest.py` documented as option |
| Navigation button state uses rule-based logic (not lookup table) | Replaced spec's 25-entry dict with 12-line `if/elif/else` — screens 1–3 are identical, making the table 60% redundant data |
| PySide6 6.7.3 API: `spy.count()` / `spy.at(i)` not `len(spy)` / `spy[i]` | `QSignalSpy` in PySide6 6.7.3 lacks `__len__` and `__getitem__` — must use accessor methods |
| `QMessageBox.StandardButton.Yes` not `QMessageBox.Yes` | Shorthand enums produce `mypy` errors in strict mode; only `StandardButton.*` qualifiers are type-safe |
| `Signal(GenerationResult)` without `qRegisterMetaType` | `qRegisterMetaType` is a PyQt5 API — absent in PySide6 6.7.3. Cross-thread registration deferred to T-013 using `QMetaType` API |
| `detect_display()` preserved unchanged | Existing test imports `forge.app.detect_display` — refactoring would break the test contract |

---

## 6. Test Coverage

### Test File

`tests/unit/test_main_window.py` — **14 tests** across **12 test classes**:

| Class | Tests | Focus | AC Coverage |
|-------|-------|-------|-------------|
| `TestAC1_WindowCreation` | 1 | Title, QStackedWidget count, indices 0–4 | AC-1 |
| `TestAC2_Screen0ButtonStates` | 1 | Previous disabled, Next enabled at navigate_to(0) | AC-2 |
| `TestAC3_Screen4ButtonStates` | 1 | Previous/Next hidden, Cancel shown at navigate_to(4) | AC-3 |
| `TestAC4_ShowError` | 1 | QMessageBox.critical monkey-patched title/text | AC-4 |
| `TestAC5_ShowConfirm` | 2 | Yes→True, No→False | AC-5 |
| `TestAC6_GenerationRequestedSignal` | 1 | QSignalSpy on next_screen from screen 3 | AC-6 |
| `TestAC7_GenerationCompletedSignal` | 1 | QSignalSpy on emit(GenerationResult) | AC-7 |
| `TestAC8_NavigateToClamping` | 2 | navigate_to(-1) clamped to 0; navigate_to(10) clamped to 4 | AC-8 |
| `TestAC9_PreviousScreenBoundary` | 1 | previous_screen() at screen 0 is no-op | AC-9 |
| `TestAC10_NextScreenBoundary` | 1 | next_screen() at screen 4 is no-op | AC-10 |
| `TestAC11_ConfirmEscape` | 1 | QMessageBox.question → Escape returns False | AC-11 |
| `TestAC12_CancelSignal` | 1 | QTest.mouseClick(cancel) → cancelled signal | AC-12 |

### Test Infrastructure

- **Fixtures** (3 in test file + 1 in conftest.py):
  - `qapp` — session-scoped QApplication (conftest.py)
  - `mock_orchestrator` — `MagicMock(spec=Orchestrator)` with canned return values
  - `main_window` — constructs, shows, yields, closes `MainWindow(orchestrator=mock_orchestrator)`
- **Mocking approach**: `MagicMock(spec=Orchestrator)` — consistent with `test_orchestrator.py` patterns
- **Modal dialog strategy**: `monkeypatch.setattr(QMessageBox, "critical"/"question", ...)` — no external dependencies
- **Signal testing**: `QSignalSpy` from `PySide6.QtTest` (included in PySide6) — no pytest-qt required

### Edge Case Coverage

| Edge Case | Test | AC |
|-----------|------|-----|
| navigate_to(-1) clamped to 0 | `test_navigate_to_negative_one_clamped_to_zero` | AC-8 |
| navigate_to(10) clamped to 4 | `test_navigate_to_ten_clamped_to_four` | AC-8 |
| previous_screen() at screen 0 no-op | `test_previous_screen_at_zero_is_noop` | AC-9 |
| next_screen() at screen 4 no-op | `test_next_screen_at_four_is_noop` | AC-10 |
| show_confirm() with Escape | `test_confirm_escape_returns_false` | AC-11 |
| Cancel button emits cancelled | `test_cancel_button_emits_cancelled` | AC-12 |

### Import Purity

Tests import from:
- `forge.domain.ProjectSpec` (domain layer — allowed)
- `forge.generation.orchestrator.GenerationResult, Orchestrator` (generation layer — allowed for mock spec)

Tests do NOT import from:
- `forge.plugins` (plugin layer — mocked)
- `forge.infrastructure` (infrastructure layer — not used)
- `forge.ui` (UI layer — this is the code under test, imported via fixture)

---

## 7. Outstanding Issues

### Non-Blocking

- [ ] LOW: `open_button` and `close_button` have object names but no ACs testing their behavior — deferred to T-013+
- [ ] LOW: `cancelled` signal AC-12 tests `QTest.mouseClick(cancel)` → `cancelled` emission, but the Cancel button's connection to `GenerationWorker.cancel()` is T-013's scope
- [ ] LOW: `qapp` fixture in top-level `conftest.py` imports PySide6 for all 361 unit tests — consider moving to `tests/unit/ui/conftest.py` when more UI test files are added
- [ ] LOW: `QSignalSpy` API differs between PySide6 versions — test patterns use `spy.count()` / `spy.at(i)` which work on 6.7.3 but may differ on 6.8+
- [ ] LOW: No integration tests for this tier — screen classes (Welcome, DomainSelection, etc.) are stubs; their integration is tested in T-014/T-015

### Resolved During Review & Implementation

#### Spec-Phase (TDD Review)

- [x] pytest-qt not installed → documented in Testing Infrastructure section
- [x] No QApplication fixture → session-scoped qapp fixture documented + added to conftest.py
- [x] No object names for buttons → 5-name table added to API spec
- [x] Modal dialog testing strategy → monkey-patch pattern documented
- [x] Zero error/edge case ACs → AC-8 through AC-12 added (4 error/edge + 1 signal)
- [x] No headless CI strategy → QT_QPA_PLATFORM=offscreen + pytest marker documented
- [x] Zero signal emission ACs → AC-6 (generation_requested), AC-7 (generation_completed), AC-12 (cancelled) added
- [x] "a window appears" ambiguous → explicit show() + windowTitle() assertions
- [x] "disabled"/"hidden" ambiguous → isEnabled/isVisible split with visibility rules table
- [x] navigate_to boundary untested → AC-8 clamping
- [x] next/previous boundary untested → AC-9 (previous at 0), AC-10 (next at 4)
- [x] cancelled signal no AC → AC-12 added, deferred Cancel→worker wiring to T-013
- [x] Signal(GenerationResult) thread safety → signal type safety section added
- [x] No MockOrchestrator fixture → documented in testing infrastructure
- [x] Conftest fixture isolation → documented future migration path
- [x] show_error icon unspecified → implicitly resolved by AC-4 monkey-patching QMessageBox.critical
- [x] forge.ui.app.py vs forge.app.py → Role Boundary section resolves delegation chain
- [x] No pytest markers → @pytest.mark.gui documented
- [x] Cancel button behavior undeclared → AC-12 added
- [x] Signal import path not shown → added to API spec
- [x] Dialog close behavior → AC-11 (Escape returns False)
- [x] Test file path missing → tests/unit/test_main_window.py listed in Files to create
- [x] T-007 implicit dependency → updated in ticket metadata
- [x] Unused `from unittest.mock import patch` in example code → removed
- [x] AC-6 ProjectSpec assertion clarity → "any non-None ProjectSpec instance"
- [x] AC-7 "fires without error" → "signal received within 1000ms"
- [x] open_button/close_button visibility → added to visibility rules table

#### Implementation-Phase

- [x] `QSignalSpy` lacks `__len__`/`__getitem__` in PySide6 6.7.3 → `spy.count()` / `spy.at(0)` workaround
- [x] `QMessageBox.Yes` deprecated in mypy strict → `QMessageBox.StandardButton.Yes` throughout
- [x] `qRegisterMetaType` absent in PySide6 → deferred to T-013 with `QMetaType` API note
- [x] Missing `@pytest.mark.gui` → added to all 12 test classes
- [x] Duplicate `qapp` fixture → removed from test file (conftest handles it)
- [x] Verbose state table → refactored from 25-row dict to 12-line rule-based approach

---

## 8. Lessons Learned

### What Went Well

1. **First ticket to document test infrastructure before implementation** — Unlike T-001 (which had no test files at all) and T-007 (which relied on pre-existing infrastructure), T-012 explicitly documented every piece of test infrastructure needed (QApplication fixture, modal dialog pattern, widget identification, CI display config) before any code was written. This is the ideal Test-First Gate behavior.

2. **Cross-referencing against actual code caught the Qt infrastructure gap** — The Round 1 review found that every single AC was untestable because the Qt widget testing infrastructure didn't exist. This was discovered by reading `tests/unit/conftest.py` and `pyproject.toml`, not by abstract reasoning. No test infrastructure = no testable ACs.

3. **Modal dialog testing strategy was the hardest gap to spot** — Unlike missing fixtures or object names (which are obvious once you look at the widget tree), blocking dialog testing requires knowledge of Qt's event loop mechanics (`QMessageBox.exec()` blocks). The monkey-patch pattern is non-obvious to developers unfamiliar with Qt testing conventions.

4. **Two review rounds caught different issue depths** — Round 1 caught structural gaps (missing infrastructure, zero error/edge ACs). Round 2 caught polish issues (unused import in example code, ambiguous signal wording, conftest isolation concern). Each round found issues invisible to the previous pass.

5. **The role boundary section prevented architectural drift** — The existing `forge.app._launch_gui()` stub and the proposed `forge.ui.app.py` had an ambiguous relationship until the call chain was explicitly documented. Without this, implementation could have produced either a circular delegation or duplicated bootstrap logic.

6. **Test-first implementation used zero new dependencies** — By choosing `QSignalSpy` + `QTest` (both ship with PySide6) instead of `qtbot` (pytest-qt), the test file has no external test dependency beyond what's already installed. This makes the test-first gate pass even without modifying `pyproject.toml`.

7. **The `MainWindow` API spec was correct from the start** — Unlike T-007 (which had return type mismatches with `list[TemplateDefinition]` vs `list[PluginBase]`), T-012's API spec referenced types that actually exist (`Orchestrator`, `ProjectSpec`, `GenerationResult`) with correct signatures. The only spec issues were about testability, not about the API contract itself.

8. **14 tests for 12 ACs is the right density** — Each test maps directly to one AC, except AC-5 (2 tests: Yes and No branches) and AC-8 (2 tests: -1 clamp and 10 clamp). No redundant tests, no missing coverage. This is the cleanest AC-to-test mapping in the project so far.

9. **Test-first caught PySide6 6.7.3 API quirks immediately** — The 3 test-level patches (`len(spy)` → `spy.count()`, `spy[0]` → `spy.at(0)`, `QMessageBox.Yes` → `StandardButton.Yes`) were discovered by running the test-first file against the actual PySide6 version, not by spec review. All fixes were test-level — zero production code changes needed. This validates the test-first approach for version-specific API compatibility.

10. **State table refactoring showed lookup-table vs rule-based tradeoff** — The initial 25-entry dict was straightforward but 60% redundant (screens 1–3 identical). The rule-based replacement (12 lines) is more concise but slightly harder to map back to the spec's visibility matrix. Both are correct; the rule-based version was chosen for maintainability.

11. **Zero new dependencies despite being the first Qt ticket** — `QSignalSpy` and `QTest` ship with PySide6; `MagicMock` is stdlib; `monkeypatch` is built into pytest. The implementation added no `pyproject.toml` dependencies beyond the `gui` marker. This is the cleanest dependency footprint of any ticket so far.

12. **Code review found issues the spec phase could not** — The 5 code review findings (missing `@pytest.mark.gui`, duplicate fixture, deprecated enums, verbose table, `qRegisterMetaType` not applicable) were all about implementation quality, not spec correctness. Even with a thorough TDD review, code review adds independent value.

### What Could Improve

1. **First Qt ticket should explicitly document that QApplication is needed** — The original ACs treated Qt widget tests like pure-Python tests. Any ticket that creates `QWidget` subclasses should, by convention, include a "Testing Infrastructure" section that documents the QApplication lifecycle requirement.

2. **Modal dialog testing needs a reusable project pattern** — Currently, each test file reinvents the monkey-patch pattern for `QMessageBox`. Consider extracting a `patch_message_box` fixture to `tests/unit/_shared.py` once a second UI test file needs it.

3. **Widget identification by object name should be a project convention** — Every `QWidget` subclass in the project should have `setObjectName()` calls documented in the same way T-012 specifies. Without this, UI tests become fragile.

4. **The `qapp` fixture placement is a tradeoff** — Putting it in top-level `conftest.py` imports PySide6 for all tests (adding ~100ms to collection time) but avoids file fragmentation. A `tests/unit/ui/conftest.py` is cleaner for CI but adds complexity. The documented migration path is sufficient.

5. **AC-12 (cancelled signal) depends on button click-to-signal wiring** — This AC tests that clicking the Cancel button emits `cancelled`. But the Cancel button's connection to `GenerationWorker.cancel()` is T-013's scope. AC-12 tests the UI wiring but not the orchestration. This is correct separation of concerns, but the boundary should be explicitly documented.

6. **`from PySide6.QtTest import QSignalSpy, QTest` should be the project standard** — Unlike `qtbot.waitSignal`, `QSignalSpy` works without any test framework dependency. It's slightly more verbose (3 lines instead of 1) but more explicit and framework-agnostic. Consider establishing this as the project convention for signal testing.

7. **No integration tests specified for this ticket** — Unlike T-007 which had `[integration]`-tagged ACs, T-012 is purely a unit-test ticket. The screen classes (Welcome, DomainSelection, Configuration, Review, Generation) are stubs — their integration is tested in subsequent tickets.

8. **`QRegisterMetaType` is PyQt5 API, not PySide6** — The spec and all review rounds assumed `qRegisterMetaType(GenerationResult)` was available. It does not exist in PySide6 6.7.3. Cross-thread signal registration for custom types in PySide6 uses `QMetaType` and has a different API. Any future cross-thread work (T-013) should verify the actual PySide6 API, not assume PyQt5 patterns translate.

9. **PySide6 version-specific API differences are a recurring risk** — The `QSignalSpy.__len__`/`__getitem__` difference between PySide6 6.6 and 6.7.3 was discovered only by running tests. The project pins `pyside6>=6.6.0,<6.8.0` which spans multiple API-breaking versions. Consider CI testing against both boundaries, or establishing a minimum-version-required policy for specific APIs.

10. **State table verbosity was not caught by spec review** — The 25-entry dict in the API spec was accepted in both TDD review rounds. Only code review flagged it as overly verbose. Spec review focuses on behavioral correctness, not implementation elegance — code review is the right layer for style improvements.

### Key Metrics

| Metric | Value |
|--------|-------|
| Original ACs | 5 |
| Refined ACs | 12 |
| TDD review rounds | 2 |
| Code review rounds | 1 |
| Implementation issues found by dependency analysis | 4 |
| Files created | 4 (source) + 1 (test) |
| Files modified | 2 |
| Files not modified (but considered) | 1 (conftest.py — qapp fixture was pre-existing) |
| Total tests | 14 |
| Full suite result | 361/361 pass (14 T-012 + 347 existing) |
| Test fixtures | 2 (inline) + 1 (conftest.py) |
| Issues found by TDD review | 7 blocking + 10 moderate + 7 low (R1) → 0 blocking + 3 moderate + 4 low (R2) |
| Issues found by implementation | 5 (3 PySide6 API quirks + 2 refactoring needs) |
| Issues found by code review | 5 minor (all fixed) |
| Issues resolved in ticket | 30 (24 spec + 6 implementation) |
| Issues deferred | 3 (open_button/close_button ACs, conftest isolation, QSignalSpy version compat) |
| New dependencies | 0 (QSignalSpy + QTest ship with PySide6) |
| Mock complexity | Low (MagicMock spec=Orchestrator, monkeypatch for QMessageBox) |
| Source lines added | ~190 (4 files) |
| Test lines added | ~237 (1 file) |
| `ruff` | Clean |
| `mypy` | Clean (39 source files, 0 errors) |

---

## 9. Acceptance Criteria Verification

| AC | Test(s) | Verification Method | Status |
|----|---------|---------------------|--------|
| AC-1 | `test_window_title_and_stacked_widget` | `windowTitle()`, `findChild(QStackedWidget).count()`, indices 0–4 | ✅ |
| AC-2 | `test_previous_disabled_next_enabled_at_screen_0` | `findChild(QPushButton, "previous_button").isEnabled()`, `next_button.isEnabled()` | ✅ |
| AC-3 | `test_previous_next_hidden_cancel_shown` | `previous_button.isVisible()`, `next_button.isVisible()`, `cancel_button.isVisible()` | ✅ |
| AC-4 | `test_show_error_calls_critical` | Monkey-patch `QMessageBox.critical` — captured `title` and `text` | ✅ |
| AC-5 | `test_confirm_yes_returns_true`, `test_confirm_no_returns_false` | Monkey-patch `QMessageBox.question` — Yes→True, No→False | ✅ |
| AC-6 | `test_generation_requested_emitted_on_next_from_screen_3` | `QSignalSpy` — signal triggered, `isinstance(args[0], ProjectSpec)` | ✅ |
| AC-7 | `test_generation_completed_signal_received` | `QSignalSpy` — `emit(GenerationResult)`, signal received in 1000ms, fields match | ✅ |
| AC-8 | `test_navigate_to_negative_one_clamped_to_zero`, `test_navigate_to_ten_clamped_to_four` | `navigate_to(-1)` → index 0, `navigate_to(10)` → index 4 | ✅ |
| AC-9 | `test_previous_screen_at_zero_is_noop` | `navigate_to(0)` → `previous_screen()` → index stays 0 | ✅ |
| AC-10 | `test_next_screen_at_four_is_noop` | `navigate_to(4)` → `next_screen()` → index stays 4 | ✅ |
| AC-11 | `test_confirm_escape_returns_false` | Monkey-patch `QMessageBox.question` → Escape returns False | ✅ |
| AC-12 | `test_cancel_button_emits_cancelled` | `QTest.mouseClick(cancel)` → `QSignalSpy` on `cancelled` → `spy.count() == 1` | ✅ |

---

## 10. Timeline

| Date | Activity |
|------|----------|
| June 22, 2026 | Original ticket loaded (5 ACs, no Qt test infrastructure) |
| June 22, 2026 | TDD review round 1 (NEEDS REVISION — 7 blocking + 10 moderate + 7 low issues) |
| June 22, 2026 | Fixed R1: added Testing Infrastructure section (pytest-qt, qapp fixture, mock orchestrator, modal dialog pattern, headless CI), added object names, expanded to 12 ACs, added role boundary, visibility rules, navigation boundaries |
| June 22, 2026 | TDD review round 2 (PASS_WITH_MINOR_FIXES — 0 blocking + 3 moderate + 4 low issues) |
| June 22, 2026 | Fixed R2: removed unused import, added Signal import to API spec, clarified AC-6/AC-7 wording, added cancelled signal AC-12, added open_button/close_button visibility rows, added conftest isolation note |
| June 22, 2026 | Test-first implementation: `tests/unit/test_main_window.py` (14 tests) + `qapp` fixture in `tests/unit/conftest.py` |
| June 22, 2026 | Verification: 14/14 tests fail with `ModuleNotFoundError: No module named 'forge.ui.main_window'` (expected), 347/347 existing tests still pass |
| June 22, 2026 | Post-mortem written (pre-implementation) |
| June 23, 2026 | **Implementation**: created 4 source files (`ui/__init__.py`, `ui/app.py`, `ui/main_window.py`, `ui/screens/__init__.py`), modified `forge.app.py` `_launch_gui()`, added `gui` marker to `pyproject.toml` |
| June 23, 2026 | **Test debugging**: 3 PySide6 6.7.3 API fixes (`len(spy)` → `spy.count()`, `spy[0]` → `spy.at(0)`, `QMessageBox.Yes` → `QMessageBox.StandardButton.Yes`); removed duplicate `qapp` fixture; removed unused `sys` import |
| June 23, 2026 | **Code review**: 5 issues found (missing `@pytest.mark.gui`, duplicate fixture, deprecated enums, verbose state table, `qRegisterMetaType` not applicable). All fixed |
| June 23, 2026 | **Verification**: 361/361 tests ✅ (14 T-012 + 347 existing), `ruff` clean ✅, `mypy` clean (39 source files, 0 errors) ✅ |
| June 23, 2026 | Post-mortem updated with implementation phase |

---

## 11. Next Steps

1. Mark T-012 as ✅ COMPLETE in tickets index document
2. Proceed to T-013 (GenerationWorker) — depends on MainWindow signals (`generation_requested`, `generation_completed`, `cancelled`) and navigation contract established here
3. Consider extracting `patch_message_box` helper to `tests/unit/_shared.py` when a second UI test file needs modal dialog testing
4. Consider moving `qapp` fixture to `tests/unit/ui/conftest.py` when UI test files exceed 2-3
5. T-014/T-015 will replace the 5 placeholder `QWidget` stubs with real screen classes (Welcome, DomainSelection, Configuration, Review, Generation)

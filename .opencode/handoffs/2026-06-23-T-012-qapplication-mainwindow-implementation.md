# Session Handoff: T-012 QApplication + MainWindow Implementation
**Date**: 2026-06-23
**Ticket/Feature**: T-012 (QApplication Bootstrap + MainWindow Shell)
**Session Duration**: ~90 minutes

## Context
Goal: Implement T-012 — create the PySide6 QApplication bootstrap and MainWindow shell with QStackedWidget + navigation footer + modal helpers. Replace the `_launch_gui()` stub from T-007 with real bootstrap code. Post-mortem also updated.

## Progress
- [x] **Completed**: Created 4 source files (`ui/__init__.py`, `ui/app.py`, `ui/main_window.py`, `ui/screens/__init__.py`) — MainWindow with 5 placeholder screens, 5 named navigation buttons, rule-based state matrix, 3 signals, `show_error`/`show_confirm` helpers
- [x] **Completed**: Modified `forge.app.py` `_launch_gui()` — replaced stub with real PluginRegistry → ValidationEngine → Orchestrator → `forge.ui.app.create_application()` chain
- [x] **Completed**: Added `gui` pytest marker to `pyproject.toml`
- [x] **Completed**: PySide6 6.7.3 API patches — `len(spy)` → `spy.count()`, `spy[0]` → `spy.at(0)`, `QMessageBox.Yes` → `QMessageBox.StandardButton.Yes`
- [x] **Completed**: Code review fixes — added `@pytest.mark.gui` to all 12 test classes, removed duplicate `qapp` fixture, fixed deprecated enum values, refactored state table from 25-row dict to rule-based
- [x] **Completed**: Updated post-mortem at `docs/context/post-mortem/tdd-qapplication-mainwindow.md` with implementation phase
- [ ] **Incomplete**: Nothing — all T-012 ACs are implemented, passing, and reviewed

## Current State
- **Last completed action**: Post-mortem updated with implementation-phase content; handoff document created
- **Key decisions made**:
  - `qRegisterMetaType()` is a PyQt5 API — does not exist in PySide6 6.7.3. Cross-thread registration deferred to T-013 using `QMetaType`
  - `pytest-qt` not needed — `QSignalSpy` + `QTest` ship with PySide6
  - Navigation button state uses rule-based logic (not lookup table) — 12 lines vs 25-entry dict
  - `QMessageBox.StandardButton.Yes` required — shorthand enums produce `mypy` errors
- **Key decisions pending**: None
- **Blockers**: None

## Code Context
New files (untracked):
```
src/forge/ui/__init__.py               # Re-exports
src/forge/ui/app.py                    # create_application(orchestrator)
src/forge/ui/main_window.py            # MainWindow(QMainWindow) — 144 lines
src/forge/ui/screens/__init__.py       # Empty init
tests/unit/test_main_window.py         # 14 tests, 12 ACs, 237 lines
```

Modified files (unstaged):
```
docs/context/dependency-analysis.md    # Updated with T-012 dependency chain
docs/context/tickets/012-qapplication-mainwindow.md  # Ticket spec
pyproject.toml                         # Added gui marker
src/forge/app.py                       # _launch_gui() real bootstrap
tests/unit/conftest.py                 # qapp fixture (pre-existing)
```

New documentation:
```
docs/context/post-mortem/tdd-qapplication-mainwindow.md  # Post-mortem (637 lines)
```

Key architecture in `src/forge/ui/main_window.py` (144 lines):
- `MainWindow.__init__()` — constructs QStackedWidget (5 pages) + 5 named QPushButtons in footer + signal wiring + `navigate_to(0)`
- `navigate_to(index)` — clamps to [0,4], sets stacked index, updates buttons
- `next_screen()` — emits `generation_requested` on 3→4 transition; no-op at 4
- `previous_screen()` — no-op at 0
- 5 object names: `previous_button`, `next_button`, `cancel_button`, `open_button`, `close_button`
- 3 signals: `generation_requested(ProjectSpec)`, `generation_completed(GenerationResult)`, `cancelled()`
- Rule-based `_update_navigation_buttons()`: special cases for screen 0 (prev disabled) and screen 4 (prev/next hidden, cancel/open/close shown)

## Specs Reference
- Ticket spec: `docs/context/tickets/012-qapplication-mainwindow.md`
- Post-mortem: `docs/context/post-mortem/tdd-qapplication-mainwindow.md`
- Architecture: `docs/context/architecture.md`
- Dependency analysis: `docs/context/dependency-analysis.md`
- Process flow: `docs/context/process-flow.md`
- ADR Index: `docs/adr/`

## Agent Outputs
- **Code Review**: APPROVE — All 12 ACs pass (14/14 tests). 5 minor issues found and fixed. Verdict: APPROVE

## Do Not Redo
- Do NOT use `qRegisterMetaType()` — it is a PyQt5 API, absent in PySide6 6.7.3. For cross-thread registration, use PySide6's `QMetaType` API (T-013 concern)
- Do NOT use `QMessageBox.Yes` / `QMessageBox.No` / `QMessageBox.Ok` — shorthand enums produce `mypy` errors. Always use `QMessageBox.StandardButton.Yes` etc.
- Do NOT use `len(QSignalSpy)` or `spy[i]` in PySide6 6.7.3 — `QSignalSpy` lacks `__len__`/`__getitem__`. Use `spy.count()` and `spy.at(i)` instead
- Do NOT use `qtbot` / `pytest-qt` — `QSignalSpy` + `QTest` ship with PySide6 and work without extra dependencies

## Next Steps (Prioritized)
1. **[T-013] GenerationWorker**: Implement QThread-based GenerationWorker that receives `generation_requested`, runs generation async, and emits `generation_completed`. Depends on MainWindow signals established here
2. **[T-014/T-015] Real screens**: Replace the 5 placeholder `QWidget` stubs with real screen classes (Welcome, DomainSelection, Configuration, Review, Generation)
3. **[Follow-up] Extract `patch_message_box`**: When a second UI test file needs modal dialog testing, extract to `tests/unit/_shared.py`
4. **[Follow-up] Move `qapp` fixture**: When UI test files exceed 2-3, move to `tests/unit/ui/conftest.py`

## Environment
- **Working directory**: `/Users/gabriel/GItHub/project-creator`
- **Commands to run**:
  - `uv run pytest tests/` — full suite (361 tests)
  - `uv run pytest tests/unit/test_main_window.py -v` — T-012 tests only (14)
  - `uv run ruff check src/forge/ui/ tests/unit/test_main_window.py` — lint
  - `uv run mypy -p forge` — typecheck
- **Key constraint**: All T-012 files are UNCOMMITTED. Run `git add` for new files + `git add -u` for modifications before committing

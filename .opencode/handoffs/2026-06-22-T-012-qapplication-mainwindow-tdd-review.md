# Session Handoff: T-012 QApplication Bootstrap + MainWindow Shell — TDD Review Gate
**Date**: 2026-06-22
**Ticket/Feature**: T-012 QApplication Bootstrap + MainWindow Shell
**Session Duration**: ~90 minutes

## Context
Review T-012 through 2 TDD review rounds (critique → fix spec → re-review) and produce a test-first gate (14 tests, zero production code) that validates all 12 acceptance criteria are testable. All structural issues found in the spec phase — no implementation began.

## Progress
- [x] **Completed**: TDD Review Round 1 — found 7 blocking + 10 moderate + 7 low issues; verdict NEEDS_REVISION
- [x] **Completed**: Fixed all R1 issues — expanded ACs from 5→12, added Testing Infrastructure section, Role Boundary, Navigation Boundary Behavior, Signal Emission Triggers, button object names table, visibility rules matrix, headless CI strategy, modal dialog monkey-patch pattern
- [x] **Completed**: TDD Review Round 2 — 0 blocking + 3 moderate + 4 low issues; verdict PASS_WITH_MINOR_FIXES
- [x] **Completed**: Fixed all R2 minor issues — removed unused import, added Signal import to API spec, clarified AC-6/AC-7 wording, added cancelled signal AC-12, open_button/close_button visibility rows, conftest isolation note
- [x] **Completed**: Created `tests/unit/test_main_window.py` — 14 tests across 12 classes covering all 12 ACs
- [x] **Completed**: Added `qapp` fixture to `tests/unit/conftest.py` (session-scoped QApplication)
- [x] **Completed**: Confirmed 14/14 tests fail with expected `ImportError` (ModuleNotFoundError — production code doesn't exist yet); 347/347 existing tests still pass
- [x] **Completed**: Created `docs/context/post-mortem/tdd-qapplication-mainwindow.md` — full post-mortem with 10 sections
- [x] **Completed**: Marked T-012 as TDD REVIEW COMPLETE in ticket file and dependency-analysis.md

## Current State
- **Last completed action**: Marked T-012 as ✅ TDD REVIEW COMPLETE in dependency analysis and ticket metadata
- **Key decisions made**:
  - Tests use `QSignalSpy` + `QTest` (PySide6 built-ins) instead of `qtbot` (pytest-qt not installed) — cleaner TDD failure signal, trivial migration later
  - `qapp` fixture placed in top-level `tests/unit/conftest.py` for simplicity, with documented option to move to `tests/unit/ui/conftest.py`
  - `cancelled` signal AC-12 tests Cancel→`cancelled` emit, but Cancel→GenerationWorker wiring explicitly deferred to T-013
  - Button visibility uses `isEnabled()`/`isVisible()` split: `Disabled` = `setEnabled(False)`, `Hidden` = `setVisible(False)`, `Shown` = `setVisible(True)`
  - `forge.ui.app.py` vs `forge.app.py` resolved via Role Boundary section: `_launch_gui()` delegates to `forge.ui.app.create_application()`
- **Key decisions pending**: None — test-first gate complete
- **Blockers**: None — ready for implementation

## Code Context
Changed files in working tree (relative to HEAD~1 — also includes T-011 HTMX Plugin):
```
docs/context/dependency-analysis.md          # T-012 status marker added
docs/context/tickets/012-qapplication-mainwindow.md  # Full spec rewrite (5→12 ACs)
tests/unit/conftest.py                       # qapp fixture added
tests/unit/test_main_window.py               # NEW — 14 tests (untracked)
docs/context/post-mortem/tdd-qapplication-mainwindow.md  # NEW — full post-mortem (untracked)
```

Run `git diff HEAD~1` for the full diff. Key files to read:
- `tests/unit/test_main_window.py` — 14 tests across 12 classes
- `docs/context/tickets/012-qapplication-mainwindow.md` — canonical spec
- `docs/context/post-mortem/tdd-qapplication-mainwindow.md` — all 24 issues found and resolved

## Specs Reference
- Ticket: `docs/context/tickets/012-qapplication-mainwindow.md`
- Post-mortem: `docs/context/post-mortem/tdd-qapplication-mainwindow.md`
- Architecture: `docs/context/architecture.md`
- Pipeline: `docs/context/pipeline.md`
- Forge Architecture: `docs/context/architecture.md`
- Forge Pipeline: `docs/context/pipeline.md`
- Forge Process Flow: `docs/context/process-flow.md`
- ADR Index: `docs/adr/`

## Agent Outputs
Findings from review agents are appended inline below.

- **TDD Review (Round 1)**: NEEDS_REVISION — 7 blocking (missing QApplication fixture, no button object names, no modal dialog strategy, zero error/edge ACs, no headless CI, zero signal ACs, no object names), 10 moderate, 7 low
- **TDD Review (Round 2)**: PASS_WITH_MINOR_FIXES — 0 blocking, 3 moderate (cancelled signal deferred, open_button/close_button incomplete, conftest isolation), 4 low (unused import, Signal import path, AC-6 wording, AC-7 wording)
- **Architecture Review**: Not needed (no production code yet)
- **Code Review**: Not needed (test-only file; pattern validated by existing tests)

## Do Not Redo
- Don't add `pytest-qt` as a dependency before implementation — `QSignalSpy` + `QTest` work without it; migration is trivial later
- Don't test Cancel→GenerationWorker wiring in this ticket — AC-12 tests button→signal, but worker wiring is T-013
- Don't create `tests/unit/ui/conftest.py` yet — one UI test file doesn't warrant the isolation; documented migration path exists
- Don't use `qtbot` for tests — zero-dependency `QSignalSpy` approach provides a cleaner TDD failure signal

## Next Steps (Prioritized)
1. **[Implementation]**: Create `src/forge/ui/__init__.py`, `src/forge/ui/app.py`, `src/forge/ui/main_window.py`, `src/forge/ui/screens/__init__.py` — implement the MainWindow shell with QStackedWidget, navigation footer, button visibility rules, and modal dialog helpers
2. **[Verify]**: Run `uv run pytest tests/unit/test_main_window.py -v --no-header` — all 14 tests should pass
3. **[Verify]**: Run `uv run pytest tests/ -v --no-header` — confirm 347+1=361 tests pass with zero regressions
4. **[Verify]**: Run `uv run mypy -p forge` — confirm type-check passes
5. **[Config]**: Add `@pytest.mark.gui` marker to `pyproject.toml` under `[tool.pytest.ini_options]`
6. **[Optional]**: Add `pytest-qt` to dev dependencies post-implementation (for `qtbot.waitSignal` convenience in T-013+)
7. **[Next ticket]**: Proceed to T-013 (GenerationWorker) which depends on `MainWindow.generation_completed`, `MainWindow.cancelled`, and `MainWindow.show_error()` established here

## Environment
- **Working directory**: `/Users/gabriel/GItHub/project-creator`
- **Commands to run**: `uv sync`, `uv run pytest tests/unit/test_main_window.py -v --no-header`, `uv run mypy -p forge`
- **Environment variables**: `QT_QPA_PLATFORM=offscreen` for headless CI runs

# Session Handoff: T-019 Output Directory Picker — Full Implementation
**Date**: 2026-06-26
**Ticket/Feature**: T-019 — Output Directory Picker on Welcome Screen
**Session Duration**: Full session (spec + TDD review + implementation + code review + post-mortem)

## Context
Add a Browse button to the Welcome screen so users can choose where generated projects are created instead of `Path.cwd() / project_name`. The ticket went through the full pipeline: drafted (9 ACs), 2 TDD review rounds (→ 11 refined ACs), test-first (18 tests), implementation (3 source files + 2 test migrations), code review (C.L.E.A.R., APPROVED), and post-mortem.

## Progress
- [x] **Completed**: Ticket drafted, TDD Review Rounds 1 & 2, 18 tests written (test-first)
- [x] **Completed**: Implementation — `welcome_screen.py` (Browse button, `_parent_dir: str = ""`, path label, `_update_path_label()`), `main_window.py` (`_output_parent_dir` property, `navigate_to()` wiring, parent-dir check in `next_screen()`), `review_screen.py` (`set_output_dir()`, dynamic `on_enter()` path)
- [x] **Completed**: Existing test migration — 2 tests in `test_wizard_screens_4_5.py` (Path.exists monkeypatch), 1 test in `test_wizard_screens.py` (output_parent_dir key)
- [x] **Completed**: Quality gate — ruff (0 new issues), mypy (0 new issues), pytest (18/18 new + 510/510 total passing)
- [x] **Completed**: Code review (C.L.E.A.R. framework) — APPROVE, 2 minor + 1 cosmetic, fixes applied
- [x] **Completed**: Post-mortem at `docs/context/post-mortem/tdd-output-directory-picker.md` (full lifecycle, 573 lines)
- [ ] **Incomplete**: Mark ticket complete in tickets index document
- [ ] **Incomplete**: End-to-end integration test for output dir through full pipeline (future)
- [ ] **Incomplete**: Session handoff archived

## Current State
- **Last completed action**: Post-mortem updated with full implementation details; code review fixes #1 and #2 applied to source
- **Key decisions made**:
  - `_parent_dir` stored as `str = ""` (not `Path`) to preserve trailing slashes from QFileDialog
  - `_output_parent_dir` implemented as property with lazy `Path.cwd()` fallback (for test compatibility — `Path.cwd()` evaluated at access time, not init time)
  - `_update_path_label()` extracted as helper — called from both `__init__` and `_on_browse`
  - `output_parent_dir` extracted in `navigate_to()` index-3 block, not `_build_spec()` (preserving T-014 purity)
  - Parent-dir existence check (`output_dir.parent.exists()`) added before overwrite check in `next_screen()`
  - `Path.exists` monkeypatch in nonexistent-parent test made surgical (`lambda self: self != Path(...)`) instead of blanket `lambda self: False`
- **Key decisions pending**: None — feature complete
- **Blockers**: None

## Code Context
Run: `git status` — 8 modified files + 4 untracked files (ticket doc, tests, post-mortem, handoff):

Modified source:
- `src/forge/ui/screens/welcome_screen.py` — Browse button, path label, `_parent_dir: str = ""`, `_update_path_label()`, `get_spec_update()` returns `output_parent_dir`
- `src/forge/ui/main_window.py` — `_output_parent_dir` property, `navigate_to()` index-3 block, parent-dir check in `next_screen()`
- `src/forge/ui/screens/review_screen.py` — `set_output_dir()`, `on_enter()` dynamic path

Modified tests:
- `tests/unit/test_main_window.py` — `Path.exists` monkeypatch updated
- `tests/unit/test_wizard_screens.py` — `output_parent_dir` key added to expected dict
- `tests/unit/test_wizard_screens_4_5.py` — `Path.exists` monkeypatch lambdas updated

Untracked:
- `tests/unit/test_output_directory_picker.py` — 18 tests, all passing
- `docs/context/tickets/019-output-directory-picker.md` — the ticket
- `docs/context/post-mortem/tdd-output-directory-picker.md` — full post-mortem
- `docs/context/dependency-analysis.md` — unrelated dependency analysis (pre-existing)

## Specs Reference
- Ticket: `docs/context/tickets/019-output-directory-picker.md`
- Post-mortem (full): `docs/context/post-mortem/tdd-output-directory-picker.md`
- Tests: `tests/unit/test_output_directory_picker.py`
- WelcomeScreen: `src/forge/ui/screens/welcome_screen.py`
- MainWindow: `src/forge/ui/main_window.py`
- ReviewScreen: `src/forge/ui/screens/review_screen.py`
- Forge Architecture: `docs/context/architecture.md`
- Forge Pipeline: `docs/context/pipeline.md`

## Agent Outputs
- **Architecture Review**: Not invoked
- **Code Review**: C.L.E.A.R. framework — APPROVE, 3 findings (all resolved):
  - Minor #1: `_parent_dir: str | None = None` → `_parent_dir: str = ""` with truthiness guard (consistent sentinel pattern)
  - Minor #2: `test_nonexistent_parent` used blanket `lambda self: False` for `Path.exists` → changed to surgical `lambda self: self != Path("/nonexistent/parent")`
  - Cosmetic #3: Imports inside test functions — kept as-is per team style
- **Pre-Commit Check**: Not invoked
- **Security Diagnosis**: Not invoked
- **TDD Review**:
  - **Round 1** (NEEDS REVISION — 2 blocking + 6 moderate + 4 low): AC-8 integration-level I/O, AC-9 parent-dir check not in spec, AC-1 wording, tooltip not in spec, _build_spec side-effect, missing test migration, no Browse cancellation AC, no _output_parent_dir default
  - **Round 2** (APPROVE — 3 minor): AC-1 ambiguous title, AC-8 testing strategy missing, migration section inaccuracy — all resolved

## Do Not Redo
- Do NOT put `output_parent_dir` extraction inside `_build_spec()` — that method is a pure-assembly function. Extract it in `navigate_to()` before calling `_build_spec()`, matching the pattern used for `backend_id`/`frontend_id` extraction from DomainSelectionScreen
- Do NOT write AC-8 as I/O verification ("files are created under the path") — unit tests can't run the full generation pipeline. Keep it as data-flow verification ("worker constructed with correct output_dir")
- Do NOT assert `"a dialog opens"` for `QFileDialog.getExistingDirectory` — in offscreen CI the dialog never renders. Assert it was *called* with the correct parent/title args instead
- Do NOT add a tooltip assertion to the AC if `setToolTip()` is not documented in the API spec — keep API spec as the single source of truth
- Do NOT rely on `len(QSignalSpy)` or `spy[i]` — use `spy.count()` and `spy.at(i)` instead (PySide6 6.7.3 quirk documented in T-012)
- Do NOT use `Path` for `_parent_dir` — `QFileDialog.getExistingDirectory` returns a `str` that may include trailing slashes; `Path` normalizes them away. Store as `str`
- Do NOT initialize `_output_parent_dir` with `Path.cwd()` at class/init time — tests monkeypatch `Path.cwd()` after construction. Use a property with lazy `Path.cwd()` fallback evaluated at access time
- Do NOT use blanket `lambda self: False` for `Path.exists` monkeypatches — existing test code paths may call `Path.exists()` and break. Use surgical lambdas targeting specific paths

## Next Steps (Prioritized)
1. **Mark ticket complete**: Update tickets index document to mark T-019 as complete
2. **End-to-end integration test**: Add E2E test verifying output directory flows through the full generation pipeline (or file as T-018 follow-up)
3. **Archive session**: Generate continuation document for future sessions (this handoff serves as archive)

## Environment
- **Working directory**: `/Users/gabriel/GItHub/project-creator`
- **Commands to run**: `uv run pytest tests/unit/test_output_directory_picker.py -v --no-header`
- **Environment variables**: `QT_QPA_PLATFORM=offscreen` for headless GUI tests

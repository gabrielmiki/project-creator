# Session Handoff: T-018 Full Pipeline Integration Tests — Implementation
**Date**: 2026-06-26
**Ticket/Feature**: T-018 — Integration Tests Full Pipeline (All Plugins, GUI Worker, Overwrite, Error/Rollback)
**Session Duration**: ~120 minutes

## Context

Implement 19 integration tests (4 files) exercising the complete pipeline: multi-plugin combos (fastapi+react, django+htmx), GUI worker thread lifecycle, overwrite confirmation flow, and error/rollback scenarios. This is the final integration test ticket after T-016 (foundation) and T-017 (CLI + pipeline).

## Progress

- [x] **TDD Review Round 1 completed** — 4 blocking + 7 moderate issues found
- [x] **Ticket revised** — all 11 issues fixed (pairwise specs, signal routing, dead-signal replacement, deferred special-chars, CLI dual patterns, scaffold overlap test, etc.)
- [x] **TDD Review Round 2 completed** — APPROVED with 1 minor N-I1 (Django config keys)
- [x] **Django config keys fixed** — `database`/`include_drf` instead of `orm`/`auth`/`include_alembic`
- [x] **Dependency analysis written** — updated `docs/context/dependency-analysis.md` with T-018 section
- [x] **4 test files created**: `test_all_plugins.py` (4), `test_gui_worker.py` (4), `test_overwrite_flow.py` (3), `test_error_scenarios.py` (8)
- [x] **conftest.py extended** — 4 GUI fixtures (`qapp` session-scoped, `full_spec`, `django_htmx_spec`, `worker`)
- [x] **Domain scanner fixed** — excluded `conftest.py`, `test_gui_*`, `test_overwrite_*` to prevent false positives
- [x] **Post-mortem created** — `docs/context/post-mortem/tdd-integration-tests-full-pipeline.md`
- [x] **Full test suite verified** — 493 passed, 1 skipped, 0 failures

## Current State

- **Last completed action**: Post-mortem written; all 493 tests green
- **Key decisions made**:
  - Pairwise plugin combos (`full_spec=fastapi+react`, `django_htmx_spec=django+htmx`) instead of 4-plugin spec (impossible — `ProjectSpec` has only 2 slots)
  - `monkeypatch.setattr` instead of `.side_effect` for mocking real `Orchestrator.generate` method
  - `MagicMock(wraps=orchestrator)` for signal-routing tests needing partial mocking
  - `QSignalSpy` (not `pytest-qt`) — matches existing test infrastructure
  - Session-scoped `qapp` — prevents QObject lifetime crashes in threaded tests
- **Key decisions pending**: None (ticket is complete)
- **Blockers**: None

## Code Context

Run: `git diff HEAD~1` to see implementation changes (4 new test files + conftest + domain scanner + post-mortem)

## Specs Reference

- Post-mortem: `docs/context/post-mortem/tdd-integration-tests-full-pipeline.md`
- Forge Architecture: `docs/context/architecture.md`
- Ticket: `docs/context/tickets/018-integration-tests-full-pipeline.md`
- Dependency Analysis: `docs/context/dependency-analysis.md`

## Agent Outputs

Findings from review agents are appended inline below.

- **Architecture Review**: Not invoked
- **Code Review**: 6 issues found during implementation (all fixed): React `package.json` assertion (scaffold-only), `_make_template` doesn't exist, `.side_effect` on real method, missing `mock_orchestrator` fixture, `_generation_output_path` assertion wrong, domain scanner over-broad
- **Pre-Commit Check**: Not invoked
- **Security Diagnosis**: Not invoked
- **TDD Review**: 
  - **Round 1** (NEEDS REVISION — 4 blocking + 7 moderate): See `.opencode/handoffs/2026-06-26-t018-tdd-review.md`
  - **Round 2** (APPROVED — 1 minor N-I1): See `.opencode/handoffs/2026-06-26-t018-tdd-review-round2.md`

## Do Not Redo

- Do NOT assert `(output_dir / "package.json").exists()` when `mock_executor` is used — React's `files()` does NOT produce `package.json` (it's scaffold-only from `create-vite`)
- Do NOT try to set `.side_effect` on `orchestrator.generate` — it's a real method, not a MagicMock. Use `monkeypatch.setattr(orchestrator, "generate", replacement_fn)`
- Do NOT assert `window._generation_output_path is not None` after `next_screen()` when `QThread.start` is monkeypatched to no-op — `_generation_output_path` is set in `_on_generation_finished` which never fires. Use `window._worker is not None` and `window._stacked.currentIndex() == 4` instead
- Do NOT call `pipeline_registry._make_template("a", "b")` — `PluginRegistry` has no such method. Use `spec_factory(backend_id="a", frontend_id="b")` or construct `TemplateDefinition` directly
- Do NOT add `worker` fixture to conftest if it imports `forge.ui.*` — the domain isolation scanner (`test_domain_models.py`) will flag it. Either exclude the file from the scanner or use a deferred import within the fixture function body

## Next Steps (Prioritized)

1. **Mark ticket complete** in tickets index document
2. **Consider CI GUI workflow**: `QT_QPA_PLATFORM=offscreen pytest -m "gui" -v` for headless GUI test execution
3. **Consider implementing sanitization** for `test_error_special_chars_in_name` (currently deferred)
4. **Consider fixing dead `GenerationWorker.error` signal** at `src/forge/ui/workers.py:55` — never emitted, T-018 works around via `finished(success=False)`

## Environment

- **Working directory**: `/Users/gabriel/GItHub/project-creator`
- **Commands to run**: `uv sync`
- **Environment variables**: `QT_QPA_PLATFORM=offscreen` for headless GUI tests

# Session Handoff: T-016 Integration Tests Foundation
**Date**: 2026-06-25
**Ticket/Feature**: T-016 — Integration Tests — Foundation (Domain, Plugin Discovery, Transaction, Validation)
**Session Duration**: ~90 minutes + ~30 minutes post-implementation (dependency analysis + code review)

## Context
Created integration tests for the foundation layer (T-001 through T-005) using real implementations instead of mocks. The ticket was refined through 2 rounds of TDD review (NEEDS REVISION → APPROVED), then implemented as 8 files with 26 tests. After implementation: dependency analysis updated `dependency-analysis.md` with T-016's 5 downstream chains, and 2 rounds of code review found 5 issues (all fixed, round 2 APPROVED). All 27 tests pass (1 external checkpoint test added during code review), ruff clean.

## Progress
- [x] **Completed**: TDD Review Round 1 — found 4 blocking + 7 non-blocking issues
- [x] **Completed**: Updated ticket to fix all 11 TDD issues
- [x] **Completed**: TDD Review Round 2 — APPROVED (0 blocking, 0 moderate)
- [x] **Completed**: Implemented all 8 test files — 26 tests total
- [x] **Completed**: Fixed 3 test execution failures (slug assertion, over-strict scanner, MagicMock KeyError)
- [x] **Completed**: Verification — 26/26 pytest pass, ruff clean
- [x] **Completed**: Post-mortem written at `docs/context/post-mortem/tdd-integration-tests-foundation.md`
- [x] **Completed**: Dependency analysis — updated `dependency-analysis.md` with T-016 detailed chain (diagram, file table, architecture notes, canary test documentation, 5 downstream chains, 3 delicate points)
- [x] **Completed**: Code Review Round 1 — 5 issues found (mock vs real registry, duplicate txn fixture, dead `registry_with_discovery` fixture, Portuguese comments, missing external checkpoint test)
- [x] **Completed**: Fixed all 5 code review issues — replaced MagicMock with `real_registry` fixture, removed duplicate txn, removed dead fixture, translated comments, added external checkpoint test
- [x] **Completed**: Code Review Round 2 — APPROVED (0 issues, 2 non-blocking suggestions: naming convention, document pre-existing ruff/mypy extent)
- [x] **Completed**: Updated post-mortem with dependency analysis + code review findings across 8 sections

## Current State
- **Last completed action**: Updated post-mortem with code review + dependency analysis findings
- **Key decisions made**:
  - AC-2 is a design constraint (fixture-based), not a runtime assertion per TDD review B1
  - `user_plugin_dir` creates both flat `.py` and subdirectory `plugin.py` formats per TDD review R7
  - `test_plugin_entry_point_discovery` loads real production plugins as a canary — documented with `@pytest.mark.skipif` guidance
  - `MockPlugin` renamed to `MinimalPlugin` — returns real in-memory plugin (not mock) per TDD review B4
  - ValidationEngine tests use real `PluginRegistry().discover()` via module-scoped `real_registry` fixture (code review N) — NO MagicMock used in any integration test
  - `txn` fixture made idempotent with `mkdir(exist_ok=True)` to safely compose with `output_dir` fixture (code review O)
  - `registry_with_discovery` fixture removed entirely — name was misleading (never scanned user `.plugins/` dir) (code review P)
  - Added `test_external_file_checkpoint_deleted_on_rollback` — verifies checkpoints outside `output_dir` survive rollback (code review R)
  - T-016 depends on 5 downstream chains (T-004, T-005, T-006, T-007, T-008) — documented in `dependency-analysis.md`
  - TDD review (structural/scope) + code review (implementation quality) are complementary — both should be standard practice
- **Key decisions pending**: None
- **Blockers**: None

## Code Context
Run: `git diff HEAD~1` to see previous session changes (T-015 wizard screens 4-5)

New files this session:
```
tests/integration/__init__.py
tests/integration/conftest.py
tests/integration/test_domain_models.py
tests/integration/test_plugin_discovery.py
tests/integration/test_transaction.py
tests/integration/test_validation.py
tests/integration/test_progress_reporter.py
tests/integration/test_plugin_capabilities.py
docs/context/post-mortem/tdd-integration-tests-foundation.md
```

Modified files this session:
```
docs/context/tickets/016-integration-tests-foundation.md   — Updated per TDD review findings
docs/context/dependency-analysis.md                         — Added T-016 detailed chain + graph refs + 5 downstream marks
```

All changes are currently untracked (not yet committed).

## Specs Reference
- T-016 Ticket: `docs/context/tickets/016-integration-tests-foundation.md`
- Dependency Analysis: `docs/context/dependency-analysis.md`
- Forge Architecture: `docs/context/architecture.md`
- Forge Pipeline: `docs/context/pipeline.md`
- Post-mortem: `docs/context/post-mortem/tdd-integration-tests-foundation.md`
- Handoff template: `.opencode/handoffs/session-handoff.md`

## Agent Outputs
Findings from review agents are appended inline below.

- **TDD Review Round 1**: 4 blocking + 7 non-blocking issues found
  - B1: AC-2 untestable → rephrased as design constraint
  - B2: 3 deferred items missing → added 4-row table
  - B3: Canary undocumented → added detailed note + skipif guard
  - B4: `mock_plugin` misnamed → renamed to `minimal_plugin`
  - R1–R7: All resolved (test count, boundary table, txn fixture, make_spec reuse, cross-component test, directory checkpoint, both .plugins/ formats)
- **TDD Review Round 2**: APPROVED — all 11 issues resolved, 0 new findings
- **Code Review Round 1**: 5 issues found (C.L.E.A.R. framework)
  1. Mock vs real registry in validation tests — `MagicMock(spec=PluginRegistry)` replaced with module-scoped `real_registry` fixture
  2. Duplicate `txn` fixture in conftest + `test_transaction.py` — removed from `test_transaction.py`, made conftest version idempotent
  3. Dead `registry_with_discovery` fixture — defined but never used; removed entirely
  4. Portuguese comments (`# Formato 1`, `# subdiretório`) — translated to English
  5. Missing external checkpoint path test — added `test_external_file_checkpoint_deleted_on_rollback`
- **Code Review Round 2**: APPROVED — all 5 fixes confirmed, 0 new issues, 2 non-blocking suggestions:
  - S1: Consistent review round naming across tools
  - S2: Document pre-existing ruff/mypy extent separately

## Do Not Redo
- `Domain(name="  My   Domain  ").slug` = `"my-domain"` (single hyphen for entire whitespace run via `\s+`), NOT `"my---domain"`
- `MagicMock(spec=PluginRegistry)` does NOT raise `KeyError` on unknown `resolve()` calls — returns new MagicMock instead. Must use `side_effect` lambda with explicit raise.
- `test_all_non_init_files_have_domain_import_or_are_exempt` is over-strict — `test_plugin_capabilities.py` imports from `forge.plugins.base` without `forge.domain` (legitimate for capability tests). Removed the test; only kept `test_init_py_excluded_from_domain_import_check`.
- `registry_with_discovery` fixture name is misleading — calls `reg.discover()` which loads entry-point plugins, NOT user `.plugins/` directory. Was dead code; remove if seen again.
- Don't use both `conftest.py` and `test_*.py` to define identical fixtures — pytest silently shadows the conftest version, masking the duplication.
- "Integration test" means real implementations, not `MagicMock`. Validation tests must use real `PluginRegistry().discover()`, not mocks.

## Next Steps (Prioritized)
1. **Mark T-016 complete** in tickets index document
2. **Stage and commit** when user confirms: `tests/integration/` (8 files), `docs/context/dependency-analysis.md`, `docs/context/post-mortem/tdd-integration-tests-foundation.md`
3. **Extract AST scanner utility** — move scanner logic from both `tests/unit/test_domain_models.py` and `tests/integration/test_domain_models.py` into a shared `tests/scanner_utils.py`
4. **T-017 (Integration: Stages + Orchestrator)** — Follow T-016 pattern: canary tests, cross-component composition, conftest fixtures
5. **T-018 (Integration: UI Workers + Wizard)** — May need `QApplication` conftest scoping similar to `tests/unit/conftest.py:qapp`
6. **T-003 MockProgressReporter `.calls` redesign** — Migrate from `list[tuple[str, ...]]` to `@dataclass`-based call records (still deferred)
7. **Run both TDD review + code review as standard practice** — they catch different categories (TDD: structural/scope, code review: implementation details)

## Environment
- **Working directory**: `/Users/gabriel/GItHub/project-creator`
- **Commands to run**:
  - `uv run pytest tests/integration/ -v --no-header` — 27/27 pass
  - `uv run pytest tests/` — 0 regressions (436+ unit + 27 integration)
  - `uv run ruff check tests/` — clean
  - `uv run mypy -p forge` — 24 pre-existing errors (unrelated, from T-012/T-014/T-015)
- **Production code**: All unchanged (T-001 through T-005 already implemented)

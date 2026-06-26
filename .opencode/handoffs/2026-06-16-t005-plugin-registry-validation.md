# Session Handoff: T-005 PluginRegistry + ValidationEngine — Complete
**Date**: 2026-06-16  
**Ticket/Feature**: T-005 — PluginRegistry + ValidationEngine
**Session Duration**: ~90 minutes (code implementation + review + fix)

## Context

Implement `PluginRegistry` (two-tier discovery, ID resolution, topological sort) and `ValidationEngine` (ProjectSpec validation, plugin config validation) per 34 pre-defined ACs. Tests (718 lines, 42 tests) were the contract — implementation must match them exactly.

## Progress

- [x] **Completed**: `src/forge/generation/registry.py` (158 lines) — PluginRegistry with 8 methods, DiscoveryError, CycleDependencyError
- [x] **Completed**: `src/forge/generation/validation.py` (140 lines) — ValidationEngine with 2 methods, ValidationError dataclass
- [x] **Completed**: `src/forge/generation/__init__.py` — added 5 new exports (PluginRegistry, ValidationEngine, ValidationError, DiscoveryError, CycleDependencyError)
- [x] **Completed**: Verification — 106/106 unit tests pass (25 registry + 17 validation + 64 pre-existing), ruff clean, mypy clean
- [x] **Completed**: Code review Round 1 — REQUEST CHANGES (1 blocking: DiscoveryError caught by broad `except`, 4 non-blocking)
- [x] **Completed**: Code review Round 2 — APPROVED (all fixes verified), AC-8 scanner clean
- [x] **Completed**: Post-mortem created — `docs/context/post-mortem-005-plugin-registry-validation.md` (425 lines, 11 sections)
- [x] **Completed**: `docs/context/dependency-analysis.md` — updated with T-005 detailed chain + 8 delicate points

## Current State

- **Last completed action**: Post-mortem written; session finished
- **Key decisions made**:
  - Entry point `name` overrides plugin class's `name` attribute (test expects entry-point-derived name, not class attribute)
  - `.plugins/` files loaded via `exec()` in namespace dict (avoids `sys.modules` pollution)
  - Topo sort: DFS cycle pre-check + Kahn's algorithm; `requires` = hard edges (in-degree), `run_after` = soft edges (priority queue)
  - `ValidationError` kept in `generation/` not `domain/` — specific to generation validation concern
  - Validation errors model stored per-field + per-answer lists, not unified (flexible client rendering)
  - Cycle path format: `"Circular dependency detected: cycle-a → cycle-b → cycle-a"`
  - `GenerationTransaction as _` import pattern used (satisfies AC-8 without unused-import warnings)
- **Key decisions pending**: None — T-005 is complete
- **Blockers**: None

## Code Context

Run `git diff HEAD~1` — uncommitted changes from this session:
- `src/forge/generation/registry.py` — **CREATED** (158 lines)
- `src/forge/generation/validation.py` — **CREATED** (140 lines)
- `docs/context/post-mortem-005-plugin-registry-validation.md` — **CREATED** (425 lines)
- `tests/unit/test_registry.py` — **CREATED** (411 lines, 25 tests)
- `tests/unit/test_validation.py` — **CREATED** (307 lines, 17 tests)
- `src/forge/generation/__init__.py` — **MODIFIED** (5 new exports added)
- `docs/context/dependency-analysis.md` — **MODIFIED** (T-005 chain + delicate points)
- `docs/context/architecture.md` — **MODIFIED**
- `docs/context/tickets/005-plugin-registry-validation.md` — **MODIFIED** (spec updates)

## Specs Reference

- Ticket: `docs/context/tickets/005-plugin-registry-validation.md`
- Post-mortem: `docs/context/post-mortem-005-plugin-registry-validation.md`
- Dependency analysis: `docs/context/dependency-analysis.md`
- Architecture: `docs/context/architecture.md`
- Prior handoffs: `.opencode/handoffs/2026-06-13-t004-generation-transaction.md`, `.opencode/handoffs/2026-06-12-t003-progress-reporter.md`

## Agent Outputs

- **Code Review (Round 1)**: REQUEST CHANGES — 1 blocking (broad `except` catching DiscoveryError), 4 non-blocking (INTEGER type guard, MULTI_SELECT non-list guard, entry point error handling, `.plugins/` subdirectory support, unused test imports)
- **Code Review (Round 2)**: APPROVED — all 5 findings fixed, 106 tests, all gates clean

## Do Not Redo

- **`bool` is a subclass of `int` in Python**: `isinstance(True, int)` is `True` — INTEGER validation must check `type(value) is not bool` before `isinstance(value, int)`. No current UI emits bools for int fields, but this is a latent trap.
- **Broad `except` hides DiscoveryError**: `try: ... except Exception: raise DiscoveryError(...)` catches the specific `DiscoveryError` before it propagates, causing double-wrap. Always `except Exception: ...` only for non-DiscoveryError exceptions.
- **Entry point name overrides class `name` attribute**: Tests expect `discovered["myplugin"].name == "myplugin"` even when `MockA.name = "a"` — the entry point registration name is the canonical key, not the class attribute.
- **`.plugins/` subdirectory support**: Plugin files may be nested one level deep (`htmx/plugin.py`); the walker must descend into subdirectories, not just flat `iterdir()`.
- **Pre-existing E501 on `test_registry.py:287`**: 104-char line length issue in test file — not introduced by this ticket, not our problem.

## Next Steps (Prioritized)

1. **[Mark Ticket]**: Mark T-005 as ✅ COMPLETE in tickets index
2. **[T-006]**: Generation Stages consumes `topological_sort` — verify `list[PluginBase]` return matches stage constructor signature
3. **[T-007]**: Orchestrator Facade creates `PluginRegistry` + `ValidationEngine` — match constructor signatures (`strict: bool = False`)
4. **[T-014]**: Wizard Screens uses `get_available_backends()` / `get_available_frontends()` — verify return type compatibility
5. **[Commit]**: Commit T-005 changes when ready — currently all uncommitted

## Environment

- **Working directory**: `/Users/gabriel/GItHub/project-creator`
- **Commands to verify**:
  - `uv run pytest tests/ -v` — expect 106/106 passing (42 new + 64 pre-existing)
  - `uv run ruff check src/` — expect clean
  - `uv run mypy -p forge` — expect clean
  - `python scripts/ticket_viz.py` — view all tickets
- **Environment variables**: None beyond standard

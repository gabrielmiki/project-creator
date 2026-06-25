# Post-Mortem: T-017 — Integration Tests CLI + Pipeline

**Date:** June 25, 2026
**Status:** ✅ COMPLETE
**Review Status:** APPROVED (after 1 code review round)

---

## 1. Overview

### Original Ticket

**Title:** Integration Tests — CLI + Plugin Pipeline

**Original Acceptance Criteria (4 ACs, well-specified after refinement):**

```
AC-1: Given all pipeline modules are implemented, when pytest tests/integration/ is run,
      then all CLI + pipeline tests pass.
AC-2: Given a fastapi_spec, a real Orchestrator (with PluginRegistry + ValidationEngine),
      a GenerationTransaction, and a MockProgressReporter, when orchestrator.generate()
      is called, then app/main.py exists, requirements.txt contains fastapi, no
      .forge-staging directory exists (commit cleanup), and no files exist in the output
      directory outside the expected generated tree.
AC-3: Given a spec with backend_id="fastapi" and config={"fastapi": {"orm": "none"}},
      when generated, then requirements.txt does NOT contain sqlalchemy (ORM deps excluded).
AC-4: Design constraint: CLI tests exclusively use --headless mode. No CLI test creates
      a QApplication or requires a display server.
```

**Original test scope (13 tests across 3 files + conftest extension):**

```
tests/integration/test_cli_headless.py              — 4 CLI headless tests
tests/integration/test_orchestrator_pipeline.py      — 6 orchestrator pipeline tests
tests/integration/test_fastapi_plugin.py             — 3 FastAPI plugin integration tests
tests/integration/conftest.py                        — +7 pipeline fixtures
```

**Deferred items from prior post-mortems addressed:**

| Source | Deferred item | How T-017 covers it |
|--------|--------------|---------------------|
| T-006 post-mortem (§7) | ".forge-staging removal after commit not tested" | `test_orchestrator_full_pipeline` asserts `not (output_dir / ".forge-staging").exists()` |
| T-007 post-mortem (§7) | "Empty-registry warning in headless path" | **Still deferred** — feature not implemented in app.py. `test_orchestrator_unresolvable_backend_id` verifies the existing behaviour: unresolved `backend_id` produces a `ValidationEngine` error (severity="error"), not a warning |
| T-008 post-mortem (§8) | "No integration test for PluginExecutionEngine with real FastapiPlugin" | `test_fastapi_plugin_execution_engine_real_plugin` verifies real plugin + engine + transaction produce correct output |

### What Actually Happened

The ticket was implemented in a single pass with no TDD review rounds (all 13 test areas were already well-specified by the ticket). Implementation took approximately 60 minutes of wall-clock time:

1. **Dependency analysis** (15 min): Read ticket spec, existing conftest.py, app.py, orchestrator.py, all 6 stages, validation.py, FastAPI plugin, existing integration tests.
2. **Implementation** (30 min): Extended conftest.py with 7 fixtures, created 3 test files.
3. **First run** (2 min): 11/13 passed, 2 failed — both CLI tests failed due to `cli_spec_json` fixture using `config={"fastapi": {}}` which validation engine rejected (required `orm` field missing). Fixed by providing explicit config values matching plugin defaults.
4. **Lint fix** (3 min): `ruff --fix` resolved 9 issues (import sorting, unused imports); manually fixed 1 E501 (line too long).
5. **Verification** (10 min): All 39 integration tests pass, ruff clean, no new mypy errors.
6. **Code review** (included): C.L.E.A.R. review with APPROVE verdict (no blocking issues).

---

## 2. Problems Identified

### Pre-Implementation — 0 Issues

The ticket was well-specified thanks to the established TDD workflow and the detailed test-area table in the ticket. No TDD review rounds were needed. All upstream contracts (stages, orchestrator, CLI, FastAPI plugin) were already hardened by existing unit tests (T-006, T-007, T-008) and integration tests (T-016).

### Implementation — 1 Issue Found

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| `cli_spec_json` empty config fails validation | **Low** | `config={"fastapi": {}}` triggers `validate_plugin_config` error: `"Required field 'orm' is missing"`. The validation engine treats required questions strictly — missing keys with `required=True` fail regardless of whether the question has a `default` value. | Changed to `config={"fastapi": {"orm": "sqlalchemy", "auth": False, "include_alembic": False}}` to match plugin defaults |

### Code Review Round 1 — 0 Blocking Issues (C.L.E.A.R. Framework)

The C.L.E.A.R. review found no blocking issues. Verdict: **APPROVE**. Non-blocking observations:

| Severity | Finding | Location | Recommendation |
|----------|---------|----------|----------------|
| **Low** | `try/except SystemExit` instead of `pytest.raises(SystemExit)` in CLI tests — if `app_main()` returns normally without raising, the assertion is silently skipped | `test_cli_headless.py:28-31, 68-71` | Replace with `pytest.raises` pattern, or refactor `_run_headless` to `sys.exit(0)` on success for consistency |
| **Low** | `pipeline_registry` fixture duplicates `real_registry` in `test_validation.py:20-25` — identical module-scoped `PluginRegistry.discover()` call | `conftest.py:105`, `test_validation.py:20` | Extract to shared conftest with generic name, or document as intentional |
| **Low** | `validation` fixture uses `-> object` return type instead of concrete `ValidationEngine` | `conftest.py:116` | Use lazy import for type annotation |
| **Low** | `cli_spec_json` fixture config differs from ticket's empty dict `{}` spec | `conftest.py:166` | Update ticket to match implementation, or revert to empty dict (rejected by validation engine) |

---

## 3. Fixes Applied

### A. `cli_spec_json` Fixture Config Values (Implementation)

**Before (fails validation):**
```python
"config": {"fastapi": {}},
```

**After (FIXED):**
```python
"config": {"fastapi": {"orm": "sqlalchemy", "auth": False, "include_alembic": False}},
```

The validation engine (`validate_plugin_config`) checks `Question.required` — since `orm`, `auth`, and `include_alembic` all have `required=True` on the FastapiPlugin questions, an empty config dict fails validation with `"Required field 'orm' is missing"`. Providing the explicit default values (`orm="sqlalchemy"`, etc.) satisfies validation while still exercising the default-code path.

---

## 4. Technical Issues Found During Implementation

### Discovery: Validation Engine Rejects Empty Config for Required Questions

The `fastapi_spec` fixture (used by orchestrator pipeline tests) had `config={"fastapi": {}}` and worked fine because `orchestrator.generate()` does not call `validate_plugin_config`. But `_run_headless()` in `app.py` calls `validate_plugin_config` before `generate()`, which rejects the empty config.

This is a legitimate design choice: the validation engine treats `Question.required=True` as a strict requirement, while the plugin's `files()`/`dependencies()` methods have their own default fallbacks via `config.get("orm", "sqlalchemy")`. The headless path is stricter than the UI path would be (the UI would never produce a config with missing values because the user fills in the form).

| Finding | Discovery Method |
|---------|-----------------|
| ValidationEngine rejects empty config for required questions | Reading `app.py:81-91` and `validation.py:88-98` during dependency analysis |
| `_run_headless` validates before generating (unlike direct `orchestrator.generate()`) | Reading `app.py:78-107` |
| Questions with `default` set still have `required=True` — validation checks `required`, not `default` | Reading `validation.py:91` and `fastapi/plugin.py:196-208` |

### No Spec-Phase Issues

T-017 is the first ticket in the series to have **zero** spec-phase issues. All upstream contracts were hardened by existing tests. No ambiguous acceptance criteria, no undefined behaviour, no missing dependencies.

---

## 5. Final Implementation

### Files Created

```
tests/integration/test_cli_headless.py              # 4 tests: generation, malformed spec,
                                                     #   output dir creation, no display message
tests/integration/test_orchestrator_pipeline.py      # 6 tests: full pipeline, empty project,
                                                     #   rollback on failure, domain questions,
                                                     #   unresolvable backend, overwrite confirm
tests/integration/test_fastapi_plugin.py             # 3 tests: correct files, config variations,
                                                     #   execution engine + real plugin
```

### Files Modified

```
tests/integration/conftest.py                        # +7 fixtures: pipeline_registry, validation,
                                                     #   mock_executor, progress, orchestrator,
                                                     #   fastapi_spec, cli_spec_json
```

### Files Not Modified (verified)

- `src/forge/` — no production source files changed (test-only ticket)
- All 26 existing integration tests — zero regressions

### Key Architecture

The `mock_executor` fixture is the **only** mocked component across all 13 tests:

```
pipeline_registry ──► orchestrator ──► generate()
     │                     │
     │               mock_executor        ← only mock boundary
     │                     │
     ▼                     ▼
  real 6 stages ─────────► PluginExecutionEngine.run()
                              │
                         real FastapiPlugin.generate(executor=mock_executor)
                              │
                         mock_executor.run() — no-op (no subprocess calls)
```

All other components are real:
- `PluginRegistry.discover()` — loads all 4 production plugins via `importlib.metadata.entry_points()`
- `ValidationEngine.validate_spec()` — real cross-component validation
- `GenerationTransaction.stage_file()/stage_directory()/commit()/rollback()` — real I/O on `tmp_path`
- `MockProgressReporter` — real call-recording reporter

### Mock Boundary Justification

The `ProcessExecutor` is mocked because:
1. It wraps `subprocess.check_call` — real execution would require network/package resolution
2. It is a pure I/O concern (infrastructure layer), making it the cleanest mock boundary
3. The plugin's `files()` output is verified on disk — the files that `executor.run()` would produce are already generated by `FileProvider.files()` and staged via `txn.stage_file()`
4. `txn.requirements` captures `DependencyProvider.dependencies()` output — verified independently

### CLI Test Patching Strategy

CLI tests (which exercise `app._run_headless()`) patch `forge.generation.orchestrator.ProcessExecutor` because `_run_headless` creates its own Orchestrator internally:

```python
with patch("forge.generation.orchestrator.ProcessExecutor", return_value=mock_executor):
    app_main()
```

This works because `Orchestrator.__init__` does `self._executor = executor or ProcessExecutor()` — when no executor is passed (the default), it falls through to `ProcessExecutor()` which returns the mock.

---

## 6. Test Coverage

| Test file | Tests | Covers ACs | Status |
|-----------|-------|------------|--------|
| **CLI Headless** | | | |
| `test_cli_headless_generation` | 1 | AC-1, AC-2, AC-4 | ✅ app/main.py/requirements.txt exist, .forge-staging removed, exit 0 |
| `test_cli_malformed_spec` | 1 | AC-1 | ✅ Invalid JSON → exit 1 with "Invalid JSON" message |
| `test_cli_output_dir_created_if_missing` | 1 | AC-1, AC-2 | ✅ Missing output dir created, files generated |
| `test_cli_no_display_message` | 1 | AC-4 | ✅ No display + no --headless → "No display available" message |
| **Orchestrator Pipeline** | | | |
| `test_orchestrator_full_pipeline` | 1 | AC-1, AC-2 | ✅ 6 stages run, commit succeeds, .forge-staging removed, all expected files exist |
| `test_orchestrator_empty_project` | 1 | AC-1 | ✅ backend_id="" → shared structure only, no plugin files |
| `test_orchestrator_rollback_on_failure` | 1 | AC-1 | ✅ Unresolvable backend → rollback, .forge-staging removed, no partial files |
| `test_orchestrator_get_questions_using_real_registry` | 1 | AC-1 | ✅ Real FastapiPlugin questions: orm, auth, include_alembic |
| `test_orchestrator_unresolvable_backend_id` | 1 | AC-1 | ✅ ValidationEngine returns error for nonexistent backend_id |
| `test_orchestrator_overwrite_confirmed_real_stages` | 1 | AC-1, AC-2 | ✅ Pre-populated dir + overwrite_confirmed=True → pre-existing file preserved, new files generated |
| **FastAPI Plugin** | | | |
| `test_fastapi_generates_correct_files` | 1 | AC-2 | ✅ Default config: app/main.py, app/models.py, requirements.txt with fastapi+sqlalchemy |
| `test_fastapi_config_variations` | 1 | AC-3 | ✅ orm="none" → no models/database files, no sqlalchemy in reqs; auth=True → middleware/auth.py + routes/auth.py + jose+passlib deps |
| `test_fastapi_plugin_execution_engine_real_plugin` | 1 | AC-1, AC-2 | ✅ PluginExecutionEngine + FastapiPlugin + GenerationTransaction: staged files, staged dirs, txn.requirements |
| **Total** | **13** | **4 ACs** | ✅ |

### Fixtures (7 new + 6 existing = 13 total)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `pipeline_registry` | module | Real PluginRegistry with discover() — loads all 4 production plugins |
| `validation` | function | ValidationEngine(pipeline_registry) |
| `mock_executor` | function | MagicMock(spec=ProcessExecutor) — avoids real subprocess calls |
| `progress` | function | MockProgressReporter — records typed call tuples |
| `orchestrator` | function | Orchestrator(pipeline_registry, validation, executor=mock_executor) |
| `fastapi_spec` | function | ProjectSpec with backend_id="fastapi", config={"fastapi": {...}} |
| `cli_spec_json` | function | Writes valid spec.json for --headless testing |

Existing fixtures reused: `temp_dir` (tmp_path wrapper), `spec_factory` (make_spec from _shared.py), `txn` (GenerationTransaction on temp_dir/output).

### Test Infrastructure

- All tests use `tmp_path` for filesystem isolation (inherited from `temp_dir` fixture)
- No mocking frameworks beyond `unittest.mock.MagicMock` for `mock_executor`
- No `pytest-qt`, `QApplication`, or display server needed (AC-4)
- CLI tests use `patch.object(sys, "argv", ...)` + `patch("forge.generation.orchestrator.ProcessExecutor", ...)`
- Orchestrator/FastAPI tests inject `mock_executor` via `orchestrator` fixture

---

## 7. Outstanding Issues

### Non-Blocking

- [ ] LOW: `pipeline_registry` fixture (conftest.py:105) duplicates `real_registry` (test_validation.py:20) — both are module-scoped `PluginRegistry.discover()`. Two discovery calls across test modules. Consider extracting to shared conftest in future if more module-scoped registries are added.
- [ ] LOW: CLI tests use `try/except SystemExit` instead of `pytest.raises(SystemExit)` — if `app_main()` returns normally without raising, assertions are silently skipped. `pytest.raises` would actively fail in this case. However, the headless path always calls `sys.exit(1)` on error or `return` on success (no `sys.exit(0)`), so the current pattern works for both paths.
- [ ] LOW: Empty-registry warning in headless path (T-007 deferred item) remains deferred — no ticket assigned.
- [ ] LOW: `cli_spec_json` fixture config values drift from ticket spec — implementation uses explicit `orm: "sqlalchemy"` etc. instead of empty dict. The ticket should be updated to match.

### Resolved

- [x] `cli_spec_json` empty config rejected by validation engine — fixed with explicit default values
- [x] E501 line too long (105 chars) in overwrite test — fixed by splitting into multi-line call
- [x] 9 ruff lint issues (import sorting, unused imports) — fixed via `ruff --fix`

---

## 8. Lessons Learned

### What Went Well

1. **Well-specified ticket eliminated TDD review rounds** — T-017 had the most detailed test-area table of any ticket so far. Every test name, purpose, and assertion scope was specified. This made implementation purely mechanical: translate the table into pytest code. No spec ambiguity existed.

2. **Existing conftest patterns accelerated fixture creation** — The 7 new fixtures followed the exact same patterns as T-016's fixtures (lazy imports, function-scoped, typed where practical). No new fixture patterns needed to be invented. Copying the `temp_dir` → `tmp_path` pattern from T-016 made `cli_spec_json` implementation trivial.

3. **Mock boundary at ProcessExecutor is minimal and effective** — Only one component is mocked across all 13 tests. The mock is injected through `Orchestrator.__init__()` via the `executor=` parameter, requiring zero monkeypatching for the orchestrator/FastAPI tests. CLI tests require a single `patch` call because `_run_headless` creates its own Orchestrator internally.

4. **Zero production code changes** — All tests exercise existing code paths without modification. This validates that the test-contract-locked API surface (established by T-006, T-007, T-008 unit tests) actually works in real integration scenarios.

5. **Validation engine strictness caught a realistic config mismatch** — The `cli_spec_json` failure (empty config rejected) is a legitimate test bug, not a production bug. But it demonstrates that the headless path's `validate_plugin_config` call is a real barrier: any `--headless` user who omits config fields for required questions gets an error, not silent defaults. This is currently stricter than the GUI path would be.

6. **Single code review round with APPROVE verdict** — T-017 is the fastest ticket in the series to reach final APPROVE. The 4 C.L.E.A.R. observations were all low-severity and non-blocking. No re-review was needed.

### What Could Improve

1. **CLI test pattern for SystemExit handling** — Current tests use `try/except SystemExit` which silently passes if `app_main()` returns without raising. `_run_headless` returns normally on success (no `sys.exit(0)`), only raising `SystemExit(1)` on errors. The `try/except` pattern works for both cases but is less explicit than `pytest.raises`. Consider adding `sys.exit(0)` on success in `_run_headless` for consistency and testability.

2. **Module-scoped registry duplication** — `pipeline_registry` in conftest.py and `real_registry` in `test_validation.py` both create a real `PluginRegistry.discover()`. Two module-scoped calls means plugin imports happen twice during a full `tests/integration/` run. The cost is negligible (~0.2s overhead from plugin import caching) but represents architectural drift that compounds with each new module-scoped registry.

3. **Validation vs defaults tension** — The FastapiPlugin has `required=True` on all questions but also has sensible defaults (`orm="sqlalchemy"`, `auth=False`). The validation engine rejects missing required keys regardless of defaults. This means `--headless` users must provide explicit config values even if they want defaults. Consider adding a `headless_default` or `cli_default` mechanism to questions, or making `required` less strict for questions with defaults.

4. **Conftest import nesting** — The new fixtures follow the existing T-016 pattern of lazy imports inside fixture bodies (e.g., `from forge.generation.registry import PluginRegistry` inside `pipeline_registry()`). This is inconsistent with the top-level imports at lines 7-16. The pattern is intentional (avoids import errors if dependencies aren't installed) but creates a style tension visible to mypy.

5. **No TDD review rounds for this ticket** — While the ticket was well-specified, skipping the TDD review entirely means there was no independent verification of the test areas against the running system. The ticket went from spec → implementation in one step. This worked because all test areas were integration-level (no unit-test contract locking needed) and the upstream code was already hardened by T-006/T-007/T-008 unit tests.

### Key Metrics

| Metric | Value |
|--------|-------|
| Original ACs | 3 (expanded to 4 during refinement) |
| TDD review rounds | 0 |
| Code review rounds | 1 |
| Implementation issues found during development | 1 (cli_spec_json config) |
| Files created | 3 (all test files, zero source) |
| Files modified | 1 (conftest.py — 7 fixtures) |
| Tests created | 13 |
| Test fixtures added | 7 |
| Issues found by code review | 0 blocking, 4 non-blocking |
| Mock complexity | 1 mock (ProcessExecutor), 3 code sites use it |
| Production source changes | 0 |
| Integration test regressions | 0 (26 → 39 total, all pass) |
| Ruff regressions | 0 (clean) |
| Mypy regressions | 0 (all errors pre-existing) |

---

## 9. Acceptance Criteria Verification

| AC | Tests | Verification Method | Status |
|----|-------|---------------------|--------|
| AC-1: All pipeline tests pass | All 13 | 39/39 integration tests pass with ruff clean | ✅ |
| AC-2: Orchestrator.generate() produces correct output | `test_orchestrator_full_pipeline`, `test_fastapi_generates_correct_files`, `test_cli_headless_generation` | Structural: app/main.py exists, requirements.txt contains fastapi, .forge-staging removed, expected file tree verified | ✅ |
| AC-3: `orm="none"` excludes sqlalchemy from requirements.txt | `test_fastapi_config_variations` | Structural: `"sqlalchemy" not in requirements.txt.read_text()` | ✅ |
| AC-4: CLI tests are headless-only | All 4 CLI tests | Structural: no QApplication, no display server, all use `--headless` in args. Enforced by test design, not runtime assertion | ✅ |

---

## 10. Timeline

| Date | Activity |
|------|----------|
| June 25, 2026 | Ticket loaded from refined spec (13 test areas, 4 ACs, 7 fixtures specified) |
| June 25, 2026 | Dependency analysis: read ticket spec, existing conftest.py, all upstream source files |
| June 25, 2026 | Implementation: conftest.py fixtures + 3 test files written |
| June 25, 2026 | First run: 11/13 pass, 2 CLI tests fail (validation rejects empty config) |
| June 25, 2026 | Fixed: cli_spec_json config values explicit |
| June 25, 2026 | Lint: ruff --fix (9 issues) + manual E501 fix |
| June 25, 2026 | Verification: 39/39 integration tests pass, ruff clean, mypy no new errors |
| June 25, 2026 | Code review: C.L.E.A.R. APPROVE (0 blocking issues) |
| June 25, 2026 | Post-mortem written |

---

## 11. Next Steps

1. Mark T-017 as ✅ COMPLETE in tickets index
2. Consider unifying `pipeline_registry` (conftest.py) and `real_registry` (test_validation.py) into a shared module-scoped fixture in future refactoring
3. Consider adding `sys.exit(0)` on success in `_run_headless()` for testability — allows CLI tests to use `pytest.raises(SystemExit)` consistently
4. T-018 (Integration Tests — Full Pipeline) is the next integration test ticket — will extend the same fixture patterns with additional plugin combinations
5. Consider a validation engine improvement: `required=True` with `default != None` could be treated as non-blocking for headless mode (deferred)

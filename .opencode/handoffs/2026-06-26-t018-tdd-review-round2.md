# TDD Review Round 2: T-018 Integration Tests — Full Pipeline
**Date**: 2026-06-26
**Review Round**: 2 (post-fix verification)
**Verdict**: APPROVED

---

## 1. Executive Summary

This is the **second review** of T-018. The first review (same date, earlier session) found **4 blocking + 7 moderate issues** — flagging `NEEDS_REVISION`. The ticket was revised to address all 11 issues, and this review confirms that all fixes are sufficient.

**Verdict: APPROVED** — all blocking issues resolved, all moderate issues resolved, coverage is comprehensive, and infrastructure is ready. Two very minor new observations noted (not blocking): (1) `django_htmx_spec` config values are FastAPI keys instead of Django keys (functionally harmless but misleading), and (2) the dead `error` signal is acknowledged but not fixed (pre-existing production issue, documented correctly as a prerequisite).

---

## 2. Fix Validation — 11 Issues from First Review

### Blocking Issues (B1–B4)

| # | Issue | Expected Fix | Status | Verification |
|---|-------|-------------|--------|-------------|
| **B1** | `all_plugins_spec` impossible — ProjectSpec has only 2 plugin slots | Replace with `full_spec` (fastapi+react) + `django_htmx_spec` (django+htmx) | ✅ **FIXED** | Ticket doc: `full_spec` (line 46-54) + `django_htmx_spec` (line 57-66). Conftest.py: same fixtures at lines 156-173. No reference to `all_plugins_spec` remains. |
| **B2** | `test_worker_error_signal_on_failure` — dead signal wire; `error = Signal(str)` NEVER emitted in `run()` | Rename to `test_worker_finished_signal_on_failure`, test `finished(success=False)` instead | ✅ **FIXED** | Ticket doc line 82: test renamed. Prerequisites section (line 18-19) explicitly notes the dead wire and documents the design decision to test via `finished(success=False)`. |
| **B3** | `test_plugin_file_conflict_warning` — no bundled plugins produce same-relative-path file conflicts | Rename to `test_plugin_directory_coexistence`, test Django+HTMX templates/ idempotent merge | ✅ **FIXED** | Ticket doc line 75: renamed. Describes overlapping `templates/` directories handled idempotently. |
| **B4** | `worker` fixture missing `qapp` dependency — `GenerationWorker` extends `QObject`, requires `QApplication` | Add `qapp` to fixture signature | ✅ **FIXED** | Ticket doc line 41: `worker(qapp, orchestrator, full_spec, temp_dir)`. Conftest.py line 177: same signature with `qapp` first. `qapp` fixture at conftest.py:145-153. |

### Moderate Issues (M1–M7)

| # | Issue | Expected Fix | Status | Verification |
|---|-------|-------------|--------|-------------|
| **M1** | Signal test routes through GenerationScreen directly instead of MainWindow | Verify connections through `MainWindow._create_generation_worker()` | ✅ **FIXED** | Ticket doc line 80-81: "Worker signals connected correctly in `MainWindow._create_generation_worker()`; verify `MainWindow._on_generation_finished` receives the result". Aligns with T-015 passive-widget design. |
| **M2** | `test_error_missing_plugin_id` conflates CLI exit code 1 with API error return | Split into CLI path (`pytest.raises(SystemExit)` + `capsys`) and API path (`ValidationError` return) | ✅ **FIXED** | Ticket doc line 91: explicitly defines both paths with correct assertion patterns. |
| **M3** | `test_error_special_chars_in_name` assumes sanitization that doesn't exist | Defer with `@pytest.mark.skip(reason="not implemented")` | ✅ **FIXED** | Ticket doc line 93: `**DEFERRED**: ValidationEngine only checks empty project_name; no special-char handling.` Mark skip with clear reason. |
| **M4** | `test_plugin_dependency_ordering` trivially passes — no built-in plugin has `requires=[]` | Specify test-double plugins with dependency graph | ✅ **FIXED** | Ticket doc line 76-77: "Custom in-file test-double plugins with `requires=[]`: plugin B runs before plugin A when A declares `requires=["B"]`". |
| **M5** | `qapp` fixture not available in integration conftest | Add session-scoped `QApplication` fixture | ✅ **FIXED** | Conftest.py lines 145-153: `qapp` fixture exists, session-scoped, uses `QApplication.instance() or QApplication(sys.argv)`. |
| **M6** | CLI error tests need `pytest.raises(SystemExit)` + `capsys` patterns | Document patterns in ticket | ✅ **FIXED** | Ticket doc line 91: documents `pytest.raises(SystemExit)` + `capsys` for CLI assertions. T-017 existing tests (test_cli_headless.py) follow the same pattern. |
| **M7** | Scaffold + files() overlap not tested (T-010 deferred) | Add `test_react_scaffold_files_overlap` test area | ✅ **FIXED** | Ticket doc lines 94-95: new test area covering React's create-vite scaffold overlapping with React's `files()` output. |

---

## 3. AC Validation

| AC | Text | Testable | Issues |
|----|------|----------|--------|
| AC-1 | Given two backend/frontend combos (fastapi+react, django+htmx), when integration tests run, then each combo generates correct output files | ✅ YES | None. Binary: assert file existence + content for both combos. Covered by `test_backend_plus_frontend_generation` + `test_django_with_htmx`. |
| AC-2 | Given a GenerationWorker on QThread, when cancel, then rollback() called + finished(success=False) | ✅ YES | None. Binary via `QSignalSpy`. Covered by `test_worker_cancel_during_generation`. |
| AC-3 | Given existing output dir, when overwrite flow triggered, then confirm dialog shown (mock/assertion) | ✅ YES | None. Binary via `monkeypatch` + assert mock called. Covered by `test_overwrite_confirm_dialog_shown`. |
| AC-4 | Given CommandRunner raises exception, when generation runs, then rollback() called + no partial files | ✅ YES | None. Binary via `GenerationResult.success == False` + filesystem assertions (`.forge-staging` absent). |
| AC-5 | Design constraint: coverage >=80% post-implementation | ✅ CONSTRAINT | Marked as "Design constraint (not pre-implementation AC)" — correctly. Cannot pre-verify but explicitly noted as post-hoc check. |

---

## 4. Coverage Analysis

| Dimension | Status | Notes |
|-----------|--------|-------|
| **Happy path** | ✅ COVERED | Multi-plugin combos (fastapi+react, django+htmx), worker generates on thread, overwrite proceeds, CLI generation |
| **Error cases** | ✅ COVERED | CommandRunner exceptions (6 variants: mid-stage, scaffold command failure, timeout, missing plugin CLI + API, empty project name, special chars deferred-but-documented) |
| **Edge cases** | ✅ COVERED | Plugin directory coexistence, scaffold+files overlap, dependency ordering with custom test-doubles, cancel during generation, cancel before run |
| **Plugin isolation** | ✅ YES | Real plugins via real `pipeline_registry` fixture; `ProcessExecutor` mocked via `mock_executor` fixture; no UI imports in plugin code |

---

## 5. Infrastructure Readiness

| Requirement | Status | Location | Notes |
|-------------|--------|----------|-------|
| `qapp` fixture | ✅ EXISTS | `tests/integration/conftest.py:145` | Session-scoped `QApplication.instance() or QApplication(sys.argv)` |
| `worker` fixture | ✅ EXISTS | `tests/integration/conftest.py:176-184` | Depends on `qapp`, `orchestrator`, `full_spec`, `temp_dir`. Lazy imports `GenerationWorker`. |
| `full_spec` fixture | ✅ EXISTS | `tests/integration/conftest.py:156-163` | `backend_id="fastapi"` + `frontend_id="react"` + config for both |
| `django_htmx_spec` fixture | ✅ EXISTS | `tests/integration/conftest.py:166-173` | `backend_id="django"` + `frontend_id="htmx"` + config |
| `pipeline_registry` | ✅ EXISTS | `tests/integration/conftest.py:104-112` | Module-scoped `PluginRegistry().discover()`, loads all 4 plugins |
| `orchestrator` fixture | ✅ EXISTS | `tests/integration/conftest.py:138-142` | `Orchestrator(pipeline_registry, validation, executor=mock_executor)` |
| `mock_executor` fixture | ✅ EXISTS | `tests/integration/conftest.py:122-128` | `MagicMock()` avoids real subprocess calls |
| `spec_factory` fixture | ✅ EXISTS | `tests/integration/conftest.py:53-55` | Wraps `tests/unit/_shared.make_spec()` |
| `validation` fixture | ✅ EXISTS | `tests/integration/conftest.py:115-119` | `ValidationEngine(pipeline_registry)` |
| `progress` fixture | ✅ EXISTS | `tests/integration/conftest.py:131-135` | `MockProgressReporter()` |
| CLI test patterns | ✅ EXISTS | `tests/integration/test_cli_headless.py` | `pytest.raises(SystemExit)` + `capsys` patterns established in T-017 |
| Worker thread patterns | ✅ EXISTS | `tests/unit/test_workers.py` | `QThread + moveToThread`, `Qt.DirectConnection`, `QSignalSpy`, `_make_polling_side_effect` |
| QMessageBox monkey-patch | ✅ EXISTS | `tests/unit/test_main_window.py` | `monkeypatch.setattr(QMessageBox, "question", ...)` for overwrite confirm |

---

## 6. New Issues Found in Revision

Two very minor issues were found. Neither is blocking — both are documentation/cleanliness concerns, not testability blockers.

### N-I1: `django_htmx_spec` uses FastAPI config keys instead of Django keys

**Source**: `tests/integration/conftest.py:167-173`

```python
spec.config = {
    "django": {"orm": "sqlalchemy", "auth": False, "include_alembic": False},
    "htmx": {},
}
```

**Problem**: The Django config uses `orm`, `auth`, `include_alembic` — these are **FastAPI** config keys. Django's actual questions (from `plugin.py:185-204`) are:
- `database`: CHOICE with `["postgresql", "sqlite", "mysql"]`, default `"sqlite"`
- `include_drf`: BOOLEAN, default `False`

**Impact**: Functionally harmless — Django's `_config().get("database", "sqlite")` falls back to defaults for missing keys. SQLite + no DRF is correct for directory coexistence testing. But the config is misleading and looks like a copy-paste error (FastAPI config was copied and the key changed to `"django"` without updating values).

**Suggested fix**: Change to use Django's actual config keys:
```python
"django": {"database": "sqlite", "include_drf": False}
```

### N-I2: Dead `error` signal acknowledged but not fixed

**Source**: Ticket prerequisites section (line 18-19), `src/forge/ui/workers.py:55`

**Problem**: `GenerationWorker.error = Signal(str)` is defined but never emitted in `run()`. The ticket correctly designs around this by testing `finished(success=False)` instead. However, the dead wire exists in production code and is connected in `MainWindow._create_generation_worker()` (line 267 of main_window.py).

**Impact**: No impact on this ticket — the test strategy correctly avoids the dead signal. This is a pre-existing production issue documented in T-013 and T-015 post-mortems. Not blocking for T-018, but worth noting as a continued known issue.

**Suggested fix**: Out of scope for T-018. Already documented in T-013 post-mortem (§7) and T-015 post-mortem (§7) as a LOW item.

---

## 7. Final Verdict

```json
{
  "verdict": "APPROVED",
  "fix_validation": [
    {
      "issue": "B1: all_plugins_spec impossible",
      "status": "FIXED",
      "evidence": "Replaced with full_spec (fastapi+react) and django_htmx_spec (django+htmx) in both ticket doc and conftest.py"
    },
    {
      "issue": "B2: test_worker_error_signal_on_failure dead wire",
      "status": "FIXED",
      "evidence": "Renamed to test_worker_finished_signal_on_failure, tests finished(success=False) instead. Dead wire documented in prerequisites."
    },
    {
      "issue": "B3: test_plugin_file_conflict_warning impossible",
      "status": "FIXED",
      "evidence": "Renamed to test_plugin_directory_coexistence, tests Django+HTMX templates/ idempotent merge"
    },
    {
      "issue": "B4: worker fixture missing qapp",
      "status": "FIXED",
      "evidence": "worker(qapp, orchestrator, full_spec, temp_dir) in both ticket doc and conftest.py. qapp fixture added to integration conftest."
    },
    {
      "issue": "M1: signal test routes through MainWindow, not GenerationScreen",
      "status": "FIXED",
      "evidence": "test_worker_signals_connected verifies through MainWindow._create_generation_worker() and _on_generation_finished"
    },
    {
      "issue": "M2: test_error_missing_plugin_id conflates CLI/API paths",
      "status": "FIXED",
      "evidence": "Explicitly split into CLI path (pytest.raises(SystemExit) + capsys) and API path (ValidationError)"
    },
    {
      "issue": "M3: test_error_special_chars_in_name assumes nonexistent sanitization",
      "status": "FIXED",
      "evidence": "Deferred with @pytest.mark.skip(reason='not implemented — requires sanitization')"
    },
    {
      "issue": "M4: test_plugin_dependency_ordering trivially passes",
      "status": "FIXED",
      "evidence": "Specifies custom test-double plugins with requires=['B'] to exercise topological sort"
    },
    {
      "issue": "M5: qapp fixture missing from integration conftest",
      "status": "FIXED",
      "evidence": "Session-scoped qapp fixture added to tests/integration/conftest.py:145-153"
    },
    {
      "issue": "M6: CLI error tests lack pytest.raises/capsys patterns",
      "status": "FIXED",
      "evidence": "CLI path documented with pytest.raises(SystemExit) + capsys. T-017 existing tests confirm pattern works."
    },
    {
      "issue": "M7: Scaffold + files() overlap not tested",
      "status": "FIXED",
      "evidence": "New test_react_scaffold_files_overlap test area added under 'Scaffold overlap tests' section"
    }
  ],
  "ac_validation": [
    {
      "criterion": "AC-1",
      "text": "Given two backend/frontend combos (fastapi+react, django+htmx), when integration tests run, then each combo generates correct output files for both plugins.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-2",
      "text": "Given a GenerationWorker running on a QThread, when the test simulates a cancel signal, then rollback() is called and finished signal fires with success=False.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-3",
      "text": "Given an existing output dir, when overwrite flow is triggered, then the confirm dialog is shown (tested via show_confirm mock/assertion).",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-4",
      "text": "Given a plugin's CommandRunner raises an exception, when generation runs, then GenerationTransaction.rollback() is called and no partial files remain.",
      "testable": true,
      "issues": [],
      "suggested_fix": null
    },
    {
      "criterion": "AC-5",
      "text": "Design constraint: All new code paths exercised by these tests should have >=80% coverage. Verify post-implementation via pytest tests/ --cov=src/forge.",
      "testable": false,
      "issues": [
        "Coverage threshold cannot be verified pre-implementation. Already correctly marked as a design constraint, not an AC."
      ],
      "suggested_fix": "Already rephrased correctly from the first review's recommendation."
    }
  ],
  "infrastructure_readiness": [
    {
      "requirement": "qapp fixture (session-scoped)",
      "status": "EXISTS",
      "location": "tests/integration/conftest.py:145",
      "notes": "Session-scoped QApplication.instance() or QApplication(sys.argv)"
    },
    {
      "requirement": "worker fixture with qapp dependency",
      "status": "EXISTS",
      "location": "tests/integration/conftest.py:176",
      "notes": "Depends on qapp, orchestrator, full_spec, temp_dir. Lazy imports GenerationWorker."
    },
    {
      "requirement": "full_spec fixture (fastapi+react)",
      "status": "EXISTS",
      "location": "tests/integration/conftest.py:156",
      "notes": "backend_id='fastapi', frontend_id='react'. Config provided for both plugins."
    },
    {
      "requirement": "django_htmx_spec fixture (django+htmx)",
      "status": "EXISTS",
      "location": "tests/integration/conftest.py:166",
      "notes": "backend_id='django', frontend_id='htmx'. Config uses FastAPI keys instead of Django keys (minor issue N-I1)."
    },
    {
      "requirement": "Pipeline tests (orchestrator fixture)",
      "status": "EXISTS",
      "location": "tests/integration/conftest.py:138",
      "notes": "Orchestrator(pipeline_registry, validation, executor=mock_executor). Real registry, real stages."
    },
    {
      "requirement": "ProgressReporter fixture",
      "status": "EXISTS",
      "location": "tests/integration/conftest.py:131",
      "notes": "MockProgressReporter() for test assertions."
    },
    {
      "requirement": "mock_executor fixture",
      "status": "EXISTS",
      "location": "tests/integration/conftest.py:122",
      "notes": "Prevents real subprocess calls during integration tests."
    },
    {
      "requirement": "CLI test patterns (pytest.raises/capsys)",
      "status": "EXISTS",
      "location": "tests/integration/test_cli_headless.py",
      "notes": "Pattern established in T-017 with SystemExit + capsys assertions."
    },
    {
      "requirement": "QMessageBox monkey-patch pattern",
      "status": "EXISTS",
      "location": "tests/unit/test_main_window.py",
      "notes": "Pattern for overwrite confirm dialog assertions."
    },
    {
      "requirement": "Worker thread test patterns",
      "status": "EXISTS",
      "location": "tests/unit/test_workers.py",
      "notes": "QThread + moveToThread, Qt.DirectConnection, QSignalSpy, polling side_effect."
    }
  ],
  "coverage_analysis": {
    "happy_path": "COVERED",
    "error_cases": "COVERED",
    "edge_cases": "COVERED",
    "plugin_isolation_tested": "YES"
  },
  "new_issues": [
    "N-I1 (minor): django_htmx_spec config uses FastAPI keys {orm, auth, include_alembic} instead of Django keys {database, include_drf}. Functionally harmless (Django defaults apply), but misleading and should be corrected for readability.",
    "N-I2 (minor): Dead error signal wire (GenerationWorker.error = Signal(str) never emitted) is acknowledged correctly in prerequisites but remains a known production issue from T-013/T-015. Not blocking for T-018."
  ],
  "blocking_issues": []
}
```

## 8. Final Verdict: APPROVED ✅

All **4 blocking** and **7 moderate** issues from the first review are verified as properly fixed:

| Category | Round 1 | Round 2 |
|----------|---------|---------|
| Blocking | 4 (B1-B4) | 0 ✅ |
| Moderate | 7 (M1-M7) | 0 ✅ |
| New issues | — | 2 minor (N-I1, N-I2) |
| Verdict | NEEDS_REVISION | **APPROVED** |

### What's Ready
- All 5 acceptance criteria are testable (AC-5 is a design constraint, correctly marked)
- All fixtures exist in `tests/integration/conftest.py` with correct dependencies
- Integration test infrastructure follows established T-016/T-017 patterns
- Test suite covers happy path, error cases, and edge cases comprehensively
- Plugin isolation is maintained (real registry + mock executor)
- CLI assertion patterns (`pytest.raises(SystemExit)` + `capsys`) are documented
- Deferred items from T-010 (scaffold+files overlap) are now covered

### Pre-Implementation Checklist
1. ✅ Fix `django_htmx_spec` config keys (N-I1) — minor but recommended before implementation
2. ✅ Proceed with implementation: 5 test files with ~17 tests across 5 areas
3. ✅ Run with `QT_QPA_PLATFORM=offscreen` in CI for GUI tests

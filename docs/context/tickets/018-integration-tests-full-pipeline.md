# T-018: Integration Tests — Full Pipeline (All Plugins, GUI Worker, Overwrite, Error/Rollback)

- **type**: task
- **complexity**: medium
- **layer**: `tests/integration/`
- **dependencies**: T-009, T-010, T-011, T-012, T-013, T-014, T-015
- **phase**: 4 — Integration Tests
- **estimated_context**: ~30% of window

## Description

Write integration tests for the complete pipeline: all 4 bundled plugins together, the GUI worker thread, overwrite confirmation flow, and error/rollback scenarios. These are the most comprehensive tests — they verify that the full system works as a whole.

**Revision note (TDD review)**: This ticket was revised to correct 4 blocking + 7 moderate issues. Key changes: replaced impossible `all_plugins_spec` with pairwise combo spec; fixed `worker` fixture to depend on `qapp`; corrected signal routing tests to go through `MainWindow`; replaced dead-signal test with viable `finished(success=False)` test; removed test for non-existent sanitization (deferred); added proper CLI assertion patterns.

## Prerequisites

- `GenerationWorker.error` signal is defined but **never emitted** (dead wire in `src/forge/ui/workers.py:55`). Either fix the emission in `run()` or note the signal is intentionally unused — tested via `finished(success=False)` instead.

## Files to create

- `tests/integration/test_all_plugins.py`
- `tests/integration/test_gui_worker.py`
- `tests/integration/test_overwrite_flow.py`
- `tests/integration/test_error_scenarios.py`
- `tests/integration/conftest.py` (extend with GUI fixtures)

## Fixtures (add to conftest.py)

```python
@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication instance for GUI tests (no pytest-qt needed)."""
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def worker(qapp, orchestrator, full_spec, temp_dir) -> GenerationWorker:
    ...


@pytest.fixture
def full_spec(spec_factory) -> ProjectSpec:
    """Returns ProjectSpec with backend_id="fastapi", frontend_id="react"
    including explicit plugin config values required by ValidationEngine."""
    spec = spec_factory(backend_id="fastapi", frontend_id="react")
    spec.config = {
        "fastapi": {"orm": "sqlalchemy", "auth": False, "include_alembic": False},
        "react": {},
    }
    return spec


@pytest.fixture
def django_htmx_spec(spec_factory) -> ProjectSpec:
    """Returns ProjectSpec with backend_id="django", frontend_id="htmx"
    for pairwise multi-plugin tests (replaces impossible all_plugins_spec)."""
    spec = spec_factory(backend_id="django", frontend_id="htmx")
    spec.config = {
        "django": {"database": "sqlite", "include_drf": False},
        "htmx": {},
    }
    return spec
```

## Test areas

| Test | What it verifies |
|---|---|
| **Multi-plugin tests** | |
| `test_backend_plus_frontend_generation` | FastAPI backend + React frontend both produce correct output files (uses `full_spec`) |
| `test_plugin_directory_coexistence` | Django + HTMX plugins produce overlapping `templates/` directories; staging handles it idempotently (no file-level conflict between bundled plugins) |
| `test_django_with_htmx` | Django backend + HTMX frontend — both plugins generate, files from each are present (uses `django_htmx_spec`) |
| `test_plugin_dependency_ordering` | Custom in-file test-double plugins with `requires=[]`: plugin B runs before plugin A when A declares `requires=["B"]` |
| **GUI worker tests** | |
| `test_worker_generates_on_thread` | Worker runs generation without blocking main thread; `finished` fires with `success=True` |
| `test_worker_cancel_during_generation` | `cancel()` stops generation mid-way, `rollback()` called, `finished` fires with `success=False` |
| `test_worker_signals_connected` | Worker signals connected correctly in `MainWindow._create_generation_worker()`; verify `MainWindow._on_generation_finished` receives the result |
| `test_worker_finished_signal_on_failure` | Worker throws during `run()` → `finished` emits `GenerationResult(success=False, error=<msg>)` |
| **Overwrite flow tests** | |
| `test_overwrite_confirm_dialog_shown` | Existing output dir triggers `show_confirm()` via `MainWindow.next_screen()` at index 3 |
| `test_overwrite_yes_continues` | User says Yes → `_create_generation_worker` is called, generation proceeds |
| `test_overwrite_no_returns_to_review` | User says No → stays on ReviewScreen (index 3), no worker created |
| **Error scenario tests** | |
| `test_error_mid_stage_rollback` | Exception in `PluginExecutionEngine` triggers rollback, output dir clean, `success=False` |
| `test_error_scaffold_command_failure` | `mock_executor.run.side_effect = RuntimeError("scaffold failed")`: error reported, rollback, `success=False` |
| `test_error_scaffold_timeout` | `mock_executor.run` simulates timeout: error reported, rollback, `success=False` |
| `test_error_missing_plugin_id` | **CLI path**: spec with non-existent `backend_id` → exit code 1 via `pytest.raises(SystemExit)` + `capsys`. **API path**: `ValidationEngine.validate_spec` returns `ValidationError` for missing backend |
| `test_error_empty_project_name` | Empty `project_name`: `ValidationEngine` returns `ValidationError` with "error" severity on `field="project_name"` |
| `test_error_special_chars_in_name` | **DEFERRED**: `ValidationEngine` only checks empty `project_name`; no special-char handling implemented anywhere in the pipeline. Mark `@pytest.mark.skip(reason="not implemented — requires sanitization")` |
| **Scaffold overlap tests** | |
| `test_react_scaffold_files_overlap` | React's create-vite scaffold produces files overlapping with React's `files()` output; staging directory handles duplication idempotently (deferred item from T-010) |

## Acceptance Criteria

1. **Given** two backend/frontend combos (fastapi+react, django+htmx), **when** integration tests run, **then** each combo generates correct output files for both plugins.
2. **Given** a `GenerationWorker` running on a QThread, **when** the test simulates a cancel signal, **then** `rollback()` is called and `finished` signal fires with `success=False`.
3. **Given** an existing output dir, **when** overwrite flow is triggered, **then** the confirm dialog is shown (tested via `show_confirm` mock/assertion).
4. **Given** a plugin's `CommandRunner` raises an exception, **when** generation runs, **then** `GenerationTransaction.rollback()` is called and no partial files remain.
5. **Design constraint** (not pre-implementation AC): All new code paths exercised by these tests should have >=80% coverage. Verify post-implementation via `pytest tests/ --cov=src/forge`.

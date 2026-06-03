# T-018: Integration Tests — Full Pipeline (All Plugins, GUI Worker, Overwrite, Error/Rollback)

- **type**: task
- **complexity**: medium
- **layer**: `tests/integration/`
- **dependencies**: T-009, T-010, T-011, T-012, T-013, T-014, T-015
- **phase**: 4 — Integration Tests
- **estimated_context**: ~30% of window

## Description

Write integration tests for the complete pipeline: all 4 bundled plugins together, the GUI worker thread, overwrite confirmation flow, and error/rollback scenarios. These are the most comprehensive tests — they verify that the full system works as a whole.

## Files to create

- `tests/integration/test_all_plugins.py`
- `tests/integration/test_gui_worker.py`
- `tests/integration/test_overwrite_flow.py`
- `tests/integration/test_error_scenarios.py`
- `tests/integration/conftest.py` (extend with GUI fixtures)

## Fixtures (add to conftest.py)

```python
@pytest.fixture
def qapp(): ...
    # QApplication instance for GUI tests (pytest-qt or manual singleton)

@pytest.fixture
def worker(orchestrator, full_spec, temp_dir) -> GenerationWorker: ...

@pytest.fixture
def full_spec(spec_factory) -> ProjectSpec: ...
    # Returns ProjectSpec with backend_id="fastapi", frontend_id="react"

@pytest.fixture
def all_plugins_spec(spec_factory) -> ProjectSpec: ...
    # Returns ProjectSpec with all available plugins somehow (if composable)
```

## Test areas

| Test | What it verifies |
|---|---|
| **Multi-plugin tests** | |
| `test_backend_plus_frontend_generation` | FastAPI backend + React frontend both produce correct files |
| `test_plugin_file_conflict_warning` | Two plugins writing to same relative path: last-writer-wins, warning logged |
| `test_django_with_htmx` | Django backend + HTMX frontend — templates directory co-exists |
| `test_plugin_dependency_ordering` | If plugin A requires B, B runs first |
| **GUI worker tests** | |
| `test_worker_generates_on_thread` | Worker runs generation without blocking main thread |
| `test_worker_cancel_during_generation` | cancel() stops generation mid-way, rollback happens |
| `test_worker_signals_connected` | Worker signals correctly connected to GenerationScreen |
| `test_worker_error_signal_on_failure` | worker.error emitted when generation fails |
| **Overwrite flow tests** | |
| `test_overwrite_confirm_dialog_shown` | Existing output dir triggers show_confirm() |
| `test_overwrite_yes_continues` | User says Yes → generation proceeds with overwrite |
| `test_overwrite_no_returns_to_review` | User says No → stays on ReviewScreen |
| **Error scenario tests** | |
| `test_error_mid_stage_rollback` | Exception in PluginExecutionEngine triggers rollback, output dir clean |
| `test_error_scaffold_command_failure` | CommandRunner that returns non-zero: error reported, rollback |
| `test_error_scaffold_timeout` | CommandRunner that exceeds timeout: error reported, rollback |
| `test_error_missing_plugin_id` | CLI spec with non-existent plugin_id: error returned, exit code 1 |
| `test_error_empty_project_name` | Empty project_name: validation error returned |
| `test_error_special_chars_in_name` | Special chars sanitized: warning logged, project created with sanitized name |

## Acceptance Criteria

1. **Given** all bundled plugins are implemented, **when** tests run, **then** backend + frontend combos generate correct output files for each combination.
2. **Given** a `GenerationWorker` running on a QThread, **when** the test simulates a cancel signal, **then** `rollback()` is called and `finished` signal fires with `success=False`.
3. **Given** an existing output dir, **when** overwrite flow is triggered, **then** the confirm dialog is shown (tested via `show_confirm` mock/assertion).
4. **Given** a plugin's `CommandRunner` raises an exception, **when** generation runs, **then** `GenerationTransaction.rollback()` is called and no partial files remain.
5. **Given** the full test suite, **when** `pytest tests/ --cov=src/forge` is run, **then** coverage is >80%.

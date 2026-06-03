# T-017: Integration Tests — CLI + Plugin Pipeline

- **type**: task
- **complexity**: medium
- **layer**: `tests/integration/`
- **dependencies**: T-006, T-007, T-008
- **phase**: 4 — Integration Tests
- **estimated_context**: ~30% of window

## Description

Write integration tests for the CLI/headless flow and the full plugin pipeline — stages running in sequence, orchestrator coordinating with rollback, and the FastAPI plugin producing correct output. These tests verify that `forge --headless spec.json output/` works end-to-end.

## Files to create

- `tests/integration/test_cli_headless.py`
- `tests/integration/test_orchestrator_pipeline.py`
- `tests/integration/test_fastapi_plugin.py`
- `tests/integration/conftest.py` (extend with pipeline fixtures)

## Fixtures (add to conftest.py)

```python
@pytest.fixture
def orchestrator(registry) -> Orchestrator: ...

@pytest.fixture
def fastapi_spec(spec_factory) -> ProjectSpec: ...
    # Returns ProjectSpec with backend_id="fastapi" and default config

@pytest.fixture
def cli_spec_json(temp_dir) -> Path: ...
    # Writes a minimal spec.json for --headless testing
```

## Test areas

| Test | What it verifies |
|---|---|
| **CLI tests** | |
| `test_cli_headless_generation` | `python -m forge --headless spec.json output/` exits 0 and produces expected files |
| `test_cli_malformed_spec` | Invalid JSON returns exit code 1 with error message |
| `test_cli_missing_output_dir` | Specified output dir is created if it doesn't exist |
| `test_cli_no_display_message` | No display + no --headless shows error message |
| **Orchestrator tests** | |
| `test_orchestrator_full_pipeline` | All 6 stages run in order, transaction commits |
| `test_orchestrator_empty_project` | Zero domains skips PluginExecutionEngine, produces shared structure |
| `test_orchestrator_rollback_on_failure` | Stage failure triggers rollback, output dir is clean |
| `test_orchestrator_duration_estimate` | estimate_duration() returns reasonable values |
| `test_orchestrator_get_questions` | get_domain_questions() returns questions for selected plugin |
| **FastAPI plugin tests** | |
| `test_fastapi_generates_correct_files` | Generated project has app/main.py, requirements.txt, app/__init__.py |
| `test_fastapi_config_variations` | Different config values produce different file content (orm choice, alembic dir) |
| `test_fastapi_question_types` | Plugin questions() returns valid Question objects |
| `test_fastapi_dependencies` | dependencies() returns valid package list |

## Acceptance Criteria

1. **Given** all pipeline modules are implemented, **when** `pytest tests/integration/` is run, **then** all CLI + pipeline tests pass.
2. **Given** a `fastapi_spec` and `orchestrator`, **when** `generate()` is called, **then** `app/main.py` exists, `requirements.txt` contains `fastapi`, and the output dir is clean (no stale files).
3. **Given** a spec with `backend_id="fastapi"` and `config={"fastapi": {"orm": "sqlmodel"}}`, **when** generated, **then** `requirements.txt` contains `sqlmodel` instead of `sqlalchemy`.
4. **Given** the CLI integration test, **when** run, **then** it does not require a display server (uses `--headless`).

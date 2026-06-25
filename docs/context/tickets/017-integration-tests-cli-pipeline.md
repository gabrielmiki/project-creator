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
@pytest.fixture(scope="module")
def pipeline_registry() -> PluginRegistry:
    """Module-scoped real registry. Named pipeline_registry to avoid
    collision with test_validation.py's module-scoped real_registry."""
    reg = PluginRegistry()
    reg.discover()
    return reg

@pytest.fixture
def validation(pipeline_registry: PluginRegistry) -> ValidationEngine:
    return ValidationEngine(pipeline_registry)

@pytest.fixture
def mock_executor():
    """Mock ProcessExecutor — avoids real uv add subprocess calls
    during integration tests."""
    from unittest.mock import MagicMock
    return MagicMock()

@pytest.fixture
def progress() -> MockProgressReporter:
    return MockProgressReporter()

@pytest.fixture
def orchestrator(pipeline_registry: PluginRegistry, validation: ValidationEngine, mock_executor) -> Orchestrator:
    return Orchestrator(pipeline_registry, validation, executor=mock_executor)

@pytest.fixture
def fastapi_spec(spec_factory) -> ProjectSpec:
    spec = spec_factory(backend_id="fastapi")
    spec.config = {"fastapi": {}}
    return spec

@pytest.fixture
def cli_spec_json(temp_dir: Path) -> Path:
    """Writes a minimal spec.json for --headless testing.
    Schema matches what _run_headless() parses via json.loads."""
    import json
    spec = {
        "project_name": "test-project",
        "template": {
            "id": "fastapi-only",
            "display_name": "FastAPI Only",
            "description": "",
            "backend_id": "fastapi",
            "frontend_id": None,
        },
        "domains": [{"name": "users"}],
        "config": {"fastapi": {}},
    }
    path = temp_dir / "spec.json"
    path.write_text(json.dumps(spec))
    return path
```

## Test areas

| Test | What it verifies |
|---|---|
| **CLI tests** | |
| `test_cli_headless_generation` | `app.main()` with `--headless` → exit 0, produces expected files; uses `pytest.raises(SystemExit)` + `capsys` for message assertions |
| `test_cli_malformed_spec` | Invalid JSON → exit code 1 with error message via `pytest.raises(SystemExit)` + `capsys` |
| `test_cli_output_dir_created_if_missing` | Specified output dir is created if it doesn't exist via GenerationTransaction.commit() |
| `test_cli_no_display_message` | No display + no `--headless` → shows "No display available" via `capsys` |
| **Orchestrator tests** | |
| `test_orchestrator_full_pipeline` | All 6 stages run in order, transaction commits, `.forge-staging` removed (assert `not (output_dir / ".forge-staging").exists()`) |
| `test_orchestrator_empty_project` | `backend_id=""` skips PluginExecutionEngine, produces shared structure |
| `test_orchestrator_rollback_on_failure` | Stage failure triggers rollback, `.forge-staging` removed, output dir is clean |
| `test_orchestrator_get_questions_using_real_registry` | `get_domain_questions()` returns questions for real resolved plugin via real `PluginRegistry` |
| `test_orchestrator_unresolvable_backend_id` | Unresolvable `backend_id` → `ValidationEngine` returns error (severity="error"); headless path exits 1. (Empty-registry warning T-007 deferred item still deferred — not implemented in app.py) |
| `test_orchestrator_overwrite_confirmed_real_stages` | `overwrite_confirmed=True` skips `DirectoryInitializer`; verifies no `DirectoryNotEmptyError` is raised when `output_dir` is pre-populated, stages 2-6 run, commit succeeds, expected files exist on disk |
| **FastAPI plugin tests** | |
| `test_fastapi_generates_correct_files` | Generated project has `app/main.py`, `requirements.txt`, `app/__init__.py` on disk via real pipeline |
| `test_fastapi_config_variations` | Different config values produce different file content (orm choice, alembic dir) via real pipeline; uses mock executor to avoid real subprocess calls |
| `test_fastapi_plugin_execution_engine_real_plugin` | `PluginExecutionEngine` + real `FastapiPlugin` + real `GenerationTransaction` produces correct staged files (`txn.staging` inspected) and deps (`txn.requirements` inspected for DependencyProvider output) |

All pipeline tests use the `orchestrator` fixture which injects `mock_executor` to prevent real subprocess calls from `CommandRunner.generate()`. The only mocked component is the executor; all other components are real (`PluginRegistry`, `ValidationEngine`, `GenerationTransaction`, `MockProgressReporter`).

## Integration vs unit boundary

| Component | Unit test pattern (mocks) | Integration test pattern (real) |
|-----------|--------------------------|--------------------------------|
| Orchestrator.generate() | Mock stages, mock txn, mock progress | Real `PluginRegistry.discover()`, real 6 stages, real `GenerationTransaction`, real `MockProgressReporter` |
| CLI headless path | Mock `detect_display()`, mock `Orchestrator` | Real `app.main()` dispatch, real `_run_headless()` parse, real `Orchestrator` with mock executor |
| FastAPI plugin | Isolated `FastapiPlugin` methods, local `_MockTransaction` | `PluginExecutionEngine` + real `FastapiPlugin` + real `GenerationTransaction` on `temp_dir` filesystem |

**Test count**: 13 tests (4 CLI + 6 orchestrator + 3 FastAPI plugin).

## Acceptance Criteria

1. **Given** all pipeline modules are implemented, **when** `pytest tests/integration/` is run, **then** all CLI + pipeline tests pass.
2. **Given** a `fastapi_spec`, a real `Orchestrator` (with `PluginRegistry` + `ValidationEngine`), a `GenerationTransaction`, and a `MockProgressReporter`, **when** `orchestrator.generate()` is called, **then** `app/main.py` exists, `requirements.txt` contains `fastapi`, no `.forge-staging` directory exists (commit cleanup), and no files exist in the output directory outside the expected generated tree.
3. **Given** a spec with `backend_id="fastapi"` and `config={"fastapi": {"orm": "none"}}`, **when** generated, **then** `requirements.txt` does NOT contain `sqlalchemy` (ORM deps excluded).
4. **Design constraint**: CLI tests exclusively use `--headless` mode. No CLI test creates a `QApplication` or requires a display server. Enforced by test design (all headless-path tests invoke `app.main()` with `--headless` in `sys.argv`), not by a runtime assertion.

## Deferred items from prior post-mortems addressed here

| Source | Deferred item | How T-017 covers it |
|--------|--------------|---------------------|
| T-006 post-mortem (§7) | AC-14: `.forge-staging` removal after commit | `test_orchestrator_full_pipeline` asserts no `.forge-staging` exists in output dir |
| T-007 post-mortem (§7) | Empty-registry warning in headless path | **Still deferred** — feature not implemented in app.py. `test_orchestrator_unresolvable_backend_id` verifies the existing behavior: unresolved `backend_id` produces a `ValidationEngine` error (severity="error"), not a warning |
| T-008 post-mortem (§8) | No integration test for PluginExecutionEngine with real FastapiPlugin | `test_fastapi_plugin_execution_engine_real_plugin` verifies real plugin + engine + transaction produce correct output |

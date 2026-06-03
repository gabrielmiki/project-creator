# T-016: Integration Tests — Foundation (Domain, Plugin Discovery, Transaction, Validation)

- **type**: task
- **complexity**: medium
- **layer**: `tests/integration/`
- **dependencies**: T-001, T-002, T-003, T-004, T-005
- **phase**: 4 — Integration Tests
- **estimated_context**: ~25% of window

## Description

Write integration tests for the foundation layer: domain models, plugin discovery (entry points + `.plugins/` directory), `GenerationTransaction` atomicity, `ValidationEngine`, `ProgressReporter`, and plugin capability mixin composition.

## Files to create

- `tests/integration/__init__.py`
- `tests/integration/conftest.py` — shared fixtures (temp dir, mock plugin, spec factory)
- `tests/integration/test_domain_models.py`
- `tests/integration/test_plugin_discovery.py`
- `tests/integration/test_transaction.py`
- `tests/integration/test_validation.py`
- `tests/integration/test_progress_reporter.py`
- `tests/integration/test_plugin_capabilities.py`

## Fixtures needed

```python
@pytest.fixture
def temp_dir(tmp_path) -> Path: ...

@pytest.fixture
def mock_plugin() -> PluginBase: ...
    # Returns a minimal in-memory plugin with all mixins for capability testing

@pytest.fixture
def spec_factory() -> Callable[..., ProjectSpec]: ...
    # Returns a function that creates ProjectSpec with overridable defaults

@pytest.fixture
def user_plugin_dir(temp_dir) -> Path: ...
    # Creates a .plugins/ directory with a test plugin.py

@pytest.fixture
def registry_with_discovery(temp_dir, user_plugin_dir) -> PluginRegistry: ...
    # PluginRegistry pre-configured to scan temp .plugins/ dir
```

## Test areas

| Test | What it verifies |
|---|---|
| `test_domain_serialization` | All domain models serialize/deserialize via dataclass `asdict()` and reconstruct |
| `test_plugin_entry_point_discovery` | Plugin found via entry points (requires test entry point in pyproject.toml) |
| `test_plugin_user_dir_discovery` | Plugin found from `.plugins/` directory |
| `test_conflict_resolution_priority` | Entry point wins over `.plugins/` with same ID |
| `test_conflict_strict_mode` | Strict=True raises on any conflict |
| `test_topo_sort_no_deps` | Single plugin returns as-is |
| `test_topo_sort_with_deps` | Plugins sorted correctly by requires |
| `test_topo_sort_cycle_detection` | CycleDependencyError raised |
| `test_transaction_stage_commit` | Staged files appear in output dir after commit |
| `test_transaction_stage_rollback` | Staged files removed on rollback |
| `test_transaction_checkpoint_rollback` | External paths registered via add_checkpoint are deleted on rollback |
| `test_transaction_context_manager_success` | Context manager commits on __exit__ with no error |
| `test_transaction_context_manager_failure` | Context manager rolls back on exception |
| `test_validation_valid_spec` | Valid ProjectSpec returns no errors |
| `test_validation_invalid_spec` | Missing required field returns ValidationError |
| `test_validation_plugin_config` | Config outside question bounds returns error |
| `test_mock_progress_reporter_tracks_calls` | MockProgressReporter records all method calls in order |
| `test_stdout_progress_reporter_output` | StdoutProgressReporter prints expected text |
| `test_plugin_mixin_composition` | Plugin with only FileProvider mixin returns False for isinstance(plugin, CommandRunner) |

## Acceptance Criteria

1. **Given** all foundation modules are implemented, **when** `pytest tests/integration/` is run, **then** all foundation integration tests pass.
2. **Given** no test modifies the filesystem outside `tmp_path`, **when** tests run, **then** no filesystem pollution occurs.
3. **Given** the test suite, **when** `ruff check tests/` is run, **then** no lint errors exist.

# T-016: Integration Tests — Foundation (Domain, Plugin Discovery, Transaction, Validation)

- **type**: task
- **complexity**: medium
- **layer**: `tests/integration/`
- **dependencies**: T-001, T-002, T-003, T-004, T-005
- **phase**: 4 — Integration Tests
- **estimated_context**: ~25% of window

## Description

Write integration tests for the foundation layer. Unlike unit tests (which use mocks and run in isolation), integration tests exercise **real implementations** — real filesystem I/O via `tmp_path`, real `PluginRegistry.discover()` with actual entry points, and real `GenerationTransaction` with staging directories. The goal is to validate that foundation components work correctly together using the same imports and infrastructure paths the application uses at runtime.

### Deferred items from prior post-mortems addressed here

| Source | Deferred item | How T-016 covers it |
|--------|--------------|---------------------|
| T-002 post-mortem (§7, §11.3) | "AC-4 test should exclude `__init__.py` from domain-import check" | `test_ac4_init_exclusion` — validates the AST scanner is refined to skip `__init__.py` |
| T-003 post-mortem (§7) | "MockProgressReporter `.calls` uses variable-length tuples" | `test_mock_progress_reporter_calls` — uses explicit `@dataclass`-based call records or tuple-length assertions |
| T-004 post-mortem (§7) | "Empty/noop commit not tested" | `test_transaction_noop_commit` — verifies commit succeeds with zero staged files |
| T-004 post-mortem (§7) | "Directory checkpoint rollback not tested" | `test_transaction_checkpoint_directory_rollback` — verifies `shutil.rmtree` behavior for directory checkpoints |

## Files to create

- `tests/integration/__init__.py`
- `tests/integration/conftest.py` — shared fixtures (temp dir, minimal plugin, spec factory, txn)
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
def minimal_plugin() -> PluginBase: ...
    # Returns a real (not mocked) in-memory plugin inheriting all 4 mixins
    # so integration tests can verify capability composition with isinstance

@pytest.fixture
def spec_factory() -> Callable[..., ProjectSpec]: ...
    # Returns a function that creates ProjectSpec with overridable defaults.
    # Consider reusing tests/unit/_shared.make_spec() to avoid duplication.

@pytest.fixture
def user_plugin_dir(temp_dir) -> Path: ...
    # Creates .plugins/ directory with BOTH a flat .py file AND a
    # subdirectory/plugin.py to test both discovery formats (T-005).

@pytest.fixture
def registry_with_discovery(temp_dir, user_plugin_dir) -> PluginRegistry: ...
    # PluginRegistry pre-configured to scan temp .plugins/ dir

@pytest.fixture
def txn(temp_dir) -> GenerationTransaction: ...
    # GenerationTransaction bound to temp_dir / "output"
```

## Integration vs unit boundary

These tests are "integration" because they use **real implementations** rather than mocks:

| Component | Unit test pattern | Integration test pattern |
|-----------|-------------------|--------------------------|
| PluginRegistry | `unittest.mock.patch` on `entry_points()` | Real `importlib.metadata.entry_points()` — loads production plugins |
| GenerationTransaction | Inline `txn` fixture | Real staging dir under `tmp_path`, verifies actual file I/O |
| ValidationEngine | `MagicMock(spec=PluginRegistry)` | Real `PluginRegistry` with discovered plugins |
| ProgressReporter | `capsys` + method assertions | Same `capsys` + real `StdoutProgressReporter` instance |

**Note on entry point discovery**: `test_plugin_entry_point_discovery` calls `PluginRegistry.discover()` which loads **all four production framework plugins** (fastapi, django, react, htmx) via `importlib.metadata.entry_points(group="forge.plugins")`. This serves as a canary — if any bundled plugin has an import error, this test catches it. All four plugins must be importable for this test to pass. If a plugin is temporarily broken during development, the test file can use `@pytest.mark.skipif` with an `ImportError` guard as a workaround.

## Test areas

| Test | What it verifies |
|---|---|
| `test_domain_serialization` | All domain models serialize/deserialize via dataclass `asdict()` and reconstruct |
| `test_plugin_entry_point_discovery` | Plugin found via entry points (loads real production plugins — see note above) |
| `test_plugin_user_dir_discovery` | Plugin found from `.plugins/` directory (both `.py` file and `plugin.py` subdirectory formats) |
| `test_conflict_resolution_priority` | Entry point wins over `.plugins/` with same ID |
| `test_conflict_strict_mode` | Strict=True raises on any conflict |
| `test_topo_sort_no_deps` | Single plugin returns as-is |
| `test_topo_sort_with_deps` | Plugins sorted correctly by requires |
| `test_topo_sort_cycle_detection` | CycleDependencyError raised |
| `test_topo_sort_run_after_soft_edge` | `run_after` creates soft ordering edge (complements T-005 AC-23 at integration level) |
| `test_transaction_stage_commit` | Staged files appear in output dir after commit |
| `test_transaction_stage_rollback` | Staged files removed on rollback |
| `test_transaction_checkpoint_file_rollback` | External file paths registered via add_checkpoint are deleted on rollback |
| `test_transaction_checkpoint_directory_rollback` | Directory checkpoints are deleted recursively via `shutil.rmtree` on rollback |
| `test_transaction_noop_commit` | Commit with zero staged files succeeds silently (deferred from T-004) |
| `test_transaction_context_manager_success` | Context manager commits on __exit__ with no error |
| `test_transaction_context_manager_failure` | Context manager rolls back on exception |
| `test_validation_valid_spec` | Valid ProjectSpec returns no errors |
| `test_validation_invalid_spec` | Missing required field returns ValidationError |
| `test_validation_plugin_config` | Config outside question bounds returns error |
| `test_validation_real_registry_composition` | Validates a spec using a real PluginRegistry (not a mock) — cross-component test |
| `test_mock_progress_reporter_calls` | MockProgressReporter records calls with explicit typed records (addresses T-003 deferred) |
| `test_stdout_progress_reporter_output` | StdoutProgressReporter prints expected text (uses `capsys` fixture) |
| `test_plugin_mixin_composition` | Real production plugin (e.g., FastapiPlugin) reports correct isinstance for each mixin |
| `test_ac4_init_exclusion` | AST scanner excludes `__init__.py` from domain-import check (addresses T-002 deferred) |

## Acceptance Criteria

1. **Given** all foundation modules are implemented, **when** `pytest tests/integration/` is run, **then** all foundation integration tests pass.
2. **Design constraint**: All tests must derive their filesystem root from `temp_dir` (which wraps `pytest`'s built-in `tmp_path`). No test writes outside its designated temp directory. Enforced by fixture design, not by a runtime assertion.
3. **Given** the test suite, **when** `ruff check tests/` is run, **then** no lint errors exist.

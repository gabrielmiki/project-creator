# T-007: Orchestrator Facade + CLI Entry Point

- **type**: story
- **complexity**: complex
- **layer**: `generation/` + `__main__`
- **dependencies**: T-003, T-005, T-006
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~50% of window

## Description

Create the `Orchestrator` facade — the single entry point for the UI layer — that coordinates all 6 stages, handles error → rollback, provides query methods (available templates, questions), and estimates duration. Also create the CLI/headless entry point in `__main__.py`.

## Files to create

- `src/forge/generation/orchestrator.py`
- `src/forge/__main__.py`
- `src/forge/app.py` (skeleton — bootstrap app, detect display, dispatch CLI vs GUI)

## API Spec

```python
class Orchestrator:
    def __init__(self, registry: PluginRegistry, validation: ValidationEngine): ...

    # Query methods (for UI)
    # Returns list[PluginBase] (not TemplateDefinition) — mirrors PluginRegistry.get_available_backends()
    # Naming: architecture.md uses get_available_templates() but the registry splits backends/frontends.
    # TODO: Add TemplateDefinition-based filtering when template definitions are designed.
    def get_available_backends(self) -> list[PluginBase]: ...
    def get_available_frontends(self) -> list[PluginBase]: ...
    # Returns hardcoded template-level questions (project_description, license) — no plugin backing.
    # See AC-8 for contract. Source is a static list in the orchestrator (not a plugin or external source).
    def get_global_questions(self) -> list[Question]: ...
    def get_domain_questions(self, backend_id: str | None, frontend_id: str | None) -> dict[str, list[Question]]: ...
    def estimate_duration(self, spec: ProjectSpec) -> DurationEstimate: ...
    # Estimation model: base = 1s (file operations). Each CommandRunner plugin adds 3s.
    # FileProvider-only plugins (no CommandRunner) add 0.5s each.
    # Total = base + per-plugin sum, clamped to minimum 1s, maximum 60s.

    # Generation
    def generate(self, spec: ProjectSpec, output_dir: Path, progress: ProgressReporter, overwrite_confirmed: bool = False) -> GenerationResult: ...

@dataclass
class GenerationResult:
    success: bool
    error: str | None
    output_path: Path | None
```

### Headless CLI

```
usage: python -m forge --headless <spec.json> <output_dir>

Spec format (minimal JSON — Orchestrator fills defaults; maps directly to ProjectSpec fields):
{
  "project_name": "my-project",
  "template": {
    "id": "fastapi-stack",
    "display_name": "FastAPI Stack",
    "description": "",
    "backend_id": "fastapi",
    "frontend_id": null
  },
  "domains": [{"name": "Web"}],
  "config": {
    "fastapi": { "orm": "sqlalchemy" }
  }
}
```

### Display detection

- If display is available and no `--headless` flag: launch GUI.
- If no display and no `--headless` flag: error with message "No display available. Use --headless mode for headless environments."
- If `--headless` flag: run CLI generation with `StdoutProgressReporter`.

### Error flow

```
# Stage instances created in __init__ (stateless, no external deps beyond registry).
# PluginExecutionEngine receives self._registry at construction time.
# When overwrite_confirmed is True, DirectoryInitializer is excluded from self._stages.
Orchestrator.generate():
  output_dir.mkdir(parents=True, exist_ok=True)   # Stage 1 is validation-only
  txn = GenerationTransaction(output_dir)
  for stage in self._stages:
    try:
      stage.run(spec, output_dir, txn, progress)  # txn passed to every stage
    except Exception as e:
      txn.rollback()
      progress.on_error(e, recoverable=False)
      return GenerationResult(success=False, error=str(e), ...)
  txn.commit()
```

## Non-functional Requirements

- **Performance**: Headless generation of a structure-only project (no plugins) should complete in <1s in CI. Not asserted in unit tests — measured via integration benchmark.
- **Cross-platform display detection**: `detect_display()` must handle Linux (X11 `DISPLAY` var), macOS (Cocoa — always available), and Windows (always available). The function is mocked in unit tests.

## User Stories Covered

- **Story 6** (Automated/CI invocation): `forge --headless spec.json output/` with `StdoutProgressReporter`.
- **Story 7** (Informed before slow operations): `estimate_duration()` called before generation, duration shown to user.

## Role Separation

- **`src/forge/__main__.py`**: Entry point called via `python -m forge`. Parses CLI flags (`--headless`, `spec.json`, `output_dir`), calls `app.main(args)`. Does not construct orchestrator or core objects directly.
- **`src/forge/app.py`**: Contains `main(args)` — the single dispatch point. Constructs `PluginRegistry` + `ValidationEngine` + `Orchestrator`. Calls `detect_display()` (extracted to a standalone function for testability). If display available and no `--headless`: launch `QApplication` + `MainWindow`. If `--headless` or no display: call `Orchestrator.generate()` with `StdoutProgressReporter` and print results.

## Testing Notes

- **CLI testing (AC-3, AC-4)**: Write in `tests/unit/test_orchestrator.py`. Extract `_run_headless(args: list[str]) -> int` helper that patches `sys.argv` and invokes the `app.main()` parse/generate flow. Avoid subprocess — use capsys for stdout assertions.
- **Validation path (AC-4a/4b/4c)**: The headless parse flow calls `app.main()` → constructs `Orchestrator` → calls `ValidationEngine.validate_spec()` before generation. Invalid JSON is caught at the JSON parse step in `app.py` before any validation runs.
- **Display detection (AC-5)**: Mock via `unittest.mock.patch('forge.app.detect_display', return_value=False)`. The detection function should use `os.environ.get("DISPLAY")` on Linux. On macOS/Windows, these platforms always have a display — `detect_display()` should return `True` by default (or attempt `QApplication` creation as a probe). Tests mock `detect_display()` directly, so platform-specific logic is isolated.
- **Infrastructure import**: `src/forge/generation/orchestrator.py` is in the `generation/` layer and MUST include `from forge.infrastructure import GenerationTransaction as _  # noqa: F401` for AC-8 scanner compliance. `__main__.py` and `app.py` are outside `generation/` and are exempt.
- **PluginRegistry failure in headless mode**: `PluginRegistry.discover()` may return empty or raise if no plugins installed. The headless path must handle an empty registry gracefully (warn, generate structure-only project).
- **Shared mocks**: Shared mock infrastructure already exists in `tests/unit/_shared.py` (`MockTransaction`, `MockFilePlugin`, `MockCommandPlugin`, `MockDepPlugin`, `build_registry()`, `make_spec()`, `make_empty_spec()`). Shared fixtures (`output_dir`, `txn`, `progress`, `spec`, `empty_spec`) are in `tests/unit/conftest.py`. Orchestrator tests should import mocks from `_shared` and reuse conftest fixtures. The `_CancellableReporter` is inline in `test_stages.py` — extract to `_shared.py` if cancellation tests are needed.
- **`overwrite_confirmed` parameter**: Controls whether `DirectoryInitializer` is skipped on non-empty `output_dir`. Default `False` — raises `DirectoryNotEmptyError`. When `True`, Stage 1 validation is bypassed (orchestrator does not run `DirectoryInitializer`).

## Acceptance Criteria

1. **[integration]** **Given** a valid `ProjectSpec` and an output directory, **when** `Orchestrator.generate()` is called, **then** a complete project is generated with shared structure + plugin files, `GenerationResult.success is True`, and `GenerationResult.output_path` is not `None`.
1a. **(unit)** **Given** a valid `ProjectSpec` (`overwrite_confirmed=False`, the default) and mock stages, **when** `Orchestrator.generate()` is called, **then** each stage's `run()` is called in order (1-6), `txn.commit()` is called after Stage 6, and `GenerationResult.success is True`.
2. **Given** a stage that raises `Exception` during `run()`, **when** caught by `Orchestrator.generate()`, **then** `txn.rollback()` is called, `progress.on_error(error, recoverable=False)` is called, and `GenerationResult(success=False, error=str(e))` is returned.
3. **Given** the `--headless` flag with a valid spec.json, **when** `__main__.py` is invoked, **then** the project is generated, output is printed, and exit code is 0.
4a. **Given** an invalid JSON string in `spec.json`, **when** parsed, **then** an error message is printed and exit code is 1.
4b. **Given** valid JSON with missing required fields (`project_name`), **when** parsed, **then** an error message is printed and exit code is 1.
4c. **Given** valid JSON with an unknown `backend_id` (not in registry), **when** parsed, **then** an error message is printed and exit code is 1.
5. **Given** no display and no `--headless` flag, **when** `app.py` runs, **then** an error is shown: "No display available."
6. **Given** a `ProjectSpec`, **when** `get_domain_questions(backend_id, frontend_id)` is called, **then** `backend_id` and `frontend_id` plugins that implement `Configurable` have their `questions()` returned in a `dict[str, list[Question]]` keyed by plugin ID. Plugins not implementing `Configurable` are silently skipped. When `frontend_id is None`, no frontend plugin is queried.
7. **[integration]** **Given** a `ProjectSpec` with `backend_id=""` (no plugins selected), **when** `Orchestrator.generate()` is called, **then** it still produces shared structure and completes without error.
8. **Given** a `ProjectSpec`, **when** `get_global_questions()` is called, **then** a `list[Question]` is returned containing at least the keys `"project_description"` and `"license"` — template-level questions not specific to any single plugin.
9. **Given** a `ProjectSpec` with at least one plugin implementing `CommandRunner`, **when** `estimate_duration()` is called, **then** returns `DurationEstimate` with `has_slow_steps=True` and `estimated_seconds >= 2`. **Given** a `ProjectSpec` with no plugins implementing `CommandRunner` and zero `FileProvider`-only plugins, **when** `estimate_duration()` is called, **then** returns `DurationEstimate` with `has_slow_steps=False` and `estimated_seconds == 1` (the model minimum).
10. **Given** a `PluginRegistry` with discovered plugins, **when** `get_available_backends()` is called, **then** returns `list[PluginBase]` containing all discovered plugins (filtering by backend type deferred — see `# TODO` in API Spec).
11. **Given** a `PluginRegistry` with no discovered plugins, **when** `get_available_frontends()` is called, **then** returns an empty `list[PluginBase]`.

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
    def get_available_backends(self) -> list[TemplateDefinition]: ...
    def get_available_frontends(self) -> list[TemplateDefinition]: ...
    def get_global_questions(self) -> list[Question]: ...
    def get_domain_questions(self, backend_id: str | None, frontend_id: str | None) -> dict[str, list[Question]]: ...
    def estimate_duration(self, spec: ProjectSpec) -> DurationEstimate: ...

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

Spec format (minimal JSON — Orchestrator fills defaults):
{
  "project_name": "my-project",
  "author": "User",
  "python_version": "3.12",
  "backend_id": "fastapi",
  "frontend_id": null,
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
Orchestrator.generate():
  for stage in stages:
    try:
      stage.run(spec, output_dir, progress)
    except Exception as e:
      transaction.rollback()
      progress.on_error(e, recoverable=False)
      return GenerationResult(success=False, error=str(e), ...)
  transaction.commit()
```

## User Stories Covered

- **Story 6** (Automated/CI invocation): `forge --headless spec.json output/` with `StdoutProgressReporter`.
- **Story 7** (Informed before slow operations): `estimate_duration()` called before generation, duration shown to user.

## Acceptance Criteria

1. **Given** a valid `ProjectSpec` and an output directory, **when** `Orchestrator.generate()` is called, **then** a complete project is generated with shared structure + plugin files.
2. **Given** a stage failure during generation, **when** caught by `Orchestrator.generate()`, **then** `rollback()` is called and `GenerationResult(success=False, error=...)` is returned.
3. **Given** the `--headless` flag with a valid spec.json, **when** `__main__.py` is invoked, **then** the project is generated and output is printed.
4. **Given** malformed `spec.json`, **when** parsed, **then** an error message is printed and exit code is 1.
5. **Given** no display and no `--headless` flag, **when** `app.py` runs, **then** an error is shown: "No display available."
6. **Given** a `ProjectSpec`, **when** `get_domain_questions()` is called, **then** each selected plugin's `Configurable.questions()` are returned.
7. **Given** a project with no plugins, **when** `generate()` is called, **then** it still produces shared structure and completes in <1s.

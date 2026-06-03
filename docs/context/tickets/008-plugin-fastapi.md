# T-008: FastAPI Plugin (MVP Bundled Plugin)

- **type**: story
- **complexity**: medium
- **layer**: `plugins/fastapi/`
- **dependencies**: T-002, T-001
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~30% of window

## Description

Create the first bundled plugin — FastAPI backend — to validate the end-to-end pipeline. Implements all 4 capability mixins (Configurable, FileProvider, CommandRunner, DependencyProvider). This is the MVP validation plugin: the `forge --headless spec.json output/` flow must produce a working FastAPI project.

## Files to create

- `src/forge/plugins/fastapi/__init__.py`
- `src/forge/plugins/fastapi/plugin.py`
- `src/forge/plugins/fastapi/templates/` (optional Jinja2 templates)

## API Spec

```python
class FastapiPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "fastapi"
    display_name = "FastAPI"
    description = "FastAPI backend with SQLAlchemy + Pydantic"
    requires: list[str] = []

    def questions(self) -> list[Question]:
        # orm: str (choice: sqlalchemy, sqlmodel, none)
        # auth: bool
        # include_alembic: bool
        ...

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        # app/main.py, app/models.py, app/schemas.py, app/database.py
        # app/routes/__init__.py, app/routes/health.py
        # requirements.txt (framework deps)
        ...

    def directories(self, spec: ProjectSpec) -> list[str]:
        # app/, app/routes/, alembic/ (if include_alembic)
        ...

    def generate(self, spec: ProjectSpec, target_dir: Path) -> None:
        # pip install fastapi uvicorn sqlalchemy (or as configured)

    def dependencies(self) -> list[str]:
        return ["fastapi>=0.115", "uvicorn[standard]>=0.34"]
```

## Acceptance Criteria

1. **Given** the FastAPI plugin is registered, **when** `discover()` is called, **then** it is found with name `"fastapi"`.
2. **Given** a valid `ProjectSpec` with `backend_id="fastapi"`, **when** `Orchestrator.generate()` is called, **then** the generated project contains `app/main.py`, `app/__init__.py`, and `requirements.txt`.
3. **Given** the plugin's `Configurable`, **when** `questions()` is called, **then** it returns questions for `orm`, `auth`, `include_alembic`.
4. **Given** `orm="sqlalchemy"` in config, **when** `files()` is called, **then** the generated `requirements.txt` includes `sqlalchemy`.
5. **Given** `include_alembic=True` in config, **when** `directories()` is called, **then** `alembic/` is in the list.

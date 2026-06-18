# T-008: FastAPI Plugin (MVP Bundled Plugin)

- **type**: story
- **complexity**: medium
- **layer**: `plugins/fastapi/`
- **dependencies**: T-002, T-001, T08.1
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~30% of window

## Description

Create the first bundled plugin — FastAPI backend — to validate the end-to-end pipeline. Implements all 4 capability mixins (Configurable, FileProvider, CommandRunner, DependencyProvider). This is the MVP validation plugin: the `forge --headless spec.json output/` flow must produce a working FastAPI project.

## Files to create

- `src/forge/plugins/fastapi/__init__.py` (must import from `forge.domain` per AC-4 scanner constraint)
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
        # orm: str (choice: sqlalchemy, none)
        # auth: bool
        # include_alembic: bool
        ...

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        # app/__init__.py, app/main.py, app/models.py, app/schemas.py, app/database.py
        # app/routes/__init__.py, app/routes/health.py
        # app/middleware/auth.py (if auth=True), app/routes/auth.py (if auth=True)
        # requirements.txt (framework deps)
        ...

    def directories(self, spec: ProjectSpec) -> list[str]:
        # app/, app/routes/, app/middleware/ (if auth=True)
        # alembic/ (if include_alembic)
        ...

    def generate(self, spec: ProjectSpec, target_dir: Path, executor: ProcessExecutor) -> None:
        # executor.run(["uv", "add", "fastapi", "uvicorn"], cwd=target_dir)

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        config = spec.config.get("fastapi", {})
        deps = ["fastapi>=0.115", "uvicorn[standard]>=0.34"]
        if config.get("auth", False):
            deps += ["python-jose[cryptography]>=3.3", "passlib[bcrypt]>=1.7"]
        return deps
```

## Design Notes (read before implementing)

1. **Config access**: The plugin accesses its config via `spec.config.get("fastapi", {})` — NOT `spec.plugin_config("fastapi")` which raises `KeyError` when the key is absent.
2. **Validation ownership**: `ValidationEngine.validate_plugin_config()` (in `generation/validation.py:80`) validates CHOICE values. The headless CLI path (`app.py:_run_headless`) calls `validate_plugin_config()` for each configured plugin after `validate_spec()`. The plugin trusts validated input and does NOT duplicate validation.
3. **Entry point**: Already registered in `pyproject.toml:15` as `fastapi = "forge.plugins.fastapi:FastapiPlugin"`. The `name` class attribute must match `"fastapi"` exactly.
4. **AC-4 scanner constraint**: Every `.py` file under `plugins/` must import from `forge.domain` (e.g., `from forge.domain import ProjectSpec`). `fastapi/__init__.py` must include this import even if only re-exporting.
5. **Generate signature**: `generate(self, spec, target_dir, executor)` — `executor` is the `ProcessExecutor` injected by `PluginExecutionEngine` (T08.1). The plugin calls `executor.run(["uv", "add", ...], cwd=target_dir)`.
6. **Jinja2 dependency**: If templates/ directory is used with Jinja2, the Forge project must add `jinja2` to its `[project.dependencies]` in pyproject.toml.

7. **AC-4 scanner infra import ban**: The AC-4 AST scanner (`test_plugin_base.py:187-196`) scans every `.py` under `plugins/` for forbidden imports from `forge.ui`, `forge.generation`, and `forge.infrastructure`. Only `base.py` is exempt (`INFRA_EXEMPT_FILES = {"base.py"}`). This means **`fastapi/plugin.py` must NOT import from `forge.infrastructure`** — not even under a `TYPE_CHECKING` guard, because the scanner walks all AST `Import`/`ImportFrom` nodes without control flow analysis. The `generate()` method in the API Spec uses an untyped `executor` parameter to avoid triggering the scanner. Use `UNUSED` or `Any` type if mypy requires annotation.

8. **Test-first construction for AC-10**: AC-10 validates that `ValidationEngine` catches invalid CHOICE values. Under test-first (plugin doesn't exist yet), tests construct `Question` objects inline matching the plugin's `orm` question spec, rather than calling `plugin.questions()`. Follow the existing pattern at `test_validation.py:test_choice_invalid_option`.

## Acceptance Criteria

### Discovery & Registration

1. **[unit]** **Given** the `FastapiPlugin` class, **when** instantiated, **then** `plugin.name` returns `"fastapi"`.

### File Generation (unit — direct plugin mixin calls)

2a. **(unit)** **Given** a valid `ProjectSpec` with `backend_id="fastapi"` and default config, **when** `files()` is called on the plugin, **then** the returned list at minimum contains `GeneratedFile` entries for `app/__init__.py`, `app/main.py`, and `requirements.txt`.

2b. **(unit via PluginExecutionEngine)** **Given** a valid `ProjectSpec` with `backend_id="fastapi"`, **when** `PluginExecutionEngine.run()` is called with a `MockTransaction`, **then** files are staged via `txn.stage_file()` for the core files listed in AC-2a, and dependencies are appended to `txn.requirements`.

### Configurable (questions)

3. **Given** the plugin's `Configurable` mixin, **when** `questions()` is called, **then** it returns `Question` objects whose `.key` attributes include `"orm"`, `"auth"`, `"include_alembic"`. The `orm` question must be `QuestionType.CHOICE` with `options` containing `["sqlalchemy", "none"]`; `auth` and `include_alembic` must be `QuestionType.BOOLEAN`.

### FileProvider — file content

4. **Given** `orm="sqlalchemy"` in the plugin's config (accessed via `spec.config.get("fastapi", {})`), **when** `files()` is called, **then** the generated `requirements.txt` content includes `sqlalchemy`.

### FileProvider — conditional directories

5. **Given** `include_alembic=True` in config, **when** `directories()` is called, **then** `"alembic/"` is in the returned list.

### DependencyProvider

6. **Given** the FastAPI plugin, **when** `dependencies()` is called, **then** it returns `["fastapi>=0.115", "uvicorn[standard]>=0.34"]`.

### CommandRunner (generate / uv add)

7. **Given** a valid `ProjectSpec` and target directory, **when** `generate()` is called with a mock `ProcessExecutor`, **then** `executor.run()` is called with a command list containing `["uv", "add", "fastapi>=0.115", "uvicorn[standard]>=0.34"]`.

### Edge cases

8. **Given** `include_alembic=False` in config, **when** `directories()` is called, **then** `"alembic/"` is NOT in the returned list.

9. **Given** `orm="none"` in config, **when** `files()` is called, **then** the generated `requirements.txt` does NOT include `"sqlalchemy"`.

10. **Given** an invalid `orm` value (e.g., `"invalid"`) in plugin config, **when** `ValidationEngine.validate_plugin_config()` is called with the plugin's questions (constructed inline per Design Note 8), **then** a `ValidationError` with severity `"error"` is returned (matching existing pattern at `test_validation.py:test_choice_invalid_option`).

11. **Given** `config={"fastapi": {}}` (empty config dict — plugin uses internal defaults), **when** `files()` and `directories()` are called, **then**: (a) `requirements.txt` contains `"sqlalchemy"`, (b) `"alembic/"` is NOT in the returned directories.

12. **Given** `config={}` (no `"fastapi"` key in `ProjectSpec.config`), **when** `files()` or `directories()` is called, **then** no exception is raised and default values are used (the plugin accesses config via `spec.config.get("fastapi", {})`).

### Auth flag

13. **Given** `auth=True` in config, **when** `dependencies()` is called, **then** the returned list includes `"python-jose[cryptography]>=3.3"` and `"passlib[bcrypt]>=1.7"`.

14. **Given** `auth=True` in config, **when** `files()` is called, **then** `GeneratedFile` entries for `app/middleware/auth.py` and `app/routes/auth.py` are present.

15. **Given** `auth=False` (default) **or** `auth` key absent from config entirely, **when** `dependencies()` is called, **then** the returned list is the base set `["fastapi>=0.115", "uvicorn[standard]>=0.34"]` (no auth packages).

### PluginBase properties

16. **[unit]** **Given** the `FastapiPlugin` class, **when** instantiated, **then** `display_name` returns `"FastAPI"` and `description` returns a non-empty string.

### Module export

17. **[unit]** **Given** the `forge.plugins.fastapi` package, **when** imported, **then** `FastapiPlugin` is importable from `forge.plugins.fastapi`.

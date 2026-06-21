# T-009: Django Plugin

- **type**: story
- **complexity**: medium
- **layer**: `plugins/django/`
- **dependencies**: T-002, T-001
- **phase**: 2 — Remaining Bundled Plugins
- **estimated_context**: ~30% of window

## Description

Create the Django bundled plugin. Follows the same pattern as FastAPI (T-008) but with Django-specific project structure (manage.py, settings module, apps directory). Implements all 4 capability mixins (Configurable, FileProvider, CommandRunner, DependencyProvider). Supports choice of database backend (PostgreSQL, SQLite, MySQL) and optional Django REST Framework (DRF).

## Files to create

- `src/forge/plugins/django/__init__.py` (must import from `forge.domain` per AC-4 scanner constraint)
- `src/forge/plugins/django/plugin.py`
- `src/forge/plugins/django/templates/` (optional Jinja2 templates)

## API Spec

```python
class DjangoPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "django"
    display_name = "Django"
    description = "Django backend with choice of database + DRF"
    requires: list[str] = []

    def questions(self) -> list[Question]:
        # database: str (choice: postgresql, sqlite, mysql, default: sqlite)
        # include_drf: bool (default: False)
        ...

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        # manage.py, config/settings.py, config/urls.py, config/wsgi.py
        # requirements.txt (framework + conditional database/DRF deps)
        ...

    def directories(self, spec: ProjectSpec) -> list[str]:
        # config/, apps/, static/, templates/
        ...

    def generate(self, spec, target_dir, executor) -> None:
        # pip install django djangorestframework (as configured)

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        config = spec.config.get("django", {})
        deps = ["django>=5.1"]
        if config.get("database", "sqlite") == "postgresql":
            deps.append("psycopg2-binary>=2.9")
        elif config.get("database", "sqlite") == "mysql":
            deps.append("mysqlclient>=2.2")
        if config.get("include_drf", False):
            deps.append("djangorestframework>=3.15")
        return deps
```

## Design Notes (read before implementing)

1. **Config access**: The plugin accesses its config via `spec.config.get("django", {})` — NOT `spec.plugin_config("django")` which raises `KeyError` when the key is absent. Follow the `_config(spec)` helper pattern established in FastAPiPlugin (`_config` static method returning `spec.config.get("django", {})`).

2. **Validation ownership**: `ValidationEngine.validate_plugin_config()` (in `generation/validation.py:80`) validates CHOICE values. The headless CLI path (`app.py:_run_headless`) calls `validate_plugin_config()` for each configured plugin after `validate_spec()`. The plugin trusts validated input and does NOT duplicate validation.

3. **Entry point**: Already registered in `pyproject.toml:16` as `django = "forge.plugins.django:DjangoPlugin"`. The `name` class attribute must match `"django"` exactly.

4. **AC-4 scanner constraint**: Every `.py` file under `plugins/` must import from `forge.domain` (e.g., `from forge.domain import ProjectSpec`). `django/__init__.py` must include this import even if only re-exporting.

5. **Generate signature**: `generate(self, spec, target_dir, executor)` — `executor` is untyped (or `Any`) to avoid the AC-4 scanner infra import ban. The injected `ProcessExecutor` is resolved via the `CommandRunner` base class. The plugin calls `executor.run(["uv", "add", ...], cwd=target_dir)`.

6. **Jinja2 dependency**: If templates/ directory is used with Jinja2, the Forge project must add `jinja2` to its `[project.dependencies]` in pyproject.toml.

7. **AC-4 scanner infra import ban**: The AC-4 AST scanner (`test_plugin_base.py:187-196`) scans every `.py` under `plugins/` for forbidden imports from `forge.ui`, `forge.generation`, and `forge.infrastructure`. Only `base.py` is exempt (`INFRA_EXEMPT_FILES = {"base.py"}`). This means **`django/plugin.py` must NOT import from `forge.infrastructure`** — not even under a `TYPE_CHECKING` guard, because the scanner walks all AST `Import`/`ImportFrom` nodes without control flow analysis. The `generate()` method uses an untyped `executor` parameter to avoid triggering the scanner.

8. **Test-first construction for validation ACs**: ACs that validate `ValidationEngine` behavior (e.g., invalid database choice) must construct `Question` objects inline matching the plugin's question spec, rather than calling `plugin.questions()`. Follow the existing pattern at `test_validation.py:test_choice_invalid_option`.

9. **Cross-method consistency**: `files()`, `dependencies()`, and `generate()` must all agree on conditional logic driven by the same config keys. If `include_drf=True` adds `rest_framework` to `INSTALLED_APPS` in `settings.py` (files), then `dependencies()` must also include `djangorestframework>=3.15` and `generate()` must install it. This was a critical lesson from T-008 code review (asyncpg mismatch, generate/dependencies inconsistency).

10. **`include_celery` out of scope**: The original questions spec included `include_celery` but it has no AC coverage and adding Celery support (broker config, task files, worker management) is a significant feature beyond this ticket's scope. Removed from API spec.

## Acceptance Criteria

### Discovery & Registration

1. **[unit]** **Given** the `DjangoPlugin` class, **when** instantiated, **then** `plugin.name` returns `"django"`.

### File Generation (unit — direct plugin mixin calls)

2a. **(unit)** **Given** a valid `ProjectSpec` with `backend_id="django"` and default config (`{"django": {}}`), **when** `files()` is called on the plugin, **then** the returned list contains `GeneratedFile` entries for `manage.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, and `requirements.txt`.

2b. **(unit via PluginExecutionEngine)** **Given** a valid `ProjectSpec` with `backend_id="django"`, **when** `PluginExecutionEngine.run()` is called with a `MockTransaction`, **then** files are staged via `txn.stage_file()` for the core files listed in AC-2a, and dependencies are appended to `txn.requirements`.

### Configurable (questions)

3. **Given** the plugin's `Configurable` mixin, **when** `questions()` is called, **then** it returns `Question` objects whose `.key` attributes include `"database"` and `"include_drf"`. The `database` question must be `QuestionType.CHOICE` with `options` containing `["postgresql", "sqlite", "mysql"]`; `include_drf` must be `QuestionType.BOOLEAN`. All keys must be unique.

### FileProvider — file content

4. **Given** `database="postgresql"` in config, **when** `files()` is called, **then**: (a) the generated `config/settings.py` contains `"ENGINE": "django.db.backends.postgresql"` in its `DATABASES` setting, and (b) `requirements.txt` includes `psycopg2-binary>=2.9`.

5. **Given** `database="sqlite"` in config, **when** `files()` is called, **then**: (a) the generated `config/settings.py` contains `"ENGINE": "django.db.backends.sqlite3"` in its `DATABASES` setting, and (b) `requirements.txt` does NOT include `psycopg2-binary` or `mysqlclient` (SQLite is built into Python's stdlib).

6. **Given** `database="mysql"` in config, **when** `files()` is called, **then**: (a) the generated `config/settings.py` contains `"ENGINE": "django.db.backends.mysql"` in its `DATABASES` setting, and (b) `requirements.txt` includes `mysqlclient>=2.2`.

### FileProvider — DRF conditional content

7. **Given** `include_drf=True` in config, **when** `files()` is called, **then**: (a) `"rest_framework"` is present in `INSTALLED_APPS` in `config/settings.py`, and (b) `requirements.txt` includes `djangorestframework>=3.15`.

8. **Given** `include_drf=False` (default) **or** `include_drf` absent from config, **when** `files()` is called, **then**: (a) `"rest_framework"` is NOT present in `INSTALLED_APPS` in `config/settings.py`, and (b) `requirements.txt` does NOT include `djangorestframework`.

### FileProvider — directories

9. **Given** the Django plugin, **when** `directories()` is called, **then** the returned list contains `"config/"`, `"apps/"`, `"static/"`, and `"templates/"`.

### DependencyProvider

10. **Given** default config (`{"django": {}}`), **when** `dependencies()` is called, **then** the returned list contains `"django>=5.1"` and does NOT contain `"djangorestframework>=3.15"`, `"psycopg2-binary>=2.9"`, or `"mysqlclient>=2.2"` (SQLite default).

11. **Given** `include_drf=True` in config, **when** `dependencies()` is called, **then** the returned list includes `"djangorestframework>=3.15"` and still includes `"django>=5.1"`.

12. **Given** `database="postgresql"` in config, **when** `dependencies()` is called, **then** the returned list includes `"psycopg2-binary>=2.9"` and still includes `"django>=5.1"`.

### CommandRunner (generate / uv add)

13. **Given** a valid `ProjectSpec` and target directory with default config, **when** `generate()` is called with a mock executor, **then** `executor.run()` is called with a command list that includes the elements `["uv", "add", "django>=5.1"]` (it may include additional arguments).

14. **Given** `include_drf=True` in config, **when** `generate()` is called with a mock executor, **then** `executor.run()` is called with a command list that includes `"djangorestframework>=3.15"`.

15. **Given** `database="postgresql"` in config, **when** `generate()` is called with a mock executor, **then** `executor.run()` is called with a command list that includes `"psycopg2-binary>=2.9"`.

16. **Given** `database="mysql"` in config, **when** `generate()` is called with a mock executor, **then** `executor.run()` is called with a command list that includes `"mysqlclient>=2.2"`.

### Error cases

17. **Given** `config={"django": {}}` (empty config dict — plugin uses internal defaults), **when** `files()` and `dependencies()` are called, **then**: (a) `requirements.txt` does NOT include `psycopg2-binary>=2.9` or `mysqlclient>=2.2` (SQLite default), (b) `dependencies()` returns only `["django>=5.1"]`, and (c) `config/settings.py` contains `sqlite3` as the database engine.

18. **Given** `config={}` (no `"django"` key in `ProjectSpec.config`), **when** `files()`, `directories()`, or `dependencies()` is called, **then** no exception is raised and default values are used (the plugin accesses config via `spec.config.get("django", {})`).

19. **Given** an invalid `database` value (e.g., `"invalid"`) in plugin config, **when** `ValidationEngine.validate_plugin_config()` is called with the plugin's questions (constructed inline per Design Note 8), **then** a `ValidationError` with severity `"error"` is returned (matching existing pattern at `test_validation.py:test_choice_invalid_option`).

### PluginBase properties

20. **[unit]** **Given** the `DjangoPlugin` class, **when** instantiated, **then** `display_name` returns `"Django"` and `description` returns a non-empty string.

### Module export

21. **[unit]** **Given** the `forge.plugins.django` package, **when** imported, **then** `DjangoPlugin` is importable from `forge.plugins.django`.

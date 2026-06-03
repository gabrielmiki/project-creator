# T-009: Django Plugin

- **type**: story
- **complexity**: medium
- **layer**: `plugins/django/`
- **dependencies**: T-002, T-001
- **phase**: 2 — Remaining Bundled Plugins
- **estimated_context**: ~30% of window

## Description

Create the Django bundled plugin. Follows the same pattern as FastAPI but with Django-specific project structure (manage.py, settings module, apps).

## Files to create

- `src/forge/plugins/django/__init__.py`
- `src/forge/plugins/django/plugin.py`
- `src/forge/plugins/django/templates/`

## API Spec

```python
class DjangoPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "django"
    display_name = "Django"
    description = "Django backend with choice of database + DRF"
    requires: list[str] = []

    def questions(self) -> list[Question]:
        # database: str (choice: postgresql, sqlite, mysql)
        # include_drf: bool
        # include_celery: bool
        ...

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        # manage.py, config/settings.py, config/urls.py, config/wsgi.py
        # requirements.txt
        ...

    def directories(self, spec: ProjectSpec) -> list[str]:
        # config/, apps/, static/, templates/
        ...

    def generate(self, spec: ProjectSpec, target_dir: Path) -> None:
        # pip install django djangorestframework psycopg2 (as configured)

    def dependencies(self) -> list[str]:
        return ["django>=5.1", "djangorestframework>=3.15"]
```

## Acceptance Criteria

1. **Given** the Django plugin is registered, **when** `discover()` is called, **then** it is found with name `"django"`.
2. **Given** a valid `ProjectSpec` with `backend_id="django"`, **when** `generate()` is called, **then** the output contains `manage.py`, `config/settings.py`, and `requirements.txt`.
3. **Given** `database="postgresql"` in config, **when** `files()` is called, **then** settings.py includes `psycopg2` in INSTALLED_APPS-style database config.
4. **Given** `include_drf=True`, **when** `files()` is called, **then** `rest_framework` is in INSTALLED_APPS in the generated settings.

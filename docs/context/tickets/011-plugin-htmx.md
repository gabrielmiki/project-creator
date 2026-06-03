# T-011: HTMX Plugin

- **type**: story
- **complexity**: medium
- **layer**: `plugins/htmx/`
- **dependencies**: T-002, T-001
- **phase**: 2 — Remaining Bundled Plugins
- **estimated_context**: ~20% of window

## Description

Create the HTMX frontend bundled plugin. HTMX is a lighter-weight frontend (no Node.js scaffold needed) — primarily generates HTML templates, base layout, and config.

## Files to create

- `src/forge/plugins/htmx/__init__.py`
- `src/forge/plugins/htmx/plugin.py`
- `src/forge/plugins/htmx/templates/`

## API Spec

```python
class HtmxPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "htmx"
    display_name = "HTMX"
    description = "HTMX + Alpine.js frontend with Jinja2 templates"
    requires: list[str] = []

    def questions(self) -> list[Question]:
        # include_alpine: bool
        # include_tailwind: bool
        # css_framework: str (choice: tailwind, bootstrap, none)
        ...

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        # templates/base.html (with htmx + alpine CDN or npm)
        # templates/index.html
        # static/css/style.css
        # requirements.txt additions (jinja2 if not already present)
        ...

    def directories(self, spec: ProjectSpec) -> list[str]:
        # templates/, static/css/, static/js/

    def dependencies(self) -> list[str]:
        return []   # templates only, no Python deps beyond project base
```

## Acceptance Criteria

1. **Given** the HTMX plugin is registered, **when** `discover()` is called, **then** it is found with name `"htmx"`.
2. **Given** a `ProjectSpec` with `frontend_id="htmx"`, **when** `files()` is called, **then** it returns `templates/base.html` with htmx script tag.
3. **Given** `include_alpine=True` in config, **when** `files()` is called, **then** `base.html` includes Alpine.js script tag.
4. **Given** `css_framework="tailwind"`, **when** `files()` is called, **then** `tailwind.config.js` is included in the output.

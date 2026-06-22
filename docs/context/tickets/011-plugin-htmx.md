# T-011: HTMX Plugin

- **type**: story
- **complexity**: medium
- **layer**: `plugins/htmx/`
- **dependencies**: T-002, T-001
- **phase**: 2 — Remaining Bundled Plugins
- **estimated_context**: ~20% of window

## Description

Create the HTMX frontend bundled plugin. HTMX is a lighter-weight frontend (no Node.js scaffold needed) — primarily generates HTML templates, base layout, and CDN-based script tags. No scaffold command exists; all files are generated via `FileProvider`.

## Files to create

- `src/forge/plugins/htmx/__init__.py`
- `src/forge/plugins/htmx/plugin.py`

## API Spec

```python
class HtmxPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "htmx"
    display_name = "HTMX"
    description = "HTMX + Alpine.js frontend with Jinja2 templates"
    requires: list[str] = []

    @staticmethod
    def _config(spec: ProjectSpec) -> dict[str, Any]:
        return spec.config.get("htmx", {})

    def questions(self) -> list[Question]:
        # Question(key="include_alpine", type=QuestionType.BOOLEAN, default=False, ...)
        # Question(key="include_tailwind", type=QuestionType.BOOLEAN, default=False, ...)
        # Question(key="css_framework", type=QuestionType.CHOICE, options=["tailwind", "bootstrap", "none"], default="none", ...)
        ...

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        # Core: templates/base.html (with htmx CDN + optional alpine + optional css framework)
        #        templates/index.html (extends base.html)
        #        static/css/style.css
        # If include_tailwind: tailwind.config.js, postcss.config.js
        ...

    def directories(self, spec: ProjectSpec) -> list[str]:
        # templates/, static/css/, static/js/
        ...

    def generate(self, spec: ProjectSpec, target_dir: Path, executor) -> None:
        # no-op — HTMX is CDN-based, no scaffold command exists

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        return []   # no Python packages — HTMX is loaded via CDN
```

## Design Notes

1. **Config access pattern**: Use `spec.config.get("htmx", {})` via a `_config(spec)` static helper (matching the T-008/T-009/T-010 established pattern). Never use `spec.plugin_config("htmx")` which raises `KeyError` when the key is absent.

2. **ValidationEngine owns input validation**: The plugin trusts that validated config arrives at its methods. Invalid `css_framework` values are caught by `ValidationEngine.validate_plugin_config()` before they reach the plugin. The plugin may use `.get()` defaults defensively but need not validate inputs.

3. **Entry point registration**: `pyproject.toml:18` already registers `htmx = "forge.plugins.htmx:HtmxPlugin"`. The class attribute `name = "htmx"` must match the entry point name.

4. **AC-4 scanner compliance**: Every `.py` file under `plugins/` must import from `forge.domain` (e.g., `from forge.domain import ProjectSpec as _  # noqa: F401`). `htmx/__init__.py` must include this import even if only re-exporting. The plugin file must NOT import from `forge.infrastructure` — not even under `TYPE_CHECKING`. Use untyped `executor` parameter in `generate()` to avoid the AC-4 scanner's infra import ban. `base.py` is exempt via `INFRA_EXEMPT_FILES`.

5. **Test-first AC-18 construction (invalid css_framework)**: The AC-18 test must construct `Question` objects inline (not call `plugin.questions()`) to avoid a circular dependency where the test needs the plugin to exist before it can test validation. Follow the existing `test_validation.py:test_choice_invalid_option` pattern.

6. **Cross-method consistency**: Only `files()` branches on config keys — `dependencies()` always returns `[]`, `generate()` is always a no-op. This means there is zero cross-method consistency risk for conditional deps (unlike T-008/T-009/T-010). However, `base.html` content must agree with the `include_tailwind`/`css_framework` config: if `include_tailwind=True`, the Tailwind CDN script should appear in `base.html` regardless of `css_framework`.

7. **`templates/` directory not used as source**: All file templates are inline module-level string constants (matching T-008/T-009/T-010 pattern). No Jinja2 dependency is needed in Forge itself — the generated templates use Jinja2 syntax because they will be served by the backend's (FastAPI/Django) template engine.

8. **generate() is no-op**: HTMX has no scaffold command. CDN script tags in `base.html` are the delivery mechanism. `executor.run()` is never called. This matches T-010's webpack no-op pattern (AC-14f).

9. **dependencies() invariants**: HTMX adds no Python packages. The backend plugin (FastAPI/Django) is responsible for the Python web framework and its template engine. `dependencies()` always returns `[]`.

10. **Question.default values**: All questions have explicit `default=` values in the `Question(...)` constructor calls. This ensures consistent behavior when no config is provided.

11. **include_tailwind vs css_framework**: These are independent questions. `include_tailwind` controls whether Tailwind PostCSS build tooling files (`tailwind.config.js`, `postcss.config.js`) are generated. `css_framework` controls which CSS framework CDN link appears in `base.html`. When `include_tailwind=True`, the Tailwind CDN link is added to `base.html` regardless of `css_framework` (the build tooling implies Tailwind at runtime). When `include_tailwind=False`, the `css_framework` setting controls the CDN link alone. When both `include_tailwind=True` and `css_framework="tailwind"` are set, the Tailwind CDN script must appear in `base.html` exactly once — the implementation must guard against duplicate CDN entries.

12. **No requirements.txt in files()**: The backend plugin (FastAPI/Django) owns `requirements.txt`. HTMX generates no Python dependencies.

### Cross-Method Consistency Map

| Config | `files()` additions | `dependencies()` | `generate()` |
|--------|---------------------|------------------|--------------|
| Default (all false / "none") | `templates/base.html`, `templates/index.html`, `static/css/style.css` | `[]` | no-op |
| `include_alpine=True` | `base.html` includes Alpine.js CDN script | `[]` | no-op |
| `include_tailwind=True` | `tailwind.config.js`, `postcss.config.js` (content paths `./templates/**/*.html`); `base.html` includes Tailwind CDN | `[]` | no-op |
| `css_framework="tailwind"` (without tailwind build tooling) | `base.html` includes Tailwind CDN script (CDN-only, no config files) | `[]` | no-op |
| `css_framework="bootstrap"` (without tailwind build tooling) | `base.html` includes Bootstrap CDN link | `[]` | no-op |
| `css_framework="none"` (without tailwind build tooling) | `base.html` has no CSS framework CDN | `[]` | no-op |
| `include_tailwind=True` + `css_framework="bootstrap"` | Tailwind build files + Bootstrap CDN in `base.html` | `[]` | no-op |
| `include_tailwind=True` + `css_framework="tailwind"` | Tailwind build files + Tailwind CDN in `base.html` (CDN added once, not duplicated) | `[]` | no-op |
| All above combined | All file variants merged | `[]` | no-op |

Note: Only `files()` is config-dependent. `dependencies()` and `generate()` are invariant across all permutations.

### Expected CDN URLs for Content Assertions

| Library | URL |
|---------|-----|
| HTMX | `https://unpkg.com/htmx.org@2.0.4` |
| Alpine.js | `https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js` |
| Tailwind CSS (CDN) | `https://cdn.tailwindcss.com` |
| Bootstrap CSS | `https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css` |

## Acceptance Criteria

### Discovery & Identity

**AC-01 — [unit] plugin.name**: Given the `HtmxPlugin` class, when instantiated, then `plugin.name` returns `"htmx"`.

### File Provider (files)

**AC-02a — files() core paths**: Given a `ProjectSpec` with `frontend_id="htmx"` and default config (`{"htmx": {}}`), when `files()` is called, then the returned list includes `GeneratedFile` entries for `templates/base.html`, `templates/index.html`, and `static/css/style.css`. All entries have `Path` objects as their `.path` attribute.

**AC-02b — engine integration**: Given a `ProjectSpec` with `frontend_id="htmx"`, when the generation pipeline is simulated (call `files()` → `txn.stage_file()`, `directories()` → `txn.stage_directory()`, `dependencies()` → `txn.requirements.extend()`), then core file paths are staged and `txn.requirements` remains empty (no dependencies).

### Configurable (questions)

**AC-03 — questions()**: Given the `Configurable` mixin, when `questions()` is called, then it returns `Question` objects whose `.key` attributes include `"include_alpine"`, `"include_tailwind"`, and `"css_framework"`. `include_alpine` and `include_tailwind` must be `QuestionType.BOOLEAN`. `css_framework` must be `QuestionType.CHOICE` with options exactly equal to `["tailwind", "bootstrap", "none"]`. All keys must be unique.

### Template Content — HTMX

**AC-04 — base.html includes HTMX**: Given a `ProjectSpec` with `frontend_id="htmx"` and any config, when `files()` is called, then `templates/base.html` content includes `htmx.org@2.0.4` in a `<script>` tag.

### Template Content — Alpine.js

**AC-05 — include_alpine=True**: Given `include_alpine=True` in config, when `files()` is called, then `templates/base.html` content includes `alpinejs@3.14.8` in a `<script>` tag.

**AC-06 — include_alpine=False or absent**: Given `include_alpine=False` (or absent from config), when `files()` is called, then `templates/base.html` content does NOT include `alpinejs`.

### CSS Framework — Tailwind Build Tooling

**AC-07 — include_tailwind=True**: Given `include_tailwind=True` in config, when `files()` is called, then `tailwind.config.js` and `postcss.config.js` are in the returned file paths. The `tailwind.config.js` content includes `"./templates/**/*.html"` as a content path. `templates/base.html` content includes `cdn.tailwindcss.com` in a `<script>` tag.

**AC-08 — include_tailwind=False or absent**: Given `include_tailwind=False` (or absent from config), when `files()` is called, then `tailwind.config.js` is NOT in the returned file paths.

### CSS Framework — CDN Choice

**AC-09 — css_framework="tailwind"**: Given `css_framework="tailwind"` in config and `include_tailwind=False`, when `files()` is called, then `templates/base.html` content includes `cdn.tailwindcss.com` in a `<script>` tag. `tailwind.config.js` and `postcss.config.js` are NOT in the returned file paths (build tooling is controlled by `include_tailwind`, not `css_framework`).

**AC-10 — css_framework="bootstrap"**: Given `css_framework="bootstrap"` in config and `include_tailwind=False`, when `files()` is called, then `templates/base.html` content includes `bootstrap@5.3.3` in a `<link>` tag.

**AC-11 — css_framework="none"**: Given `css_framework="none"` in config and `include_tailwind=False`, when `files()` is called, then `templates/base.html` content does NOT include `cdn.tailwindcss.com`, `cdn.jsdelivr.net/npm/bootstrap`, or any CSS framework CDN URL.

### Combined Config

**AC-12a — include_tailwind=True + css_framework="bootstrap"**: Given `include_tailwind=True` and `css_framework="bootstrap"` in config, when `files()` is called, then `templates/base.html` content includes both `cdn.tailwindcss.com` `<script>` and `bootstrap@5.3.3` `<link>` CDN tags; `tailwind.config.js` and `postcss.config.js` are in the returned file paths.

**AC-12b — include_tailwind=True + css_framework="tailwind" CDN deduplication**: Given `include_tailwind=True` and `css_framework="tailwind"` in config, when `files()` is called, then `templates/base.html` content includes `cdn.tailwindcss.com` **exactly once** (no duplicate `<script>` tags for Tailwind CDN); `tailwind.config.js` and `postcss.config.js` are in the returned file paths.

### Directories

**AC-13 — directories()**: Given the HTMX plugin, when `directories()` is called, then the returned list contains `"templates/"`, `"static/css/"`, and `"static/js/"`.

### Dependencies

**AC-14 — dependencies() is empty**: Given any config permutation (default, Alpine-only, Tailwind, Bootstrap, or combined), when `dependencies()` is called, then the returned list is empty (`[]`).

### Command Runner (generate)

**AC-15 — generate() is no-op**: Given any config permutation, when `generate()` is called with a mock executor, then `executor.run()` is NOT called.

### Error and Edge Cases

**AC-16 — empty config dict**: Given `config={"htmx": {}}` (empty config dict — plugin uses internal defaults), when `files()`, `directories()`, and `dependencies()` are called, then defaults are used: `include_alpine` defaults to `False`, `include_tailwind` defaults to `False`, `css_framework` defaults to `"none"`. No exception is raised.

**AC-17 — missing "htmx" config key**: Given `config={}` (no `"htmx"` key in `ProjectSpec.config`), when `files()`, `directories()`, and `dependencies()` are called, then no exception is raised and default values are used (the plugin accesses config via `spec.config.get("htmx", {})`).

**AC-18 — invalid css_framework value**: Given an invalid `css_framework` value (e.g., `"invalid"`) in plugin config, when `ValidationEngine.validate_plugin_config()` is called with the plugin's questions (constructed inline per Design Note 5), then at least one `ValidationError` with severity `"error"` is returned (i.e., `len(errors) >= 1`).

### Identity & Module

**AC-19 — display_name and description**: Given the `HtmxPlugin` class, when instantiated, then `display_name` returns `"HTMX"` and `description` returns a non-empty string.

**AC-20 — module export**: Given the `forge.plugins.htmx` package, when imported, then `HtmxPlugin` is importable from `forge.plugins.htmx`.

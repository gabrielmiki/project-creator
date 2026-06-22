# T-010: React Plugin

- **type**: story
- **complexity**: medium
- **layer**: `plugins/react/`
- **dependencies**: T-002, T-001
- **phase**: 2 — Remaining Bundled Plugins
- **estimated_context**: ~25% of window

## Description

Create the React frontend bundled plugin. Uses Vite (default) or Webpack for bundling. For Vite, the plugin runs `create-vite` via `CommandRunner` for initial scaffold, then injects additional files via `FileProvider`. For Webpack, all files are generated directly (no scaffold command).

## Files to create

- `src/forge/plugins/react/__init__.py`
- `src/forge/plugins/react/plugin.py`

## API Spec

```python
class ReactPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "react"
    display_name = "React"
    description = "React frontend with Vite + TypeScript"
    requires: list[str] = []

    @staticmethod
    def _config(spec: ProjectSpec) -> dict[str, Any]:
        return spec.config.get("react", {})

    def questions(self) -> list[Question]:
        # Question(key="bundler", type=QuestionType.CHOICE, options=["vite", "webpack"], default="vite", ...)
        # Question(key="include_typescript", type=QuestionType.BOOLEAN, default=True, ...)
        # Question(key="include_router", type=QuestionType.BOOLEAN, default=False, ...)
        # Question(key="include_tailwind", type=QuestionType.BOOLEAN, default=False, ...)
        # Question(key="state_management", type=QuestionType.CHOICE, options=["none", "zustand", "redux"], default="none", ...)
        ...

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        # Core: src/App.tsx, src/main.tsx, public/index.html
        # If ts: src/vite-env.d.ts, tsconfig.json
        # If bundler=vite: vite.config.ts
        # If bundler=webpack: webpack.config.js
        # If tailwind: tailwind.config.js, postcss.config.js
        # If no ts: src/App.jsx, src/main.jsx (no .tsx files)
        # (vite scaffold + files() overlap is safe — staging overwrite handles it)
        ...

    def directories(self, spec: ProjectSpec) -> list[str]:
        # src/, src/components/, src/pages/, public/
        ...

    def generate(self, spec: ProjectSpec, target_dir: Path, executor) -> None:
        # if bundler == "vite":
        #     scaffold command: npm create vite@latest . -- --template react[-ts]
        #     then executor.run(["npm", "install"], cwd=target_dir)
        #     then executor.run(["npm", "install", "react-router-dom", ...], cwd=target_dir) if configured
        # if bundler == "webpack": no-op (files() handles everything)

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        # Base: react, react-dom
        # If ts: typescript, @types/react, @types/react-dom
        # If router: react-router-dom
        # If tailwind: tailwindcss, postcss, autoprefixer
        # If state_management == "zustand": zustand
        # If state_management == "redux": @reduxjs/toolkit, react-redux
```

## Design Notes

1. **Config access pattern**: Use `spec.config.get("react", {})` via a `_config(spec)` static helper (matching the T-008/T-009 established pattern). Never use `spec.plugin_config("react")` which raises `KeyError` when the key is absent.

2. **ValidationEngine owns input validation**: The plugin trusts that validated config arrives at its methods. Invalid bundler values are caught by `ValidationEngine.validate_plugin_config()` before they reach the plugin. The plugin may use `.get()` defaults defensively but need not validate inputs.

3. **Entry point registration**: `pyproject.toml:17` already registers `react = "forge.plugins.react:ReactPlugin"`. The class attribute `name = "react"` must match the entry point name. The T-005 handoff documents that the entry point name is the canonical ID — the class attribute must remain consistent.

4. **AC-4 scanner compliance**: Every `.py` file under `plugins/` must import from `forge.domain` (e.g., `from forge.domain import ProjectSpec as _  # noqa: F401`). `react/__init__.py` must include this import even if only re-exporting. The plugin file must NOT import from `forge.infrastructure` — not even under `TYPE_CHECKING`. Use untyped `executor` parameter in `generate()` to avoid the AC-4 scanner's infra import ban. `base.py` is exempt from the infra ban via `INFRA_EXEMPT_FILES`.

5. **Test-first AC-17 construction (invalid bundler)**: The AC-17 test must construct `Question` objects inline (not call `plugin.questions()`) to avoid a circular dependency where the test needs the plugin to exist before it can test validation. Follow the existing `test_validation.py:test_choice_invalid_option` pattern.

6. **Cross-method consistency**: Three methods (`files()`, `dependencies()`, `generate()`) produce output based on the same config keys. The implementation must ensure all three methods agree for every config permutation. The cross-method consistency matrix below documents the required mappings. **This is the same class of bug** found as a CRITICAL issue in T-008 code review (the `generate()` method only installed framework deps, ignoring conditional deps — causing generated projects to crash at runtime).

7. **`templates/` directory not used**: All file templates are small inline f-strings or module-level string constants (matching T-008/T-009 pattern). No Jinja2 dependency is needed.

8. **`state_management` is a config passthrough**: The `state_management` question is stored in config for downstream use but no framework-specific generated code is produced in this ticket. The plugin's `files()` and `generate()` do not branch on `state_management`; `dependencies()` conditionally includes the package (zustand or @reduxjs/toolkit + react-redux). Full state management scaffolding (store files, provider wrappers, devtools) is deferred to a follow-up ticket.

9. **Webpack scaffolding**: There is no standard Webpack scaffold command. When `bundler="webpack"`, `generate()` is a no-op (the plugin generates webpack.config.js and all other files via `files()` directly). When `bundler="vite"`, `generate()` runs `create-vite` and then installs additional npm packages.

10. **`generate()` duplicates `dependencies()` conditional logic**: Intentional design — `dependencies()` feeds `txn.requirements` (PluginExecutionEngine pipeline) while `generate()` runs `npm install` in the target directory. Same logic, different consumers.

11. **Question.default values**: All questions have explicit `default=` values in the `Question(...)` constructor calls. This ensures consistent behavior when no config is provided.

12. **Scaffold + files() overlap**: When `bundler="vite"`, the `create-vite` scaffold creates `public/index.html`, `src/main.tsx`, `src/App.tsx`, `vite.config.ts`, `tsconfig.json`, `src/vite-env.d.ts`, and `src/index.css`. The plugin's `files()` also generates these files (the staging directory's overwrite semantics handle the duplication safely). This avoids branching the file list based on bundler choice and keeps the implementation simple. For `bundler="webpack"`, `files()` is the sole generator of all project files since no scaffold command runs. The `directories()` method always declares the full directory tree regardless of bundler.

### Cross-Method Consistency Matrix

| Config | `files()` additions | `dependencies()` additions | `generate()` scaffold + install |
|--------|---------------------|---------------------------|--------------------------------|
| Default (vite + TS + no extras) | `src/App.tsx`, `src/main.tsx`, `src/vite-env.d.ts`, `src/index.css`, `vite.config.ts`, `tsconfig.json` (files() generates all listed files — scaffold creates the same files, staging overwrite handles duplication safely) | `react`, `react-dom`, `typescript`, `@types/react`, `@types/react-dom` (installed by create-vite scaffold) | `npm create vite@latest . -- --template react-ts` → `npm install [conditional deps]` |
| bundler=webpack | `webpack.config.js`, `tsconfig.json` (no `vite.config.ts`) | Same base | no-op |
| include_typescript=False | `src/App.jsx`, `src/main.jsx` (no `.tsx`), `src/vite-env.d.ts` absent | No `typescript`, `@types/react`, `@types/react-dom` | `npm create vite@latest . -- --template react` (no `-ts`) |
| bundler=webpack + include_typescript=False | `webpack.config.js`, `src/App.jsx`, `src/main.jsx` (no `.tsx`), `tsconfig.json` absent, `src/vite-env.d.ts` absent | No ts deps (same as above) | no-op |
| include_tailwind=True | `tailwind.config.js`, `postcss.config.js` | `tailwindcss`, `postcss`, `autoprefixer` | `npm install tailwindcss @tailwindcss/vite` |
| include_router=True | — (no extra files) | `react-router-dom` | `npm install react-router-dom` |
| state_management=zustand | — | `zustand` | `npm install zustand` |
| state_management=redux | — | `@reduxjs/toolkit`, `react-redux` | `npm install @reduxjs/toolkit react-redux` |
| All above combined | All file variants | All dep variants | All install steps |

Note: `files()` always produces either `.tsx` or `.jsx` variants based on `include_typescript`. The core file set is the same regardless of bundler choice (except for bundler-specific config files). `dependencies()` and `generate()` must produce consistent package lists for all permutations.

## Acceptance Criteria

### Discovery & Identity

**AC-01 — [unit] plugin.name**: Given the `ReactPlugin` class, when instantiated, then `plugin.name` returns `"react"`.

### File Provider (files)

**AC-02a — files() core paths**: Given a `ProjectSpec` with `frontend_id="react"` and default config (`{"react": {}}`), when `files()` is called, then the returned list includes `GeneratedFile` entries for `src/App.tsx`, `src/main.tsx`, and `public/index.html`. All entries have `Path` objects as their `.path` attribute.

**AC-02b — engine integration**: Given a `ProjectSpec` with `frontend_id="react"`, when `PluginExecutionEngine.run()` is simulated (call `files()` → `txn.stage_file()`, `directories()` → `txn.stage_directory()`, `dependencies()` → `txn.requirements.extend()`), then core file paths are staged and base dependencies are appended to `txn.requirements`.

### Configurable (questions)

**AC-03 — questions()**: Given the `Configurable` mixin, when `questions()` is called, then it returns `Question` objects whose `.key` attributes include `"bundler"`, `"include_typescript"`, `"include_router"`, `"include_tailwind"`, and `"state_management"`. The `bundler` question must be `QuestionType.CHOICE` with options exactly equal to `["vite", "webpack"]`. `include_typescript`, `include_router`, and `include_tailwind` must be `QuestionType.BOOLEAN`. `state_management` must be `QuestionType.CHOICE` with options exactly equal to `["none", "zustand", "redux"]`. All keys must be unique.

### Bundler Variants

**AC-04 — bundler=vite**: Given `bundler="vite"` in config, when `files()` is called, then `vite.config.ts` is in the returned file paths, and `webpack.config.js` is NOT in the returned file paths.

**AC-05 — bundler=webpack**: Given `bundler="webpack"` in config, when `files()` is called, then `webpack.config.js` is in the returned file paths, and `vite.config.ts` is NOT in the returned file paths.

### Tailwind CSS

**AC-06 — include_tailwind=True**: Given `include_tailwind=True` in config, when `files()` is called, then `tailwind.config.js` is in the returned file paths, and its content contains `"./index.html"` and `"./src/**/*.{ts,tsx}"` (or `"{js,jsx}"` when TypeScript is disabled) as content paths. `postcss.config.js` is also present.

**AC-07 — include_tailwind=False or absent**: Given `include_tailwind=False` (or absent from config), when `files()` is called, then `tailwind.config.js` is NOT in the returned file paths.

### TypeScript Variants

**AC-08 — include_typescript=True**: Given `include_typescript=True` in config, when `files()` is called, then `src/App.tsx` and `src/main.tsx` are in the returned file paths, and no `.jsx` files are present. When `dependencies()` is called, the returned list includes `"typescript"`, `"@types/react"`, and `"@types/react-dom"`.

**AC-09 — include_typescript=False**: Given `include_typescript=False` in config, when `files()` is called, then `src/App.jsx` and `src/main.jsx` are in the returned file paths, and no `.tsx` or `.ts` files are present. When `dependencies()` is called, the returned list does NOT include `"typescript"`, `"@types/react"`, or `"@types/react-dom"`.

### Router

**AC-10a — include_router=True**: Given `include_router=True` and `bundler="vite"` in config, when `dependencies()` is called, then the returned list includes `"react-router-dom"`. When `generate()` is called, the executor command includes `"react-router-dom"`.

**AC-10b — include_router=False or absent**: Given `include_router=False` (or absent from config), when `dependencies()` is called, then the returned list does NOT include `"react-router-dom"`.

### Directories

**AC-11 — directories()**: Given the React plugin, when `directories()` is called, then the returned list contains `"src/"`, `"src/components/"`, `"src/pages/"`, and `"public/"`.

### Dependencies

**AC-12a — dependencies() base set**: Given default config (`{"react": {}}` which implies `include_typescript=True`), when `dependencies()` is called, then the returned list includes `"react"`, `"react-dom"`, `"typescript"`, `"@types/react"`, and `"@types/react-dom"`, and does NOT include `"react-router-dom"`, `"tailwindcss"`, `"zustand"`, or `"@reduxjs/toolkit"`.

**AC-12b — dependencies() with zustand**: Given `state_management="zustand"` in config, when `dependencies()` is called, then the returned list includes `"zustand"` and still includes `"react"` and `"react-dom"`.

**AC-12c — dependencies() with redux**: Given `state_management="redux"` in config, when `dependencies()` is called, then the returned list includes `"@reduxjs/toolkit"` and `"react-redux"`, and still includes `"react"` and `"react-dom"`.

### Command Runner (generate)

**AC-13 — generate() default config**: Given default config and `bundler="vite"`, when `generate()` is called with a mock executor, then `executor.run()` is called at least once with a command list that includes `"npm"`, `"create"`, `"vite"`, and `"--template"` followed by `"react-ts"` (since `include_typescript` defaults to `True`). The `cwd` parameter is passed to at least one `executor.run()` call.

**AC-14a — generate() with router**: Given `include_router=True` and `bundler="vite"` in config, when `generate()` is called with a mock executor, then at least one `executor.run()` call includes `"react-router-dom"` in its command list.

**AC-14b — generate() with tailwind**: Given `include_tailwind=True` and `bundler="vite"` in config, when `generate()` is called with a mock executor, then at least one `executor.run()` call includes `"tailwindcss"` in its command list.

**AC-14c — generate() with zustand**: Given `state_management="zustand"` and `bundler="vite"` in config, when `generate()` is called with a mock executor, then at least one `executor.run()` call includes `"zustand"` in its command list.

**AC-14d — generate() with redux**: Given `state_management="redux"` and `bundler="vite"` in config, when `generate()` is called with a mock executor, then at least one `executor.run()` call includes `"@reduxjs/toolkit"` in its command list.

**AC-14e — generate() with no TypeScript**: Given `include_typescript=False` and `bundler="vite"` in config, when `generate()` is called with a mock executor, then at least one `executor.run()` call includes `"--template"` followed by `"react"` (not `"react-ts"`) in its command list.

**AC-14f — generate() with webpack is no-op**: Given `bundler="webpack"` in config, when `generate()` is called with a mock executor, then `executor.run()` is NOT called.

The dependency list in `generate()` must match the `dependencies()` output for the same config across all variants.

### Error and Edge Cases

**AC-15 — empty config dict**: Given `config={"react": {}}` (empty config dict — plugin uses internal defaults), when `files()`, `directories()`, and `dependencies()` are called, then defaults are used: bundler defaults to `"vite"`, `include_typescript` defaults to `True`, `include_tailwind` defaults to `False`, `state_management` defaults to `"none"`. No exception is raised.

**AC-16 — missing "react" config key**: Given `config={}` (no `"react"` key in `ProjectSpec.config`), when `files()`, `directories()`, and `dependencies()` are called, then no exception is raised and default values are used (the plugin accesses config via `spec.config.get("react", {})`).

**AC-17 — invalid bundler value**: Given an invalid `bundler` value (e.g., `"invalid"`) in plugin config, when `ValidationEngine.validate_plugin_config()` is called with the plugin's questions (constructed inline per Design Note 5), then a `ValidationError` with severity `"error"` is returned.

### Identity & Module

**AC-18 — display_name and description**: Given the `ReactPlugin` class, when instantiated, then `display_name` returns `"React"` and `description` returns a non-empty string.

**AC-19 — module export**: Given the `forge.plugins.react` package, when imported, then `ReactPlugin` is importable from `forge.plugins.react`.

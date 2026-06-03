# T-010: React Plugin

- **type**: story
- **complexity**: medium
- **layer**: `plugins/react/`
- **dependencies**: T-002, T-001
- **phase**: 2 — Remaining Bundled Plugins
- **estimated_context**: ~25% of window

## Description

Create the React frontend bundled plugin. Unlike Django/FastAPI which generate files directly, React can optionally use `create-react-app` via `CommandRunner` for initial scaffold, then inject additional files.

## Files to create

- `src/forge/plugins/react/__init__.py`
- `src/forge/plugins/react/plugin.py`
- `src/forge/plugins/react/templates/`

## API Spec

```python
class ReactPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "react"
    display_name = "React"
    description = "React frontend with Vite + TypeScript"
    requires: list[str] = []

    def questions(self) -> list[Question]:
        # bundler: str (choice: vite, webpack, cra)
        # include_typescript: bool
        # include_router: bool
        # include_tailwind: bool
        # state_management: str (choice: none, zustand, redux)
        ...

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        # src/App.tsx, src/main.tsx, src/api/client.ts
        # vite.config.ts (if vite), tailwind.config.js (if tailwind)
        ...

    def directories(self, spec: ProjectSpec) -> list[str]:
        # src/, src/components/, src/pages/, public/
        ...

    def generate(self, spec: ProjectSpec, target_dir: Path) -> None:
        # npx create-vite@latest --template react-ts (if vite + ts)
        # or: npx create-react-app . (if cra)

    def dependencies(self) -> list[str]:
        return []   # Node.js project, not Python
```

## Acceptance Criteria

1. **Given** the React plugin is registered, **when** `discover()` is called, **then** it is found with name `"react"`.
2. **Given** a `ProjectSpec` with `frontend_id="react"`, **when** `files()` is called, **then** it returns `src/App.tsx` and `public/index.html` stubs.
3. **Given** `bundler="vite"` in config, **when** `generate()` is called, **then** Vite-specific config files are included.
4. **Given** `include_tailwind=True`, **when** `files()` is called, **then** `tailwind.config.js` content references the correct paths.

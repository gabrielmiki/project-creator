# Forge

Local-first desktop application for generating project structures from predefined templates. Written in Python with PySide6 (Qt).

## Tech Stack

- **Language**: Python 3.12+
- **UI**: PySide6
- **Package manager**: uv
- **Lint/format**: ruff
- **Type checker**: mypy
- **Test**: pytest

## Project Structure

```
src/forge/                # Application package
├── __main__.py           # Entry point: `forge` (CLI or GUI)
├── app.py                # QApplication bootstrap
├── domain/               # Pure leaf models (zero imports from other layers)
│   └── project_spec.py, questions.py, generated_file.py
├── plugins/              # Plugin system + framework plugins
│   ├── base.py           # PluginBase + capability mixins (Configurable, FileProvider, ...)
│   ├── fastapi/
│   ├── django/
│   ├── react/
│   └── htmx/
├── ui/                   # PySide6 wizard screens
│   ├── main_window.py
│   ├── screens/          # 5 wizard screens
│   ├── widgets/          # Reusable widgets
│   └── workers.py        # QThread-based GenerationWorker
├── generation/           # Facade layer — single UI entry point
│   ├── orchestrator.py   # Thin coordinator of stages
│   ├── stages/           # DirectoryInitializer, SharedStructureScaffolder, PluginExecutionEngine, ...
│   ├── registry.py       # PluginRegistry (discovery via entry points + .plugins/, ID resolution)
│   ├── validation.py     # ValidationEngine
│   └── progress.py       # ProgressReporter protocol + StdoutProgressReporter
├── infrastructure/       # All I/O (filesystem, subprocess, staging)
│   ├── file_operations.py
│   ├── process_executor.py
│   └── transaction.py    # GenerationTransaction (staging → commit/rollback)
tests/
├── unit/
├── integration/
└── fixtures/
.plugins/                 # User-installed plugins (flat, no nesting)
```

## Commands

| Action | Command |
|---|---|
| Run app (GUI) | `python -m forge` |
| Run app (CLI) | `python -m forge --headless <spec.json> <output>` |
| Install deps | `uv sync` |
| Add dependency | `uv add <package>` |
| Lint check | `uv run ruff check src/` |
| Format | `uv run ruff format src/` |
| Type check | `uv run mypy src/` |
| Run tests | `uv run pytest tests/` |
| Test w/ coverage | `uv run pytest tests/ --cov=src/forge` |

## Architecture Rules

1. **Layer separation**: `ui/` → `generation/` → `plugins/` — plugins never import from UI, UI never imports from plugins/infrastructure directly
2. **Generation layer is the single facade**: UI queries templates, questions, and triggers generation through the generation layer only — no direct plugin access from UI
3. **Plugins are isolated**: each plugin in its own directory, registered via entry points; capability mixins (not monolithic interface)
4. **Domain models contain zero UI logic** and **zero imports from any other Forge layer** — models use string IDs, not class references
5. **No circular imports**: domain/ is the leaf dependency; PluginRegistry in generation/ resolves IDs to plugin instances
6. **Infrastructure is the only I/O layer**: no filesystem writes or subprocess calls outside infrastructure/
7. **Type hints required** in all `src/forge/` modules
8. **Generated projects** follow the AI Engineering Master Process structure
9. **Atomic generation**: staging directory + commit/rollback prevents partially-generated projects

## For Framework Authors

See `docs/context/architecture.md` for plugin authoring (capability mixin interface, discovery conventions, dependency ordering).

## Forge Design Principles

- Local-first: no network, no auth, no accounts
- Plugin extensibility: frameworks are plugins, never core changes
- Wizard UX: linear, no side navigation, one step at a time
- Destructive regeneration: generated structure is the source of truth
- Atomic generation: staging + rollback on failure
- Threaded generation: QThread-based worker prevents UI freeze

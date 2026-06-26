# Forge

**Local-first desktop application for generating project structures from predefined templates.**

Forge is a PySide6-based wizard that scaffolds complete software projects from a set of configurable templates. Choose a backend framework (FastAPI, Django) and frontend framework (React, HTMX), configure options through an interactive UI, and generate a production-ready project structure — all locally, with no network or accounts required.

---

## Features

- **GUI wizard** — 5-step linear interface: template selection, domain definition, stack configuration, review summary, generation with progress
- **Headless CLI** — `forge --headless spec.json output/` for automation and CI pipelines
- **4 bundled plugins** — FastAPI, Django, React (Vite/Webpack), HTMX (Alpine.js, Tailwind, Bootstrap)
- **Plugin system** — Extend via entry points or `.plugins/` directory; plugins implement capability mixins (files, commands, config questions, dependencies)
- **Atomic generation** — Staging directory with commit/rollback prevents partial projects on failure
- **Dependency resolution** — Topological sort of plugins based on `requires` and `run_after` declarations
- **Validation** — Spec validation (project name, plugin IDs, config bounds) before generation
- **Threaded generation** — Background QThread keeps the UI responsive during project generation
- **Override-safe** — Confirmation dialog when output directory exists; overwrite preserves pre-existing files alongside generated ones

---

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)

### Install and Run

```bash
# Clone the repository
git clone https://github.com/gabrielmiki/project-creator.git
cd project-creator

# Install dependencies
uv sync

# Launch the GUI
python -m forge
```

### Try Headless Mode

```bash
# Generate a FastAPI project from a JSON spec
python -m forge --headless spec.json output/
```

Example `spec.json`:

```json
{
  "project_name": "my-api",
  "template": {
    "id": "fastapi-only",
    "display_name": "FastAPI Only",
    "description": "FastAPI backend",
    "backend_id": "fastapi",
    "frontend_id": null
  },
  "domains": [{"name": "users"}],
  "config": {
    "fastapi": {
      "orm": "sqlalchemy",
      "auth": true,
      "include_alembic": true
    }
  }
}
```

---

## Usage

### GUI Mode

When run without arguments, Forge opens a Qt wizard with 5 linear screens:

| Screen | Description |
|--------|-------------|
| **Welcome** | Enter project name |
| **Domains** | Select backend (FastAPI/Django) and optional frontend (React/HTMX) |
| **Configuration** | Configure plugin-specific options (ORM, auth, bundler, CSS framework, etc.) |
| **Review** | Summary tree of what will be generated, estimated duration |
| **Generation** | Progress bar + live log; then "Open Project" or "Close" |

### CLI Mode

```bash
python -m forge --headless <spec.json> <output-dir>
```

The CLI path performs the same validation and generation pipeline as the GUI, reporting progress to stdout:

- Exit code `0` on success
- Exit code `1` on validation error, JSON parse error, missing file, or generation failure

### Available Plugins

| Plugin | ID | Backend/Frontend | Scaffold Command |
|--------|----|------------------|------------------|
| FastAPI | `fastapi` | Backend | `uv add` with conditional deps |
| Django | `django` | Backend | `uv add` with conditional deps |
| React | `react` | Frontend | `create-vite` (or no-op for Webpack) |
| HTMX | `htmx` | Frontend | No-op (static file generation only) |

---

## Project Structure

```
src/forge/                # Application package
├── __main__.py           # Entry point: `python -m forge`
├── app.py                # QApplication bootstrap + CLI entry
├── domain/               # Pure leaf models (zero imports from other layers)
│   ├── project_spec.py   # ProjectSpec, TemplateDefinition, Domain
│   ├── questions.py      # Question, QuestionType, ValidationRule
│   └── generated_file.py # GeneratedFile, DurationEstimate
├── plugins/              # Plugin system + framework plugins
│   ├── base.py           # PluginBase + capability mixins
│   ├── fastapi/          # FastAPI backend plugin
│   ├── django/           # Django backend plugin
│   ├── react/            # React frontend plugin (Vite/Webpack)
│   └── htmx/             # HTMX frontend plugin (Alpine/Tailwind/Bootstrap)
├── ui/                   # PySide6 wizard screens
│   ├── main_window.py    # MainWindow with navigation + signal routing
│   ├── screens/          # 5 wizard screen implementations
│   ├── widgets/          # Reusable UI components
│   └── workers.py        # QThread-based GenerationWorker
├── generation/           # Facade layer — single UI entry point
│   ├── orchestrator.py   # Thin coordinator of 6 generation stages
│   ├── stages/           # Stage implementations
│   ├── registry.py       # PluginRegistry (entry points + .plugins/)
│   ├── validation.py     # ValidationEngine (spec + config validation)
│   └── progress.py       # ProgressReporter protocol + implementations
└── infrastructure/       # All I/O (filesystem, subprocess)
    ├── file_operations.py
    ├── process_executor.py
    └── transaction.py    # GenerationTransaction (staging → commit/rollback)

tests/                    # Test suite
├── unit/                 # ~300+ unit tests (mocked dependencies)
├── integration/          # ~60+ integration tests (real registry + transaction)
└── fixtures/             # Shared test data

docs/
├── adr/                  # Architecture Decision Records
├── context/              # Architecture docs, tickets, post-mortems
│   ├── architecture.md   # Full architecture reference
│   ├── pipeline.md       # Generation pipeline details
│   ├── tickets/          # Feature tickets
│   └── post-mortem/      # Post-implementation retrospectives
└── plan/                 # Planning documents
```

---

## Architecture Overview

Forge follows a strict layered architecture with unidirectional dependencies:

```
UI (PySide6) → Generation (facade) → Plugins → Domain (leaf)
                                            → Infrastructure (I/O)
```

### Key Design Principles

1. **Layer separation** — UI never imports from plugins or infrastructure directly. All interaction goes through the generation facade.
2. **Domain is pure leaf** — Domain models have zero imports from any other Forge layer. They are simple dataclasses with string IDs (not class references).
3. **Plugins are isolated** — Each plugin is a self-contained directory. Plugins opt into capability mixins (ISP compliance), never inherit a monolithic interface.
4. **Infrastructure is the only I/O layer** — No code outside `infrastructure/` writes files or runs subprocesses.
5. **Atomic generation** — All file writes go to a staging directory first. On success, staging is committed atomically. On failure, staging and any registered checkpoint paths are rolled back.

### Generation Pipeline

```
Orchestrator.generate(spec, output_dir, progress)
  ├── Stage 1: DirectoryInitializer      — Validate output dir exists and is empty
  ├── Stage 2: SharedStructureScaffolder — README.md, .gitignore, .python-version, docs/
  ├── Stage 3: PluginExecutionEngine     — Topo-sorted plugin execution (files + cmds + deps)
  ├── Stage 4: JustfileGenerator         — Generate project-level Justfile
  ├── Stage 5: ProjectDocumentationWriter — AGENTS.md + CLAUDE.md
  └── Stage 6: AgentSkillScaffolder      — .opencode/ agent/skill/handoff stubs
```

### Plugin Mixin System

Plugins inherit only the capabilities they need:

```python
class FastapiPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "fastapi"
    display_name = "FastAPI"
    description = "FastAPI backend with SQLAlchemy + Pydantic"
    # questions(), files(), directories(), generate(), dependencies()
```

| Mixin | Purpose |
|-------|---------|
| `Configurable` | Supplies wizard questions for Step 3 (ORM choice, auth toggle, etc.) |
| `FileProvider` | Declares files and directories to create |
| `CommandRunner` | Runs scaffold commands (e.g., `uv add`, `npm create vite`) |
| `DependencyProvider` | Lists Python package dependencies |

---

## Development

### Setup

```bash
uv sync                   # Install all dependencies
```

### Commands

```bash
uv run ruff check src/    # Lint
uv run ruff format src/   # Format
uv run mypy -p forge      # Type check
uv run pytest tests/      # Run all tests (unit + integration)
uv run pytest tests/ --cov=src/forge  # With coverage
```

### GUI Tests

GUI tests require a display server and are marked with `@pytest.mark.gui`. Run headless:

```bash
QT_QPA_PLATFORM=offscreen uv run pytest -m "gui" -v
```

Skip GUI tests entirely:

```bash
uv run pytest -m "not gui" -v
```

### Testing Philosophy

- **Unit tests** (`tests/unit/`) — Mock all dependencies (registry, orchestrator, executor). Fast, isolated, ~300 tests.
- **Integration tests** (`tests/integration/`) — Use real `PluginRegistry` (discovers real plugins via entry points), real `GenerationTransaction`, real generation stages. Only `ProcessExecutor` is mocked to prevent real subprocess calls. ~60+ tests covering full pipeline, multi-plugin combos, GUI worker lifecycle, overwrite flow, and error/rollback scenarios.

---

## Plugin Authoring (For Framework Authors)

Create a new plugin by placing a package under `src/forge/plugins/<name>/` with a `plugin.py` exposing a plugin instance.

### Minimal Plugin

```python
# src/forge/plugins/custom/plugin.py
from forge.plugins.base import PluginBase, FileProvider
from forge.domain import GeneratedFile, ProjectSpec

class CustomPlugin(PluginBase, FileProvider):
    name = "custom"
    display_name = "Custom Framework"
    description = "Generates custom project scaffolding"

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        return [
            GeneratedFile(path="README.md", content="# Custom Project"),
        ]

    def directories(self, spec: ProjectSpec) -> list[str]:
        return ["src", "tests"]
```

### Registration

Plugins register via entry points in `pyproject.toml`:

```toml
[project.entry-points."forge.plugins"]
custom = "forge.plugins.custom:CustomPlugin"
```

Or by placing a `.py` file in the `.plugins/` directory (for user-installed plugins, lower priority).

### Full Reference

See `docs/context/architecture.md` for the complete plugin authoring guide, including:
- Capability mixin interface details
- Dependency ordering (`requires`, `run_after`)
- Question configuration for wizard integration
- Discovery conventions and conflict resolution

---

## Project Status

Forge is built incrementally using feature tickets tracked in `docs/context/tickets/`. Each ticket goes through TDD review, implementation, code review, and post-mortem documentation. The project currently implements:

- T-001: Domain models
- T-002: Plugin base + mixin system
- T-003: FastAPI plugin
- T-004: Generation transaction (atomic commit/rollback)
- T-005: Plugin registry (entry points + .plugins/)
- T-006: Generation stages (pipeline decomposition)
- T-007: Progress reporter (protocol + Qt/stdout/mock implementations)
- T-008: Validation engine (spec + plugin config)
- T-009: Django plugin
- T-010: React plugin
- T-011: HTMX plugin
- T-012: QApplication + MainWindow
- T-013: Generation worker (QThread)
- T-014: Wizard screens 1–3
- T-015: Wizard screens 4–5 + overwrite + lifecycle
- T-016: Integration tests — foundation
- T-017: Integration tests — CLI + pipeline
- T-018: Integration tests — full pipeline

# Forge Architecture

## Overview

Forge is a local-first desktop application that generates software project structures from predefined templates. It uses a plugin architecture where each framework (FastAPI, Django, React, HTMX) is an independent plugin.

## Architecture Layers

```
UI Layer (PySide6)
    └── Wizard screens (Template → Domains → Config → Summary → Generate)
            │
Generation Layer (facade — single entry point for UI)
    ├── Orchestrator (thin coordinator of stages)
    ├── PluginRegistry (discovery via entry points + .plugins/, ID resolution)
    ├── ValidationEngine (validates ProjectSpec + plugin config)
    ├── ProgressReporter (protocol → Qt signals / stdout / mock)
    └── Stages (DirectoryInitializer, SharedStructureScaffolder, PluginExecutionEngine, JustfileGenerator, ProjectDocumentationWriter, AgentSkillScaffolder)
            │
Plugin Layer
    ├── PluginBase (abstract — name, display_name, description)
    ├── Configurable (questions for Step 3 wizard)
    ├── FileProvider (declared files + directories)
    ├── CommandRunner (scaffold commands, subprocess)
    └── DependencyProvider (Python packages)
            ├── fastapi/plugin.py
            ├── django/plugin.py
            ├── react/plugin.py
            └── htmx/plugin.py
            │
Domain Layer (pure leaf models, zero imports from other layers)
    ├── ProjectSpec, TemplateDefinition, Domain
    ├── Question, QuestionType, GeneratedFile
    └── ValidatedConfig
            │
Infrastructure Layer (all I/O encapsulated here)
    ├── FileOperations (atomic writes, staging directory)
    ├── ProcessExecutor (subprocess management)
    └── GenerationTransaction (staging → commit / rollback)
```

## Layer Rules

1. **UI → Generation only**: UI never imports from `plugins/` or `infrastructure/` directly. All interaction is through the generation facade.
2. **Domain is pure leaf**: Domain models never import from `plugins/`, `ui/`, `generation/`, or `infrastructure/`. They contain zero logic beyond data structure.
3. **Plugins never import UI**: Plugin code has no knowledge of Qt or wizard screens.
4. **Infrastructure is the only I/O layer**: No code outside `infrastructure/` writes files, runs subprocesses, or manages directories.

## Plugin Architecture

Each plugin is a directory under `src/forge/plugins/<name>/` containing:

- `plugin.py` — plugin class(es) implementing capability mixins
- `templates/` — optional Jinja2 template files (for content-heavy plugins)

Plugins are discovered via two paths with explicit priority:

| Source | Priority | Override behavior |
|--------|----------|-------------------|
| `entry_points["forge.plugins"]` | 10 (system) | Highest — wins all conflicts |
| `.plugins/` directory | 5 (user) | Lower — only fills gaps, cannot override system |

Conflict resolution:
- Same-name plugins: higher priority wins; a warning is logged with both sources
- Strict mode: errors on ANY conflict (for development/CI)
- `.plugins/` files: each entry is either a `.py` file or a directory with `plugin.py`; must export a `plugin` attribute
- Deterministic: sorted file iteration, explicit priority tiers

### Dependency ordering between plugins

```python
class PluginBase(ABC):
    name: str
    display_name: str
    description: str
    requires: list[str] = []       # plugin IDs that must run first
    run_after: list[str] = []      # soft ordering hints
```

PluginExecutionEngine resolves the graph topologically and detects cycles. Each plugin is guaranteed that its dependencies have already generated their structure.

## Plugin Interface (ISP-compliant mixins)

```python
# forge/plugins/base.py

class PluginBase(ABC):
    """Minimal base — every plugin must provide these."""
    name: str
    display_name: str
    description: str
    requires: list[str] = []
    run_after: list[str] = []

class Configurable(ABC):
    """Plugin has user-configurable questions (wizard Step 3)."""
    def questions(self) -> list[Question]: ...

class FileProvider(ABC):
    """Plugin declares files and directories it creates."""
    def files(self, spec: ProjectSpec) -> list[GeneratedFile]: ...
    def directories(self, spec: ProjectSpec) -> list[str]: ...

class CommandRunner(ABC):
    """Plugin runs shell commands or scaffold tools during generation."""
    def generate(self, spec: ProjectSpec, target_dir: Path) -> None: ...

class DependencyProvider(ABC):
    """Plugin requires Python packages."""
    def dependencies(self) -> list[str]: ...
```

Plugins inherit only the mixins they need:

```python
class FastapiPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "fastapi"
    display_name = "FastAPI"
    description = "FastAPI backend with SQLAlchemy + Pydantic"

class TailwindConfigPlugin(PluginBase, FileProvider):
    name = "tailwind"
    display_name = "Tailwind CSS Config"
    description = "Generates tailwind.config.js"
```

The orchestrator checks capabilities at runtime via `isinstance()`.

## Domain Models

All models live in `src/forge/domain/` with zero imports from other Forge layers.

```python
@dataclass
class Question:
    key: str
    label: str
    description: str = ""
    type: QuestionType = QuestionType.STRING
    required: bool = True
    default: Any = None
    options: list[str] | None = None
    placeholder: str | None = None
    validation: Callable[[Any], bool | str] | None = None

class QuestionType(Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    INTEGER = "integer"

@dataclass
class ProjectSpec:
    project_name: str
    template: TemplateDefinition
    domains: list[Domain]
    config: dict[str, dict[str, Any]]    # plugin_id → {key: value}

    def plugin_config(self, plugin_id: str) -> dict[str, Any]:
        """Namespaced accessor. Raises KeyError if plugin has no config."""
        return self.config[plugin_id]

@dataclass
class TemplateDefinition:
    id: str
    display_name: str
    backend_id: str                       # string ID, resolved via PluginRegistry
    frontend_id: str | None               # string ID, resolved via PluginRegistry
    description: str

@dataclass
class Domain:
    name: str
    slug: str                             # auto-derived, URL-safe

@dataclass
class GeneratedFile:
    path: str                             # relative path in generated project
    content: str                          # rendered content
    executable: bool = False              # chmod +x
```

## Generation Pipeline (decomposed orchestrator)

```
Orchestrator.generate(spec, output_dir, progress: ProgressReporter)
    │
    ├── Stage 1: DirectoryInitializer
    │       output_dir.mkdir(parents=True, exist_ok=True)
    │
    ├── Stage 2: SharedStructureScaffolder
    │       docs/, AGENTS.md, .gitignore, README.md, .claude/, tests/, scripts/
    │
    ├── Stage 3: PluginExecutionEngine (topo-sorted)
    │       For each plugin (by dependency order):
    │           Check capabilities (isinstance mixins)
    │           If FileProvider: write files + create directories
    │           If DependencyProvider: install packages
    │           If CommandRunner: run scaffold commands
    │
    ├── Stage 4: JustfileGenerator
    │       Serializes ProjectSpec → Justfile
    │
    ├── Stage 5: ProjectDocumentationWriter
    │       AGENTS.md + CLAUDE.md for the generated project
    │
    └── Stage 6: AgentSkillScaffolder
            .claude/agents/ + .claude/skills/ + .claude/handoffs/ stubs
```

Each stage implements:

```python
class GenerationStage(ABC):
    name: str
    def run(self, spec: ProjectSpec, output_dir: Path, progress: ProgressReporter) -> None: ...
```

## Cross-Cutting Concerns

### ProgressReporter (abstract protocol)

```python
class ProgressReporter(Protocol):
    def on_stage_start(self, stage_name: str, total_steps: int) -> None: ...
    def on_step_complete(self, step_name: str) -> None: ...
    def on_log(self, message: str, level: str = "info") -> None: ...
    def on_error(self, error: Exception, recoverable: bool) -> None: ...
    def should_cancel(self) -> bool: ...
```

Implementations:
- **QtProgressReporter**: Emits PySide6 signals → wizard progress bar + log widget
- **MockProgressReporter**: Collects calls for test assertions
- **StdoutProgressReporter**: CLI/headless mode

### GenerationTransaction (atomicity)

```python
class GenerationTransaction:
    def __init__(self, output_dir: Path):
        self.staging = output_dir / ".forge-staging"
        self.manifest: list[Path] = []

    def stage_file(self, path: Path, content: str) -> None: ...
    def commit(self) -> None: ...            # atomic rename staging → output
    def rollback(self) -> None: ...          # clean up staging
```

Scaffold commands (which can't be staged) use checkpoint-based rollback: track created paths, delete on failure.

### ValidationEngine

```python
class ValidationEngine:
    def validate_spec(self, spec: ProjectSpec) -> list[ValidationError]: ...
    def validate_plugin_config(self, plugin_id: str, config: dict[str, Any], questions: list[Question]) -> list[ValidationError]: ...
```

### Threading strategy

Generation runs on a `QThread` to prevent UI freezing:

```
UI Thread:     MainWindow (responsive during generation)
                    │ receives Qt signals
QThread:       GenerationWorker → Orchestrator.generate()
                    │ emits progress_changed, log_message, finished, error_occurred
```

The `ProgressReporter` protocol keeps the orchestrator framework-agnostic. The Qt binding happens in the worker class, not in the orchestrator.

## UI Workflow

The wizard has 5 linear screens with no side navigation:

1. **Template Selection** — Choose from predefined stack combinations (queries `Orchestrator.get_available_templates()` facade)
2. **Domain Definition** — Tag editor for project domains (auth, users, payments)
3. **Stack Config** — Dynamic form rendered from plugin questions (queries `Orchestrator.get_questions(template_id)` facade)
4. **Review Summary** — Tree view of what will be generated
5. **Generation** — Progress bar + status log (via `ProgressReporter`), then "Open Project" / "Close"

## Design Decisions

- **No persistent state**: The app never saves or reopens projects. Each run is ephemeral.
- **Destructive regeneration**: The generated structure is the source of truth. Removed domains = deleted directories.
- **Justfile as spec model**: The Justfile is a declarative representation of the project structure, capable of recreating it.
- **Templates are code**: Framework templates live in Python, not config files. No template marketplace. Plugins generate file content via f-strings, builder methods, or Jinja2 templates bundled in the plugin directory (resolving the template_loader.md contradiction).
- **Plugin capabilities via mixins**: Plugins opt in to the interfaces they need (ISP compliance). No forced empty methods.
- **Generation layer as facade**: UI never touches plugins or infrastructure directly. All interaction goes through the generation layer.
- **Atomic generation**: Staging directory + commit/rollback prevents partially-generated projects on failure.
- **Plugin discovery with priority**: System plugins (entry points) always win over user plugins (.plugins/). Conflicts are logged, never silent.
- **Plugin dependency ordering**: `requires` and `run_after` declarations enable topo-sorted execution, not hardcoded "backend first, frontend second".

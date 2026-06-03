# Forge — Application Functions PRD

## Goals & Non-Goals

### Goals
- Provide a single-shot local desktop wizard that scaffolds a complete AI Engineering Master Process project from user-selected templates
- Support two entry modes: interactive GUI (default) and headless CLI for automation
- Allow zero or more domains (plugins) to be selected per project — generating only the shared structure when none are chosen
- Show estimated duration before generation begins, and warn on unusually large or time-consuming operations
- Auto-rollback on generation failure with a clear error message; no silent partial output
- Ask the user for confirmation before overwriting an existing directory
- Support both global project configuration (author, Python version, etc.) and per-plugin configuration step
- Be local-first: no network, no auth, no accounts, no telemetry
- Complete from launch to output in a single session — no project reopening or resuming

### Non-Goals
- Not a web app, SaaS, or client/server architecture
- Not a general-purpose editor or IDE — Forge generates and exits
- Not a package manager or runtime environment
- Not a dry-run or preview mode — generation is all-or-nothing with atomic rollback
- Not a multi-user or CI system — single local user only
- Not a plugin authoring IDE — plugins are code written outside Forge
- No account system, cloud sync, or user data persistence across sessions

---

## User Stories

### Solo Developer — Primary Persona

**Story 1: Quick scaffold**
> As a developer, I want to launch Forge, answer a few questions, and get a fully-structured project with justfile, README, agent skills, and my chosen framework boilerplate — so I can start coding immediately instead of manually setting up the project skeleton.

**Story 2: Framework starter**
> As a developer starting a Django + HTMX project, I want to select Django as backend and HTMX as frontend, configure each (DB choice, CSS framework, etc.), and get a ready-to-run project with both frameworks wired together.

**Story 3: Minimal structure only**
> As a developer who just wants the project scaffold without any framework, I want to select zero domains and get the shared structure (justfile, README, .gitignore, agent skills) so I can add my own code structure manually.

**Story 4: Safe regeneration**
> As a developer re-running generation into the same directory, I want to be prompted before Forge overwrites anything, so I don't accidentally lose my work.

**Story 5: Failed generation recovery**
> As a developer running a project with a long scaffold command (e.g., create-react-app via npx), if it fails partway through, I want Forge to clean up the partial output automatically and show me what went wrong — no stale directories left behind.

**Story 6: Automated/CI invocation**
> As a developer or automation user, I want to run `forge --headless spec.json output/` with a minimal JSON spec and get the same result as the GUI, so I can integrate scaffolding into scripts or pipelines.

**Story 7: Informed before slow operations**
> As a developer, I want to see an estimated duration and a warning if generation will take longer than expected (e.g., >10s or >100 files), so I can decide whether to proceed or adjust my choices.

---

## API Contract Sketches

### Orchestrator Facade (single UI entry point in `generation/`)

```
Query:    Orchestrator.get_available_backends() -> list[TemplateDefinition]
Query:    Orchestrator.get_available_frontends() -> list[TemplateDefinition]
Query:    Orchestrator.get_domains_for_selection() -> BackendFrontendPair
Query:    Orchestrator.get_global_questions() -> list[Question]
Query:    Orchestrator.get_domain_questions(backend_id: str | None, frontend_id: str | None) -> dict[str, list[Question]]
Query:    Orchestrator.estimate_duration(project_spec: ProjectSpec) -> DurationEstimate

Path:     Orchestrator.generate(project_spec: ProjectSpec, progress: ProgressReporter, output_dir: Path) -> GenerationResult
Body:     ProjectSpec { project_name, author, python_version, backend_id, frontend_id, config }
Returns:  GenerationResult { success: bool, error: str | None, output_path: Path }
```

### Domain Models (`domain/`)

```
data class ProjectSpec:
  project_name: str
  author: str
  python_version: str
  backend_id: str | None
  frontend_id: str | None
  config: dict[str, dict[str, Any]]       # namespaced by plugin_id

data class TemplateDefinition:
  id: str
  name: str
  description: str
  category: Literal["backend", "frontend"]
  type: Literal["plugin"]
  config_questions: list[Question]

data class Question:
  id: str
  label: str
  question_type: QuestionType
  required: bool
  default: Any | None
  options: list[str] | None               # for CHOICE / MULTI_SELECT
  validation: ValidationRule | None
  group: str | None                        # for grouping in UI

enum QuestionType:
  STRING = "string"
  BOOLEAN = "boolean"
  CHOICE = "choice"
  MULTI_SELECT = "multi_select"
  INTEGER = "integer"

data class ValidationRule:
  min: int | None
  max: int | None
  pattern: str | None                      # regex string

data class GeneratedFile:
  path: Path
  content: str
  executable: bool

data class DurationEstimate:
  estimated_seconds: int
  has_slow_steps: bool
  slow_step_details: list[str]
```

### Generation Stages (`generation/stages/`)

```
Stage:    DirectoryInitializer
Input:    output_dir: Path, overwrite_confirmed: bool
Action:   Creates output_dir; if exists, confirms overwrite
Error:    DirectoryNotEmptyError if user declines overwrite

Stage:    SharedStructureScaffolder
Input:    project_spec: ProjectSpec, output_dir: Path
Action:   Generates justfile, README.md, .gitignore, .env.example, .python-version, AgentSkills/*
Output:   list[GeneratedFile]

Stage:    PluginExecutionEngine
Input:    plugin: PluginBase, project_spec: ProjectSpec, output_dir: Path, progress: ProgressReporter
Action:   Runs plugin's file_providers (copy/link) and command_runners (subprocess scaffold)
Output:   list[GeneratedFile | CommandResult]

Stage:    JustfileGenerator
Input:    project_spec: ProjectSpec, output_dir: Path
Action:   Generates framework-aware justfile with commands for each selected domain
Output:   list[GeneratedFile]

Stage:    ProjectDocumentationWriter
Input:    project_spec: ProjectSpec, output_dir: Path
Action:   Generates AGENTS.md, CLAUDE.md wiki doc with domain-specific instructions, prompt templates
Output:   list[GeneratedFile]

Stage:    AgentSkillScaffolder
Input:    project_spec: ProjectSpec, output_dir: Path
Action:   Generates .opencode/skills/ context based on selected frameworks
Output:   list[GeneratedFile]
```

### Infrastructure (`infrastructure/`)

```
Transaction:  GenerationTransaction
Actions:      .stage(work: Callable[[Path], None])    # queue work
              .commit()                                # move staged to final
              .rollback()                              # clean up partial
Behavior:     On any exception during stage(), auto-rollback all staged work
```

### Progress Reporting

```
Protocol:   ProgressReporter
Methods:    .on_stage_start(name: str, total_steps: int)
            .on_step_complete(step: int, message: str)
            .on_stage_complete(name: str)
            .on_error(stage: str, error: str)
            .on_duration_estimate(estimate: DurationEstimate)

Implementations:
  - QtProgressReporter  (GUI — emits signals to QProgressBar + status label)
  - StdoutProgressReporter  (CLI — writes to terminal)
  - MockProgressReporter  (tests)
```

---

## Edge Cases & Error States

| Scenario | Behavior |
|---|---|
| **Output directory exists** | Dialog: "Directory exists. Overwrite?" → Yes: Stage then clear + regenerate. No: Return to step 3 to choose new path. Cancel: Exit. |
| **Plugin not found** | At launch: log warning, exclude from available list. At generation (CLI): error with message "Plugin '{id}' not installed or not found." |
| **Plugin has unmet dependencies** | On selection: show error "Plugin {X} requires {Y} which is not selected." Block proceeding to next step. |
| **Generation fails mid-scaffold** | Auto-rollback: GenerationTransaction.rollback() cleans up partial output. Show error dialog with stage name + exception message. "Generation failed at stage '{stage}': {error}. All partial output has been cleaned up." |
| **Scaffold command times out** | Individual command timeout (configurable, default 300s). On timeout: rollback that plugin's work, continue? Or fail entire generation. Decision: fail entire generation and auto-rollback. User can retry. |
| **Scaffold command returns non-zero** | Capture stdout/stderr. Fail generation for that plugin. Auto-rollback entire transaction. Show error with captured output. |
| **Empty project (zero domains)** | Skip PluginExecutionEngine entirely. Generate only shared structure (justfile, README, .gitignore, skills). Should complete in <1s. |
| **Malformed CLI spec.json** | Validate on load. Return error: "Invalid spec.json: {field} is required" or "{field} has invalid value {val}". Exit code 1. |
| **CLI missing --headless flag** | If no display available and no --headless flag: error "No display available. Use --headless mode for headless environments." |
| **Project name with special chars** | Sanitize: replace non-alphanumeric chars (except - and _) with underscores. Warn user if sanitization occurred. |
| **Very long project name (>100 chars)** | Truncate to 100 chars with warning. |
| **Wizard back/forward during slow operation** | Generation step disables navigation. If generation is running, buttons are disabled. No concurrent operations. |
| **Plugin file conflicts** | If two plugins write to the same relative path: last-writer-wins with a warning logged. Documented plugin contract: plugins should namespace their files. |

---

## Alternatives Considered

| Approach | Why Rejected |
|---|---|
| **cookiecutter** | Template-only, can't run scaffold commands (create-react-app, etc.). Jinja2 rendering is good for files but can't express multi-step generation with subprocess scaffolding. No Qt GUI. |
| **degit** | Copies git repos without history. No interactive config, no per-plugin file variation, no command execution. Works for static starters only. |
| **Yeoman** | Heavy Node.js dependency for a Python-native tool. Generator ecosystem is Node-centric. Poor integration with Python/PySide6 desktop app. |
| **hygen** | File-level code generator (add a component, add a route). Not designed for whole-project scaffolding. Wrong level of abstraction. |
| **Shell scripts / Makefiles** | What Forge replaces. No interactivity, no validation, no rollback, no progress reporting. Error-prone and duplicated across projects. |
| **IDE project wizards** | Tied to specific IDEs (VS Code, PyCharm, etc.). Not portable, not scriptable, not extensible via Python plugins. |

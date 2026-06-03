# Post-Mortem: Architecture Review Phase

**Date:** June 3, 2026
**Status:** ✅ COMPLETE
**Review Status:** APPROVED (after 3 architecture review rounds)

---

## 1. Overview

### Original Architecture Plan

The original architecture for Forge (a local-first desktop app generating project structures from predefined templates) was documented in `docs/context/architecture.md`, `process-flow.md`, `pipeline.md`, and `AGENTS.md`. The plan defined a 5-layer architecture (UI → Application → Plugin → Domain → Infrastructure) with 4 bundled plugins (FastAPI, Django, React, HTMX) and a linear 5-step wizard.

### Key Design Decisions (Original)

- **Plugin isolation**: Each framework in its own directory, discovered via `project.entry-points."forge.plugins"` in pyproject.toml
- **No persistent state**: App never saves/reopens projects. Each run is ephemeral.
- **Destructive regeneration**: Generated structure = source of truth. Removed domains = deleted directories.
- **Templates are code**: Framework templates live in Python, not config files
- **Justfile as spec model**: Declarative representation of project structure
- **Linear wizard**: 5 steps, no side navigation, back/next/generate only

### Original Plugin Interface (Monolithic)

```python
class AbstractBasePlugin:
    name: str
    display_name: str
    description: str
    def questions(self) -> list[Question]: ...
    def generate(self, spec: ProjectSpec, target_dir: Path) -> None: ...
    def dependencies(self) -> list[str]: ...
    def directories(self) -> list[str]: ...
    def files(self) -> list[GeneratedFile]: ...
```

---

## 2. Problems Identified

### Architecture Review Round 1 — 5 Critical + 7 Major + 3 Minor Issues

The initial architecture review found systemic issues across SOLID principles, layer separation, and cross-cutting concerns:

#### Critical Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| Circular dependency (domain → plugins) | **Critical** | `TemplateDefinition` in `domain/` held `type[AbstractBasePlugin]` class references, creating a `plugins ↔ domain` cycle. Violated "domain/ is the leaf dependency" rule. Domain could not be imported without pulling in the entire plugin layer including PySide6. |
| Orchestrator is a God Object | **Critical** | Single `Orchestrator.generate()` handled 7+ distinct responsibilities: filesystem setup, shared structure creation, plugin coordination, package installation, scaffold commands, Justfile generation, documentation writing. Violated SRP. |
| Missing Question model | **Critical** | `Question` referenced in plugin interface but undefined. No model for what questions look like, how they're typed, or how they validate responses. Plugins and UI cannot be built in parallel without this shared vocabulary. |
| No async/threading strategy | **Critical** | Generation pipeline described as synchronous. Scaffold commands like `create-react-app` take 30-90 seconds. Running on Qt main thread would freeze the UI entirely with no progress feedback. |
| No error handling/rollback | **Critical** | Destructive regeneration + no rollback = data loss. If a plugin fails mid-generation, the output directory is left in a partially-created state indistinguishable from a successful generation. |

#### Major Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| UI bypasses generation layer | **Major** | UI queried `PluginRegistry` directly for templates and plugin questions, violating `ui/ → generation/ → plugins/` rule. Any change to plugin discovery required UI changes. |
| Plugin interface violates ISP | **Major** | All 7 methods forced on every plugin. A declarative-only plugin (no commands) must implement empty `generate()`. A scaffold-only plugin (CRA) must return empty `files()`. Dead code becomes indistinguishable from intentional stubs. |
| Plugin dependency ordering unspecified | **Major** | Only one rule: "backend first, frontend second." Breaks with multiple backends (FastAPI + Celery), infra-as-code plugins (Pulumi), or plugins needing pre/post hooks. |
| `ProjectSpec.config: dict[str, Any]` untyped | **Major** | No validation, no namespace isolation. Two plugins both using `port` key would collide silently. No type enforcement (plugin expects `int`, UI submits `"8080"`). |
| Dual discovery conflict resolution | **Major** | Two paths (entry points + `.plugins/` directory) with no conflict rules. User dropping `fastapi.py` into `.plugins/` would silently shadow bundled FastAPI. Non-deterministic behavior on duplicate names. |
| Progress reporting mechanism unspecified | **Major** | Step 5 wizard shows "progress bar + status log" but no mechanism for orchestrator to communicate progress without coupling to Qt signals. Headless mode and testing have no progress visibility. |
| Shared structure hardcoded in orchestrator | **Major** | The list of shared files (AGENTS.md, .claude/, tests/, etc.) is inline in the orchestrator pipeline. Adding `.github/workflows/ci.yml` or `docker-compose.yml` requires modifying the orchestrator. |

#### Minor Issues

| Issue | Severity | Problem |
|-------|----------|---------|
| Orchestrator/Infrastructure overlap | **Minor** | Both `generation/` and `infrastructure/` deal with filesystem I/O. Orchestrator creates directories directly in pipeline steps. Unclear which layer owns what. |
| Template contradiction | **Minor** | "Templates are code" but `template_loader.py` suggests loading files. Contradictory messaging for plugin authors. |
| No headless/CLI mode | **Minor** | Architecture is 100% UI-dependent. No way to run generation headlessly, test without QApplication, or script generation in CI. |

---

### Architecture Review Round 2 — CONDITIONAL (2 Documentation Contradictions)

After fixes were applied, the re-review found all 5 critical + 7 major issues adequately resolved, but identified 2 documentation inconsistencies:

| Issue | Severity | Problem | Fix |
|-------|----------|---------|-----|
| PluginRegistry double-booked | **Warning** | `plugins/registry.py` AND `generation/registry.py` both listed in AGENTS.md. Two files cannot occupy the same logical module path. | Pick one location. Given rules 2 and 5 (generation layer is facade, registry resolves IDs there), keep `generation/registry.py`. Remove `plugins/registry.py`. |
| SharedStructureScaffolder in two layers | **Warning** | Listed in Infrastructure layer (architecture.md layer diagram) AND as a generation stage (architecture.md pipeline section, AGENTS.md). Must be in one place. | Move to `generation/stages/shared_structure.py` as a `GenerationStage` subclass. I/O helpers can delegate to `infrastructure/`. |

Additionally, 4 NIT-level guidance items were noted:

| Issue | Severity | Guidance |
|-------|----------|----------|
| Thread safety of `should_cancel()` | **NIT** | Called from QThread, set from UI thread — needs `QAtomicInt` or equivalent. Document that all `ProgressReporter` implementations must be thread-safe. |
| Cancellation flow not coordinated | **NIT** | Orchestrator's contract with stages on cancel (abort mid-stage? complete current then rollback?) is unspecified. Add a cancellation contract section. |
| CommandRunner I/O carve-out | **NIT** | Rule says "infrastructure is only I/O" but `CommandRunner.generate()` takes `target_dir` directly. Document that CLI tools are the acknowledged exception with checkpoint-based rollback. |
| StdoutProgressReporter location unspecified | **NIT** | Defined in protocol but no module path. Lives in `generation/progress.py` (same file as protocol). Wiring logic belongs in `__main__.py`. |

---

### Architecture Review Round 3 — APPROVED

The final verification confirmed:
- All 5 critical issues resolved (circular dep → string IDs, god orchestrator → 6 stages, missing Question → defined, no threading → ProgressReporter + QThread, no rollback → GenerationTransaction)
- All 7 major issues resolved (ISP → 5 mixins, UI bypass → generation facade, ordering → requires/run_after, untyped config → namespaced dict, discovery conflicts → priority tiers, progress → protocol, shared structure → extracted stage)
- Both Round 2 documentation contradictions resolved (PluginRegistry → generation/ only, SharedStructureScaffolder → generation/stages/ only)
- No remaining cross-layer violations
- All 4 NIT items either documented in architecture or noted for implementation

---

## 3. Fixes Applied

### A. Resolved Circular Dependency (R1 C1)

**Before:** `TemplateDefinition` held `type[AbstractBasePlugin]` class references

```python
@dataclass
class TemplateDefinition:
    id: str
    display_name: str
    backend: type[AbstractBasePlugin]       # ← domain depends on plugins
    frontend: type[AbstractBasePlugin] | None
    description: str
```

**After (FIXED):** String IDs, resolved via PluginRegistry in generation/

```python
@dataclass
class TemplateDefinition:
    id: str
    display_name: str
    backend_id: str                          # string ID, resolved at runtime
    frontend_id: str | None                  # string ID, resolved at runtime
    description: str
```

**Why it matters:** Domain models must be pure leaf dependencies. If domain imports plugins, you cannot import a `TemplateDefinition` without pulling in PySide6 and every plugin's dependencies. Unit tests for domain models become integration tests. Circular imports at module load time cause fragile initialization order.

### B. Decomposed Orchestrator (R1 C2)

**Before:** Single `Orchestrator.generate()` with 7+ responsibilities

**After (FIXED):** 6 focused stages with thin coordinator:

| Stage | Responsibility |
|-------|---------------|
| `DirectoryInitializer` | Create root output directory |
| `SharedStructureScaffolder` | Generate docs/, .claude/, AGENTS.md, .gitignore, etc. |
| `PluginExecutionEngine` | Topo-sort plugins, check capabilities, run in order |
| `JustfileGenerator` | Serialize ProjectSpec → Justfile |
| `ProjectDocumentationWriter` | Generate AGENTS.md + CLAUDE.md for generated project |
| `AgentSkillScaffolder` | Create .claude/agents/, .claude/skills/, .claude/handoffs/ |

Each stage implements `GenerationStage(ABC)`:
```python
class GenerationStage(ABC):
    name: str
    def run(self, spec: ProjectSpec, output_dir: Path, progress: ProgressReporter) -> None: ...
```

**Why it matters:** A God Object with 7 responsibilities means every pipeline change requires modifying the orchestrator. Individual stages are independently testable (mock a temp dir, no plugins needed), swapable (add a `DockerComposeGenerator` stage), and provide natural progress reporting (each stage name becomes a progress bar segment).

### C. Defined Question Model (R1 C3)

**Before:** Referenced but undefined — `questions() -> list[Question]` with no model

**After (FIXED):** Defined in `domain/` with zero Forge imports:

```python
class QuestionType(Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    INTEGER = "integer"

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
```

**Why it matters:** The `Question` model is the shared vocabulary between plugins (which define questions) and UI (which renders them). Without it, plugin authors have no template for what questions look like, the UI has no schema for rendering, and `ProjectSpec.config` remains an opaque `dict[str, Any]` with no validation rules.

### D. Added Async/Threading Strategy (R1 C4)

**Before:** Synchronous generation on Qt main thread — UI freeze during scaffold commands

**After (FIXED):** Three-part strategy:

1. **ProgressReporter protocol** (abstract, framework-agnostic):
```python
class ProgressReporter(Protocol):
    def on_stage_start(self, stage_name: str, total_steps: int) -> None: ...
    def on_step_complete(self, step_name: str) -> None: ...
    def on_log(self, message: str, level: str = "info") -> None: ...
    def on_error(self, error: Exception, recoverable: bool) -> None: ...
    def should_cancel(self) -> bool: ...
```

2. **Three implementations**: `QtProgressReporter` (emits PySide6 signals → wizard), `MockProgressReporter` (collects calls for tests), `StdoutProgressReporter` (headless/CLI mode)

3. **QThread execution**: `GenerationWorker` (in `ui/workers.py`) runs `Orchestrator.generate()` on a background thread, UI stays responsive

**Why it matters:** Scaffold commands like `create-react-app` take 30-90 seconds. Running on the main Qt thread means the window freezes, progress bar never updates, and the OS may show the "spinning beachball" cursor. The protocol keeps the orchestrator testable without Qt — tests use `MockProgressReporter`, headless uses `StdoutProgressReporter`.

### E. Added Error Handling/Rollback (R1 C5)

**Before:** No mechanism to recover from partial generation failures

**After (FIXED):** `GenerationTransaction` in `infrastructure/`:

```python
class GenerationTransaction:
    def __init__(self, output_dir: Path):
        self.staging = output_dir / ".forge-staging"
        self.manifest: list[Path] = []

    def stage_file(self, path: Path, content: str) -> None: ...
    def commit(self) -> None: ...            # atomic rename staging → output
    def rollback(self) -> None: ...          # delete staging directory
```

Scaffold commands (e.g., `npx create-react-app`) use checkpoint-based rollback: track created paths, clear on failure.

**Why it matters:** Destructive regeneration means the generated output IS the source of truth. If generation fails halfway, the user has a partially-created project that looks valid but is broken. Without staging, you can't distinguish "successful generation" from "generation failed at step 5 of 6." The checkpoint mechanism handles the one case staging can't cover: external CLI tools that write directly to the output directory.

### F. Split Plugin Interface into Mixins (R1 M2)

**Before:** Monolithic `AbstractBasePlugin` with 7 methods — every plugin forced to implement all

**After (FIXED):** 5 focused mixins, plugins opt in to what they need:

```python
class PluginBase(ABC):
    """Minimal base — every plugin must provide these."""
    name: str
    display_name: str
    description: str
    requires: list[str] = []
    run_after: list[str] = []

class Configurable(ABC):
    """Plugin has user-configurable questions."""
    def questions(self) -> list[Question]: ...

class FileProvider(ABC):
    """Plugin declares files and directories it creates."""
    def files(self, spec: ProjectSpec) -> list[GeneratedFile]: ...
    def directories(self, spec: ProjectSpec) -> list[str]: ...

class CommandRunner(ABC):
    """Plugin runs shell commands during generation."""
    def generate(self, spec: ProjectSpec, target_dir: Path) -> None: ...

class DependencyProvider(ABC):
    """Plugin requires Python packages."""
    def dependencies(self) -> list[str]: ...
```

Usage example:
```python
class FastapiPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "fastapi"

class TailwindConfigPlugin(PluginBase, FileProvider):
    name = "tailwind"
```

The orchestrator checks capabilities at runtime via `isinstance()`.

**Why it matters:** ISP says "no client should be forced to depend on methods it does not use." A declarative-only plugin (just files, no commands) should not implement empty `generate()`. A scaffold-only plugin (CRA, which produces a dynamic file tree) should not return empty `files()` that look like bugs. The mixin pattern makes plugin intent visible at the class definition level — `class TailwindConfigPlugin(PluginBase, FileProvider)` immediately tells you "this plugin only provides files."

### G. Made Generation Layer the Single Facade (R1 M1)

**Before:** UI queried `PluginRegistry` directly for templates and questions

**After (FIXED):** Generation layer exposes everything the UI needs:

- `Orchestrator.get_available_templates()` — Step 1
- `Orchestrator.get_questions(template_id)` — Step 3
- `Orchestrator.generate(spec, output_dir, progress)` — Step 5
- `Orchestrator.validate_config(template_id, config)` — validation

**Why it matters:** Layer separation rules are meaningless if the UI bypasses them. Direct plugin access from UI means any change to plugin discovery (e.g., adding a new discovery path, changing the registry API) forces UI changes. The generation layer facade encapsulates all plugin interaction behind a stable API.

### H. Added Plugin Dependency Ordering (R1 M3)

**Before:** Hardcoded "backend first, frontend second" — no mechanism for complex ordering

**After (FIXED):** `requires` and `run_after` declarations on `PluginBase`:

```python
class PluginBase(ABC):
    requires: list[str] = []       # plugin IDs that must run first
    run_after: list[str] = []      # soft ordering hints
```

`PluginExecutionEngine` resolves the graph topologically and detects cycles.

**Why it matters:** A user running FastAPI + Celery + Pulumi needs Celery after FastAPI, and Pulumi after both. Hardcoded "backend → frontend" breaks with 3+ plugins or infrastructure-as-code plugins. Topological sort with cycle detection handles arbitrary dependency graphs.

### I. Namespaced ProjectSpec.config (R1 M4)

**Before:** `config: dict[str, Any]` — no namespace, no type safety

**After (FIXED):** `config: dict[str, dict[str, Any]]` — namespaced by plugin_id:

```python
@dataclass
class ProjectSpec:
    project_name: str
    template: TemplateDefinition
    domains: list[Domain]
    config: dict[str, dict[str, Any]]    # plugin_id → {key: value}

    def plugin_config(self, plugin_id: str) -> dict[str, Any]:
        return self.config[plugin_id]
```

**Why it matters:** Two plugins might both use `port` as a config key. Without namespace isolation, `ProjectSpec.config["port"]` is ambiguous. With `plugin_config("fastapi")["port"]`, the key collision disappears. The type change from `dict[str, Any]` to `dict[str, dict[str, Any]]` enforces the namespace structure at the type level.

### J. Defined Plugin Discovery Conflict Resolution (R1 M5)

**Before:** Two discovery paths (entry points + `.plugins/` directory), no conflict rules

**After (FIXED):** Explicit priority and deduplication:

| Source | Priority | Override behavior |
|--------|----------|-------------------|
| `entry_points["forge.plugins"]` | 10 (system) | Highest — wins all conflicts |
| `.plugins/` directory | 5 (user) | Lower — only fills gaps, cannot override system |

- Same name, same priority → last loaded wins, logged as warning
- Same name, different priority → higher priority wins, logged
- Strict mode → error on ANY conflict (for development/CI)
- `.plugins/` files: `.py` file or directory with `plugin.py`; must export `plugin` attribute
- Deterministic: sorted file iteration

**Why it matters:** Silent shadowing is dangerous — a user dropping `fastapi.py` into `.plugins/` might think they're running the bundled FastAPI generator but actually running their own outdated version. Without priority tiers, the behavior is non-deterministic (depends on scan order). Without logging, conflicts go undetected for weeks.

### K. Added ProgressReporter + StdoutProgressReporter Location (R2 NIT 4)

**Before:** `StdoutProgressReporter` defined but no module path

**After (FIXED):** `generation/progress.py` — same file as the `ProgressReporter` protocol. `__main__.py` wires the right implementation based on `--headless` flag.

**Why it matters:** The `StdoutProgressReporter` cannot live in `ui/` (that would pull Qt into headless mode). Placing it in `generation/progress.py` keeps it framework-agnostic alongside the protocol it implements.

---

## 4. Technical Issues Found During Architecture Review

### Discovery Method

| Finding | Discovery Method |
|---------|-----------------|
| Circular dependency (domain → plugins) | Reading `TemplateDefinition` model — `type[AbstractBasePlugin]` reference |
| Plugin interface violates ISP | Analyzing method usage across 4 distinct plugin types (declarative, imperative, hybrid, config-only) |
| UI bypasses generation layer | Tracing UI wizard steps: Step 1 queries registry, Step 3 calls `plugin.questions()` — both skip generation layer |
| Dual discovery conflict resolution gap | Cross-referencing two discovery mechanisms — no conflict policy defined |

### Impact of Pre-Implementation Discovery

All 5 critical and 7 major issues were found during the architecture review phase — zero structural issues required code changes to fix. This validates the multi-pass review approach even at the architecture level, before any Python code exists.

### Root Causes

| Issue | Root Cause |
|-------|------------|
| Circular dependency | Modeling `TemplateDefinition` as a "plugin reference" instead of a "string ID lookup" — treating plugins as first-class types in a layer that should have no plugin knowledge |
| God orchestrator | Designing the pipeline as a single linear process ("just do these 7 things in order") instead of composing independent stages with single responsibilities |
| Missing Question model | Assuming "a list of questions" was self-explanatory — no specification of what questions look like, how they're typed, or how they validate |
| No threading strategy | Assuming generation is fast (it's not — scaffold commands take minutes) and ignoring Qt's main-thread constraint |
| No error handling | Assuming generation always succeeds — no failure mode analysis against a real 6-stage pipeline with subprocess calls |

---

## 5. Final Architecture

### Layer Diagram

```
UI Layer (PySide6)
    └── Wizard screens (Template → Domains → Config → Summary → Generate)
            │
Generation Layer (facade — single entry point for UI)
    ├── Orchestrator (thin coordinator of stages)
    ├── PluginRegistry (discovery via entry points + .plugins/, ID resolution)
    ├── ValidationEngine (validates ProjectSpec + plugin config)
    ├── ProgressReporter (protocol → Qt signals / stdout / mock)
    └── Stages (DirectoryInitializer, SharedStructureScaffolder, PluginExecutionEngine,
                JustfileGenerator, ProjectDocumentationWriter, AgentSkillScaffolder)
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

### Architecture Rules

1. **UI → Generation only**: UI never imports from `plugins/` or `infrastructure/` directly. All interaction is through the generation facade.
2. **Domain is pure leaf**: Domain models never import from `plugins/`, `ui/`, `generation/`, or `infrastructure/`. String IDs for cross-layer references.
3. **Plugins never import UI**: Plugin code has no knowledge of Qt or wizard screens.
4. **Infrastructure is the only I/O layer**: No code outside `infrastructure/` writes files, runs subprocesses, or manages directories.
5. **Generation layer is the single facade**: UI queries templates, questions, and triggers generation through the generation layer only.
6. **Plugin capabilities via mixins**: Plugins opt in to the interfaces they need (ISP compliance). The orchestrator checks capabilities via `isinstance()`.
7. **Atomic generation**: Staging directory + commit/rollback prevents partially-generated projects on failure.
8. **Plugin discovery with priority**: System plugins (entry points) always win over user plugins (`.plugins/`). Conflicts are logged, never silent.
9. **Plugin dependency ordering**: `requires` and `run_after` declarations enable topo-sorted execution.
10. **Threaded generation**: `QThread` + `GenerationWorker` prevents UI freeze. `ProgressReporter` protocol keeps orchestrator framework-agnostic.

### Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| String IDs for plugins in domain | Breaks circular dependency; PluginRegistry in generation/ resolves IDs at runtime |
| Capability mixins instead of monolithic base | ISP compliance: plugins implement only what they need. Intent visible at class definition |
| GenerationTransaction with staging | Atomic commit/rollback prevents partially-generated projects |
| ProgressReporter as protocol | Framework-agnostic: Qt signals for GUI, stdout for CLI, mock for tests |
| Topo-sorted plugin execution | Handles arbitrary dependency graphs, detects cycles, no hardcoded ordering |
| Two-tier discovery with priorities | System plugins always win; user plugins fill gaps. Conflicts logged, never silent |
| Namespaced config by plugin_id | Prevents key collisions between plugins. Type-level enforcement via nested dict |

---

## 6. Architecture Compliance Verification

| Rule | Status | Verification |
|------|--------|-------------|
| Layer separation (UI → generation → plugins) | ✅ COMPLIANT | UI queries only through generation facade (`get_available_templates()`, `get_questions()`, `generate()`). No direct plugin imports from UI |
| Domain is pure leaf | ✅ COMPLIANT | `TemplateDefinition` uses `backend_id: str` / `frontend_id: str | None`. No imports from plugins. `Question` model defined entirely in domain |
| Infrastructure is only I/O | ✅ COMPLIANT | FileOperations, ProcessExecutor, GenerationTransaction encapsulate all I/O. CommandRunner acknowledged exception for CLI tools |
| No circular imports | ✅ COMPLIANT | Dependency graph: domain → nothing; plugins → domain; generation → plugins + domain + infrastructure; UI → generation only. Acyclic |
| Plugin isolation | ✅ COMPLIANT | Each plugin in own directory. Capability mixins instead of monolithic interface. Entry-point registration |
| ISP compliance | ✅ COMPLIANT | 5 mixins (PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider). `isinstance()` runtime capability check |
| Atomic generation | ✅ COMPLIANT | GenerationTransaction with staging/commit/rollback. Checkpoint-based rollback for scaffold commands |
| Plugin ordering | ✅ COMPLIANT | `requires`/`run_after` on PluginBase. Topological sort + cycle detection in PluginExecutionEngine |
| Thread safety | ✅ COMPLIANT | ProgressReporter protocol + QThread worker. `should_cancel()` documented as thread-safe requirement |
| Type hints | ✅ COMPLIANT | All domain models, mixins, and stage interfaces fully typed |

---

## 7. Outstanding Issues

### Resolved During Architecture Review

- [x] Circular dependency (domain → plugins) → string IDs + PluginRegistry resolution
- [x] Orchestrator God Object → 6 focused stages with thin coordinator
- [x] Missing Question model → defined in domain with QuestionType enum
- [x] No async/threading strategy → ProgressReporter protocol + QThread
- [x] No error handling/rollback → GenerationTransaction + checkpoint rollback
- [x] UI bypasses generation layer → generation layer is single facade
- [x] Plugin interface violates ISP → capability mixins
- [x] Plugin dependency ordering unspecified → requires/run_after + topo sort
- [x] ProjectSpec.config untyped → namespaced dict[str, dict[str, Any]]
- [x] Dual discovery conflict resolution → priority tiers + logging + strict mode
- [x] Progress reporting mechanism unspecified → ProgressReporter protocol
- [x] Shared structure hardcoded in orchestrator → extracted to SharedStructureScaffolder stage
- [x] Orchestrator/Infrastructure overlap → infrastructure is only I/O; stages call infrastructure
- [x] Template contradiction → clarified: f-strings/builders, optional Jinja2 in plugin dir
- [x] No headless/CLI mode → forge --headless entry point
- [x] PluginRegistry double-booked → removed from plugins/, kept in generation/
- [x] SharedStructureScaffolder in two layers → moved to generation/stages/, removed from infrastructure

### Non-Blocking (Implementation Guidance)

- [ ] NIT: Thread safety of `ProgressReporter.should_cancel()` — should use `QAtomicInt` in Qt implementation; document that all implementations must be thread-safe
- [ ] NIT: Cancellation contract — orchestrator should catch `GenerationCancelled` from stages and call `transaction.rollback()`
- [ ] NIT: `CommandRunner.generate()` I/O carve-out — document that CLI tools are the exception; checkpoint rollback tracks created paths
- [ ] NIT: `StdoutProgressReporter` wiring — `__main__.py` detects `--headless` flag and instantiates the correct implementation

---

## 8. Lessons Learned

### What Went Well

1. **Three-pass review found different depth levels** — Round 1 caught structural/SOLID violations (circular dependency, God Object missing Question model). Round 2 caught documentation contradictions (PluginRegistry double-booked, SharedStructureScaffolder in two layers). Round 3 confirmed all issues resolved. Each pass surfaced a different category of issue.

2. **Zero structural issues required code changes** — All critical and major issues were found during the architecture phase, before any Python code existed. This is the ideal outcome of reviewing at the right time.

3. **Domain purity was the hardest constraint to enforce** — The circular dependency (domain → plugins) was the most subtle issue and would have been the most expensive to fix after implementation. String IDs instead of class references is a small change at the architecture level but a massive refactor if discovered later.

4. **ISP compliance via mixins is cleaner than expected** — The original monolithic interface made all plugin types look identical. The mixin pattern (`class FastapiPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider)`) makes plugin capabilities visible at a glance.

5. **Architecture documentation consistency matters** — The PluginRegistry double-booking was found by cross-referencing AGENTS.md against architecture.md. If these two documents disagree, a new developer loading the project would have conflicting mental models.

### What Could Improve

1. **Define Question model earlier** — The Question model is the shared vocabulary that plugins, UI, and validation all depend on. It should have been defined before any plugin interface work began. In the initial architecture, it was referenced but undefined — a gap that would force parallel work to stall.

2. **Include threading strategy from the start** — Desktop app architectures often ignore threading until UI freezing becomes a problem during testing. Threading should be part of the first architecture draft, not added as a fix.

3. **Cross-validate file listings against each other** — The PluginRegistry inconsistency was found by cross-referencing AGENTS.md with architecture.md. A simple validation step ("are all referenced files consistent across docs?") would catch this automatically.

4. **Failure mode analysis should be systematic** — The lack of error handling/rollback was found by asking "what happens when each step fails?" for each of the 6 pipeline stages. A systematic failure mode analysis (FMEA-style) should be standard for any pipeline architecture.

5. **Plugin interface should always start as a minimum viable interface** — The original monolithic interface was too large because it tried to anticipate everything a plugin might need. Better approach: start with the smallest possible interface (PluginBase + one capability), add mixins as real plugin implementations demonstrate the need.

6. **Domain models are the most critical to get right** — The domain models (ProjectSpec, TemplateDefinition, Domain, Question, GeneratedFile) are the shared vocabulary across all layers. A mistake here propagates everywhere. The circular dependency in TemplateDefinition is the kind of error that, if caught during implementation, would require touching every plugin and the orchestrator.

### Key Metrics

| Metric | Value |
|--------|-------|
| Review rounds | 3 |
| Issues found: Critical | 5 |
| Issues found: Major | 7 |
| Issues found: Minor | 3 |
| Issues found: Documentation contradictions | 2 |
| Issues found: NIT guidance | 4 |
| Total issues resolved pre-implementation | 17 |
| Architecture rules defined | 10 |
| Plugin mixins | 5 |
| Generation stages | 6 |
| Domain models defined | 6 (ProjectSpec, TemplateDefinition, Domain, Question, QuestionType, GeneratedFile) |
| Lines of architecture documentation | 294 (architecture.md) + 147 (process-flow.md) + 82 (pipeline.md) + 87 (AGENTS.md) |
| New ADRs needed | 0 (all decisions documented inline) |

---

## 9. Architecture Rules Verification

| AC | Verification Method | Status |
|----|---------------------|--------|
| Layer separation: UI → generation → plugins | Cross-reference: UI wizard steps only call `Orchestrator.get_*()` facade methods. No direct imports from plugins/ or infrastructure/ | ✅ |
| Domain is pure leaf | Read all domain model definitions — zero imports from plugins/, ui/, generation/, infrastructure/. TemplateDefinition uses string IDs | ✅ |
| Infrastructure is only I/O | All filesystem writes, subprocess calls, and directory management are in infrastructure/. No stage or plugin writes files directly | ✅ |
| No circular imports | Dependency graph traced: domain → nothing; plugins → domain; generation → plugins + domain + infrastructure; UI → generation only | ✅ |
| Plugin isolation | Each plugin in own directory under plugins/. No cross-plugin imports. Entry-point registration via pyproject.toml | ✅ |
| ISP compliance | PluginBase + 4 optional mixins. Plugin implements only what it needs. `isinstance()` capability detection | ✅ |
| Atomic generation | GenerationTransaction with staging/commit/rollback. Scaffold checkpoint system for CLI tools | ✅ |
| Plugin dependency ordering | requires/run_after on PluginBase. Topological sort + cycle detection | ✅ |
| Thread safety | ProgressReporter protocol. QThread-based GenerationWorker. Documented thread-safe requirement for should_cancel() | ✅ |
| Type hints | All examples in documentation include complete type hints. mypy strict mode configured | ✅ |

---

## 10. Timeline

| Date | Activity |
|------|----------|
| June 3, 2026 | Architecture docs initially drafted (architecture.md, process-flow.md, pipeline.md) |
| June 3, 2026 | Architecture review round 1 — 5 critical + 7 major + 3 minor issues found |
| June 3, 2026 | Design discussion: circular dependency fix (string IDs), orchestrator decomposition (6 stages), Question model definition |
| June 3, 2026 | Design discussion: threading strategy (ProgressReporter + QThread), error handling (GenerationTransaction), ISP mixins |
| June 3, 2026 | Design discussion: discovery conflict resolution (priority tiers), plugin ordering (requires/run_after), namespaced config |
| June 3, 2026 | Fix round 1: all 5 critical + 7 major + 3 minor issues addressed in all 4 docs |
| June 3, 2026 | Architecture review round 2 (CONDITIONAL — 2 documentation contradictions + 4 NIT guidance items) |
| June 3, 2026 | Fix round 2: PluginRegistry removed from plugins/, SharedStructureScaffolder moved to generation/stages/ |
| June 3, 2026 | Architecture review round 3 (APPROVED — all issues resolved, docs consistent) |
| June 3, 2026 | Post-mortem written |

---

## 11. Next Steps

1. Begin implementation of domain models (ProjectSpec, TemplateDefinition, Domain, Question, QuestionType, GeneratedFile) — these are pure data classes with zero dependencies
2. Implement PluginBase + capability mixins (Configurable, FileProvider, CommandRunner, DependencyProvider) in plugins/base.py
3. Implement PluginRegistry (discovery via entry points + .plugins/, ID resolution) in generation/registry.py
4. Implement ProgressReporter protocol + StdoutProgressReporter in generation/progress.py
5. Implement GenerationTransaction in infrastructure/transaction.py
6. Implement generation stages one at a time (DirectoryInitializer → SharedStructureScaffolder → PluginExecutionEngine → JustfileGenerator → ProjectDocumentationWriter → AgentSkillScaffolder)
7. Implement plugin base + stage base before any concrete plugin — enables integration testing from the start
8. Codify "cross-validate file listings across docs" step for future architecture reviews — prevents documentation contradictions
9. Consider adding a systematic failure mode analysis (FMEA-style) step to the architecture review checklist

# Dependency Analysis

> Living document — updated with each ticket implementation.
> Tracks the dependency tree, affected files, and delicate points across the entire application.

## Layer Dependency Rules

```
UI Layer ─────────────► Generation Layer ──────► Plugin Layer
    │                       │                          │
    │                       │                          │
    └─── (never direct)     │                          │
                            │                          │
                            ▼                          ▼
                    Infrastructure Layer         Domain Layer (pure leaf)
                         (I/O only)           (imported by ALL layers)
```

- **Domain** is the leaf — zero imports from any other Forge layer
- **UI** → **Generation** only (never plugins or infrastructure directly)
- **Infrastructure** is the only I/O layer
- **Plugins** never import UI

## Dependency Graph by Ticket

```
Legend: ──► direct dependency     ~ ~ ~ ► transitive dependency
        [layer]    ticket title

[domain]  T-001 Domain Models (leaf — zero deps)
            │
            ├─► [plugins] T-002 PluginBase + Capability Mixins
            │     (imports: Question, GeneratedFile, ProjectSpec)
            │       │
            │       ├─► [plugins] T-008 FastAPI Plugin
            │       │     (imports: Question, GeneratedFile, ProjectSpec)
            │       ├─► [plugins] T-009 Django Plugin
            │       │     (imports: Question, GeneratedFile, ProjectSpec)
            │       ├─► [plugins] T-010 React Plugin
            │       │     (imports: Question, GeneratedFile, ProjectSpec)
            │       └─► [plugins] T-011 HTMX Plugin
            │             (imports: Question, GeneratedFile, ProjectSpec)
            │
            ├─► [generation] T-003 ProgressReporter Protocol
            │     (imports: DurationEstimate)
            │     (test-enforced: requires infrastructure/__init__.py)
            │       │
            │       ├─► [generation] T-006 Generation Stages
            │       │     (injects ProgressReporter into each stage)
            │       ├─► [generation] T-007 Orchestrator Facade + CLI
            │       │     (creates StdoutProgressReporter for CLI mode)
            │       └─► [ui] T-013 GenerationWorker
            │             (QtProgressReporter implements the protocol)
            │
            ├─► [generation] T-005 PluginRegistry + ValidationEngine
            │     (imports: TemplateDefinition, ProjectSpec, Question, ValidationRule)
            │       │
            │       └─► [generation] T-007 Orchestrator Facade + CLI
            │             (imports: TemplateDefinition, Question, ProjectSpec,
            │              DurationEstimate)
            │               │
            │               ├─► [ui] T-012 QApplication + MainWindow
            │               ├─► [ui] T-013 GenerationWorker
            │               ├─► [ui] T-014 Wizard Screens 1-3
            │               │     (uses: ProjectSpec, TemplateDefinition, Question)
            │               └─► [ui] T-015 Wizard Screens 4-5
            │                     (uses: ProjectSpec, GeneratedFile, DurationEstimate)
            │
            ├─► [generation] T-006 Generation Stages (all 6)
            │     (imports: ProjectSpec, GeneratedFile, DurationEstimate,
            │      ProgressReporter, GenerationTransaction,
            │      PluginBase, FileProvider, CommandRunner, DependencyProvider,
            │      PluginRegistry, CycleDependencyError,
            │      DirectoryNotEmptyError, MissingDependencyError)
            │       │
            │       ├─► [generation] T-007 Orchestrator (sequence + orchestrate)
            │       ├─► [tests] T-016 Integration Tests — Foundation
            │       ├─► [tests] T-017 Integration Tests — CLI/Pipeline
            │       └─► [tests] T-018 Integration Tests — Full Pipeline
            │
            ├─► [tests] T-016 Integration Tests — Foundation
            ├─► [tests] T-017 Integration Tests — CLI/Pipeline
            └─► [tests] T-018 Integration Tests — Full Pipeline

[infrastructure]
  T-004 GenerationTransaction
      (imports: nothing — pure stdlib: pathlib, os, shutil)
        │
        ├─► [generation] T-006 Generation Stages
        │       └── stage_file / stage_directory / add_checkpoint
        │
        ├─► [generation] T-007 Orchestrator Facade + CLI
        │       └── creates GenerationTransaction, passes through 6 stages
        │
        ├─► [ui] T-013 GenerationWorker
        │       └── orchestrator wraps transaction for generation
        │
        └─► [tests] T-016, T-017, T-018 Integration Tests
                └── test atomic commit/rollback end-to-end

  T08.1 ProcessExecutor
      (imports: nothing — subprocess.run)
        │
        ├─► [generation] T-006 PluginExecutionEngine
        │       └── injected into engine (__init__ param), passed to CommandRunner.generate()
        │
        └─► [plugins] T-008 FastAPI Plugin
                └── consumed via untyped executor param in generate() (AC-4 ban forbids type annotation)

Architecture dependency notes:
    T-003 ProgressReporter Protocol — conceptually independent (no domain imports)
        but test AC-8 (`test_progress.py:141-152`) enforces that every generation/
        file imports from `forge.infrastructure`, creating a practical ordering
        requirement on infrastructure/__init__.py being present.
        T-003 creates the _PLACEHOLDER stub → T-004 replaces it with real exports.
    T-004 GenerationTransaction — imports nothing from any Forge layer (pure stdlib).
        However, it has a reverse coupling from T-003: T-003's AC-8 AST scanner
        enforces that every generation/ file imports from forge.infrastructure.
        T-004 must preserve this import (using `as _` + `# noqa: F401`) or T-003
        tests break. Downstream: T-006, T-007, T-013, T-016–T-018.
    T-006 Generation Stages — test-first coupling via `test_stages.py` (638 lines,
        14 ACs, 6 test classes). Every stage class name, module path, `run()` signature,
        and error type is locked by the existing test file. Each of the 8 new files in
        `stages/` must include a `from forge.infrastructure import GenerationTransaction as _  # noqa: F401`
        to satisfy T-003's AC-8 scanner — this cross-ticket coupling is easy to miss.
        `PluginExecutionEngine` is the riskiest stage: it simultaneously couples to
        `PluginBase` mixins (T-002), `PluginRegistry.topological_sort()` (T-005),
        `ProgressReporter.should_cancel()` (T-003), and `GenerationTransaction` (T-004).
    T-008 FastAPI Plugin — first concrete bundled plugin validating the end-to-end pipeline.
        Implements all 4 capability mixins. 30 test-first tests in `test_plugin_fastapi.py`
        (453 lines) cover 17 acceptance criteria. The AC-4 AST scanner (test_plugin_base.py:TestAC4)
        applies to the new fastapi/*.py files: they must import from `forge.domain` and must NOT
        import from `forge.ui`, `forge.generation`, or `forge.infrastructure`. The `base.py`
        exemption does NOT extend to plugin files. The `DependencyProvider.dependencies(spec)`
        signature was changed during TDD review (Round 2) to accept `spec: ProjectSpec`,
        enabling conditional auth deps. All upstream interface changes are resolved and committed;
        the codebase is implementation-ready.
```

### Detailed Chain: T-002 PluginBase + Mixins

```
T-001 (domain) ──► T-002 (plugins/base.py)
                     │
                     ├──► T-005 PluginRegistry ──► T-007 Orchestrator ──► UI (T-012–T-015)
                     │         (type-checks        (drives plugins       (screens + worker)
                     │          PluginBase)         via registry)
                     │
                     ├──► T-008 FastAPI Plugin ──► T-006 Generation Stages
                     ├──► T-009 Django Plugin        (plugin_execution_engine
                     ├──► T-010 React Plugin          iterates plugins)
                     └──► T-011 HTMX Plugin
                              │
                              └──► T-016/T-017/T-018 Integration Tests
                                     (need concrete plugins to test pipeline)
```

**Key chain insight:** T-002 is the narrowest bottleneck in the entire dependency graph — every downstream ticket (generation, UI, tests) either directly or transitively depends on the PluginBase + mixin interface. A breaking change to `PluginBase` or any mixin signature cascades through every subsequent ticket.

### Detailed Chain: T-003 ProgressReporter Protocol

```
T-001 (domain) ──► T-003 (generation/progress.py)
  DurationEstimate      │
                        ├──► T-006 Generation Stages
                        │         (injected via constructor or method param)
                        │
                        ├──► T-007 Orchestrator Facade
                        │         (creates StdoutProgressReporter for --headless;
                        │          accepts ProgressReporter for injection in GUI)
                        │
                        └──► T-013 GenerationWorker (ui/workers.py)
                                  (QtProgressReporter adapts protocol to
                                   PySide6 signals for thread-safe UI updates)
```

**Key chain insight:** T-003 is a **fan-out leaf** — it defines the protocol that all downstream reporting consumers will depend on, but has no existing consumers at creation time. This makes it the safest ticket to implement early: the interface can be designed cleanly without breaking anything. The risk is **design adequacy**: if the protocol is missing a method that downstream needs (e.g., `set_total_steps` for indeterminate progress), later tickets will need to retrofit.

### Detailed Chain: T-004 GenerationTransaction

```
T-003 (ProgressReporter) ──► T-004 (infrastructure/transaction.py)
  creates __init__.py             │
  with _PLACEHOLDER stub           ├──► T-006 Generation Stages
                                   │         (stage_file, stage_directory, add_checkpoint
                                   │          called inside context manager block)
                                   │
                                   ├──► T-007 Orchestrator Facade
                                   │         (creates GenerationTransaction(output_dir);
                                   │          passes through stages as shared context;
                                   │          __exit__ handles commit/rollback)
                                   │
                                   ├──► T-013 GenerationWorker (ui/workers.py)
                                   │         (orchestrator wrapped in worker; rollback
                                   │          triggers on exception or cancellation)
                                   │
                                   └──► T-016/T-017/T-018 Integration Tests
                                         (test: "when CommandRunner raises
                                          exception → rollback called, no partial files")
```

**Key chain insight:** T-004 is the narrowest **I/O gate** in the dependency graph. Every downstream ticket that generates files (stages, orchestrator, UI worker, integration tests) depends on `GenerationTransaction` as the sole atomic commit/rollback mechanism. However, unlike T-002 (which requires careful interface design for 4 mixins), T-004's risk is **implementation correctness** — the 8-method API must correctly handle filesystem edge cases (collision, cross-platform rename, directory recursion) that are difficult to validate in spec review alone. The 14 tests in `test_transaction.py` provide broad coverage (12 ACs, 8/8 methods, happy + error + edge), but the cross-filesystem `EXDEV` case and Windows `PermissionError` are not tested.

**Import chain coupling:** T-003's AC-8 AST scanner (`test_progress.py:TestAC8`) requires every `.py` in `generation/` to import from `forge.infrastructure`. T-004's replacement of `_PLACEHOLDER` with `GenerationTransaction` must preserve this import — the `as _` alias + `# noqa: F401` pattern satisfies the scanner while keeping the import as a no-op placeholder for future consumer files.

### Detailed Chain: T-005 PluginRegistry + ValidationEngine

```
T-001 (domain) ──► T-002 (plugins/base.py) ──► T-005 (generation/registry.py + validation.py)
  ProjectSpec,            PluginBase                 │
  TemplateDefinition,                                 ├── discovers plugins via entry_points + .plugins/
  Question,                                            │   (importlib.metadata, pathlib I/O)
  QuestionType,                                        │
  ValidationRule                                       ├── resolves plugin_id → PluginBase instance
                                                       │
                                                       ├── topological_sort (requires + run_after)
                                                       │   └── CycleDependencyError on cycles
                                                       │
                                                       ├── validate_spec(ProjectSpec) → list[ValidationError]
                                                       │   ├── project_name non-empty
                                                       │   ├── template valid + backend_id resolvable
                                                       │   ├── frontend_id resolvable (if set)
                                                       │   └── domains non-empty
                                                       │
                                                       ├── validate_plugin_config(id, config, questions)
                                                       │   ├── required keys present
                                                       │   ├── INTEGER: min/max bounds
                                                       │   ├── STRING: pattern regex
                                                       │   ├── CHOICE: valid option
                                                       │   └── MULTI_SELECT: all valid options
                                                       │
                                                       ├──► T-006 Generation Stages
                                                       │     (plugin_execution_engine consumes
                                                       │      topological_sort order)
                                                       │
                                                       ├──► T-007 Orchestrator Facade
                                                       │     (creates PluginRegistry, ValidationEngine;
                                                       │      calls discover(), validate_spec(),
                                                       │      resolve_many(), topological_sort())
                                                       │
                                                       ├──► T-013 GenerationWorker (ui/workers.py)
                                                       │     (validation errors → UI error display)
                                                       │
                                                       ├──► T-014 Wizard Screens 1-3
                                                       │     (get_available_backends/frontends
                                                       │      → template selection lists)
                                                       │
                                                       └──► T-016/T-017/T-018 Integration Tests
                                                             (pipeline: spec validation → plugin
                                                              resolution → staged generation)
```

**Key chain insight:** T-005 is a **fan-in node** — it consumes the domain models (T-001) and PluginBase (T-002) and exposes the resolved, validated plugin set to every downstream ticket. Unlike T-002 (interface bottleneck) or T-004 (I/O gate), T-005's risk is **test-contract coupling**: the 718 combined lines of existing tests in `test_registry.py` and `test_validation.py` define the exact API, error types, and behavior. Any method signature mismatch, missing exception type, or return type deviation causes immediate test failure.

**Architectural tension:** `registry.py` performs filesystem I/O (reading `.plugins/` directory, calling `importlib.metadata.entry_points()`), which violates the rule that "Infrastructure is the only I/O layer." The tests work around this via `patch` and `MagicMock`, but the production code embeds I/O directly in the generation layer — a design trade-off accepted by the ticket spec.

**AC-8 coupling:** `test_progress.py:TestAC8` requires every `.py` in `generation/` to import from `forge.infrastructure`. Both `registry.py` and `validation.py` must include `from forge.infrastructure import GenerationTransaction as _  # noqa: F401` or T-003 tests fail.

### Detailed Chain: T-006 Generation Stages (all 6)

T-006 is the ultimate fan-in node — it consumes from 5 upstream tickets and is contract-locked by the existing `tests/unit/test_stages.py` (638 lines).

```
T-001 (domain) ──────────────────────────────────────────┐
  ProjectSpec, GeneratedFile, DurationEstimate            │
                                                          │
T-003 (progress) ──► T-004 (infrastructure)              │
  ProgressReporter      GenerationTransaction              ├──► T-006 Generation Stages
                                                          │      │
T-002 (plugins/base) ──► T-005 (generation/registry)     │      ├──► T-007 Orchestrator
  PluginBase               PluginRegistry                 │      ├──► T-013 GenWorker
  FileProvider              topological_sort()             │      └──► T-016/T-017/T-018
  CommandRunner             CycleDependencyError          │
  DependencyProvider        MissingDependencyError ◄──────┘
```

**Key chain insight:** T-006 is the **ultimate fan-in node** — consuming from 5 upstream tickets (T-001 → T-005) with its entire API surface contract-locked by the test-first `test_stages.py` file. Any breaking change to domain models, plugin mixins, the progress protocol, the transaction API, or the registry sorts propagates through the stage implementations. The `PluginExecutionEngine` is the highest-risk stage because it simultaneously depends on T-002 mixin `isinstance()` checks, T-005 registry sorts, T-003 cancellation, and T-004 checkpoint registration.

**Test-first coupling (638 lines):** Every stage class name, module path, `run()` signature, error type, and import path is defined by `test_stages.py`:
- Import paths: `from forge.generation.stages.<module> import <StageClass>`
- `run()` signature: `(spec: ProjectSpec, output_dir: Path, txn, progress) -> None`
- `PluginExecutionEngine` constructor: takes `PluginRegistry` as argument
- Error types: `DirectoryNotEmptyError`, `MissingDependencyError`, `CycleDependencyError`
- All 8 new `stages/` files require the `from forge.infrastructure import GenerationTransaction as _  # noqa: F401` for T-003 AC-8 compliance

### Detailed Chain: T-007 Orchestrator Facade + CLI

T-007 is the **MVP gateway** — the single entry point that the UI layer calls. It consumes from 5 upstream tickets and is contract-locked by the existing `tests/unit/test_orchestrator.py` (564 lines, 14 tests, 6 test classes). It also creates the CLI/headless entry point (`__main__.py` + dispatch in `app.py`).

```
T-001 (domain) ──────────────────────────────────────┐
  ProjectSpec, TemplateDefinition, DurationEstimate,  │
  Question, QuestionType, Domain                       │
                                                       │
T-002 (plugins/base) ─────────────────────────────────┤
  PluginBase, Configurable (isinstance check)           ├──► T-007 Orchestrator
                                                       │      │
T-003 (progress) ──► T-004 (infrastructure) ──────────┤      ├── creates 3 files:
  ProgressReporter      GenerationTransaction           │      │   orchestrator.py
  StdoutProgressReporter (for --headless)               │      │   __main__.py
                                                       │      │   app.py
T-005 (generation/registry + validation) ──────────────┘      │
  PluginRegistry (injected at __init__)                        ├──► T-012 QApplication + MainWindow
  ValidationEngine (injected at __init__)                      ├──► T-013 GenerationWorker
  ValidationError, DirectoryNotEmptyError,                     ├──► T-014 Wizard Screens 1-3
  MissingDependencyError, CycleDependencyError                 └──► T-015 Wizard Screens 4-5
                                                                    (all query via Orchestrator)

T-006 (stages) ──► T-007 Orchestrator
  (6 stage classes iterated in order inside generate();
   overwrite_confirmed skips DirectoryInitializer at index 0)
```

**Consumer relationship:** Unlike T-006 (which stages consume plugins directly), T-007 is consumed **by the UI layer**. All 4 UI tickets (T-012–T-015) and the headless CLI path depend on the `Orchestrator` API:
- `get_available_backends()` / `get_available_frontends()` → template selection screens
- `get_global_questions()` → project-level settings (description, license)
- `get_domain_questions(backend_id, frontend_id)` → stack config screen
- `estimate_duration(spec)` → generation screen progress bar
- `generate(spec, output_dir, txn, progress)` → actual generation

**Test-first coupling (564 lines):** `tests/unit/test_orchestrator.py` defines the exact API surface:
- `Orchestrator` constructor: `(registry: PluginRegistry, validation: ValidationEngine, stages: list | None = None)`
- `generate()` signature: `(spec, output_dir, txn, progress, overwrite_confirmed=False) -> GenerationResult`
- `GenerationResult` dataclass: `success: bool`, `error: str | None`, `output_path: Path | None`
- Query methods: `get_available_backends()`, `get_available_frontends()`, `get_global_questions()`, `get_domain_questions(backend_id, frontend_id)`, `estimate_duration(spec)`
- `app.main()` — the dispatch function in `app.py` — handles `--headless`, constructs objects, calls generate, returns exit code
- `detect_display()` — standalone function in `app.py`, patched by test via `forge.app.detect_display`
- `_run_headless(args)` — test helper that patches `sys.argv` and calls `app.main()`, no subprocess

**Key chain insight:** T-007 is the **MVP assembly point** — the first ticket that wires together the registry, validation, progress reporting, infrastructure, and all 6 stages into a single callable pipeline. Its risk is **signature surface area**: the constructor takes 2+ objects, `generate()` takes 5 parameters, and there are 5 query methods, each with specific contracts tested by the 564-line test file. Every method signature, return type, and error path is locked. Unlike T-006 (complex stage internals) or T-005 (complex registry logic), T-007's complexity is in **coordination correctness**: stage ordering, error→rollback propagation, and the `overwrite_confirmed` branch.

### Detailed Chain: T-008 FastAPI Plugin

T-008 is the **first concrete bundled plugin** — validates the end-to-end pipeline. Unlike the upstream infrastructure tickets (T-003 through T-007), T-008 is a pure plugin implementation with no new layering. All upstream contracts are already locked by existing tests; the codebase is implementation-ready.

```
T-001 (domain) ──────────────────────────────────────┐
  ProjectSpec, Question, GeneratedFile, QuestionType   │
                                                        │
T-002 (plugins/base.py) ──────────────────────────────┤
  PluginBase (name, requires)                           ├──► T-008 FastAPI Plugin
  Configurable (questions)                               │      (2 files to create:
  FileProvider (files, directories)                      │       __init__.py + plugin.py)
  CommandRunner (generate)                               │
  DependencyProvider (dependencies)                      │
                                                        │
T-005 (generation/registry + validation) ──────────────┤
  PluginRegistry.discover() ──► entry_points            │
  ValidationEngine.validate_plugin_config()              │
                                                        │
T08.1 (infrastructure/process_executor.py) ────────────┘
  ProcessExecutor
    │
    ├──► T-006 Generation Stages — PluginExecutionEngine
    │      (isinstance dispatch per mixin;
    │       FileProvider → txn.stage_file / stage_directory;
    │       DependencyProvider → txn.requirements;
    │       CommandRunner → executor.run())
    │
    ├──► T-007 Orchestrator Facade
    │      (registry.discover → instantiate FastapiPlugin;
    │       headless path calls validate_plugin_config;
    │       generate() passes txn + executor through stages)
    │
    ├──► tests/unit/test_plugin_fastapi.py (30 tests, 17 ACs)
    │      (all fail test-first: ImportError — expected)
    │
    └──► T-016/T-017/T-018 Integration Tests
           (end-to-end pipeline with real FastapiPlugin)
```

**Key chain insight:** T-008 is a **pure downstream consumer** — it implements interfaces defined by T-002, registers via T-005 discovery, and is executed by T-006's PluginExecutionEngine. The implementation has zero impact on upstream files: no base class changes, no registry changes, no engine changes. The 30 test-first tests in `test_plugin_fastapi.py` serve as the complete acceptance specification. All 3 TDD review rounds are complete (8 issues found and fixed across 6 files); the codebase is ready for implementation with no further refactoring.

**Pre-implementation issues already resolved:**
1. `DependencyProvider.dependencies()` missing `spec` param → fixed in TDD R2 (6 call sites updated)
2. AC-4 scanner `glob()` → `rglob()` → fixed in TDD R1
3. `base.py` INFRA_EXEMPT_FILES → fixed in TDD R1
4. Headless validation path missing `validate_plugin_config()` → fixed in TDD R1
5. `spec.config.get()` pattern documented → fixed in TDD R1

**Files to create:**
| File | Purpose | Constraints |
|------|---------|-------------|
| `src/forge/plugins/fastapi/__init__.py` | Package init + re-export | Must import from `forge.domain` (AC-4); must NOT import infra/ui/generation |
| `src/forge/plugins/fastapi/plugin.py` | FastapiPlugin (4 mixins, 5 methods) | Same AC-4 constraints; executor param must be untyped |
| `src/forge/plugins/fastapi/templates/` | Optional Jinja2 templates | If used, add `jinja2` to `pyproject.toml` |

**Test verification:**
- 30 tests in `test_plugin_fastapi.py` → all will auto-resolve from FAIL to PASS
- 2 AC-10 tests in `test_validation.py` → already PASS (inline Question construction)
- AC-4 scanner in `test_plugin_base.py` → must pass on new files
- 166 existing unit tests → zero expected regressions

---

### Detailed Chain: T-010 React Plugin

T-010 is the **third concrete bundled plugin** — follows the same pattern as T-008/T-009 but for a JavaScript/TypeScript frontend framework. All upstream contracts are locked by existing tests; the codebase is implementation-ready. The React plugin adds 5 config keys (bundler, include_typescript, include_router, include_tailwind, state_management) with a cross-method consistency matrix spanning 48 config permutations.

```
T-001 (domain) ──────────────────────────────────────┐
  ProjectSpec, Question, GeneratedFile, QuestionType   │
                                                        │
T-002 (plugins/base.py) ──────────────────────────────┤
  PluginBase (name, requires)                           ├──► T-010 React Plugin
  Configurable (questions)                               │      (2 files to create:
  FileProvider (files, directories)                      │       __init__.py + plugin.py)
  CommandRunner (generate)                               │
  DependencyProvider (dependencies)                      │
                                                        │
T-005 (generation/registry + validation) ──────────────┤
  PluginRegistry.discover() ──► entry_points            │
  ValidationEngine.validate_plugin_config()              │
                                                        │
T08.1 (infrastructure/process_executor.py) ────────────┘
  ProcessExecutor
    │
    ├──► T-006 Generation Stages — PluginExecutionEngine
    │      (isinstance dispatch per mixin;
    │       FileProvider → txn.stage_file / stage_directory;
    │       DependencyProvider → txn.requirements;
    │       CommandRunner → executor.run())
    │
    ├──► T-007 Orchestrator Facade
    │      (registry.discover → instantiate ReactPlugin;
    │       headless path calls validate_plugin_config;
    │       generate() passes txn + executor through stages)
    │
    ├──► tests/unit/test_plugin_react.py (875 lines, 22 ACs)
    │      (all fail test-first: ImportError — expected)
    │
    └──► tests/unit/test_validation.py (AC-17 equivalent)
           (inline Question construction for bundler choice;
            already PASS — no dependency on plugin files)
```

**Key chain insight:** T-010 is a **pure downstream consumer** — architecturally identical to T-008/T-009. It implements interfaces defined by T-002, registers via T-005 discovery, and is executed by T-006's PluginExecutionEngine. The implementation has zero impact on upstream files: no base class changes, no registry changes, no engine changes. Like T-009, T-010 benefits from all upstream interfaces being hardened by T-008's implementation.

**Critical design differences from T-008/T-009:**
1. **5 config keys** (vs T-008's 3 and T-009's 2) — bundler, include_typescript, include_router, include_tailwind, state_management. 2×2×2×2×3 = 48 config permutations across 3 output methods (files, dependencies, generate).
2. **npm-based scaffold**, not Python/pip. `npm create vite@latest . -- --template react[-ts]` for Vite; no scaffold for Webpack. `executor.run()` uses npm commands, not `uv add`.
3. **Scaffold + files() overlap** — Vite's `create-vite` generates the same files as `files()` (Design Note 12). Staging overwrite handles duplication safely, but mismatch risk exists between scaffold output and plugin-generated templates.
4. **JSX/TSX inline templates** — all file content is inline f-strings (no Jinja2). JSX curly braces `{}` require Python f-string escaping (`{{`/`}}`), adding a template-authoring friction not present in T-008/T-009's Python templates.
5. **`state_management` is config passthrough** (Design Note 8) — stored in config for downstream use but `files()` and `generate()` do NOT branch on it. Only `dependencies()` conditionally includes the package. Full state management scaffolding is deferred.

**Files to create:**
| File | Purpose | Constraints |
|------|---------|-------------|
| `src/forge/plugins/react/__init__.py` | Package init + re-export | Must `from forge.domain import ProjectSpec as _` (AC-4); must NOT import infra/ui/generation |
| `src/forge/plugins/react/plugin.py` | ReactPlugin (4 mixins, 6 methods: questions, files, directories, dependencies, generate + _config) | Same AC-4 constraints; executor param must be untyped (`Any`); `_config(spec)` static helper matching FastAPI/Django pattern |

**Test verification:**
- 875 lines in `test_plugin_react.py` (19 test classes, 22 ACs) → all fail with `ImportError` (expected); will auto-resolve to PASS on file creation
- AC-17 test in `test_plugin_react.py:TestAC17_InvalidBundler` → uses inline `Question` construction (same pattern as Django's AC-19); no dependency on plugin files
- AC-4 scanner in `test_plugin_base.py` → must pass on new `react/*.py` files
- 0 regressions expected in 166+ existing unit tests

## Affected Files by Layer

### Domain Layer (T-001 — ✅ complete)
| File | Status | Notes |
|---|---|---|
| `src/forge/domain/__init__.py` | ✅ **Created** | Re-exports all 8 models |
| `src/forge/domain/project_spec.py` | ✅ **Created** | `Domain`, `TemplateDefinition`, `ProjectSpec` |
| `src/forge/domain/questions.py` | ✅ **Created** | `Question`, `QuestionType`, `ValidationRule` |
| `src/forge/domain/generated_file.py` | ✅ **Created** | `GeneratedFile`, `DurationEstimate` |
| `tests/unit/test_domain_models.py` | ✅ **Created** | 244 lines, all ACs covered |

### Plugin Layer (T-002, T-008–T-011)
| File | Action | Depends on | Created by |
|---|---|---|---|
| `src/forge/plugins/base.py` | ✅ **Created** | `Question`, `GeneratedFile`, `ProjectSpec` | T-002 |
| `src/forge/plugins/__init__.py` | ✅ **Created** | `base.py` (re-exports) | T-002 |
| `tests/unit/test_plugin_base.py` | ✅ **Already exists** | `PluginBase`, all 4 mixins | T-016 (test-first) |
| `tests/unit/conftest.py` | ✅ **Already exists** | `PluginBase`, all 4 mixins + fixtures | T-016 (test-first) |
| `src/forge/plugins/fastapi/__init__.py` | **CREATE** | Must import from `forge.domain` (AC-4 scanner req); re-export `FastapiPlugin` | T-008 |
| `src/forge/plugins/fastapi/plugin.py` | **CREATE** | `Question`, `GeneratedFile`, `ProjectSpec`; NO infra imports; untyped executor param | T-008 |
| `src/forge/plugins/fastapi/templates/` | Optional | Jinja2 templates (would require `jinja2` in `pyproject.toml`) | T-008 |
| `tests/unit/test_plugin_fastapi.py` | ✅ **Passing** | 453 lines, 30 tests covering 17 ACs — all resolved from FAIL to PASS | T-016 (test-first) |
| `src/forge/plugins/django/__init__.py` | **CREATE** | Must import `ProjectSpec` from `forge.domain` (AC-4); re-export `DjangoPlugin` | T-009 |
| `src/forge/plugins/django/plugin.py` | **CREATE** | `Question`, `GeneratedFile`, `ProjectSpec`; NO infra imports; untyped executor param; `_config(spec)` static helper | T-009 |
| `src/forge/plugins/django/templates/` | Optional | Jinja2 templates (would require `jinja2` in `pyproject.toml`) | T-009 |
| `tests/unit/test_plugin_django.py` | ✅ **Already exists (test-first)** | 574 lines, 21 tests covering 21 ACs — all fail with ImportError (expected) | T-016 (test-first) |
| `tests/unit/test_validation.py:TestAC19` | ✅ **Already exists (PASS)** | 2 tests — inline `Question` construction; no dependency on Django plugin files | T-016 (test-first) |
| `src/forge/plugins/react/__init__.py` | ✅ **Created** | AC-4 domain import; re-exports `ReactPlugin` | T-010 |
| `src/forge/plugins/react/plugin.py` | ✅ **Created** | `Question`, `GeneratedFile`, `ProjectSpec`; NO infra imports; untyped `executor: Any`; `_config(spec)` static helper; all 4 mixins; 5 config keys (bundler, ts, router, tailwind, state_mgmt) | T-010 |
| `tests/unit/test_plugin_react.py` | ✅ **Passing** | 875 lines, 61 tests across 28 test classes, 20 ACs — all PASS | T-010 |
| `src/forge/plugins/htmx/plugin.py` | Pending | `Question`, `GeneratedFile`, `ProjectSpec` | T-011 |

> **Test-first coupling:** `test_plugin_base.py` and `conftest.py` reference `forge.plugins.base` imports before the module exists.
> T-002 must export exactly `PluginBase`, `Configurable`, `FileProvider`, `CommandRunner`, `DependencyProvider` with no naming mismatches.

### Generation Layer (T-003, T-004 import update, T-005–T-007)
| File | Status | Action | Depends on |
|---|---|---|---|
| `src/forge/generation/__init__.py` | ✅ **Created (T-003/T-004)** → **T-006 update** → **T-007 update** | Re-exports ProgressReporter, StdoutProgressReporter, MockProgressReporter, PluginRegistry, ValidationEngine, errors + infrastructure import; T-006 adds re-exports for GenerationStage + all 6 stage classes; T-007 adds Orchestrator + GenerationResult | `DurationEstimate`, `GenerationTransaction` |
| `src/forge/generation/progress.py` | ✅ **Created (T-003)** | ProgressReporter protocol, StdoutProgressReporter, MockProgressReporter | `DurationEstimate` |
| `src/forge/generation/errors.py` | ✅ **Created (cross-ticket)** | DirectoryNotEmptyError, MissingDependencyError — both used by T-006 stages | None |
| `src/forge/generation/registry.py` | ✅ **Created (T-005)** | PluginRegistry, CycleDependencyError, DiscoveryError | `PluginBase`, `TemplateDefinition`, `ProjectSpec` |
| `src/forge/generation/validation.py` | ✅ **Created (T-005)** | ValidationEngine, ValidationError | `PluginRegistry`, `Question`, `QuestionType`, `ValidationRule`, `ProjectSpec` |
| `tests/unit/test_registry.py` | Already exists (T-005) | 411 lines, 23 ACs (constructor → topo sort) | — |
| `tests/unit/test_validation.py` | Already exists (T-005) | 307 lines, 11 ACs (spec + config validation) | — |
| `src/forge/generation/stages/__init__.py` | **CREATE (T-006)** | Subpackage init; re-exports GenerationStage + all 6 stage classes; must include infrastructure import | — |
| `src/forge/generation/stages/base.py` | **CREATE (T-006 — TEST-FIRST)** | `GenerationStage` protocol/ABC; `run(spec, output_dir, txn, progress)` | `ProjectSpec`, `ProgressReporter`, `GenerationTransaction` |
| `src/forge/generation/stages/directory_initializer.py` | **CREATE (T-006 — TEST-FIRST)** | Validates output_dir; raises DirectoryNotEmptyError if non-empty | `ProjectSpec`, `DirectoryNotEmptyError`, `ProgressReporter`, `GenerationTransaction` |
| `src/forge/generation/stages/shared_structure_scaffolder.py` | **CREATE (T-006 — TEST-FIRST)** | Shared files: README.md, .gitignore, .env.example, .python-version, docs/ stub | `ProjectSpec`, `ProgressReporter`, `GenerationTransaction` |
| `src/forge/generation/stages/plugin_execution_engine.py` | **CREATE (T-006 — TEST-FIRST)** | Resolves plugin order (topological_sort), checks missing deps, executes plugins via isinstance() mixin checks, handles cancellation | `ProjectSpec`, `PluginRegistry`, `PluginBase`, `FileProvider`, `CommandRunner`, `DependencyProvider`, `ProgressReporter`, `GenerationTransaction`, `MissingDependencyError`, `CycleDependencyError` |
| `src/forge/generation/stages/justfile_generator.py` | **CREATE (T-006 — TEST-FIRST)** | Framework-aware justfile with setup/dev/test/lint/format/build | `ProjectSpec`, `ProgressReporter`, `GenerationTransaction` |
| `src/forge/generation/stages/project_documentation_writer.py` | **CREATE (T-006 — TEST-FIRST)** | AGENTS.md + .claude/CLAUDE.md | `ProjectSpec`, `ProgressReporter`, `GenerationTransaction` |
| `src/forge/generation/stages/agent_skill_scaffolder.py` | **CREATE (T-006 — TEST-FIRST)** | .opencode/skills/, .opencode/agents/, .opencode/handoffs/ stubs | `ProjectSpec`, `ProgressReporter`, `GenerationTransaction` |
| `tests/unit/test_stages.py` | **Already exists (T-016 test-first)** | 638 lines, 14 ACs, 6 test classes — contract-locks all stage APIs | — |
| `src/forge/generation/orchestrator.py` | **CREATE (T-007 — TEST-FIRST)** | Orchestrator facade class + GenerationResult dataclass; coordinates 6 stages, handles error→rollback, provides query methods; must include AC-8 infrastructure import | `TemplateDefinition`, `Question`, `ProjectSpec`, `DurationEstimate`, `PluginRegistry`, `ValidationEngine`, `GenerationTransaction`, `ProgressReporter`, all 6 `GenerationStage` classes |
| `tests/unit/test_orchestrator.py` | **Already exists (T-007 test-first)** | 564 lines, 14 tests, 6 test classes — contract-locks Orchestrator API, GenerationResult, query methods, headless CLI flow | — |

### Infrastructure Layer (T-003 creates __init__.py → T-004 replaces placeholder + creates transaction.py → T08.1 creates ProcessExecutor)
| File | Status | Action | Depends on |
|---|---|---|---|
| `src/forge/infrastructure/__init__.py` | ✅ **Created (T-003)** → **Update (T-004)** → **Update (T08.1)** | Replace `_PLACEHOLDER` with `GenerationTransaction`; T08.1 adds `ProcessExecutor` re-export | T-003 scaffold → T-004 → T08.1 |
| `src/forge/infrastructure/transaction.py` | ✅ **Created (T-004)** | `GenerationTransaction` class — 8 methods | None (pure stdlib) |
| `src/forge/infrastructure/process_executor.py` | ✅ **Created (T08.1)** | `ProcessExecutor` — wraps `subprocess.run()`, injected into `PluginExecutionEngine` | None (pure stdlib) |
| `src/forge/generation/progress.py` | ✅ **Created (T-003)** → **Update (T-004)** | Change import: `_PLACEHOLDER as _` → `GenerationTransaction as _` | `GenerationTransaction` |
| `src/forge/generation/__init__.py` | ✅ **Created (T-003)** → **Update (T-004)** | Change import: `_PLACEHOLDER as _` → `GenerationTransaction as _` | `GenerationTransaction` |

### CLI / App Layer (T-007 — ⏳ pending)
| File | Status | Action | Depends on |
|---|---|---|---|
| `src/forge/app.py` | **CREATE (T-007)** | Bootstrap: `main(args)` dispatch function; constructs PluginRegistry + ValidationEngine + Orchestrator; `detect_display()` extracted as standalone function for mockability; dispatches to headless CLI or GUI | `PluginRegistry`, `ValidationEngine`, `Orchestrator`, `GenerationTransaction`, `StdoutProgressReporter` |
| `src/forge/__main__.py` | **CREATE (T-007)** | Entry point called via `python -m forge`; parses `--headless`, `spec.json`, `output_dir`; delegates to `app.main()`; does not construct core objects directly | `forge.app.main()` |

### UI Layer (T-012–T-015)
| File | Domain dependency |
|---|---|
| `src/forge/ui/main_window.py` | Uses ProjectSpec (via Orchestrator) |
| `src/forge/ui/workers.py` | Uses DurationEstimate, ProjectSpec |
| `src/forge/ui/screens/template_selection.py` | Uses TemplateDefinition |
| `src/forge/ui/screens/domain_definition.py` | Uses Domain |
| `src/forge/ui/screens/stack_config.py` | Uses Question |
| `src/forge/ui/screens/review_summary.py` | Uses ProjectSpec |
| `src/forge/ui/screens/generation.py` | Uses DurationEstimate |

## Domains Models — API Surface Exposed

Models from `forge.domain` that other layers import:

```
Domain(name, slug)
TemplateDefinition(id, display_name, description, backend_id, frontend_id)
ProjectSpec(project_name, template, domains, config)
    └── plugin_config(plugin_id) -> dict

QuestionType enum: STRING, BOOLEAN, CHOICE, MULTI_SELECT, INTEGER
ValidationRule(min, max, pattern)
Question(key, label, question_type, required, default, description, options, placeholder, validation, group)

GeneratedFile(path, content, executable)
DurationEstimate(estimated_seconds, has_slow_steps, slow_step_details)
```

## Delicate Points

| Point | Ticket | Risk |
|---|---|---|
| AC-7: Static import analysis requires `ast.parse()` scanner | T-001 | Medium — unique testing approach |
| AC-4: Slug regex — 5 edge cases | T-001 | Low — well-scoped but easy to miss |
| AC-5: Nested dataclass serialization with ValidationRule | T-001 | Low — `asdict()` handles it |
| `plugin_config()` error message is a de facto contract | T-001 | Low — downstream catches KeyError |
| Strict mypy + `Any` in domain models | T-001 | Low — standard typing pattern |
| `__init__.py` re-export hygiene | T-001 | Low — keep explicit |
| **Mutable default on `requires` / `run_after`** (class-level `= []` shared across instances) | T-002 | Low — follows spec, but latent cross-instance mutation risk |
| **`@property @abstractmethod` + class-level assignment** — tests use `name = "file-only"` class attributes, which satisfy the ABC contract via data descriptor protocol | T-002 | Low — well-known Python idiom, but dual patterns (class attr vs instance property) can confuse newcomers |
| **AC-4 static import analysis requires unconditional domain import** — test `test_plugin_base.py:165-211` calls `pytest.fail` if no `forge.domain` import is found; `TYPE_CHECKING`-only imports would fail the AST scan | T-002 | Low — constraint forces non-conditional import |
| **Test-first coupling** — `conftest.py` and `test_plugin_base.py` import from `forge.plugins.base` before it exists; any rename or signature change breaks tests silently | T-002 | Medium — tests act as an implicit API contract, any deviation causes cascading test failures |
| **AC-8 AST scanner requires `forge.infrastructure` import in new generation/ files** — both `registry.py` and `validation.py` must include `from forge.infrastructure import GenerationTransaction as _  # noqa: F401` or T-003's `test_progress.py:TestAC8` fails | T-005 | **High** — cross-ticket test coupling; easy to forget when creating new files |
| **Filesystem I/O in generation layer** — `registry.py` reads `.plugins/` directory and calls `importlib.metadata.entry_points()`. Violates "infrastructure is the only I/O layer" architectural rule by design | T-005 | **High** — architectural tension; tests stub the I/O but production code embeds it |
| **`.plugins/` dynamic module loading** — must load `.py` files via `importlib.util.spec_from_file_location` + `exec()` or equivalent. Error handling for missing `plugin` attribute, syntax errors, or import errors is unspecified | T-005 | Medium — untested edge cases in dynamic loading |
| **Topological sort: `requires` (hard) vs `run_after` (soft) edges** — cycle detection must only fail on hard-edge cycles. AC-19 expects `CycleDependencyError` with cycle path string. Soft edges (AC-23) must not cause false positives | T-005 | Medium — dual-edge semantics are easy to get wrong |
| **Discovery conflict resolution — priority tiers + strict mode** — entry_points (priority 10) wins over .plugins/ (priority 5); warning logged on non-strict conflict; `DiscoveryError` raised in strict mode | T-005 | Medium — ordering of discovery sources matters |
| **Unknown plugin ID in `get_missing_dependencies`** — must raise `KeyError` before accessing `self._discovered` | T-005 | Low — well-scoped but easy to miss ordering |
| **BOOLEAN question type — no explicit validation rule** — spec defines rules for INTEGER, STRING, CHOICE, MULTI_SELECT only. Missing required key check still applies to BOOLEAN | T-005 | Low — unspecified but trivial |
| **Test-contract coupling (718 combined lines)** — `test_registry.py` + `test_validation.py` define exact API; any signature mismatch causes cascading test failures | T-005 | Medium — tests are the spec; high implementation cost to fix if wrong |
| **AC-8 AST scanner requires `forge.infrastructure` import in generation/ files** — T-004 replaces `_PLACEHOLDER` with `GenerationTransaction` but must preserve the `import GenerationTransaction as _` + `# noqa: F401` pattern or T-003's `test_progress.py:TestAC8` fails | T-004→T-003 | **High** — cross-ticket test coupling; import alias must match exactly |
| **Cross-filesystem `os.rename` (EXDEV)** — `commit()` uses `os.rename` which fails with `EXDEV` if staging/ and output_dir/ are on different filesystems. Tests use `tmp_path` (same fs), making this invisible to the test suite | T-004 | Medium — unrecoverable runtime error in production if user specifies output on a different mount |
| **Platform-specific `PermissionError` vs `FileExistsError`** — `os.rename` raises `PermissionError` on Windows when destination exists (not `FileExistsError`). AC-10 asserts `FileExistsError`. Implementation must use explicit `os.path.exists()` pre-check | T-004 | Medium — test would fail on Windows CI |
| **Checkpoint directory deletion via `shutil.rmtree`** — `add_checkpoint` with directory paths requires recursive deletion. AC-6 only tests file checkpoints | T-004 | Medium — untested edge case; failure would leave partial directories on rollback |
| **Transaction single-use enforcement** — AC-11 tests double-commit raises `RuntimeError`, but `stage_file()` after commit, `rollback()` after rollback, or `stage_file()` after rollback are not specified | T-004 | Low — sensible default (single-use) but no test for stale-state misuse |
| **Empty/noop commit** — committing with zero staged files has no AC. Current spec implies silent success | T-004 | Low — no test coverage; unusual edge case |
| QtProgressReporter bridging protocol → PySide6 signals | T-013 | Medium — thread safety |
| **Exception `__eq__` identity gotcha** — `test_progress.py:66-67` compares tuple containing raw `Exception` object; `ValueError("config err") == ValueError("config err")` is `False` because `BaseException` inherits `object.__eq__` (identity). A naive `MockProgressReporter` storing the raw exception fails this assertion. | T-003 | **High** — requires non-obvious implementation (store call metadata, not raw exception) |
| **AC-8 AST scanner requires `forge.infrastructure` import in every generation/ file** — test iterates all `.py` files in `generation/` and fails if any lacks a `from forge.infrastructure import ...` statement. Both `progress.py` and `__init__.py` must contain it. | T-003 | **High** — creates cross-layer ordering dependency (T-003 must create `infrastructure/__init__.py` before T-004) |
| `should_cancel()` return value contract — `MockProgressReporter` defaults to `False`; `StdoutProgressReporter` behavior unspecified. Downstream (`T-013 QtProgressReporter`) may need thread-safe cancellation signal. | T-003 | Low — clean interface now, future-proofing needed |
| `test_progress.py` already exists (169 lines, 9 AC classes) — implementation must match exact method signatures, return types, and export names. Any mismatch causes test failures. | T-003 | Low — well-documented by the test itself |
| **AC-8 AST scanner applies to all 8 new stages/ files** — every `.py` in `stages/` must include `from forge.infrastructure import GenerationTransaction as _  # noqa: F401` or T-003's `test_progress.py:TestAC8` fails. **8 files, 1 chance to miss.** | T-006→T-003 | **High** — cross-ticket test coupling; forgetting the import in even one file breaks an unrelated test |
| **PluginExecutionEngine — multi-mixin isinstance dispatch** — must simultaneously handle 3 mixin capabilities (FileProvider, CommandRunner, DependencyProvider) via isinstance checks, route each to correct GenerationTransaction method, and check missing deps + cancellation between plugins. Most architecturally complex stage. | T-006 | **High** — multi-dimensional coupling across T-002, T-003, T-004, T-005 |
| **`output_dir` vs `target_dir` pass-through** — AC-5 requires `target_dir = output_dir`. An implementation that passes `txn.staging` instead silently breaks the CommandRunner contract. | T-006 | Medium — easy to get wrong given the staging abstraction |
| **Cancellation check timing** — AC-13 checks `progress.should_cancel()` before executing each plugin. The `_CancellableReporter` in tests hardcodes `cancel_after=N`. Check must happen at the right point in the loop (before each plugin iteration). | T-006 | Medium — off-by-one in cancel timing fails tests |
| **MissingDependencyError message contract** — AC-6 asserts `"missing-plugin" in str(exc.value)`. Error message must include the missing plugin ID for test to pass. | T-006 | Low — trivial but easy to forget when wrapping the registry call |
| **CycleDependencyError must propagate, not catch** — AC-11 tests that `topological_sort` raising `CycleDependencyError` is not caught by the engine. Must use bare `registry.topological_sort()` with no try/except. | T-006 | Low — natural flow, but any defensive try/except would break tests |
| **Empty plugin list → no-op** — AC-7 integration: zero plugins selected → Stage 3 must be skipped. Implementation must check `if not plugin_ids: return` before any registry calls. | T-006 | Low — well-scoped edge case |
| **Test-first coupling (638 lines)** — `test_stages.py` defines exact import paths, class names, run() signatures, error types. Any deviation causes immediate test failure. Same pattern as T-002/T-005. | T-006 | **High** — tests are the spec; 14 ACs across 6 test classes, 638 lines |
| **`__init__.py` export hygiene** — `generation/__init__.py` must re-export all new stage classes + GenerationStage protocol. Missing any breaks downstream (T-007) imports. | T-006 | Low — standard boilerplate, one-time task |
| **Framework-awareness ambiguity** — ticket says "framework-aware justfile" and "stubs based on selected frameworks" for AgentSkillScaffolder, but tests only verify generic existence, not framework-specific content. Risk of over-engineering or under-delivering. | T-006 | Low — implement minimally to pass tests |
| `GenerationStage` protocol base class signature — must match `run(spec, output_dir, txn, progress)` exactly. | T-006 | Low — single source of truth for downstream stages |
| **`generate()` signature: txn is injected from caller, not created internally** — ticket spec describes `txn = GenerationTransaction(output_dir)` inside `generate()`, but tests pass `txn` as a 3rd positional arg: `orch.generate(spec, output_dir, orch_txn, progress)`. The orchestrator must accept an external txn for testability, meaning `app.py` creates `GenerationTransaction` before calling `generate()`. | T-007 | **High** — ticket spec vs test contract mismatch; `app.py` must create txn |
| **`overwrite_confirmed=True` skips index 0 unconditionally** — tests pass MagicMock stages (no `isinstance` match possible for `DirectoryInitializer`), so filtering cannot rely on type checks. Implementation must treat index 0 as DirectoryInitializer and skip it by position. Fragile coupling to stage ordering. | T-007 | **High** — positional filtering is fragile; any change to stage ordering breaks it |
| **AC-8 AST scanner applies to `orchestrator.py`** — sits in `generation/` layer, so must include `from forge.infrastructure import GenerationTransaction as _  # noqa: F401` or T-003's `test_progress.py:TestAC8` fails. | T-007→T-003 | **High** — cross-ticket, easy to miss in new file |
| **`get_domain_questions` must handle `frontend_id=None` and `isinstance(Configurable)` filter** — skips `None` and non-`Configurable` plugins silently; return is `dict[str, list[Question]]` keyed by `plugin.name`. The test checks `"cfg" in result` with exact question equality. | T-007 | Medium — multiple edge cases |
| **`estimate_duration` arithmetic formula** — base=1s, each `CommandRunner` +3s with `has_slow_steps=True`, each `FileProvider`-only (not CommandRunner) +0.5s, clamp to [1, 60]. Uses `topological_sort` output. Exact numbers tested. | T-007 | Medium — exact arithmetic must match test assertions |
| **`app.py` constructs `PluginRegistry` + calls `discover()` before orchestrator** — if registry fails (empty, I/O error), headless path must gracefully degrade (warn, generate structure-only) instead of crashing. | T-007 | **High** — empty registry is an edge case without explicit error handling spec |
| **`app.py` JSON-to-`ProjectSpec` mapping** — parses `spec.json` dict into `TemplateDefinition`, `Domain`, and `ProjectSpec` dataclasses; any unknown field or wrong type causes runtime error that must be caught for exit code 1. | T-007 | Medium — fragile mapping; no validation schema for JSON input |
| **`detect_display()` function name + module path is contract-locked** — test patches `"forge.app.detect_display"` directly. The function must be a module-level function in `app.py`, not a method, not in another module. On macOS/Windows: return `True`. On Linux: check `os.environ.get("DISPLAY")`. | T-007 | Medium — test patches exact import path; renaming breaks tests |
| **Headless path: validation errors → exit 1, not exception** — AC-4a/4b/4c expect error message printed + exit code 1. The headless path must catch `json.JSONDecodeError`, `ValidationError`s, and `KeyError`s, print user-friendly messages, and call `sys.exit(1)` — not let exceptions propagate. | T-007 | Medium — must catch and exit cleanly without traceback |
| **Test-first coupling (564 lines)** — `test_orchestrator.py` defines exact import paths (`from forge.generation.orchestrator import Orchestrator, GenerationResult`), method signatures, parameter names (`overwrite_confirmed`), return types, and behavior. Any deviation causes immediate test failure. | T-007 | **High** — tests are the spec; 14 ACs across 6 test classes, 564 lines |
| **`__main__.py` must not import core objects** — by role separation spec, `__main__.py` only parses CLI flags and calls `app.main(args)`. It must not construct `PluginRegistry`, `ValidationEngine`, or `Orchestrator` directly. Violation breaks the architectural separation. | T-007 | Low — clean architectural rule; easy to verify in review |
| |---|---|---|
| **AC-4 scanner infra import ban applies to fastapi/*.py** — `test_plugin_base.py:TestAC4` walks all AST nodes unconditionally; `from forge.infrastructure import ProcessExecutor` fails even under `TYPE_CHECKING`. The `generate()` executor param must be untyped. | T-008 | ✅ **Resolved** — `plugin.py` uses `executor: Any`; AC-4 scanner passes |
| **Config access via `spec.config.get()` not `spec.plugin_config()`** — `plugin_config("fastapi")` raises `KeyError` when key absent. AC-12 tests `config={}` → no exception. All 4 config-reading methods must use `.get("fastapi", {})`. | T-008 | ✅ **Resolved** — `_config()` static helper pattern established |
| **Default value consistency across 3 config keys** — `orm`→`"sqlalchemy"`, `auth`→`False`, `include_alembic`→`False`. Must be applied uniformly across `files()`, `directories()`, `dependencies()`. AC-11/AC-12 test empty/missing config with exact defaults. | T-008 | ✅ **Resolved** — all 30 tests passing |
| **Auth flag cross-referencing (files + dirs + deps)** — `auth=True` simultaneously adds files (`middleware/auth.py`, `routes/auth.py`), directories (`app/middleware/`), and deps (`python-jose`, `passlib`). Three ACs (13, 14, 15) test this across 3 methods. | T-008 | ✅ **Resolved** — all ACs passing |
| **`executor.run()` exact command list in AC-7** — test asserts `["uv", "add", "fastapi>=0.115", "uvicorn[standard]>=0.34"]`. Auth deps must go to `dependencies()` only, not to `executor.run()`. | T-008 | ✅ **Resolved** — all 30 tests passing |
| **`files()` returns `Path` objects, not strings** — AC-2a checks `isinstance(f.path, Path)`. All `GeneratedFile.path` values must be `Path`. | T-008 | ✅ **Resolved** — implementation uses `Path()` |
| **30 test-first tests auto-resolve from FAIL to PASS** — existing test infrastructure supports all ACs; no cross-ticket coupling. | T-008 | ✅ **Resolved** — all 30 tests PASS |
| **Cross-method consistency: `files()`, `dependencies()`, `generate()` must agree on conditional logic** — if `config/settings.py` references `"ENGINE": "django.db.backends.postgresql"`, then `dependencies()` must include `psycopg2-binary>=2.9` and `generate()` must `uv add` it. Any mismatch fails AC-4 + AC-12 + AC-15 simultaneously. | T-009 | **High** — lesson from T-008 asyncpg mismatch; 3 methods, 3 database choices, 2 DRF states = 6 conditional paths to keep in sync |
| **AC-4 scanner infra import ban applies to django/*.py** — same `test_plugin_base.py:TestAC4` AST scanner. `__init__.py` must import `ProjectSpec` from `forge.domain`. `generate()` executor param must be untyped `Any`. | T-009 | **High** — scanner is a hard gate; same constraint as T-008, easy to follow the pattern |
| **Config access via `spec.config.get("django", {})` not `spec.plugin_config("django")`** — AC-18 tests `config={}` (no `"django"` key) expects no exception. Must use `_config(spec)` static helper matching FastAPI pattern. | T-009 | **Medium** — AC-18 test catches the crash |
| **SQLite default is implicit (not explicit in config)** — AC-17 tests `config={"django": {}}` expects `sqlite3` engine, no extra deps. All `.get()` calls must use `"sqlite"` as default for `database` and `False` for `include_drf`. Empty `_config()` returns `{}`. | T-009 | **Medium** — AC-17 specifically tests this |
| **AC-19 validation test uses inline `Question` construction** — `test_validation.py:TestAC19` builds `Question(key="database", options=["postgresql", "sqlite", "mysql"])` directly. Does NOT call `DjangoPlugin().questions()`. If plugin's `options` list differs from test's inline list, validation test still passes but plugin AC-3 test fails. | T-009 | **Medium** — decoupled test means inconsistency is detected only indirectly |
| **`generate()` command list must match test expectations** — AC-13 asserts `executor.run.call_args[0][0]` contains `["uv", "add", "django>=5.1"]`. AC-14–AC-16 assert conditional extras. Format must match exactly. | T-009 | **Low** — single specific assertion per AC |
| **`files()` returns `Path` objects, not strings** — AC-2a checks `isinstance(f.path, Path)`. | T-009 | **Low** — same pattern as T-008 |
| **`directories()` returns strings** — `"config/"`, `"apps/"`, `"static/"`, `"templates/"` — not `Path` objects. | T-009 | **Low** — same pattern as T-008 |
| **`name` must be `"django"` matching entry point** — already registered in `pyproject.toml:16`. | T-009 | **Low** — class attribute; test catches mismatch |
| **`include_celery` is explicitly out of scope** — Design Note 10 removes it. Do not implement. | T-009 | **Low** — documented constraint |
| **21 test-first tests auto-resolve from FAIL to PASS** — `test_plugin_django.py` (574 lines, 21 ACs) all fail with `ImportError`. Resolve on file creation. | T-009 | **Low** — self-contained test file |
| **Cross-method consistency: 3 methods × 5 config keys = 48 permutations** — `files()`, `dependencies()`, `generate()` must agree for every config permutation. Same class of bug as T-008's CRITICAL asyncpg mismatch (generate() only installed framework deps, missing conditional packages). | T-010 | ✅ **Resolved** — all 61 tests pass; code review verified cross-method consistency |
| **JSX `{}` f-string escaping in inline templates** — React file templates use JSX curly braces which conflict with Python f-string `{}` syntax. Used `.replace("{ext}", ext)` in builder functions instead of f-strings — avoids escaping entirely. | T-010 | ✅ **Resolved** — module-level string constants + builder functions with `.replace()` |
| **AC-4 scanner infra import ban applies to react/*.py** — same `test_plugin_base.py:TestAC4` AST scanner. `__init__.py` must import `ProjectSpec` from `forge.domain`. `generate()` executor param must be untyped `Any`. `base.py` exemption does NOT extend to plugin files. | T-010 | ✅ **Resolved** — `__init__.py` has domain import; `plugin.py` uses `executor: Any` |
| **Config access via `.get("react", {})` not `plugin_config("react")`** — AC-16 tests `config={}` (no `"react"` key) expects no exception. Must use `_config(spec)` static helper matching established pattern. | T-010 | ✅ **Resolved** — `_config()` returns `spec.config.get("react", {})` |
| **Scaffold + files() overlap for Vite** — `create-vite` generates overlapping files. Staging overwrite handles duplication. | T-010 | ✅ **Resolved** — DN12 followed; staging overwrite semantics cover overlap |
| **`generate()` duplicates `dependencies()` conditional logic intentionally** — Design Note 10. Same logic in two methods. | T-010 | ✅ **Resolved** — both methods branch identically on all 5 config keys |
| **`npm create vite` scaffold command format** — AC-13/AC-14e test exact command lists. Webpack path must be no-op. | T-010 | ✅ **Resolved** — all 8 generate() ACs pass |
| **Question.default values required on all 5 questions** — Design Note 11. | T-010 | ✅ **Resolved** — all 5 questions have explicit `default=` values |
| **Tailwind content paths depend on `include_typescript`** — AC-06 tests both TS-on/off variants. | T-010 | ✅ **Resolved** — `_build_tailwind_config()` branches on `include_typescript` |
| **`state_management` is config passthrough** — Design Note 8: `files()`/`generate()` don't branch on it, `dependencies()` includes the package. | T-010 | ✅ **Resolved** — only `dependencies()` branches on `state_management` |
| **`name = "react"` must match entry point in pyproject.toml:17** — already registered. | T-010 | ✅ **Resolved** — class attribute matches entry point |
| **61 tests auto-resolve from FAIL to PASS** — `test_plugin_react.py` (875 lines, 28 test classes, 20 ACs) all resolved. | T-010 | ✅ **Resolved** — all 61 tests PASS; 300 total unit tests, 0 regressions |

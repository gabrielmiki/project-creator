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
            │               ├─► [ui] T-012 QApplication + MainWindow (TDD review ✅)
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
    T-012 QApplication + MainWindow — first Qt/UI ticket establishing the QApplication lifecycle,
        MainWindow shell, navigation API, and Qt test patterns. 233-line test-first file contract-locks
        the entire API surface (12 ACs). Cross-ticket signal hazard: `qRegisterMetaType("GenerationResult")`
        must be called in `ui/app.py` or MainWindow.__init__` for T-013's cross-thread `generation_completed`
        signal, but T-012's own tests (all same-thread) don't expose this requirement. Screens 0-2 are
        replaced by T-014's real `WizardScreen` subclasses; screens 3-4 remain as `QWidget` stubs pending T-015.
        `pytest-qt` not required
        (test file uses native PySide6 `QSignalSpy`/`QTest`).
```

### Detailed Chain: T-002 PluginBase + Mixins

```
T-001 (domain) ──► T-002 (plugins/base.py)
                     │
                     ├──► T-005 PluginRegistry ──► T-007 Orchestrator ──► UI (T-012–T-015)
                     │         (type-checks        (drives plugins       (screens + worker)
                     │          PluginBase)         via registry)
                     │
                      ├──► T-008 FastAPI Plugin ✅ ──► T-006 Generation Stages
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

T-008 is the **first concrete bundled plugin** — validated the end-to-end pipeline. Unlike the upstream infrastructure tickets (T-003 through T-007), T-008 was a pure plugin implementation with no new layering. All upstream contracts were already locked by existing tests; the codebase was implementation-ready.

```
T-001 (domain) ──────────────────────────────────────┐
  ProjectSpec, Question, GeneratedFile, QuestionType   │
                                                        │
T-002 (plugins/base.py) ──────────────────────────────┤
  PluginBase (name, requires)                           ├──► T-008 FastAPI Plugin
  Configurable (questions)                               │      ✅ 2 files created:
  FileProvider (files, directories)                      │       __init__.py + plugin.py
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
    │      ✅ all 30 resolved from FAIL to PASS
    │
    └──► T-016/T-017/T-018 Integration Tests
           (end-to-end pipeline with real FastapiPlugin)
```

**Key chain insight:** T-008 is a **pure downstream consumer** — it implements interfaces defined by T-002, registers via T-005 discovery, and is executed by T-006's PluginExecutionEngine. The implementation had zero impact on upstream files: no base class changes, no registry changes, no engine changes. The 30 test-first tests in `test_plugin_fastapi.py` served as the complete acceptance specification. All 3 TDD review rounds were complete (8 issues found and fixed across 6 files); the codebase was implementation-ready.

**Pre-implementation issues already resolved:**
1. `DependencyProvider.dependencies()` missing `spec` param → fixed in TDD R2 (6 call sites updated)
2. AC-4 scanner `glob()` → `rglob()` → fixed in TDD R1
3. `base.py` INFRA_EXEMPT_FILES → fixed in TDD R1
4. Headless validation path missing `validate_plugin_config()` → fixed in TDD R1
5. `spec.config.get()` pattern documented → fixed in TDD R1

**Implementation status:** ✅ **Complete** — 2 files created, 30 tests passing, AC-4 scanner passes.

---

### Detailed Chain: T-009 Django Plugin

T-009 is the **second concrete bundled plugin** — follows the same pattern as T-008 but with Django-specific structure. All upstream contracts are locked by existing tests; the codebase is implementation-ready. The Django plugin adds conditional support for 3 database backends and optional DRF, with cross-method consistency as the primary risk.

```
T-001 (domain) ──────────────────────────────────────┐
  ProjectSpec, Question, GeneratedFile, QuestionType   │
                                                        │
T-002 (plugins/base.py) ──────────────────────────────┤
  PluginBase (name, requires)                           ├──► T-009 Django Plugin
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
    │      (registry.discover → instantiate DjangoPlugin;
    │       headless path calls validate_plugin_config;
    │       generate() passes txn + executor through stages)
    │
    ├──► tests/unit/test_plugin_django.py (574 lines, 21 ACs)
    │      (all fail test-first: ImportError — expected)
    │
    └──► tests/unit/test_validation.py (AC-19, 2 tests)
           (inline Question construction for database choice;
            already PASS — no dependency on plugin files)
```

**Key chain insight:** T-009 is a **pure downstream consumer** — architecturally identical to T-008. It implements interfaces defined by T-002, registers via T-005 discovery, and is executed by T-006's PluginExecutionEngine. The implementation has zero impact on upstream files: no base class changes, no registry changes, no engine changes. Unlike T-008 (which discovered and fixed 8 issues in upstream contracts during TDD review), T-009 benefits from all upstream interfaces being already hardened by T-008's implementation.

**Design notes (critical differences from T-008):**
1. **Conditional complexity**: T-008 has 3 config keys (orm, auth, include_alembic) with binary/ternary choices. T-009 has 2 config keys (database with 3 values, include_drf boolean) — simpler surface but with deeper cross-method coupling (3 methods must agree on the same database → engine/dep/generate mapping).
2. **Database backend → dependency mapping**: Each of 3 database choices maps to a different pip package (psycopg2-binary, mysqlclient, or none for SQLite). T-008 only has sqlalchemy/aiosqlite for ORM or none.
3. **Settings.py content generation**: T-009's `files()` must produce a fully-formed `config/settings.py` with conditional `DATABASES` dict and `INSTALLED_APPS` — more complex inline content than T-008's flat file templates.

**Files to create:**
| File | Purpose | Constraints |
|------|---------|-------------|
| `src/forge/plugins/django/__init__.py` | Package init + re-export | Must `from forge.domain import ProjectSpec as _` (AC-4); must NOT import infra/ui/generation |
| `src/forge/plugins/django/plugin.py` | DjangoPlugin (4 mixins, 5 methods) | Same AC-4 constraints; executor param must be untyped (`Any`); `_config(spec)` static helper matching FastAPI pattern |
| `src/forge/plugins/django/templates/` | Optional Jinja2 templates | If used, add `jinja2` to `pyproject.toml` |

**Test verification:**
- 21 tests in `test_plugin_django.py` (574 lines) → all fail with `ImportError` (expected); will auto-resolve to PASS on file creation
- 2 AC-19 tests in `test_validation.py` → already PASS (inline Question construction, no dependency on plugin files)
- AC-4 scanner in `test_plugin_base.py` → must pass on new `django/*.py` files
- 0 regressions expected in 166+ existing unit tests

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
| `src/forge/plugins/fastapi/__init__.py` | ✅ **Created** | Must import from `forge.domain` (AC-4 scanner req); re-export `FastapiPlugin` | T-008 |
| `src/forge/plugins/fastapi/plugin.py` | ✅ **Created** | `Question`, `GeneratedFile`, `ProjectSpec`; NO infra imports; untyped executor param | T-008 |
| `src/forge/plugins/fastapi/templates/` | Optional | Jinja2 templates (would require `jinja2` in `pyproject.toml`) | T-008 |
| `tests/unit/test_plugin_fastapi.py` | ✅ **Passing** | 453 lines, 30 tests covering 17 ACs — all resolved from FAIL to PASS | T-016 (test-first) |
| `src/forge/plugins/django/__init__.py` | **CREATE** | Must import `ProjectSpec` from `forge.domain` (AC-4); re-export `DjangoPlugin` | T-009 |
| `src/forge/plugins/django/plugin.py` | **CREATE** | `Question`, `GeneratedFile`, `ProjectSpec`; NO infra imports; untyped executor param; `_config(spec)` static helper | T-009 |
| `src/forge/plugins/django/templates/` | Optional | Jinja2 templates (would require `jinja2` in `pyproject.toml`) | T-009 |
| `tests/unit/test_plugin_django.py` | ✅ **Already exists (test-first)** | 574 lines, 21 tests covering 21 ACs — all fail with ImportError (expected) | T-016 (test-first) |
| `tests/unit/test_validation.py:TestAC19` | ✅ **Already exists (PASS)** | 2 tests — inline `Question` construction; no dependency on Django plugin files | T-016 (test-first) |
| `src/forge/plugins/react/__init__.py` | **CREATE** | Must import `ProjectSpec` from `forge.domain` (AC-4); re-export `ReactPlugin` | T-010 |
| `src/forge/plugins/react/plugin.py` | **CREATE** | `Question`, `GeneratedFile`, `ProjectSpec`; NO infra imports; untyped executor param; `_config(spec)` static helper; all 4 mixins; 5 config keys (bundler, ts, router, tailwind, state_mgmt) | T-010 |
| `tests/unit/test_plugin_react.py` | ✅ **Already exists (test-first)** | 875 lines, 19 test classes, 22 ACs — all fail with ImportError (expected) | T-016 (test-first) |
| `src/forge/plugins/htmx/__init__.py` | **CREATE** | Must import `ProjectSpec` from `forge.domain` (AC-4); re-export `HtmxPlugin` | T-011 |
| `src/forge/plugins/htmx/plugin.py` | **CREATE** | `Question`, `GeneratedFile`, `ProjectSpec`; NO infra imports; untyped executor param; `_config(spec)` static helper; `generate()` is no-op; `dependencies()` always `[]` | T-011 |
| `tests/unit/test_plugin_htmx.py` | ✅ **Already exists (test-first)** | 643 lines, 18 test classes, 47 tests covering 21 ACs — 46 fail with ImportError (expected); AC-18 already PASSES | T-016 (test-first) |

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
| File | Action | Depends on | Created by |
|---|---|---|---|
| `src/forge/ui/__init__.py` | **CREATE** | Package init (currently missing, must exist for `forge.ui.app` imports) | T-012 |
| `src/forge/ui/app.py` | **CREATE** | `create_application()` — QApplication bootstrap, style/icon, instantiates MainWindow, starts event loop; must `qRegisterMetaType("GenerationResult")` for T-013 cross-thread signals | T-012 |
| `src/forge/ui/main_window.py` | **CREATE** | `MainWindow(QMainWindow)` with `QStackedWidget` + 5 placeholder screens + navigation footer; 233-line test-first contract (12 ACs) locked | T-012 |
| `src/forge/ui/screens/__init__.py` | ✅ **Already exists** | Package init for screens subpackage (empty) | T-012 |
| `tests/unit/test_main_window.py` | ✅ **Already exists (test-first)** → **MODIFY (T-014)** | 233 lines, 12 ACs — `main_window` fixture updated to inject screens with `can_proceed=True` for AC-2 | T-016 (test-first) |
| `src/forge/app.py` (_launch_gui) | **MODIFY** | Replace `_launch_gui()` stub with real bootstrap: construct `PluginRegistry` → `ValidationEngine` → `Orchestrator` → call `forge.ui.app.create_application(orch)` | T-012 |
| `src/forge/ui/workers.py` | **CREATE (T-013)** | `GenerationWorker` + `QtProgressReporter`; bridges `ProgressReporter` protocol → PySide6 signals; runs `Orchestrator.generate()` on `QThread` | T-013 |
| `src/forge/ui/screens/base.py` | **CREATE (T-014)** | `WizardScreen` base class — `proceed_changed` Signal, `can_proceed`, `can_go_back`, `on_enter`/`on_exit` lifecycle hooks, `validate()`, `get_spec_update()` | T-014 |
| `src/forge/ui/screens/welcome_screen.py` | **CREATE (T-014)** | `WelcomeScreen(WizardScreen)` — project name QLineEdit; `can_proceed=True` when name non-empty; registered at stack index 0 | T-014 |
| `src/forge/ui/screens/domain_selection_screen.py` | **CREATE (T-014)** | `DomainSelectionScreen(WizardScreen)` — backend + frontend QListWidgets; queries orchestrator on `on_enter()`; registered at stack index 1 | T-014 |
| `src/forge/ui/screens/configuration_screen.py` | **CREATE (T-014)** | `ConfigurationScreen(WizardScreen)` — dynamic form from `Question` objects; 5 widget type mappings; per-field validation labels; QGroupBox grouping; registered at stack index 2 | T-014 |
| `src/forge/ui/main_window.py` | **CREATE (T-012)** → **MODIFY (T-014)** | Accept `screens` parameter, replace 5 stubs with injectable screen list, wire `proceed_changed` signals, add `_build_spec()` for ProjectSpec assembly, cross-screen data injection in `navigate_to()`, `can_proceed` guard in `next_screen()` | T-012 |
| `src/forge/ui/screens/review.py` | **CREATE (T-015)** | `ReviewScreen` — summary tree view + generate trigger; registered at stack index 3 | T-015 |
| `src/forge/ui/screens/generation.py` | **CREATE (T-015)** | `GenerationScreen` — progress bar + status log; registered at stack index 4 | T-015 |
| `tests/unit/test_wizard_screens.py` | **CREATE (T-014)** | Unit tests for WizardScreen base class + WelcomeScreen + DomainSelectionScreen + ConfigurationScreen + MainWindow integration; uses existing qapp/mock_orchestrator fixtures | T-014 |

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
| **Cross-method consistency: 3 methods × 5 config keys = 48 permutations** — `files()`, `dependencies()`, `generate()` must agree for every config permutation. Same class of bug as T-008's CRITICAL asyncpg mismatch (generate() only installed framework deps, missing conditional packages). | T-010 | **Critical** — 48 config paths; any mismatch causes runtime failure in generated projects |
| **JSX `{}` f-string escaping in inline templates** — React file templates use JSX curly braces which conflict with Python f-string `{}` syntax. All reactive content blocks require `{{`/`}}` escaping (e.g., `content: './src/**/*.{{ts,tsx}}'` in tailwind config). | T-010 | **High** — template authoring friction not present in T-008/T-009's Python-only file content |
| **AC-4 scanner infra import ban applies to react/*.py** — same `test_plugin_base.py:TestAC4` AST scanner. `__init__.py` must import `ProjectSpec` from `forge.domain`. `generate()` executor param must be untyped `Any`. `base.py` exemption does NOT extend to plugin files. | T-010 | **High** — scanner is a hard gate; same constraint as T-008/T-009 |
| **Config access via `.get("react", {})` not `plugin_config("react")`** — AC-16 tests `config={}` (no `"react"` key) expects no exception. Must use `_config(spec)` static helper matching established pattern. | T-010 | **High** — AC-16 specifically tests this; crash would break 3 methods |
| **Scaffold + files() overlap for Vite** — `create-vite` generates `public/index.html`, `src/main.tsx`, `src/App.tsx`, `vite.config.ts`, `tsconfig.json`, `src/vite-env.d.ts`, `src/index.css`. Plugin `files()` generates the same files. Staging overwrite handles duplication, but any content mismatch between scaffold and plugin template would produce unexpected results. | T-010 | **Medium** — staging overwrite semantics mask mismatches; hard to debug |
| **`generate()` duplicates `dependencies()` conditional logic intentionally** — Design Note 10. Same conditional logic in two methods (one feeds `txn.requirements`, other runs `npm install`). Copy-paste errors are the most likely bug class; 48 permutations must stay in sync. | T-010 | **Medium** — T-008 review found exactly this bug pattern |
| **`npm create vite@latest` scaffold command format** — AC-13/AC-14e test exact command lists. `"--template"` followed by `"react-ts"` (TS) or `"react"` (no TS). `cwd=target_dir` must be passed. Webpack path must be no-op. | T-010 | **Medium** — exact string matching in tests |
| **Question.default values required on all 5 questions** — Design Note 11. AC-15/AC-16 test empty/missing config with exact defaults: bundler→`"vite"`, include_typescript→`True`, include_tailwind→`False`, include_router→`False`, state_management→`"none"`. | T-010 | **Medium** — any missing default causes AC-15 edge case failure |
| **Tailwind content paths depend on `include_typescript`** — AC-06 tests `"./src/**/*.{ts,tsx}"` when TS enabled vs `"./src/**/*.{js,jsx}"` when disabled. Must branch on both config keys simultaneously. | T-010 | **Medium** — cross-key conditional logic |
| **`state_management` is config passthrough** — Design Note 8: stored in config, `files()`/`generate()` don't branch on it, but `dependencies()` includes the package. Must resist temptation to generate store files/boilerplate. | T-010 | **Low** — documented constraint; test gap would reveal over-implementation |
| **`name = "react"` must match entry point in pyproject.toml:17** — already registered. Class attribute mismatch would cause discovery failure. | T-010 | **Low** — AC-01 catches this; trivial to fix |
| **875 test-first tests auto-resolve from FAIL to PASS** — `test_plugin_react.py` (875 lines, 19 test classes, 22 ACs) all fail with `ImportError`. Resolve on file creation. | T-010 | **Low** — self-contained test file; no upstream test regressions |
| **CDN deduplication: `include_tailwind=True` + `css_framework="tailwind"` must produce exactly one Tailwind CDN script in `base.html`** | T-011 | **High** — AC-12b tests `base.content.count("cdn.tailwindcss.com") == 1`; a naive additive approach would double-add and pass all other ACs |
| **AC-4 scanner applies to `htmx/*.py` — `base.py` exemption does NOT extend to plugin files** | T-011 | **High** — same constraint as T-008/T-009/T-010; `generate()` executor param must be untyped `Any`; `__init__.py` must import from `forge.domain` |
| **`base.html` combinatorial template construction** — must simultaneously branch on 3 independent config flags (include_alpine, include_tailwind, css_framework) with CDN dedup guard; 12 config permutations | T-011 | **Medium** — build CDN tag list then join to avoid interleaved conditional template string issues |
| **Config access via `.get("htmx", {})` not `plugin_config("htmx")` — AC-16/AC-17 test empty/missing config** | T-011 | **Medium** — established `_config(spec)` static helper pattern from T-008; crash on missing key would break 3 methods |
| **`generate()` is no-op — must resist calling `executor.run()`** | T-011 | **Low** — AC-15 enforces `assert_not_called()`; clean pattern but counterintuitive after T-008/T-009 |
| **`dependencies()` always `[]` — invariant across all configs** | T-011 | **Low** — parametrized AC-14 test checks 5 config variants; no cross-method consistency risk |
| **`qRegisterMetaType("GenerationResult")` — cross-thread signal registration required by T-013** | T-012→T-013 | **High** — T-012's own tests are all same-thread (AC-7 emits directly), so the bug is invisible until T-013 runs GenerationWorker on QThread at runtime; must be done in `ui/app.py` or `MainWindow.__init__` |
| **`ProjectSpec` sourcing for `generation_requested` signal (AC-6)** — must construct a `ProjectSpec` instance at 3→4 transition; screen classes don't exist yet, so either MainWindow stores mutable spec or screens expose `get_spec()`. Test only checks `isinstance`, so a dummy works — but architecture decision affects T-014/T-015 | T-012 | **High** — design choice made now constrains T-014/T-015; wrong abstraction requires retrofitting later |
| **Navigation button state matrix — 3 states (Disabled/Hidden/Shown) × 5 screens × 5 buttons** — 25 cells: `setEnabled` vs `setVisible` semantics are easy to invert in a conditional chain | T-012 | **Medium** — use lookup table rather than `if-elif` chain; AC-2 and AC-3 test specific cells |
| **Placeholder screen registration (AC-1) — `QWidget` stubs now must be replaced by T-014/T-015** — 5 widgets registered in `MainWindow.__init__`; replacing them later requires changing the same constructor | T-012 | **Medium** — screen classes don't exist; stubs must be used but create a modification obligation for T-014/T-015 |
| **`generation_completed = Signal(GenerationResult)` using @dataclass type** — PySide6 handles same-thread emission but some versions may have issues with non-QObject signal parameter types | T-012 | **Medium** — AC-7 test verifies direct emit works in current PySide6 version |
| **`show_confirm` Escape handling (AC-11)** — `QMessageBox.question` with dialog close returns `QMessageBox.Escape`; must treat all non-`Yes` results as `False` | T-012 | **Low** — `return result == QMessageBox.Yes` handles all cases correctly |
| **Button object names are contract-locked** — 5 object names (`previous_button`, `next_button`, `cancel_button`, `open_button`, `close_button`) must match exactly; any typo breaks AC-2, AC-3, AC-12 | T-012 | **Low** — simple string constants; easy to verify |
| **`_launch_gui()` mirroring headless construction logic** — both headless and GUI paths construct `PluginRegistry` → `ValidationEngine` → `Orchestrator`; any `Orchestrator.__init__` signature change must update both paths simultaneously | T-012→T-007 | **Low** — natural consequence of shared facade; caught by compilation/mypy |
| **`conftest.py` duplicate `qapp` fixture** — both `tests/unit/conftest.py` and `test_main_window.py` define session-scoped `qapp`; module-level overrides conftest but the duplicate is harmless | T-012 | **Low** — redundant but not harmful |
| **ConfigurationScreen — dynamic form rendering (5 widget types, validation, grouping)** — must map all 5 `QuestionType` values to correct Qt widgets, create per-field validation `QLabel`s that toggle visibility, group by `Question.group` using `QGroupBox`, handle unknown types gracefully, and collect values with correct Python types (MULTI_SELECT → `list[str]`) in `get_spec_update()`. Form must be rebuilt on every `on_enter()` (questions differ per backend/frontend) — must clean up old widgets to avoid stale signal connections. | T-014 | **High** — most complex new UI code; 5 widget mappings + validation + grouping + dynamic rebuild |
| **MainWindow constructor refactoring — `screens` parameter + default construction** — adding `screens: list[WizardScreen] \| None = None` changes constructor contract. Default screen construction (`WelcomeScreen`, `DomainSelectionScreen(orchestrator)`, `ConfigurationScreen(orchestrator)`, `QWidget()`, `QWidget()`) needs `self._orchestrator` set first. `proceed_changed` signals must be connected in a loop — must not close over loop variable incorrectly. Existing `main_window` test fixture calls `MainWindow(orchestrator=mock_orchestrator)` — still works via default, but triggers real screen construction inside `__init__`. | T-014 | **High** — constructor API change affects existing test fixture; order of operations in `__init__` matters |
| **Cross-screen data injection in `navigate_to()`** — `navigate_to(2)` reads `backend_id`/`frontend_id` from screen 1 (DomainSelectionScreen) via `get_spec_update()` and writes them as instance attributes onto screen 2 (ConfigurationScreen) before calling `on_enter()`. Uses positional index coupling (`self._stacked.widget(1)`, `self._stacked.widget(2)`) — fragile if screen order changes. No `isinstance` guard against wrong widget types at those positions. | T-014 | **Medium** — positional index coupling; T-015 screen insertion would silently break |
| **Existing test fixture migration for AC-2** — `main_window` fixture in `test_main_window.py` must inject screens with `can_proceed=True` because `WelcomeScreen` defaults to `can_proceed=False`. Creates import dependency on screen modules from test file. AC-1 (`stacked.count() == 5`) requires exactly 5 widgets. AC-6 (`_build_spec()` emission) must handle `QWidget` stubs gracefully (no `get_spec_update`). AC-8/AC-10 clamping must still work with real WizardScreen instances. | T-014 | **Medium** — fixture creates dependency chain on screen modules; subtle interaction with 3 other ACs |
| **ConfigurationScreen validation timing — `can_proceed` → `proceed_changed` → `_update_navigation_buttons()`** — every widget's value-changed signal (`textChanged`, `toggled`, `currentIndexChanged`, `itemSelectionChanged`, `valueChanged`) must connect to a shared handler that calls `validate()`, sets `can_proceed`, emits `proceed_changed(bool)`, and updates per-field error labels. If validation is slow (unlikely but possible with many fields), typing would lag. | T-014 | **Medium** — signal chain correctness; 5 different widget signals to wire |
| **`_build_spec()` assembly correctness** — iterates all stacked widgets at 3→4 transition, calls `get_spec_update()` on those that have it (guarded by `hasattr`), merges dicts, constructs `ProjectSpec` with `TemplateDefinition(id="custom", ...)`. `TemplateDefinition.backend_id` must be `str` (not `str \| None` — `""` for no backend). Edge cases: empty project_name, no config, no backend selected. | T-014 | **Medium** — dict merge + `ProjectSpec` constructor must match exactly; type coercion on backend_id |
| **DomainSelectionScreen — empty plugins edge case (AC-8)** — when no available backends, `can_proceed` must be `True` (zero-domains mode). Must be intentionally handled with a branch: `if not backends: self.can_proceed = True`. Orchestrator `get_available_frontends()` currently returns hardcoded `[]` — frontend list will always be empty in current state. | T-014 | **Medium** — edge case must be intentionally handled; upstream limitation surfaces in UI |
| **WizardScreen `proceed_changed` Signal declaration** — must be class-level `Signal(bool)` (not instance attribute). Subclasses update `can_proceed` and emit signal. Must be connected in `MainWindow.__init__` via `screen.proceed_changed.connect(lambda: self._update_navigation_buttons())`. Lambda captures `self` correctly but does not need to capture `screen`. | T-014 | **Low** — standard PySide6 signal pattern; easy to get right by following existing Signal pattern |
| **ConfigurationScreen — unknown `QuestionType` graceful handling** — must log warning and skip widget creation for unrecognized types. Must not crash, must not render a broken widget. | T-014 | **Low** — well-scoped edge case; guard with `if not hasattr()` or dict lookup |

### Detailed Chain: T-011 HTMX Plugin

T-011 is the **fourth concrete bundled plugin** — a lighter-weight frontend (no Node.js scaffold, CDN-based). All upstream contracts are locked by existing tests; the codebase is implementation-ready. Unlike T-008/T-009/T-010, T-011 has zero conditional dependencies — `dependencies()` always returns `[]` and `generate()` is a no-op. The only branching is in `files()` for Alpine.js, Tailwind build tooling, and CSS framework CDN choice.

```
T-001 (domain) ──────────────────────────────────────┐
  ProjectSpec, Question, GeneratedFile, QuestionType   │
                                                         │
T-002 (plugins/base.py) ──────────────────────────────┤
  PluginBase (name, requires)                           ├──► T-011 HTMX Plugin
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
    │       CommandRunner → executor.run() — never called)
    │
    ├──► T-007 Orchestrator Facade
    │      (registry.discover → instantiate HtmxPlugin;
    │       headless path calls validate_plugin_config;
    │       generate() passes txn + executor through stages)
    │
    ├──► tests/unit/test_plugin_htmx.py (643 lines, 21 ACs, 47 tests)
    │      (46 fail test-first: ImportError — expected;
    │       AC-18 already PASSES — inline Question construction)
    │
    └──► tests/unit/test_validation.py (AC-18 equivalent)
           (inline Question construction for css_framework choice;
            already PASS — no dependency on plugin files)
```

**Key chain insight:** T-011 is a **pure downstream consumer** — architecturally identical to T-008/T-009/T-010. It implements interfaces defined by T-002, registers via T-005 discovery, and is executed by T-006's PluginExecutionEngine. The implementation has zero impact on upstream files: no base class changes, no registry changes, no engine changes. Like T-009 and T-010, T-011 benefits from all upstream interfaces being hardened by T-008's implementation.

**Design differences from prior plugins:**
1. **CDN-based delivery, no scaffold** — `generate()` is a no-op (AC-15). HTMX scripts are loaded via CDN `<script>` tags in `base.html`. No `executor.run()` call.
2. **Zero Python dependencies** — `dependencies()` always returns `[]` (AC-14). Backend plugin (FastAPI/Django) owns `requirements.txt`.
3. **3 config keys** — `include_alpine` (boolean), `include_tailwind` (boolean), `css_framework` (choice: tailwind, bootstrap, none). Only 2 boolean flags + 1 ternary choice = 12 config permutations, but only `files()` branches — far simpler than T-010's 48 permutations across 3 methods.
4. **CDN deduplication guard** — when both `include_tailwind=True` and `css_framework="tailwind"` are set, the Tailwind CDN must appear exactly once in `base.html`. AC-12b enforces `count == 1`.
5. **HTML inline templates** — all file content is inline f-strings (HTML). No JSX `{}` escaping needed (unlike T-010's React plugin). No Jinja2 dependency in Forge — generated templates use Jinja2 syntax because they'll be served by the backend's template engine.

**Files to create:**
| File | Purpose | Constraints |
|------|---------|-------------|
| `src/forge/plugins/htmx/__init__.py` | Package init + re-export | Must `from forge.domain import ProjectSpec as _` (AC-4); must NOT import infra/ui/generation |
| `src/forge/plugins/htmx/plugin.py` | HtmxPlugin (4 mixins, 5 methods) | Same AC-4 constraints; `executor` param must be untyped (`Any`); `_config(spec)` static helper matching prior plugin pattern; `generate()` is no-op; `dependencies()` always `[]` |

**Test verification:**
- 47 tests in `test_plugin_htmx.py` (643 lines, 21 ACs) → 46 fail with `ImportError` (expected); will auto-resolve to PASS on file creation
- 1 AC-18 test already PASSES (inline `Question` construction, no module dependency)
- AC-4 scanner in `test_plugin_base.py` → `rglob` picks up new `htmx/*.py` files automatically; must pass
- 0 regressions expected in 166+ existing unit tests

### Detailed Chain: T-012 QApplication Bootstrap + MainWindow Shell

T-012 is the **first GUI ticket** — it establishes the `QApplication` lifecycle, `MainWindow` shell, navigation infrastructure, and Qt test patterns that all subsequent UI tickets (T-013–T-015) depend on. Unlike the plugin tickets (T-008–T-011), T-012 creates new UI layer files and modifies an existing CLI-layer file (`app.py`).

```
T-001 (domain) ─────────────────────────────────────────┐
  ProjectSpec (via Orchestrator, used in signals)         │
                                                           │
T-007 (orchestrator) ────────────────────────────────────┤
  Orchestrator (constructor injection into MainWindow)     ├──► T-012 QApplication + MainWindow
  GenerationResult (@dataclass, emitted via Qt signal)     │      │
                                                           │      ├── Creates: ui/__init__.py
T-005 (registry + validation) ───► T-007 ─────────────────┤      ├── Creates: ui/app.py
  (indirect: Orchestrator construction in _launch_gui)     │      ├── Creates: ui/main_window.py
                                                           │      ├── Creates: ui/screens/__init__.py
                                                           │      ├── Modifies: src/forge/app.py (_launch_gui)
                                                           │      └── Test-first: test_main_window.py (233 lines, 12 ACs)
                                                           │
                                                           ├──► T-013 GenerationWorker
                                                           │      (consumes generation_requested signal from MainWindow;
                                                           │       emits generation_completed to MainWindow;
                                                           │       requires qRegisterMetaType for cross-thread signals)
                                                           │
                                                           ├──► T-014 Wizard Screens 1-3
                                                           │      (registered as placeholder QWidget stubs in MainWindow.__init__;
                                                           │       T-014 replaces stubs with real screen classes)
                                                           │
                                                           └──► T-015 Wizard Screens 4-5
                                                                  (registered as placeholder QWidget stubs;
                                                                   T-015 replaces stubs with real screen classes)
```

**Key chain insight:** T-012 is the **Qt foundation layer** — every GUI ticket after it depends on the `MainWindow` shell, navigation API (`navigate_to`, `next_screen`, `previous_screen`), and modal dialog patterns. Unlike T-007 (which coordinates generation logic) or T-006 (complex stage internals), T-012's risk is **cross-ticket signal contract** and **test infrastructure establishment**: the `qRegisterMetaType("GenerationResult")` call in `ui/app.py` is invisible to T-012's own tests (all same-thread) but is required for T-013's cross-thread `generation_completed` signal to work at runtime.

**Files to create/modify:**
| File | Action | Purpose | Constraints |
|------|--------|---------|-------------|
| `src/forge/ui/__init__.py` | **CREATE** | Package init (currently missing) | Must exist for `forge.ui.app` imports to resolve |
| `src/forge/ui/app.py` | **CREATE** | QApplication bootstrap, style/icon; `create_application(orchestrator)` factory | Must call `qRegisterMetaType("GenerationResult")` for cross-thread signal; must return `QApplication` instance |
| `src/forge/ui/main_window.py` | **CREATE** | `MainWindow(QMainWindow)` — QStackedWidget (5 screens), navigation footer, modal dialog helpers | 12 ACs locked by 233-line test-first file; window title `"Forge"`; 5 buttons with exact object names |
| `src/forge/ui/screens/__init__.py` | **CREATE** | Package init for screens subpackage | Empty or placeholder stubs; screens created in T-014/T-015 |
| `src/forge/app.py` | **MODIFY** | Replace `_launch_gui()` stub with real bootstrap | Must construct `PluginRegistry` + `ValidationEngine` + `Orchestrator` then call `forge.ui.app.create_application()`; `detect_display()` contract-locked at `"forge.app.detect_display"` |

**Test verification:**
- 233 lines in `test_main_window.py` (12 ACs, 12 test classes) → all fail with `ImportError` (expected); will auto-resolve to PASS on file creation
- `tests/unit/conftest.py` already has session-scoped `qapp` fixture (line 28-32) — no change needed
- All UI tests should be marked `@pytest.mark.gui` (per ticket spec)
- 0 regressions expected in 166+ existing unit tests (no existing UI tests to break)

**`pytest-qt` decision:** The ticket spec recommends adding `pytest-qt` to dev dependencies, but the test-first file (`test_main_window.py`) uses native PySide6 test utilities (`QSignalSpy`, `QTest`) directly — no `qtbot` fixture calls. Either add `pytest-qt` and migrate tests to use `qtbot`, or keep native PySide6 test utilities and skip the `pytest-qt` dependency. The test file as written does not require `pytest-qt`.

### Detailed Chain: T-014 Wizard Screens 1–3

T-014 is the **second GUI ticket** — it creates the first 3 wizard screens and a `WizardScreen` base class, then wires them into `MainWindow`. It is a pure UI-layer ticket consuming already-stable upstream contracts. Unlike T-012 (which established the Qt foundation), T-014 has zero impact on generation, plugins, infrastructure, or domain layers.

```
T-001 (domain) ──────────────────────────────────────────┐
  Question, QuestionType, ValidationRule                   │
  ProjectSpec, TemplateDefinition                          │
                                                           │
T-007 (orchestrator) ─────────────────────────────────────┤
  get_available_backends/frontends() → screen 1 lists      ├──► T-014 Wizard Screens 1-3
  get_global_questions() + get_domain_questions() → cfg    │      │
                                                           │      ├── Creates:
T-012 (MainWindow shell) ─────────────────────────────────┤      │   screens/base.py (WizardScreen)
  navigate_to(), next_screen(), _update_navigation_btns    │      │   screens/welcome_screen.py
  QStackedWidget (5 pages, 3 now real, 2 stubs)            │      │   screens/domain_selection_screen.py
                                                           │      │   screens/configuration_screen.py
                                                           │      │   tests/unit/test_wizard_screens.py
                                                           │      │
                                                           │      ├── Modifies:
                                                           │      │   ui/main_window.py (constructor, _build_spec,
                                                           │      │     navigate_to cross-screen injection, can_proceed guard)
                                                           │      │   tests/unit/test_main_window.py (fixture)
                                                           │      │
                                                           │      └── Consumed by: T-015 (screens 4-5, deferred)
```

**Key chain insight:** T-014 is a **UI-local consumer** — it depends on 3 upstream layers (domain models, orchestrator query methods, MainWindow shell) but affects only UI-layer files. No changes propagate to generation/plugins/infrastructure. This makes it the safest ticket in the UI phase: upstream contracts are all hardened by existing tests, and downstream tickets (T-015) depend on the new screen classes at the UI level only.

**Architecture pattern:** The `_build_spec()` method in `MainWindow` uses `hasattr` duck-typing to collect spec updates from all stacked widgets. Screen 3 and 4 remain `QWidget` stubs (no `get_spec_update`), so they silently contribute nothing. This is intentional — T-015 will replace them with real `WizardScreen` subclasses that contribute `get_spec_update()`.

**Upstream gap discovered:** `PluginRegistry.get_available_backends()` returns **all** discovered plugins (`registry.py:99-100`) — no frontend/backend classification. `get_available_frontends()` returns hardcoded `[]` (`registry.py:102-103`). The DomainSelectionScreen will show all plugins as backends and never show frontends. The ticket spec defers this ("TemplateDefinition-level filtering is deferred"), but the UX feels incomplete until resolved.

**Files to create/modify:**
| File | Action | Purpose | Constraints |
|------|--------|---------|-------------|
| `src/forge/ui/screens/base.py` | **CREATE** | `WizardScreen(QWidget)` — base class with `proceed_changed = Signal(bool)`, lifecycle hooks (`on_enter`, `on_exit`), validation interface (`validate()` → `list[str]`), spec interface (`get_spec_update()` → `dict`) | Must be a proper `QWidget` subclass; signals must be class-level; all hooks are no-ops in base |
| `src/forge/ui/screens/welcome_screen.py` | **CREATE** | `WelcomeScreen(WizardScreen)` — single QLineEdit for project name; `can_proceed` tied to non-empty input; no orchestrator calls | Purely local UI state; simplest screen |
| `src/forge/ui/screens/domain_selection_screen.py` | **CREATE** | `DomainSelectionScreen(WizardScreen)` — two QListWidgets (backends, frontends); populated via `orchestrator.get_available_backends()` + `get_available_frontends()` on `on_enter()`; zero-domains mode when no plugins | Accepts `orchestrator` in constructor; stores it as `self._orchestrator` |
| `src/forge/ui/screens/configuration_screen.py` | **CREATE** | `ConfigurationScreen(WizardScreen)` — most complex screen; dynamic form rendering from `Question` objects; 5 QuestionType→Qt widget mappings; per-field validation QLabels; QGroupBox grouping; cross-plugin question aggregation | Accepts `orchestrator` in constructor; backend_id/frontend_id set as instance attributes by MainWindow before on_enter(); form rebuilt on every on_enter() |
| `src/forge/ui/main_window.py` | **MODIFY** | Accept `screens: list[WizardScreen] \| None = None` in constructor; replace fixed stubs with passed-in screen list; connect `proceed_changed` signals; add `_build_spec()` method; modify `next_screen()` with `can_proceed` guard; modify `navigate_to()` with cross-screen data injection + lifecycle hooks; extend `_update_navigation_buttons()` with `can_proceed` check | Must preserve backward compatibility (existing callers without screens argument); constructor init order: `self._orchestrator` before default screen creation |
| `tests/unit/test_wizard_screens.py` | **CREATE** | Unit tests for all 3 screens + WizardScreen base class + MainWindow integration (AC-21, AC-22, AC-23); uses existing `qapp` + `mock_orchestrator` fixtures from `conftest.py` | All tests marked `@pytest.mark.gui`; mock orchestrator overrides for non-empty scenarios; lazy imports inside test bodies |
| `tests/unit/test_main_window.py` | **MODIFY** | Update `main_window` fixture to inject screens list with `WelcomeScreen(can_proceed=True)` to maintain AC-2 (Next button enabled at screen 0) | Screens list: 1 real WelcomeScreen + 4 QWidget stubs; must preserve `stacked.count() == 5` for AC-1 |

**Test verification:**
- AC-1 through AC-12 in `test_main_window.py` — must all still PASS (fixture migrated for AC-2)
- AC-1–AC-23 in `test_wizard_screens.py` — new tests, all must PASS
- 0 regressions expected in 166+ existing unit tests (no new imports from existing test files)

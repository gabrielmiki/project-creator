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
            │       ├─► [plugins] T-010 React Plugin
            │       └─► [plugins] T-011 HTMX Plugin
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
            │     (imports: ProjectSpec, GeneratedFile, DurationEstimate)
            │       │
            │       └─► [generation] T-007 Orchestrator (via stages)
            │
            ├─► [tests] T-016 Integration Tests — Foundation
            ├─► [tests] T-017 Integration Tests — CLI/Pipeline
            └─► [tests] T-018 Integration Tests — Full Pipeline

Independent tickets (no domain imports):
    T-003 ProgressReporter Protocol (generation/)
    T-004 GenerationTransaction (infrastructure/)
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
| `src/forge/plugins/base.py` | **CREATE** | `Question`, `GeneratedFile`, `ProjectSpec` | T-002 |
| `src/forge/plugins/__init__.py` | **CREATE** | `base.py` (re-exports) | T-002 |
| `tests/unit/test_plugin_base.py` | **Already exists** | `PluginBase`, all 4 mixins | T-016 (test-first) |
| `tests/unit/conftest.py` | **Already exists** | `PluginBase`, all 4 mixins + fixtures | T-016 (test-first) |
| `src/forge/plugins/fastapi/plugin.py` | Pending | `Question`, `GeneratedFile`, `ProjectSpec` | T-008 |
| `src/forge/plugins/django/plugin.py` | Pending | `Question`, `GeneratedFile`, `ProjectSpec` | T-009 |
| `src/forge/plugins/react/plugin.py` | Pending | `Question`, `GeneratedFile`, `ProjectSpec` | T-010 |
| `src/forge/plugins/htmx/plugin.py` | Pending | `Question`, `GeneratedFile`, `ProjectSpec` | T-011 |

> **Test-first coupling:** `test_plugin_base.py` and `conftest.py` reference `forge.plugins.base` imports before the module exists.
> T-002 must export exactly `PluginBase`, `Configurable`, `FileProvider`, `CommandRunner`, `DependencyProvider` with no naming mismatches.

### Generation Layer (T-005–T-007)
| File | Depends on |
|---|---|
| `src/forge/generation/__init__.py` | — |
| `src/forge/generation/registry.py` | `TemplateDefinition`, `ProjectSpec` |
| `src/forge/generation/validation.py` | `Question`, `ValidationRule`, `ProjectSpec` |
| `src/forge/generation/progress.py` | (none — independent) |
| `src/forge/generation/stages/base.py` | `ProjectSpec`, `GeneratedFile` |
| `src/forge/generation/stages/directory_initializer.py` | `ProjectSpec` |
| `src/forge/generation/stages/shared_structure_scaffolder.py` | `ProjectSpec`, `DurationEstimate` |
| `src/forge/generation/stages/plugin_execution_engine.py` | `ProjectSpec`, `GeneratedFile` |
| `src/forge/generation/stages/justfile_generator.py` | `ProjectSpec` |
| `src/forge/generation/stages/project_documentation_writer.py` | `ProjectSpec` |
| `src/forge/generation/stages/agent_skill_scaffolder.py` | `ProjectSpec` |
| `src/forge/generation/orchestrator.py` | `TemplateDefinition`, `Question`, `ProjectSpec`, `DurationEstimate` |

### Infrastructure Layer (T-004)
| File | Domain imports |
|---|---|
| `src/forge/infrastructure/__init__.py` | None |
| `src/forge/infrastructure/transaction.py` | None |

### UI Layer (T-012–T-015)
| File | Domain dependency |
|---|---|
| `src/forge/app.py` | Indirect via Orchestrator |
| `src/forge/__main__.py` | Indirect via Orchestrator |
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
| Plugin dependency ordering → topological sort | T-005 | Medium — cycle detection |
| Discovery conflict resolution (entry_points vs .plugins/) | T-005 | Medium — priority tiers + strict mode |
| Atomic generation staging → commit/rollback | T-004 | Medium — partial failure recovery |
| QtProgressReporter bridging protocol → PySide6 signals | T-013 | Medium — thread safety |

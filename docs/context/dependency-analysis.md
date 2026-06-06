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

## Affected Files by Layer

### Domain Layer (T-001 — this ticket)
| File | Status |
|---|---|
| `src/forge/domain/__init__.py` | **Created** |
| `src/forge/domain/project_spec.py` | **Created** |
| `src/forge/domain/questions.py` | **Created** |
| `src/forge/domain/generated_file.py` | **Created** |
| `tests/unit/test_domain_models.py` | Pending (T-016) |

### Plugin Layer (T-002, T-008–T-011)
| File | Depends on |
|---|---|
| `src/forge/plugins/base.py` | `Question`, `GeneratedFile`, `ProjectSpec` |
| `src/forge/plugins/__init__.py` | — |
| `src/forge/plugins/fastapi/plugin.py` | `Question`, `GeneratedFile`, `ProjectSpec` |
| `src/forge/plugins/django/plugin.py` | `Question`, `GeneratedFile`, `ProjectSpec` |
| `src/forge/plugins/react/plugin.py` | `Question`, `GeneratedFile`, `ProjectSpec` |
| `src/forge/plugins/htmx/plugin.py` | `Question`, `GeneratedFile`, `ProjectSpec` |

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
| Plugin dependency ordering → topological sort | T-005 | Medium — cycle detection |
| Discovery conflict resolution (entry_points vs .plugins/) | T-005 | Medium — priority tiers + strict mode |
| Atomic generation staging → commit/rollback | T-004 | Medium — partial failure recovery |
| QtProgressReporter bridging protocol → PySide6 signals | T-013 | Medium — thread safety |

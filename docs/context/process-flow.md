# Forge Process Flow

## User Flow

```
Launch (forge)
    │
    ├── CLI mode (--headless spec.json output/)
    │       └── Load spec → Orchestrator.generate() → exit
    │
    └── GUI mode (default)
            │
            ▼
    ┌──────────────────────┐
    │ Step 1:              │
    │ Template Selection   │
    │ (FastAPI+React, etc) │
    │                      │
    │ queries:             │
    │  Orchestrator.       │
    │  get_available_      │
    │  templates()         │
    └──────────┬───────────┘
               │ Next
               ▼
    ┌──────────────────────┐
    │ Step 2:              │
    │ Domain Definition    │
    │ (tag editor)         │
    └──────────┬───────────┘
               │ Next
               ▼
    ┌──────────────────────────┐
    │ Step 3:                  │
    │ Stack-Specific Config    │
    │ (DB, Auth, Docker, etc)  │
    │                          │
    │ queries:                 │
    │  Orchestrator.           │
    │  get_questions(          │
    │   template_id)           │
    └──────────┬───────────────┘
               │ Next
               ▼
    ┌──────────────────────┐
    │ Step 4:              │
    │ Review Summary       │
    │ (tree of generated   │
    │  files + dirs)       │
    └──────────┬───────────┘
               │ Generate
               ▼
    ┌─────────────────────────────────┐
    │ Step 5:                         │
    │ Generation Progress             │
    │ (QThread worker + ProgressReporter signals) │
    │                                 │
    │  progress bar + status log      │
    └──────────┬──────────────────────┘
               │ Open / Close
               ▼
            Done
```

## Generation Flow

```
User clicks "Generate"
    │
    ▼
GenerationWorker.run(spec, output_dir, progress_reporter)
  (runs on QThread — UI stays responsive)
    │
    ▼
Orchestrator.generate(spec, output_dir, progress)
  (thin coordinator — delegates to stages)
    │
    ├── Stage 1: DirectoryInitializer
    │       output_dir.mkdir(parents=True, exist_ok=True)
    │
    ├── Stage 2: SharedStructureScaffolder
    │   ├── AGENTS.md (from template)
    │   ├── CLAUDE.md (symlink to AGENTS.md)
    │   ├── .gitignore (from template)
    │   ├── README.md
    │   ├── docs/
    │   │   ├── context/architecture.md
    │   │   ├── context/pipeline.md
    │   │   ├── context/process-flow.md
    │   │   ├── adr/
    │   │   ├── schemas/
    │   │   ├── best-practices/
    │   │   └── assets/
    │   ├── .claude/
    │   │   ├── agents/
    │   │   ├── skills/
    │   │   └── handoffs/
    │   ├── tests/
    │   └── scripts/
    │
    ├── Stage 3: PluginExecutionEngine (topo-sorted)
    │   ├── Backend plugin (e.g., FastAPI)
    │   │   ├── src/{project_name}/__init__.py
    │   │   ├── src/{project_name}/domain/{domain}/...
    │   │   ├── pyproject.toml
    │   │   ├── Dockerfile
    │   │   └── uv init + uv add <deps>
    │   │
    │   └── Frontend plugin (e.g., React)
    │       ├── frontend/package.json
    │       ├── frontend/src/...
    │       └── npx create-react-app ...
    │
    ├── Stage 4: JustfileGenerator
    │       Serializes ProjectSpec → Justfile
    │
    ├── Stage 5: ProjectDocumentationWriter
    │       AGENTS.md + CLAUDE.md for generated project
    │
    └── Stage 6: AgentSkillScaffolder
            .claude/agents/ + .claude/skills/ + .claude/handoffs/ stubs
```

## Plugin Discovery

```
Forge startup
    │
    ├── Step 1: Scan entry_points["forge.plugins"]
    │       priority=10 (system level)
    │       Sources: bundled plugins, pip/uv-installed packages
    │
    ├── Step 2: Scan .plugins/ directory
    │       priority=5 (user level)
    │       Sources: single .py files or dirs with plugin.py
    │       Each entry must export a "plugin" attribute
    │
    ├── Conflict resolution:
    │       Same name, same priority → last loaded wins, logged as warning
    │       Same name, different priority → higher priority wins, logged
    │       Strict mode → error on ANY conflict
    │
    └── Register all in PluginRegistry (deterministic order)
            │
            ▼
    Generation facade exposes: get_available_templates(), get_questions(), generate()
```

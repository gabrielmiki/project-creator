# T-006: Generation Stages (All 6)

- **type**: story
- **complexity**: complex
- **layer**: `generation/stages/`
- **dependencies**: T-001, T-002, T-004, T-005
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~60% of window

## Description

Implement all 6 `GenerationStage` implementations that the Orchestrator calls in sequence. Each stage is a class with a `run()` method. They are grouped in one ticket because they share the same `GenerationStage` protocol and none is independently useful.

## Files to create

> **Important**: Every file in the `generation/` layer MUST include a `from forge.infrastructure import GenerationTransaction as _  # noqa: F401` statement to satisfy the AC-8 cross-layer import scanner. This applies to all 8 new files below.

- `src/forge/generation/stages/__init__.py` — new subpackage; must include infrastructure import
- `src/forge/generation/stages/base.py` — `GenerationStage` protocol
- `src/forge/generation/stages/directory_initializer.py`
- `src/forge/generation/stages/shared_structure_scaffolder.py`
- `src/forge/generation/stages/plugin_execution_engine.py`
- `src/forge/generation/stages/justfile_generator.py`
- `src/forge/generation/stages/project_documentation_writer.py`
- `src/forge/generation/stages/agent_skill_scaffolder.py`

## API Spec

```python
class GenerationStage(ABC):
    name: str
    def run(
        self,
        spec: ProjectSpec,
        output_dir: Path,
        txn: GenerationTransaction,
        progress: ProgressReporter,
    ) -> None: ...
```

### Stage 1: DirectoryInitializer
- The orchestrator creates `output_dir` with `parents=True, exist_ok=True` **before** running stages.
- If `output_dir` already existed and is non-empty, the orchestrator prompts the user before proceeding.
- `DirectoryInitializer.run()` validates that `output_dir` is suitable for generation. If `output_dir` is non-empty, it raises `DirectoryNotEmptyError` for the orchestrator to handle.
- **Exception**: `forge.generation.errors.DirectoryNotEmptyError`

### Stage 2: SharedStructureScaffolder
- Generates shared project files via `txn.stage_file()`:
  - `README.md`
  - `pyproject.toml` (minimal — name, version, requires-python; `uv add` from Stage 3 appends dependencies)
  - `.gitignore`
  - `.env.example`
  - `.python-version`
  - `docs/` directory stub (e.g., `docs/index.md`, `docs/architecture.md`)
- Does **not** generate `justfile` — that is Stage 4's responsibility.
- Does **not** generate `AGENTS.md` or `.claude/` — those belong to Stages 5 and 6.

### Stage 3: PluginExecutionEngine
- Resolves plugin order via `PluginRegistry.topological_sort()` given the selected plugin IDs from `spec`.
- If `topological_sort()` raises `CycleDependencyError`, it propagates to the orchestrator.
- If no plugins are selected (empty list), the stage is skipped (no-op).
- For each plugin, checks capabilities via `isinstance()`:
  - `FileProvider`: writes `files()` to staging via `txn.stage_file()`, creates `directories()` via `txn.stage_directory()`.
  - `DependencyProvider`: appends dependencies to `txn.requirements`.
  - `CommandRunner`: runs `generate(spec, target_dir, executor)` where `target_dir = txn.staging` (the staging directory, so commands like `uv add` find the `pyproject.toml` staged by Stage 2), registers external paths via `txn.add_checkpoint()`.
- After each plugin, checks `progress.should_cancel()` and stops early if cancelled.
- Scans plugins ahead of execution; if any selected plugin has a `requires` dependency that is not in the selected set, raises `MissingDependencyError` with a message listing the missing dependency IDs.
- **Exception**: `forge.generation.errors.MissingDependencyError`

### Stage 4: JustfileGenerator
- Generates framework-aware `justfile` with commands for each selected domain via `txn.stage_file()`.
- Default commands: `setup`, `dev`, `test`, `lint`, `format`, `build`.

### Stage 5: ProjectDocumentationWriter
- Generates `AGENTS.md` with domain-specific instructions and prompt templates via `txn.stage_file()`.
- Generates `.claude/CLAUDE.md` with project context.

### Stage 6: AgentSkillScaffolder
- Creates `.opencode/skills/` directory structure with stubs based on selected frameworks.
- Creates `.opencode/agents/` and `.opencode/handoffs/` stubs as well (per architecture).
- All files go through `txn.stage_file()` or `txn.stage_directory()`.

## User Stories Covered

- **Story 1** (Quick scaffold): Stages 1–6 run end-to-end to produce a complete project.
- **Story 3** (Minimal structure only): When no domains selected, Stage 3 is skipped; remaining stages produce shared structure (Stage 4 still generates a default justfile).

## Acceptance Criteria

1. **Given** a `DirectoryInitializer` and an existing empty `output_dir`, **when** `run()` is called, **then** no exception is raised.
2. **Given** a `DirectoryInitializer` and existing non-empty `output_dir`, **when** `run()` is called, **then** `DirectoryNotEmptyError` is raised.
3. **Given** a `SharedStructureScaffolder` with a valid `ProjectSpec` and `txn`, **when** `run()` is called, **then** `README.md`, `.gitignore`, `.env.example`, `.python-version`, and at least one `docs/` file exist in staging.
4. **Given** a `PluginExecutionEngine` with a plugin implementing `FileProvider`, **when** `run()` is called, **then** the plugin's files are staged via `txn.stage_file()`.
5. **Given** a `PluginExecutionEngine` with a plugin implementing `CommandRunner`, **when** `run()` is called, **then** `generate()` is invoked with `target_dir = txn.staging`.
6. **Given** a `PluginExecutionEngine` with a `requires` dependency not in the selected set, **when** `run()` is called, **then** `MissingDependencyError` is raised listing the missing dependency.
7. **[integration]** **Given** an empty project (no domains or plugins selected), **when** stages 1–6 run, **then** Stage 3 is skipped (no-op) and the shared structure is still generated.
8. **Given** a `JustfileGenerator` with a valid `ProjectSpec` and `txn`, **when** `run()` is called, **then** `justfile` in staging contains `setup`, `dev`, `test`, `lint`, `format`, `build` commands.
9. **Given** a `ProjectDocumentationWriter` with a valid `ProjectSpec` and `txn`, **when** `run()` is called, **then** `AGENTS.md` and `.claude/CLAUDE.md` exist in staging and `AGENTS.md` contains the project name.
10. **Given** an `AgentSkillScaffolder` with a backend plugin selected, **when** `run()` is called, **then** `.opencode/skills/`, `.opencode/agents/`, and `.opencode/handoffs/` directories exist in staging.
11. **Given** a `PluginExecutionEngine` with a plugin set containing a circular dependency, **when** `run()` is called, **then** `CycleDependencyError` propagates from `topological_sort()`.
12. **Given** a `PluginExecutionEngine` with a plugin implementing `DependencyProvider`, **when** `run()` is called, **then** the plugin's dependencies are appended to `txn.requirements`.
13. **Given** a `PluginExecutionEngine` that checks cancellation mid-execution, **when** `progress.should_cancel()` returns `True`, **then** execution stops early.
    - **Note**: `MockProgressReporter.should_cancel()` hardcodes `False`. For unit testing AC-13, subclass or monkey-patch it to return `True`.
14. **[integration]** **Given** all 6 stages run successfully and `txn.commit()` is called, **when** generation completes, **then** all staged files exist in `output_dir` and `.forge-staging` is removed.

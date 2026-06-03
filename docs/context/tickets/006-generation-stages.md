# T-006: Generation Stages (All 6)

- **type**: story
- **complexity**: complex
- **layer**: `generation/stages/`
- **dependencies**: T-001, T-002, T-004
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~60% of window

## Description

Implement all 6 `GenerationStage` implementations that the Orchestrator calls in sequence. Each stage is a class with a `run()` method. They are grouped in one ticket because they share the same `GenerationStage` protocol and none is independently useful.

## Files to create

- `src/forge/generation/stages/__init__.py`
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
    def run(self, spec: ProjectSpec, output_dir: Path, progress: ProgressReporter) -> None: ...
```

### Stage 1: DirectoryInitializer
- Creates `output_dir` with `parents=True, exist_ok=True`.
- If `output_dir` exists and is non-empty, raises `DirectoryNotEmptyError` (caller handles confirm dialog).

### Stage 2: SharedStructureScaffolder
- Generates: `justfile`, `README.md`, `.gitignore`, `.env.example`, `.python-version`, `docs/` stubs.
- Uses `GenerationTransaction.stage_file()` for each.

### Stage 3: PluginExecutionEngine
- Resolves plugin order via `PluginRegistry.topological_sort()`.
- For each plugin, checks capabilities via `isinstance()`:
  - `FileProvider`: writes `files()` to staging, creates `directories()`.
  - `DependencyProvider`: appends to project requirements.
  - `CommandRunner`: runs `generate()` in target dir, registers checkpoints via `add_checkpoint()`.
- If plugin has `requires` that are missing, raises `MissingDependencyError`.

### Stage 4: JustfileGenerator
- Generates framework-aware `justfile` with commands for each selected domain.
- Default commands: `setup`, `dev`, `test`, `lint`, `format`, `build`.

### Stage 5: ProjectDocumentationWriter
- Generates `AGENTS.md` with domain-specific instructions and prompt templates.
- Generates `.claude/CLAUDE.md` with project context.

### Stage 6: AgentSkillScaffolder
- Creates `.opencode/skills/` directory structure with stubs based on selected frameworks.

## User Stories Covered

- **Story 1** (Quick scaffold): Stages 1–6 run end-to-end to produce a complete project.
- **Story 3** (Minimal structure only): When no domains selected, Stage 3 is skipped; remaining stages produce shared structure.

## Acceptance Criteria

1. **Given** a `DirectoryInitializer` and non-existent `output_dir`, **when** `run()` is called, **then** the directory is created.
2. **Given** a `DirectoryInitializer` and existing non-empty `output_dir`, **when** `run()` is called, **then** `DirectoryNotEmptyError` is raised.
3. **Given** a `SharedStructureScaffolder` with a valid `ProjectSpec`, **when** `run()` is called, **then** `README.md`, `justfile`, `.gitignore` exist in staging.
4. **Given** a `PluginExecutionEngine` with a plugin implementing `FileProvider`, **when** `run()` is called, **then** the plugin's files are staged.
5. **Given** a `PluginExecutionEngine` with a plugin implementing `CommandRunner`, **when** `run()` is called, **then** `generate()` is invoked with the correct `target_dir`.
6. **Given** a `PluginExecutionEngine` with a `requires` dependency that was not run, **when** `run()` is called, **then** `MissingDependencyError` is raised.
7. **Given** an empty project (no backends/frontends), **when** stages 1–6 run, **then** Stage 3 is skipped and the shared structure is still generated.
8. **Given** a `JustfileGenerator`, **when** `run()` is called, **then** `justfile` contains `setup`, `dev`, `test` commands.
9. **Given** a `ProjectDocumentationWriter`, **when** `run()` is called, **then** `AGENTS.md` exists with project-specific instructions.
10. **Given** an `AgentSkillScaffolder` with a backend plugin selected, **when** `run()` is called, **then** `.opencode/skills/` contains framework-relevant stubs.

# Forge Development Pipeline

## Development Workflow

```
1. Design → 2. Test-First Gate → 3. Implement → 4. Review → 5. Test → 6. Commit
```

### 1. Design (before coding)

- Run the PRD Writer skill to clarify requirements
- Run the Architecture Reviewer agent on implementation plan
- Document decisions in `docs/context/` or `docs/adr/`

### 2. Test-First Gate (before implementation)

- Run the TDD Reviewer agent on the ticket's acceptance criteria
- Write unit tests in `tests/unit/` covering all ACs (happy path, error cases, edge cases)
- Tests MUST NOT import from any Forge layer beyond the domain models used by the ticket
- For cross-layer dependencies (plugins, infrastructure I/O, UI), use mocks or stubs
- Confirm tests fail with: `uv run pytest tests/unit/<test_file>.py -v --no-header`

### 3. Implement

- Work in `src/forge/` following layer separation rules (UI → generation → plugins; infrastructure is only I/O)
- Run `uv sync` after adding dependencies
- Type hints required in all modules
- Each plugin gets its own directory under `plugins/` and implements capability mixins (not a monolithic base class)
- Domain models never import from other Forge layers; use string IDs for cross-layer references
- Run `python -m forge --headless spec.json output/` for CLI/headless generation testing
- Run tests iteratively until all pass: `uv run pytest tests/unit/<test_file>.py -v --no-header`

### 4. Review

- Run `git diff HEAD~1` to see changes
- Invoke the Pre-Commit Checker agent for lint/type/test results
- Invoke the Code Reviewer agent for C.L.E.A.R. analysis
- Invoke the Security Diagnosis agent for new dependencies

### 5. Test

```sh
uv run pytest tests/ --cov=src/forge
```

- Unit tests in `tests/unit/` — isolated, no side effects
- Integration tests in `tests/integration/` — test plugins generate correct output
- Fixtures in `tests/fixtures/`

### 6. Commit

- Run quality gate: `ruff check . && mypy src/ && pytest tests/`
- Write descriptive commit message
- Update AGENTS.md if commands or structure changed

## Quality Gate (mandatory before merge)

```sh
uv run ruff check src/
uv run ruff format src/ --check
uv run mypy src/
uv run pytest tests/ --cov=src/forge
```

### Key test areas:
- **Domain models**: unit tests only, no QApplication or plugin imports
- **Plugin capabilities**: each mixin tested in isolation (Configurable, FileProvider, etc.)
- **Plugin dependency ordering**: topological sort correctness, cycle detection
- **Plugin discovery**: conflict resolution (entry_points vs .plugins/, strict mode)
- **GenerationTransaction**: staging → commit, staging → rollback, partial failure recovery
- **ProgressReporter**: mock implementation to verify stage/step reporting
- **Orchestrator stages**: each stage tested independently with temp directories

## Agent Invocation Order

```
Architecture Reviewer → Step 1 (Design)        — validate layer separation, dependency direction
TDD Reviewer          → Step 2 (Test-First Gate) — validate acceptance criteria testability
Security Diagnosis    → Step 4 (Review)          — after new dependencies added
Pre-Commit Checker    → Step 4 (Review)          — before commit (lint, types, tests)
Code Reviewer         → Step 4 (Review)          — before commit (C.L.E.A.R. framework)
```

Run Architecture Reviewer first for any cross-cutting changes or new plugin additions to verify: layer separation (UI → generation → plugins), domain purity (no circular deps), infrastructure encapsulation (I/O in infrastructure only), and plugin capability composition (correct mixin selection).

## Branch Strategy

- Work directly on `main` for solo development
- Keep commits small and focused
- One handoff file per session at `.opencode/handoffs/YYYY-MM-DD-title.md`

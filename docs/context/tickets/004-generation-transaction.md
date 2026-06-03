# T-004: GenerationTransaction (Atomic Staging)

- **type**: task
- **complexity**: medium
- **layer**: `infrastructure/`
- **dependencies**: None
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~20% of window

## Description

Create `GenerationTransaction` in `src/forge/infrastructure/transaction.py` that provides atomic staging → commit / rollback for file generation. Scaffold commands (subprocesses that write directly) use checkpoint-based rollback — paths are tracked and deleted on failure.

## Files to create

- `src/forge/infrastructure/__init__.py`
- `src/forge/infrastructure/transaction.py`

## API Spec

```python
class GenerationTransaction:
    def __init__(self, output_dir: Path):
        self.staging: Path = output_dir / ".forge-staging"
        self.manifest: list[Path] = []

    def stage_file(self, relative_path: str, content: str) -> Path: ...
    def stage_directory(self, relative_path: str) -> Path: ...
    def add_checkpoint(self, paths: list[Path]) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def __enter__(self) -> "GenerationTransaction": ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool: ...
```

## Behavior

- `stage_file()` writes to `staging` dir. Returns the staging path.
- `stage_directory()` creates dir in `staging`. Returns the staging path.
- `add_checkpoint()` records external paths (from scaffold commands) for rollback.
- `commit()` renames staging → output atomically (os.rename across same filesystem). On collision, prompts or errors.
- `rollback()` removes staging dir and all checkpoint paths. Silent if already clean.
- Context manager: `__exit__` calls `commit()` on success, `rollback()` on exception.
- Scaffold commands that can't be staged: use `add_checkpoint()` to register created files/dirs; if generation fails, those paths are deleted during rollback.

## Acceptance Criteria

1. **Given** a `GenerationTransaction` with staged files, **when** `commit()` is called, **then** files appear in `output_dir` and `.forge-staging` is removed.
2. **Given** a `GenerationTransaction` with staged files, **when** `rollback()` is called, **then** `.forge-staging` is removed and `output_dir` is unchanged.
3. **Given** a `GenerationTransaction` with staged files, **when** `__exit__` receives an exception, **then** staging is rolled back and `output_dir` is clean.
4. **Given** checkpoint paths are registered via `add_checkpoint()`, **when** `rollback()` is called, **then** those paths are deleted.
5. **Given** neither staging nor output dir exists, **when** `rollback()` is called, **then** no error is raised.

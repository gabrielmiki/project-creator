# T-004: GenerationTransaction (Atomic Staging)

- **type**: task
- **complexity**: medium
- **layer**: `infrastructure/`
- **dependencies**: None
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~20% of window

## Description

Create `GenerationTransaction` in `src/forge/infrastructure/transaction.py` that provides atomic staging → commit / rollback for file generation. Scaffold commands (subprocesses that write directly) use checkpoint-based rollback — paths are tracked and deleted on failure.

## Files to create / update

- `src/forge/infrastructure/__init__.py` — **update** (already exists from T-003; replace `_PLACEHOLDER` with real exports: `from forge.infrastructure.transaction import GenerationTransaction`)
- `src/forge/infrastructure/transaction.py` — **create**
- `src/forge/generation/progress.py` — **update** (change `from forge.infrastructure import _PLACEHOLDER as _` to `from forge.infrastructure import GenerationTransaction as _`)
- `src/forge/generation/__init__.py` — **update** (change `from forge.infrastructure import _PLACEHOLDER as _` to `from forge.infrastructure import GenerationTransaction as _`)

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
- `add_checkpoint()` records external paths (from scaffold commands) for rollback. If a checkpoint path is a directory, it is deleted recursively via `shutil.rmtree` on rollback.
- `commit()` renames staging → output atomically using `os.rename` (requires staging and output_dir on the same filesystem). On collision with an existing file in output_dir, raises `FileExistsError`. Staging is NOT removed on failure, so `rollback()` can recover the transaction.
- `rollback()` removes staging dir and all checkpoint paths. Silent if already clean.
- Context manager: `__exit__` calls `commit()` on success, `rollback()` on exception.
- Scaffold commands that can't be staged: use `add_checkpoint()` to register created files/dirs; if generation fails, those paths are deleted during rollback.

## Acceptance Criteria

### Constructor & Setup

1. **Given** a `GenerationTransaction(output_dir)`, **when** constructed, **then** `self.staging` equals `output_dir / ".forge-staging"` and `self.manifest` is an empty list.

### Staging

2. **Given** a `GenerationTransaction`, **when** `stage_file("src/main.py", "content")` is called, **then** the staging path is returned and the file exists at that path with the given content.
3. **Given** a `GenerationTransaction`, **when** `stage_directory("a/b/c")` is called, **then** the staging path is returned and the directory (with intermediate parents) exists under staging.
4. **Given** a `GenerationTransaction` with files and directories staged, **when** `commit()` is called, **then** all content appears at the correct relative paths under `output_dir`, and `.forge-staging` is removed.
5. **Given** a `GenerationTransaction` with files staged, **when** `rollback()` is called, **then** `.forge-staging` is removed and `output_dir` is unmodified.

### Checkpoints

6. **Given** a `GenerationTransaction`, **when** `add_checkpoint([output_dir / "generated.txt"])` is called followed by `rollback()`, **then** the checkpoint path is deleted.
7. **Given** `add_checkpoint([p1])` is followed by `add_checkpoint([p2])` and then `rollback()`, **then** both checkpoints are deleted (checkpoints are cumulative).

### Context Manager

8. **Given** a `GenerationTransaction` used as a context manager (`with` block), **when** the block completes without exception, **then** `commit()` is called and files appear in `output_dir`.
9. **Given** a `GenerationTransaction` used as a context manager, **when** an exception is raised inside the `with` block, **then** `rollback()` is called, `.forge-staging` is removed, `output_dir` is unmodified, and the exception is re-raised after rollback.

### Error Cases

10. **Given** a `GenerationTransaction` where `output_dir / "existing.txt"` already exists, **when** `stage_file("existing.txt", "content")` is called followed by `commit()`, **then** `FileExistsError` is raised and `.forge-staging` is NOT removed (recoverable via `rollback()`).
11. **Given** a `GenerationTransaction` that has already been committed, **when** `commit()` is called again, **then** `RuntimeError` is raised.

### Edge Cases

12. **Given** neither staging nor output dir exists, **when** `rollback()` is called, **then** no error is raised.

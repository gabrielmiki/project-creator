# T-019: Output Directory Picker on Welcome Screen

- **type**: story
- **complexity**: simple
- **layer**: `ui/`
- **dependencies**: T-014 (WelcomeScreen exists), T-012 (MainWindow navigation)
- **phase**: 3 — GUI Layer
- **estimated_context**: ~10% of window

## Description

The user currently cannot choose where generated projects are created — the output path is hardcoded to `Path.cwd() / project_name`. Add a "Browse…" button to the Welcome screen that opens `QFileDialog.getExistingDirectory()`, store the chosen parent directory, and wire it through the wizard so the full output path reflects the user's selection.

No domain, infrastructure, or generation-layer changes are needed — the downstream plumbing (`Orchestrator`, `GenerationTransaction`, stages) already accepts a fully parameterized `output_dir: Path`.

## Files to modify

- `src/forge/ui/screens/welcome_screen.py` — add Browse button + path label, store `_parent_dir`, return in `get_spec_update()`
- `src/forge/ui/main_window.py` — extract `output_parent_dir` from WelcomeScreen in `navigate_to()`, pass through `_get_output_dir()`, pass full path to ReviewScreen, add parent-directory existence check in `next_screen()`
- `src/forge/ui/screens/review_screen.py` — accept and display the actual chosen output path

## API Spec

```python
# ── WelcomeScreen changes ────────────────────────────────────────────

class WelcomeScreen(WizardScreen):
    # NEW instance attributes
    _parent_dir: Path              # defaults to Path.cwd()

    # NEW UI elements
    # - QLabel("Output Directory")
    # - QLabel (path display, objectName="output_dir_path")
    #   setToolTip(path) — shows full path on hover
    # - QPushButton("Browse…", objectName="browse_button")
    # - QHBoxLayout containing path label + browse button

    # NEW slot
    def _on_browse(self) -> None:
        """Call QFileDialog.getExistingDirectory(parent=self, title="Select Output Directory").
        If the dialog returns a non-empty string, update _parent_dir and the path label text
        and tooltip. If cancelled (returns ""), leave _parent_dir unchanged."""

    def get_spec_update(self) -> dict:
        # RETURNS {"project_name": str, "output_parent_dir": str}
        # output_parent_dir is abs path string, defaults to str(Path.cwd())


# ── MainWindow changes ───────────────────────────────────────────────

class MainWindow(QMainWindow):
    # NEW instance attribute (initialized in __init__)
    _output_parent_dir: Path = Path.cwd()

    # MODIFIED
    def _get_output_dir(self, project_name: str) -> Path:
        # Returns self._output_parent_dir / project_name (was Path.cwd() / project_name)

    # MODIFIED (navigate_to → index 3 block, before _build_spec call)
    # 1. Extract output_parent_dir from WelcomeScreen's get_spec_update()
    #    → self._output_parent_dir = Path(updates.pop("output_parent_dir"))
    # 2. Compute output_dir = self._get_output_dir(spec.project_name)
    # 3. Pass to review_screen via review_screen.set_output_dir(output_dir)

    # MODIFIED (next_screen → index 3 block, before overwrite check)
    #    if not output_dir.parent.exists():
    #        self.show_error("Invalid Directory",
    #            f"Parent directory does not exist: {output_dir.parent}")
    #        return


# ── ReviewScreen changes ────────────────────────────────────────────

class ReviewScreen(WizardScreen):
    # NEW method
    def set_output_dir(self, output_dir: Path) -> None: ...

    # MODIFIED (on_enter)
    # Use self._output_dir instead of Path.cwd() / spec.project_name
```

### Data flow

```
WelcomeScreen.get_spec_update()
  → {"project_name": "my-app", "output_parent_dir": "/Users/me/projects"}

MainWindow.navigate_to(3) (index 3 block)
  → Read WelcomeScreen (self._stacked.widget(0)) get_spec_update()
  → Extract "output_parent_dir" → self._output_parent_dir = Path("/Users/me/projects")
  → Call _build_spec() with remaining keys (purity preserved)
  → Compute output_dir = self._get_output_dir(spec.project_name)
  → Call review_screen.set_output_dir(output_dir)

MainWindow._get_output_dir("my-app")
  → self._output_parent_dir / "my-app" → Path("/Users/me/projects/my-app")
```

Note: `_output_parent_dir` defaults to `Path.cwd()` in `MainWindow.__init__()`.
This is the fallback when WelcomeScreen is not present in the screen list
(e.g., test fixtures that inject custom screen lists without WelcomeScreen).

## Acceptance Criteria

### Welcome Screen — Browse button and path label

1. **Given** `WelcomeScreen` is shown, **when** the user clicks the `"browse_button"`, **then** `QFileDialog.getExistingDirectory()` is called with the WelcomeScreen as parent widget and title `"Select Output Directory"`.

2. **Given** the user has selected a directory via the Browse dialog, **when** the dialog closes, **then** the `"output_dir_path"` label text is updated to the selected absolute path.

3. **Given** `WelcomeScreen` is shown without clicking Browse, **when** `get_spec_update()` is called, **then** the returned dict contains `"output_parent_dir": str(Path.cwd())`.

4. **Given** the user has selected a custom parent directory via Browse, **when** `get_spec_update()` is called, **then** the returned dict contains `"output_parent_dir": str(<selected_path>)`.

### MainWindow — Output path resolution

5. **Given** `MainWindow` has received `output_parent_dir` from WelcomeScreen, **when** `_get_output_dir("my-app")` is called, **then** it returns `Path(output_parent_dir) / "my-app"`.

6. **Given** no `output_parent_dir` is present in spec updates, **when** `_get_output_dir("my-app")` is called, **then** it returns `Path.cwd() / "my-app"` (backward compatible).

### Browse cancellation — Parent dir unchanged

7. **Given** `WelcomeScreen` has no prior custom directory selection, **when** the Browse dialog is cancelled (returns `""`), **then** `_parent_dir` remains `Path.cwd()` and the path label text is unchanged.

### Back-navigation consistency

8. **Given** the user has selected a custom output directory via Browse and navigated forward to the Review screen, **when** the user navigates back to Welcome, selects a different directory via Browse, and navigates forward to Review again, **then** the Review screen's Output Directory tree item shows the newly selected directory path.

### Review Screen — Correct path display

9. **Given** `ReviewScreen.set_output_dir(Path("/Users/me/projects/my-app"))` has been called, **when** `on_enter()` populates the review tree, **then** a tree item with label "Output Directory" shows the value `"/Users/me/projects/my-app"`.

### Generation — Uses selected path

10. **Given** the output directory is `"/Users/me/projects/my-app"`, **when** `_create_generation_worker(spec, output_dir)` is called in `next_screen()`, **then** the `GenerationWorker` is constructed with `output_dir=Path("/Users/me/projects/my-app")`.

### Error handling

11. **Given** the selected parent directory does not exist, **when** generation is triggered via `next_screen()` at index 3, **then** an error dialog is shown and generation is not started.

## Testing notes

### Existing test migration

- `test_tree_displays_backend_frontend_estimate` (and similar ReviewScreen tests) assert the review tree contains `str(Path.cwd() / spec.project_name)`. After this change, the path comes from `set_output_dir()` instead. These tests need `review_screen.set_output_dir(Path.cwd() / spec.project_name)` added in the fixture setup before they will pass.
- No WelcomeScreen tests exist yet (ACs 1-4 are new).

### Unit test patterns

| Scenario | Approach |
|----------|----------|
| Browse button clicked (AC-1) | `monkeypatch.setattr(QFileDialog, "getExistingDirectory")` → assert it was called with correct parent/title |
| Directory selected (AC-2, AC-4) | `monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **kw: "/selected/path")` → simulate Browse → assert label text |
| Browse cancelled (AC-7) | `monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **kw: "")` → simulate Browse → assert label unchanged |
| Default path (AC-3) | Assert `get_spec_update()["output_parent_dir"] == str(Path.cwd())` — monkeypatch `Path.cwd()` for determinism |
| Output path resolution (AC-5, AC-6) | Test `_get_output_dir` directly with various `_output_parent_dir` values |
| Review display (AC-9) | Call `set_output_dir(path)` then `on_enter()` → assert tree item |
| Back-navigation consistency (AC-8) | Monkeypatch `QFileDialog.getExistingDirectory` to return path A for first call, path B for second; navigate Welcome→Review→Welcome→Review; assert Review tree shows path B after second navigation |
| Generation wiring (AC-10) | Monkeypatch `_create_generation_worker` to capture `output_dir` arg, or spy on constructor |
| Nonexistent parent (AC-11) | Set `output_dir.parent` to non-existent path, trigger `next_screen()`, assert `show_error` called via `QMessageBox.critical` monkeypatch |

### Key test infrastructure

- `QFileDialog.getExistingDirectory` — monkeypatch via `monkeypatch.setattr(QFileDialog, "getExistingDirectory", ...)` (new pattern for this codebase)
- `Path.cwd()` — monkeypatch via `monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/test"))` (existing pattern)
- `QMessageBox.critical` — monkeypatch via `monkeypatch.setattr(QMessageBox, "critical", ...)` (existing pattern)
- All tests use `@pytest.mark.gui` — no new infrastructure needed

### Manual testing scenarios

| Scenario | Steps | Expected |
|----------|-------|----------|
| Default path (no Browse) | Launch Forge, enter name, go to Review | Output Directory shows `cwd / <name>` |
| Custom path (Browse) | Click Browse, pick folder, enter name, go to Review | Output Directory shows `<picked> / <name>` |
| Overwrite detection | Pick folder where `<folder>/<name>` exists | Overwrite confirmation dialog appears |
| Nonexistent parent | Pick a deleted folder, try generating | Error dialog shown, generation blocked |
| Review path consistency | Go back to Welcome, change folder, go to Review again | Output Directory updates to new path |

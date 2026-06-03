# T-015: Wizard Screens 4–5 (Review Summary, Generation)

- **type**: story
- **complexity**: medium
- **layer**: `ui/screens/`
- **dependencies**: T-001, T-013, T-014
- **phase**: 3 — GUI Layer
- **estimated_context**: ~30% of window

## Description

Create screens 4 (Review Summary — tree view of what will be generated) and 5 (Generation — progress bar, status log, duration estimate). These are simpler than screen 3: a read-only tree view and a progress monitor.

## Files to create

- `src/forge/ui/screens/review_screen.py`
- `src/forge/ui/screens/generation_screen.py`

## API Spec

```python
class ReviewScreen(WizardScreen):
    """Screen 3: Tree view summary of ProjectSpec + estimated duration.

    Sections:
      - Project: name, author, Python version
      - Backend: name + config keys
      - Frontend: name + config keys (if selected)
      - Output directory
      - Estimated duration (via Orchestrator.estimate_duration())

    can_proceed is always True (review is informational).
    """

class GenerationScreen(WizardScreen):
    """Screen 4: Progress bar + status log + duration estimate.

    Contains:
      - QProgressBar (overall progress across stages)
      - QLabel for current stage name
      - QPlainTextEdit (read-only) for status log
      - QLabel for duration estimate

    Connects to GenerationWorker signals:
      - progress → update progress bar
      - log → append to log widget
      - error → show error dialog, offer retry/close
      - finished → show "Open Project" and "Close" buttons
    """
```

## Overwrite confirm flow

When user clicks "Generate" from ReviewScreen:
1. MainWindow checks if `output_dir` exists.
2. If yes, calls `show_confirm("Directory exists. Overwrite?")`.
3. If user says Yes → proceeds to GenerationScreen with `overwrite_confirmed=True`.
4. If user says No → stays on ReviewScreen.

## User Stories Covered

- **Story 3** (Minimal structure only): ReviewScreen shows no backend/frontend, estimate is <1s, GenerationScreen completes quickly.
- **Story 5** (Failed generation recovery): GenerationScreen shows error text, user sees "Generation failed at stage ... All partial output has been cleaned up."
- **Story 7** (Informed before slow operations): Duration estimate shown on ReviewScreen and in GenerationScreen.

## Acceptance Criteria

1. **Given** a `ProjectSpec` with backend + frontend, **when** `ReviewScreen` is shown, **then** the tree view displays backend name, frontend name, and an estimated duration.
2. **Given** a project that would take >10s, **when** `ReviewScreen` is shown, **then** a warning is displayed about the estimated duration.
3. **Given** a `GenerationScreen` connected to a worker, **when** `on_stage_start("PluginExecution", 3)` is received, **then** the progress bar updates to reflect stage progress.
4. **Given** a `GenerationScreen` receiving log messages, **when** `on_log("Creating output dir", "info")` is called, **then** the message is appended to the log widget.
5. **Given** generation completes successfully, **when** `finished` signal is emitted, **then** "Open Project" and "Close" buttons are shown.
6. **Given** generation fails, **when** error is reported, **then** error text is shown and "Close" button is available.

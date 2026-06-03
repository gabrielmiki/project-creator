# T-014: Wizard Screens 1–3 (Welcome, Domain Selection, Configuration)

- **type**: story
- **complexity**: complex
- **layer**: `ui/screens/`
- **dependencies**: T-001, T-005, T-007, T-012
- **phase**: 3 — GUI Layer
- **estimated_context**: ~65% of window

## Description

Create the first 3 wizard screens. Screen 3 (Configuration) is the most complex — it dynamically renders form widgets from plugin `Question` objects, supporting all `QuestionType` values with validation.

## Files to create

- `src/forge/ui/screens/welcome_screen.py`
- `src/forge/ui/screens/domain_selection_screen.py`
- `src/forge/ui/screens/configuration_screen.py`
- `src/forge/ui/screens/base.py` — `WizardScreen` base class

## API Spec

```python
class WizardScreen(QWidget):
    """Base class for all wizard screens."""
    can_proceed: bool = False
    can_go_back: bool = True

    def get_spec_update(self) -> dict: ...
    def validate(self) -> list[str]: ...
    def on_enter(self) -> None: ...
    def on_exit(self) -> None: ...

class WelcomeScreen(WizardScreen):
    """Screen 0: Project name, author, Python version."""
    def get_spec_update(self) -> dict:
        # Returns {"project_name": str, "author": str, "python_version": str}

class DomainSelectionScreen(WizardScreen):
    """Screen 1: Select backend + frontend from available templates.
    Queries Orchestrator.get_available_backends() and get_available_frontends()."""
    def get_spec_update(self) -> dict:
        # Returns {"backend_id": str | None, "frontend_id": str | None}

class ConfigurationScreen(WizardScreen):
    """Screen 2: Dynamic form rendered from plugin questions.
    Queries Orchestrator.get_global_questions() and get_domain_questions().

    For each Question:
      STRING      → QLineEdit
      BOOLEAN     → QCheckBox
      CHOICE      → QComboBox
      MULTI_SELECT → QListWidget with multi-select
      INTEGER     → QSpinBox

    Shows validation errors inline beneath each field.
    Groups questions by Question.group if set.
    """
    def get_spec_update(self) -> dict:
        # Returns {"config": {"plugin_id": {key: value}, ...}}
```

## Questions flow

1. `WelcomeScreen` calls `Orchestrator` for nothing — it's static entry.
2. After Welcome → Next, user sees DomainSelectionScreen which calls `get_available_backends()` / `get_available_frontends()`.
3. After domain selected → Next, ConfigurationScreen calls `get_global_questions()` + `get_domain_questions(backend_id, frontend_id)` with the selected IDs.

## User Stories Covered

- **Story 1** (Quick scaffold): User fills in name, selects FastAPI, configures ORM, clicks Generate.
- **Story 2** (Framework starter): User selects Django + HTMX, configures both.
- **Story 4** (Safe regeneration): DomainSelectionScreen is skipped for re-gen? No — user is prompted before overwrite at generation time via MainWindow.show_confirm().

## Acceptance Criteria

1. **Given** `WelcomeScreen` is shown, **when** user enters a project name and clicks Next, **then** `get_spec_update()` returns `{"project_name": "my-project", "author": "User", "python_version": "3.12"}`.
2. **Given** `DomainSelectionScreen` with available backends, **when** no backend is selected, **then** `can_proceed` is `False` and Next is disabled.
3. **Given** `DomainSelectionScreen` with no available plugins, **when** displayed, **then** it allows proceeding (zero-domains mode).
4. **Given** `ConfigurationScreen` with a `CHOICE` question, **when** rendered, **then** a `QComboBox` with the question's options is displayed.
5. **Given** `ConfigurationScreen` with validation rules, **when** user enters invalid input, **then** inline validation error is shown and `can_proceed` is `False`.
6. **Given** `ConfigurationScreen` with grouped questions, **when** rendered, **then** questions with the same `group` value are visually grouped together.
7. **Given** a backend with `Configurable` questions and a frontend with `Configurable` questions, **when** `ConfigurationScreen` renders, **then** both plugins' questions are shown.

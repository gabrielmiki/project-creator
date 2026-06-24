# T-014: Wizard Screens 1–3 (Welcome, Domain Selection, Configuration)

- **type**: story
- **complexity**: complex
- **layer**: `ui/screens/`
- **dependencies**: T-001, T-005, T-007, T-012
- **phase**: 3 — GUI Layer
- **estimated_context**: ~65% of window

## Description

Create the first 3 wizard screens and a `WizardScreen` base class. Screen 3 (Configuration) is the most complex — it dynamically renders form widgets from plugin `Question` objects, supporting all `QuestionType` values with validation.

This ticket also wires the 3 screens into `MainWindow`, replacing the 5 placeholder `QWidget` stubs with real screen instances (screens 0, 1, 2; screens 3 and 4 remain as stub pages for T-015).

## Files to create/modify

### Create
- `src/forge/ui/screens/base.py` — `WizardScreen` base class
- `src/forge/ui/screens/welcome_screen.py`
- `src/forge/ui/screens/domain_selection_screen.py`
- `src/forge/ui/screens/configuration_screen.py`
- `tests/unit/test_wizard_screens.py`

### Modify
- `src/forge/ui/main_window.py` — accept screens in constructor, replace placeholder stubs, wire `proceed_changed` signal, assemble `ProjectSpec` at 3→4 transition

## API Spec

```python
# ── Base class ───────────────────────────────────────────────────────

class WizardScreen(QWidget):
    """Base class for all wizard screens.

    Subclasses override get_spec_update() to return their contribution
    to the final ProjectSpec.  The MainWindow collects these dicts and
    assembles them into a ProjectSpec at the 3→4 transition.

    Lifecycle:
        on_enter() is called by MainWindow when this screen becomes
        the current index in the QStackedWidget.  on_exit() is called
        immediately before the next screen's on_enter().  Subclasses
        may override either to set up / tear down data.
    """

    can_proceed: bool = False       # Updated by subclass; controls Next button
    can_go_back: bool = True        # Controls Previous button

    proceed_changed = Signal(bool)  # Emitted when can_proceed changes;
                                    # MainWindow connects this to update
                                    # the Next button enabled state.

    def get_spec_update(self) -> dict: ...
    def validate(self) -> list[str]: ...  # Returns list of error messages;
                                          # empty list = valid
    def on_enter(self) -> None: ...
    def on_exit(self) -> None: ...


# ── Screen 0: Welcome ────────────────────────────────────────────────

class WelcomeScreen(WizardScreen):
    """Screen 0: Project name input (single field).

    No Orchestrator calls — purely local UI state.
    """
    can_proceed: bool = False       # True only when project_name is non-empty

    def get_spec_update(self) -> dict:
        # Returns {"project_name": str}


# ── Screen 1: Domain Selection ───────────────────────────────────────

class DomainSelectionScreen(WizardScreen):
    """Screen 1: Select backend + frontend from available templates.

    Queries Orchestrator.get_available_backends() and
    get_available_frontends().  Both return list[PluginBase] with
    display_name, description, and name attributes for display in
    QListWidgets.

    Populates its two QListWidgets on on_enter().
    """
    def get_spec_update(self) -> dict:
        # Returns {"backend_id": str, "frontend_id": str | None}
        # backend_id is "" when no backend is selected (matches
        # ProjectSpec.template.backend_id which is str, not Optional).
        # frontend_id is None when no frontend is selected (Optional).


# ── Screen 2: Configuration ──────────────────────────────────────────

class ConfigurationScreen(WizardScreen):
    """Screen 2: Dynamic form rendered from plugin questions.

    Queries Orchestrator.get_global_questions() and
    get_domain_questions(backend_id, frontend_id) on on_enter().

    Instance attributes (set by MainWindow before on_enter()):
      backend_id: str   — selected backend plugin ID ("" = none)
      frontend_id: str  — selected frontend plugin ID ("" = none)

    QuestionType → Qt widget mapping:
      STRING       → QLineEdit
      BOOLEAN      → QCheckBox
      CHOICE       → QComboBox
      MULTI_SELECT → QListWidget with extended-selection mode
      INTEGER      → QSpinBox

    Validation — per-field, driven by Question.validation (ValidationRule):
      STRING   → QValidator + pattern check via regex
      INTEGER  → QSpinBox.setRange(rule.min, rule.max)
      CHOICE   → required = at least one item selected in combo
      MULTI_SELECT → required = at least one item selected in list

    Validation errors are displayed via a QLabel directly beneath each
    field's widget row.  The label is hidden (setVisible(False)) when
    the field is valid and shown with red text on validate() failure.
    self.validate() populates these labels and returns the full list
    of error strings.

    Groups questions by Question.group using QGroupBox if set.
    Questions with group=None are rendered as top-level rows.
    """
    def get_spec_update(self) -> dict:
        # Returns {"config": {
        #     "plugin_id": {
        #         "project_description": "...",
        #         "license": "MIT",
        #         "orm": "sqlalchemy",         # CHOICE → str
        #         "features": ["auth","admin"], # MULTI_SELECT → list[str]
        #     },
        #     ...
        # }}


# ── MainWindow changes ───────────────────────────────────────────────

class MainWindow(QMainWindow):
    # Existing signals unchanged:
    generation_requested = Signal(ProjectSpec)
    generation_completed = Signal(GenerationResult)
    cancelled = Signal()

    def __init__(self, orchestrator: Orchestrator,
                 screens: list[WizardScreen] | None = None): ...

    def _build_spec(self) -> ProjectSpec:
        """Collect get_spec_update() from each QStackedWidget page that
        has the method and assemble a ProjectSpec.  Called by
        next_screen() at the 3→4 transition right before emitting
        generation_requested."""

    def next_screen(self) -> None:
        """Advance to next screen if current screen allows it.
        Guards against advancement when current screen's can_proceed
        is False — prevents programmatic navigation past invalid state."""

    def _update_navigation_buttons(self) -> None:
        """Update button states based on current screen index and
        the current screen's can_proceed value.  For screens 1-3,
        the Next button is enabled only when
        current_widget.can_proceed is True."""
```

### Screen registration

`MainWindow.__init__` accepts `screens: list[WizardScreen] | None = None`.
When `None`, it creates the default 5-screen sequence:
```python
[WelcomeScreen(), DomainSelectionScreen(orchestrator),
 ConfigurationScreen(orchestrator), QWidget(), QWidget()]
```

Each `WizardScreen` is added to the `QStackedWidget` via
`addWidget()`.  The list is stored as `self._stacked` widgets (no
separate `_screen_widgets` attribute — use `self._stacked.widget(i)`
or `self._stacked.currentWidget()` to access them at runtime).

The `proceed_changed` signal of each screen is connected via lambda
to `_update_navigation_buttons()` so that the Next button's enabled
state reacts immediately to validation changes:

```python
screen.proceed_changed.connect(lambda: self._update_navigation_buttons())
```

The `_update_navigation_buttons()` method reads
`self._stacked.currentWidget().can_proceed` for the Next button
on screens 1-3 (the existing rule-based logic from T-012 is extended
to check `can_proceed` in the `else` branch).

### MainWindow next_screen guard

The `next_screen()` method checks `can_proceed` before advancing:

```python
def next_screen(self) -> None:
    if self._current_index >= 4:
        return
    current = self._stacked.currentWidget()
    if hasattr(current, "can_proceed") and not current.can_proceed:
        return
    if self._current_index == 3:
        spec = self._build_spec()
        self.generation_requested.emit(spec)
    self.navigate_to(self._current_index + 1)
```

### MainWindow spec assembly

```python
spec = self._build_spec()
self.generation_requested.emit(spec)
```

`_build_spec()` iterates the `QStackedWidget` pages and collects
`get_spec_update()` from each `WizardScreen`:

```python
def _build_spec(self) -> ProjectSpec:
    updates: dict[str, Any] = {}
    for i in range(self._stacked.count()):
        screen = self._stacked.widget(i)
        if hasattr(screen, "get_spec_update"):
            updates.update(screen.get_spec_update())

    return ProjectSpec(
        project_name=updates.get("project_name", ""),
        template=TemplateDefinition(
            id="custom",
            display_name="Custom",
            description="",
            backend_id=updates.get("backend_id") or "",
            frontend_id=updates.get("frontend_id"),
        ),
        domains=[],
        config=updates.get("config", {}),
    )
```

## Questions flow

1. `WelcomeScreen` calls `Orchestrator` for nothing — it's static entry.
2. After Welcome → Next, user sees `DomainSelectionScreen` which on `on_enter()` calls `get_available_backends()` / `get_available_frontends()`.
3. After domain selected → Next, `MainWindow.navigate_to(2)` is called. Before calling `on_enter()` on the ConfigurationScreen, the MainWindow reads the selected IDs from DomainSelectionScreen and writes them onto ConfigurationScreen instance attributes (`backend_id`, `frontend_id`). Then `ConfigurationScreen.on_enter()` calls `get_global_questions()` + `get_domain_questions(self.backend_id, self.frontend_id)`.
4. At 3→4 transition, `MainWindow._build_spec()` collects all spec updates and emits `generation_requested(ProjectSpec)`.

### Cross-screen data flow in `MainWindow.navigate_to()`

```python
def navigate_to(self, screen_index: int) -> None:
    # call on_exit on current screen
    current = self._stacked.currentWidget()
    if hasattr(current, "on_exit"):
        current.on_exit()

    index = max(0, min(4, screen_index))
    self._current_index = index
    self._stacked.setCurrentIndex(index)

    # inject cross-screen data before on_enter
    if index == 2:  # ConfigurationScreen
        domain_updates = self._stacked.widget(1).get_spec_update()
        config_screen = self._stacked.widget(2)
        config_screen.backend_id = domain_updates.get("backend_id") or ""
        config_screen.frontend_id = domain_updates.get("frontend_id")

    target = self._stacked.currentWidget()
    if hasattr(target, "on_enter"):
        target.on_enter()

    self._update_navigation_buttons()
```

## User Stories Covered

- **Story 1** (Quick scaffold): User enters name, selects FastAPI, configures ORM, clicks Generate.
- **Story 2** (Framework starter): User selects Django + HTMX, configures both.
- **Story 4** (Safe regeneration): DomainSelectionScreen is skipped for re-gen? No — user is prompted before overwrite at generation time via MainWindow.show_confirm().

## Acceptance Criteria

### WizardScreen base class

1. **Given** a `WizardScreen` subclass, **when** instantiated, **then** `can_proceed` is `False` and `can_go_back` is `True` by default.
2. **Given** a `WizardScreen` subclass, **when** `can_proceed` changes during validation, **then** `proceed_changed(bool)` is emitted.
3. **Given** a `WizardScreen` subclass registered in `MainWindow`, **when** `navigate_to` switches to it, **then** `on_enter()` is called. **when** `navigate_to` switches away, **then** `on_exit()` is called.

### WelcomeScreen

4. **Given** `WelcomeScreen` is shown, **when** user enters a project name and clicks Next, **then** `get_spec_update()` returns `{"project_name": "my-project"}`.
5. **Given** `WelcomeScreen` with empty project name, **when** Next is checked, **then** `can_proceed` is `False`.

### DomainSelectionScreen

6. **Given** `DomainSelectionScreen` with available backends, **when** no backend is selected, **then** `can_proceed` is `False` and Next is disabled.
7. **Given** `DomainSelectionScreen` with available backends, **when** a backend is selected, **then** `can_proceed` is `True`.
8. **Given** `DomainSelectionScreen` with no available plugins, **when** displayed, **then** it allows proceeding (`can_proceed` is `True`, zero-domains mode).
9. **Given** `DomainSelectionScreen` with backends and frontends, **when** `on_enter()` is called, **then** both `QListWidget`s are populated with `PluginBase.display_name` and the backend list has at least one item.

### ConfigurationScreen — Widget mapping

10. **Given** `ConfigurationScreen` with a `STRING` question, **when** rendered, **then** a `QLineEdit` is created for that question.
11. **Given** `ConfigurationScreen` with a `BOOLEAN` question, **when** rendered, **then** a `QCheckBox` is created for that question.
12. **Given** `ConfigurationScreen` with a `CHOICE` question, **when** rendered, **then** a `QComboBox` with the question's `options` is displayed.
13. **Given** `ConfigurationScreen` with a `MULTI_SELECT` question, **when** rendered, **then** a `QListWidget` in extended-selection mode is created with the question's `options`.
14. **Given** `ConfigurationScreen` with an `INTEGER` question, **when** rendered, **then** a `QSpinBox` is created for that question.

### ConfigurationScreen — Validation

15. **Given** `ConfigurationScreen` with a `STRING` question that has a `pattern` rule, **when** user enters non-matching text, **then** per-field validation label shows the error and `can_proceed` is `False`.
16. **Given** `ConfigurationScreen` with an `INTEGER` question that has `min`/`max` constraints, **when** the spin box value is out of range, **then** `can_proceed` is `False`.
17. **Given** `ConfigurationScreen` with a `required` CHOICE question, **when** no option is selected, **then** `can_proceed` is `False`.

### ConfigurationScreen — Grouping & display

18. **Given** `ConfigurationScreen` with questions sharing the same `group` value, **when** rendered, **then** those questions are visually grouped inside a `QGroupBox` with the group name as its title.
19. **Given** `ConfigurationScreen` with questions from both a backend and frontend plugin, **when** rendered, **then** both plugins' questions appear on the form.

### ConfigurationScreen — Output

20. **Given** `ConfigurationScreen` with mixed question types, **when** `get_spec_update()` is called, **then** the returned dict follows the format `{"config": {"plugin_id": {key: value, ...}}}` where `MULTI_SELECT` values are `list[str]` and all others are their native types.

### MainWindow integration

21. **Given** `MainWindow` with real screens installed, **when** user navigates from screen 0 to screen 3 (tested via `get_spec_update()` calls on each screen and verifying `_build_spec()` output — not full widget-interaction simulation), **then** `next_screen()` at screen 3 emits `generation_requested` with a `ProjectSpec` whose fields match the screen inputs.
22. **Given** `MainWindow` with screens, **when** `navigate_to(0)` is called, **then** `WelcomeScreen.on_enter()` is called. **when** `navigate_to(1)` follows, **then** `WelcomeScreen.on_exit()` is called and `DomainSelectionScreen.on_enter()` is called.
23. **Given** `MainWindow` at screen 1 where `can_proceed` is `False`, **when** `next_screen()` is called programmatically, **then** the screen index does not advance (guard prevents bypassing disabled Next button).

## Testing notes

### Test infrastructure

- **qapp fixture**: Session-scoped `QApplication` in `tests/unit/conftest.py` (pre-existing).
- **mock_orchestrator fixture**: `MagicMock(spec=Orchestrator)` in `tests/unit/conftest.py` (pre-existing). Override `.return_value` for non-empty scenarios.
- **Lazy imports**: All screen imports use `from forge.ui.screens.<name> import <Class>` inside fixtures/test bodies.
- **Headless CI**: `QT_QPA_PLATFORM=offscreen` (pre-existing).

### T-012 test migration

The existing `tests/unit/test_main_window.py` AC-2 test (Screen 0 button states)
asserts `next_button.isEnabled() is True`. After T-014, screen 0 is a real
`WelcomeScreen` with `can_proceed=False` by default, so Next would be
disabled. **Fix the `main_window` fixture** to inject screens with
`can_proceed=True`:

```python
@pytest.fixture
def main_window(qapp, mock_orchestrator):
    from forge.ui.main_window import MainWindow
    from forge.ui.screens.welcome_screen import WelcomeScreen

    screens = [WelcomeScreen()]
    for _ in range(4):
        screens.append(QWidget())

    # Set can_proceed so T-012 AC-2 continues to pass
    screens[0].can_proceed = True

    window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
    window.show()
    yield window
    window.close()
```

### Test structure

Write tests in `tests/unit/test_wizard_screens.py`. Use `@pytest.mark.gui` for all test classes. Test pattern for each screen:

```python
@pytest.fixture
def welcome_screen(qapp, mock_orchestrator): ...

@pytest.fixture
def domain_screen(qapp, mock_orchestrator): ...

@pytest.fixture
def config_screen(qapp, mock_orchestrator): ...
```

Mock dependency notes:
- `DomainSelectionScreen` tests that verify list population need `mock_orchestrator.get_available_backends.return_value = [Mock(display_name="FastAPI", ...)]`
- `ConfigurationScreen` tests need `mock_orchestrator.get_global_questions.return_value = [...]` and `get_domain_questions.return_value = {...}`
- `MainWindow` integration tests need the full screen list: `screens = [WelcomeScreen(), ...]`

### Validation edge cases

| Edge case | Test approach |
|-----------|---------------|
| ValidationRule with `pattern` only | Mock question with pattern rule; feed bad text |
| ValidationRule with `min`/`max` only | Mock question with bounds; set spinbox out of range |
| `required=True` with empty field | Question with no default; assert `can_proceed` False |
| `required=False` with empty field | Question with `required=False`; assert `can_proceed` True |
| Unknown `QuestionType` | Gracefully skip (log warning, don't render widget) |
| Empty questions list | All plugins return `[]`; screen shows empty scroll area |
| `MULTI_SELECT` with no selection | `get_spec_update()` returns empty `list[str]` |
| `validate()` with multiple errors | Return list of multiple error strings; all labels visible |

## Unsolved / Deferred

- **Domain steps (T-015)**: Screen 3 (domain tags / domain definition) is stubbed as `QWidget()` — deferred to T-015.
- **Review + generation screens**: Screens 4 and 5 remain `QWidget()` stubs — deferred to T-015.
- **TemplateDefinition mapping**: `get_available_backends()` returns `list[PluginBase]` not `list[TemplateDefinition]`. The TemplateDefinition-level filtering is deferred — the wizard uses `PluginBase.display_name` for display and `PluginBase.name` as the `backend_id`/`frontend_id`.
- **`_build_spec` deferral note**: The spec assembly logic is intentionally simple (dict merge). If future screens need cross-screen validation or conditional fields, extract `_build_spec` into the Orchestrator facade.
- **Integration tests**: End-to-end wizard flow (Welcome → Domain → Config → Generate) deferred until T-015 completes the remaining screens.

# T-001: Domain Models

- **type**: task
- **complexity**: simple
- **layer**: `domain/`
- **dependencies**: None
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~20% of window

## Description

Create all pure domain models in `src/forge/domain/` as `@dataclass` classes with no imports from any other Forge layer. These are the leaf-level data structures that every other layer depends on.

## Files to create

- `src/forge/domain/__init__.py`
- `src/forge/domain/project_spec.py` — `ProjectSpec`, `TemplateDefinition`, `Domain`
- `src/forge/domain/questions.py` — `Question`, `QuestionType`, `ValidationRule`
- `src/forge/domain/generated_file.py` — `GeneratedFile`, `DurationEstimate`

## API Spec

```python
# project_spec.py
@dataclass
class Domain:
    name: str
    slug: str   # auto-derived, URL-safe

@dataclass
class TemplateDefinition:
    id: str
    display_name: str
    description: str
    backend_id: str     # string ID, resolved via PluginRegistry
    frontend_id: str | None = None

@dataclass
class ProjectSpec:
    project_name: str
    author: str
    python_version: str
    backend_id: str | None
    frontend_id: str | None
    config: dict[str, dict[str, Any]]   # namespaced by plugin_id

    def plugin_config(self, plugin_id: str) -> dict[str, Any]: ...

# questions.py
class QuestionType(Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    MULTI_SELECT = "multi_select"
    INTEGER = "integer"

@dataclass
class ValidationRule:
    min: int | None = None
    max: int | None = None
    pattern: str | None = None

@dataclass
class Question:
    id: str
    label: str
    question_type: QuestionType
    required: bool = True
    default: Any = None
    options: list[str] | None = None
    validation: ValidationRule | None = None
    group: str | None = None

# generated_file.py
@dataclass
class GeneratedFile:
    path: Path
    content: str
    executable: bool = False

@dataclass
class DurationEstimate:
    estimated_seconds: int
    has_slow_steps: bool
    slow_step_details: list[str]
```

## Acceptance Criteria

1. **Given** no other Forge modules exist, **when** the domain package is imported, **then** all dataclasses and enums are available with zero import errors.
2. **Given** a `ProjectSpec` with `config={"fastapi": {"orm": "sqlalchemy"}}`, **when** `plugin_config("fastapi")` is called, **then** it returns `{"orm": "sqlalchemy"}`.
3. **Given** a `Domain` with name `"User Management"`, **when** instantiated, **then** `slug` is `"user-management"`.
4. **Given** a `Question` with `question_type=QuestionType.CHOICE` and `options=["a","b"]`, **when** serialized to dict, **then** all fields round-trip correctly.
5. **Given** the domain module, **when** searched for imports from `plugins`, `ui`, `generation`, or `infrastructure`, **then** none exist.

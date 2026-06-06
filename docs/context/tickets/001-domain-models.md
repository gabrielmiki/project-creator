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
# __init__.py — re-exports all models
from forge.domain.project_spec import Domain, TemplateDefinition, ProjectSpec
from forge.domain.questions import Question, QuestionType, ValidationRule
from forge.domain.generated_file import GeneratedFile, DurationEstimate

# project_spec.py
import re

@dataclass
class Domain:
    name: str
    slug: str = ""

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = re.sub(r"\s+", "-", self.name.strip().lower())

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
    template: TemplateDefinition
    domains: list[Domain]
    config: dict[str, dict[str, Any]]   # namespaced by plugin_id

    def plugin_config(self, plugin_id: str) -> dict[str, Any]:
        if plugin_id not in self.config:
            raise KeyError(f"Plugin '{plugin_id}' has no configuration")
        return self.config[plugin_id]

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
    key: str
    label: str
    question_type: QuestionType
    required: bool = True
    default: Any = None
    description: str = ""
    options: list[str] | None = None
    placeholder: str | None = None
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
3. **Given** a `ProjectSpec` with `config={"fastapi": {"orm": "sqlalchemy"}}`, **when** `plugin_config("django")` is called, **then** it raises `KeyError`.
4. **Given** a `Domain` with name `"User Management"`, **when** `Domain(name="User Management")` is called, **then** `slug` is `"user-management"`. **Given** a `Domain` with name `"  API V2  "`, **when** instantiated, **then** `slug` is `"api-v2"` (stripped, lowered, hyphenated). **Given** a `Domain` with name `"a  b"`, **when** instantiated, **then** `slug` is `"a-b"` (consecutive whitespace collapsed). **Given** `Domain(name="X", slug="custom")`, **when** constructed, **then** slug respects the explicit override. **Given** `Domain(name="")`, **when** instantiated, **then** `slug` is `""`.
5. **Given** a `Question` with `question_type=QuestionType.CHOICE`, `key="orm"`, `label="ORM"`, and `options=["a","b"]`, **when** serialized via `dataclasses.asdict()`, **then** all fields round-trip correctly through `Question(**asdict(q))`.
6. **Given** a `TemplateDefinition` with `id="fastapi-react"`, `display_name="FastAPI + React"`, `description="Full-stack template"`, `backend_id="fastapi"`, **when** constructed, **then** all fields match and `frontend_id` defaults to `None`.
7. **Given** the domain module, **when** searched for imports from `plugins`, `ui`, `generation`, or `infrastructure`, **then** none exist.
8. **Given** a `GeneratedFile` with `path=Path("src/main.py")`, `content="print('hello')"`, `executable=True`, **when** constructed, **then** all fields match.
9. **Given** a `DurationEstimate` with `estimated_seconds=30`, `has_slow_steps=True`, `slow_step_details=["npm install"]`, **when** constructed, **then** all fields match.

### Implementation notes

- AC-7 requires static-analysis (e.g., `ast` module) rather than a runtime import test,
  since the condition "no other Forge modules exist" cannot be enforced at import time.
- AC-5 round-trip covers the `validation=None` case. A full round-trip with a non-None
  `ValidationRule` would need a custom serialization helper (beyond `dataclasses.asdict()`).
- Domain models are pure data containers with no self-validation. Cross-field constraints
  (e.g., `QuestionType.CHOICE` requires `options`) are enforced by `ValidationEngine`.

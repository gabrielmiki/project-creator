# T-002: PluginBase + Capability Mixins

- **type**: task
- **complexity**: simple
- **layer**: `plugins/`
- **dependencies**: T-001
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~20% of window

## Description

Create the abstract plugin base class and ISP-compliant capability mixins in `src/forge/plugins/base.py`. Each mixin defines a single responsibility. Plugins inherit only what they need.

## Files to create

- `src/forge/plugins/__init__.py`
- `src/forge/plugins/base.py`

## API Spec

```python
class PluginBase(ABC):
    name: str
    display_name: str
    description: str
    requires: list[str] = []
    run_after: list[str] = []

class Configurable(ABC):
    def questions(self) -> list[Question]: ...

class FileProvider(ABC):
    def files(self, spec: ProjectSpec) -> list[GeneratedFile]: ...
    def directories(self, spec: ProjectSpec) -> list[str]: ...

class CommandRunner(ABC):
    def generate(self, spec: ProjectSpec, target_dir: Path) -> None: ...

class DependencyProvider(ABC):
    def dependencies(self) -> list[str]: ...
```

## Acceptance Criteria

1. **Given** the mixins are defined, **when** a plugin class inherits from `PluginBase` and `FileProvider`, **then** it must implement only `name`, `display_name`, `description`, `files()`, and `directories()` — no forced empty methods.
2. **Given** a plugin that does NOT inherit `CommandRunner`, **when** `isinstance(plugin, CommandRunner)` is checked, **then** it returns `False`.
3. **Given** `PluginBase` is abstract, **when** instantiated directly, **then** `TypeError` is raised.
4. **Given** the module, **when** searched for imports from `ui`, `generation`, or `infrastructure`, **then** none exist (may import from `domain` only).

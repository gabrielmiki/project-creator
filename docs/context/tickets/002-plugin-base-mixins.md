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
from abc import ABC, abstractmethod


class PluginBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def display_name(self) -> str: ...
    @property
    @abstractmethod
    def description(self) -> str: ...
    requires: list[str] = []
    run_after: list[str] = []

class Configurable(ABC):
    @abstractmethod
    def questions(self) -> list[Question]: ...

class FileProvider(ABC):
    @abstractmethod
    def files(self, spec: ProjectSpec) -> list[GeneratedFile]: ...
    @abstractmethod
    def directories(self, spec: ProjectSpec) -> list[str]: ...

class CommandRunner(ABC):
    @abstractmethod
    def generate(self, spec: ProjectSpec, target_dir: Path) -> None: ...

class DependencyProvider(ABC):
    @abstractmethod
    def dependencies(self) -> list[str]: ...
```

## Acceptance Criteria

1. **Given** `PluginBase` and `FileProvider` are defined, **when** a class inherits from both, **then** it must instantiate successfully by implementing only `name`, `display_name`, `description`, `files()`, and `directories()`, and `isinstance` checks for uninherited mixins (`CommandRunner`, `Configurable`, `DependencyProvider`) must return `False`.
2. **Given** a plugin that does NOT inherit `CommandRunner`, **when** `isinstance(plugin, CommandRunner)` is checked, **then** it returns `False`.
3. **Given** `PluginBase` is abstract, **when** instantiated directly, **then** `TypeError` is raised.
4. **Given** the module, **when** searched for imports from `forge.ui`, `forge.generation`, or `forge.infrastructure`, **then** none exist. Imports from `forge.domain` and the standard library are permitted.

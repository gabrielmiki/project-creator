# T-005: PluginRegistry + ValidationEngine

- **type**: task
- **complexity**: medium
- **layer**: `generation/`
- **dependencies**: T-001, T-002
- **phase**: 1 — MVP Foundation
- **estimated_context**: ~30% of window

## Description

Create `PluginRegistry` for plugin discovery (entry points + `.plugins/` directory with priority tiers) and ID resolution, and `ValidationEngine` for validating `ProjectSpec` and plugin config against questions.

Also includes topological sort for dependency ordering and cycle detection.

## Files to create or update

- `src/forge/generation/__init__.py` — **update** (already exists from T-003/T-004; add PluginRegistry, ValidationEngine, ValidationError, DiscoveryError, CycleDependencyError to exports)
- `src/forge/generation/registry.py` — **create**
- `src/forge/generation/validation.py` — **create**

## API Spec

```python
class PluginRegistry:
    strict: bool = False             # public read-only attribute
    def __init__(self, strict: bool = False): ...
    def discover(self) -> dict[str, PluginBase]: ...
    def resolve(self, plugin_id: str) -> PluginBase: ...
    def resolve_many(self, plugin_ids: list[str]) -> list[PluginBase]: ...
    def get_available_backends(self) -> list[PluginBase]: ...
    def get_available_frontends(self) -> list[PluginBase]: ...
    def get_missing_dependencies(self, plugin_id: str) -> list[str]: ...
    def topological_sort(self, plugin_ids: list[str]) -> list[PluginBase]: ...

class ValidationEngine:
    def __init__(self, registry: PluginRegistry) -> None: ...
    def validate_spec(self, spec: ProjectSpec) -> list[ValidationError]: ...
    def validate_plugin_config(self, plugin_id: str, config: dict[str, Any], questions: list[Question]) -> list[ValidationError]: ...

class DiscoveryError(Exception):
    """Raised when strict=True and a plugin ID conflict is detected."""

class CycleDependencyError(Exception):
    """Raised when topological_sort detects a circular dependency."""

@dataclass
class ValidationError:
    field: str
    message: str
    severity: Literal["error", "warning"]
```

## Validation Rules

`validate_spec()` checks the following rules against a `ProjectSpec`:

| Rule | Field | Condition |
|------|-------|-----------|
| 1 | `project_name` | Must be a non-empty string |
| 2 | `template` | Must be a valid `TemplateDefinition` with non-empty `id`, `display_name`, `backend_id` |
| 3 | `template.backend_id` | Must be resolvable via the `PluginRegistry` (i.e., the plugin ID exists in discovered plugins) |
| 4 | `template.frontend_id` | If not `None`, must be resolvable via the `PluginRegistry` |
| 5 | `domains` | Must contain at least one `Domain` |

`validate_plugin_config()` checks the following rules against a config dict and its corresponding `Question` list:

| Rule | Question Type | Condition |
|------|--------------|-----------|
| 1 | All | Required question (`required=True`) with key missing from config |
| 2 | `INTEGER` | Value falls outside `validation.min` / `validation.max` bounds |
| 3 | `STRING` | Value does not match `validation.pattern` regex |
| 4 | `CHOICE` | Value is not in `options` list |
| 5 | `MULTI_SELECT` | At least one value is not in `options` list |

## Discovery priority

| Source | Priority | Behavior |
|--------|----------|----------|
| `entry_points["forge.plugins"]` | 10 | System — wins all conflicts |
| `.plugins/` directory | 5 | User — only fills gaps |

- Same-name plugins: higher priority wins; a warning is logged with both sources.
- Strict mode (`strict=True`): errors on ANY conflict.
- `.plugins/` files: `.py` file or directory with `plugin.py`; must export `plugin` attribute.
- Deterministic: sorted file iteration, explicit priority tiers.

## Dependency ordering

- `topological_sort()` resolves `requires` and `run_after` declarations.
- Detects cycles and raises `CycleDependencyError` with the cycle path.
- Each plugin in the result is guaranteed its dependencies have been run first.

## Cross-ticket implementation notes

### T-003 AC-8 AST scanner coupling

T-003's `test_progress.py:TestAC8_NoCrossLayerImports` iterates all `*.py` files in `generation/` and asserts:
1. No imports from `forge.ui`
2. At least one import from `forge.infrastructure`

**Every new file in `generation/`** (including `registry.py` and `validation.py`) will be auto-scanned. To satisfy this test:
- Add `from forge.infrastructure import GenerationTransaction as _  # noqa: F401` to each new file if no real infrastructure import is needed
- Ensure no `forge.ui` imports exist

### Existing `__init__.py` state

`src/forge/generation/__init__.py` already exists from T-003 and was updated by T-004. It currently exports:
- `ProgressReporter`, `StdoutProgressReporter`, `MockProgressReporter`
- `GenerationTransaction` (imported as `_`)

Update it to also export: `PluginRegistry`, `ValidationEngine`, `ValidationError`, `DiscoveryError`, `CycleDependencyError`.

### PluginBase import path (T-002)

`PluginBase` lives at `src/forge/plugins/base.py` and is exported via `forge.plugins`:
```python
from forge.plugins.base import PluginBase
```

The mutable-default risk (`requires: list[str] = []` shared across instances) is mitigated — T-002's implementation creates per-instance copies via `list(self.__class__.requires or [])`.

### ValidationError module location

`ValidationError` lives in `src/forge/generation/validation.py` alongside `ValidationEngine`. It is not in `domain/` because it is a validation result type specific to the generation layer's validation concern. Tests import it from `forge.generation`. If serialization or cross-layer reuse is needed later, it can be promoted to `domain/` in a future ticket.

## Acceptance Criteria

### PluginRegistry — Constructor

1. **Given** no arguments, **when** `PluginRegistry()` is constructed, **then** the instance has `strict=False` and no error is raised.
2. **Given** `strict=True`, **when** `PluginRegistry(strict=True)` is constructed, **then** the instance has `strict=True`.

### PluginRegistry — Discovery

3. **Given** an installed plugin with an entry point, **when** `discover()` is called, **then** the plugin is found in the returned dict and `discovered[plugin_id]` is a `PluginBase` instance.
4. **Given** a conflict between entry_points and `.plugins/` for the same ID, **when** `discover()` is called, **then** entry_points wins and a warning is logged at WARNING level containing the plugin ID and both source paths.
5. **Given** `strict=True` and a conflict, **when** `discover()` is called, **then** `DiscoveryError` is raised before any resolution occurs.
6. **Given** no entry points and no `.plugins/` directory, **when** `discover()` is called, **then** an empty dict is returned.

### PluginRegistry — Resolution

7. **Given** a registry with discovered plugin `"myplugin"`, **when** `resolve("myplugin")` is called, **then** the returned `PluginBase` instance has `name == "myplugin"`.
8. **Given** a registry with no plugin named `"unknown"`, **when** `resolve("unknown")` is called, **then** `KeyError` is raised.
9. **Given** a registry with discovered plugins `["a", "b"]`, **when** `resolve_many(["a", "b"])` is called, **then** a list of two `PluginBase` instances is returned in the same order.
10. **Given** a registry where plugin `"a"` is discovered but `"unknown"` is not, **when** `resolve_many(["a", "unknown"])` is called, **then** `KeyError` is raised.
11. **Given** an empty list, **when** `resolve_many([])` is called, **then** an empty list is returned.

### PluginRegistry — Available Plugins

12. **Given** no entry points but a `.plugins/` directory with a valid plugin file, **when** `discover()` is called, **then** the plugin is found in the returned dict.
13. **Given** discovered plugins, **when** `get_available_backends()` is called, **then** a list of `PluginBase` instances is returned (may include all discovered plugins; backend/frontend differentiation will be added in a future ticket).
14. **Given** discovered plugins, **when** `get_available_frontends()` is called, **then** an empty list is returned (frontend differentiation deferred to a future ticket).

### PluginRegistry — Missing Dependencies

15. **Given** a plugin `"a"` whose `requires` are all resolved (present in discovered plugins), **when** `get_missing_dependencies("a")` is called, **then** an empty list is returned.
16. **Given** a plugin `"a"` with `requires=["b"]` where `"b"` is NOT in discovered plugins, **when** `get_missing_dependencies("a")` is called, **then** the returned list contains `"b"`.
17. **Given** a plugin ID `"unknown"` that is not in discovered plugins, **when** `get_missing_dependencies("unknown")` is called, **then** `KeyError` is raised.

### PluginRegistry — Topological Sort

18. **Given** plugin `"a"` declares `requires=["b"]` (a needs b first) and plugin `"b"` declares no requires, **when** `topological_sort(["a","b"])` is called, **then** plugin `"b"` (dependency) appears before plugin `"a"` (dependent) in the returned list.
19. **Given** a circular dependency (A requires B, B requires A), **when** `topological_sort(["A","B"])` is called, **then** `CycleDependencyError` is raised with a message containing the cycle path (e.g., `"A → B → A"`).
20. **Given** a single plugin with no `requires`, **when** `topological_sort(["only"])` is called, **then** a list with that single plugin is returned unchanged.
21. **Given** an empty list, **when** `topological_sort([])` is called, **then** an empty list is returned.
22. **Given** a plugin list where no plugins declare `requires` or `run_after`, **when** `topological_sort(["b","a"])` is called, **then** the returned list preserves input order (stable sort).
23. **Given** plugin `"a"` declares `run_after=["b"]` (a prefers b first) and plugin `"b"` declares nothing, **when** `topological_sort(["a","b"])` is called, **then** plugin `"b"` appears before plugin `"a"` in the returned list (`run_after` creates a soft ordering edge).

### ValidationEngine — Spec Validation

24. **Given** a valid `ProjectSpec` (non-empty `project_name`, valid `template` with resolvable `backend_id`, at least one `Domain`), **when** `validate_spec()` is called, **then** an empty list is returned.
25. **Given** a `ProjectSpec` with `project_name=""`, **when** `validate_spec()` is called, **then** the returned list contains a `ValidationError` where `error.field == "project_name"`.
26. **Given** a `ProjectSpec` with an empty `domains` list, **when** `validate_spec()` is called, **then** the returned list contains a `ValidationError` where `error.field == "domains"`.
27. **Given** a `ProjectSpec` with `template.backend_id` that does not resolve to any discovered plugin, **when** `validate_spec()` is called, **then** the returned list contains a `ValidationError` where `error.field == "template.backend_id"`.
28. **Given** a `ProjectSpec` with both `project_name=""` and empty `domains`, **when** `validate_spec()` is called, **then** the returned list contains at least two `ValidationError` entries, one with `field == "project_name"` and one with `field == "domains"`.

### ValidationEngine — Plugin Config Validation

29. **Given** a required `Question` with `key="host"` and no default, **when** `validate_plugin_config("myplugin", {}, [question])` is called, **then** the returned list contains a `ValidationError` where `error.field == "host"`.
30. **Given** a `Question` with `key="port"`, `question_type=QuestionType.INTEGER`, and `validation=ValidationRule(min=1024, max=65535)`, **when** `validate_plugin_config("myplugin", {"port": 80}, [question])` is called, **then** the returned list contains a `ValidationError` where `error.field == "port"` and `error.severity == "error"`.
31. **Given** a `Question` with `key="db"`, `question_type=QuestionType.CHOICE`, and `options=["sqlite","postgres"]`, **when** `validate_plugin_config("myplugin", {"db": "mysql"}, [question])` is called, **then** the returned list contains a `ValidationError` where `error.field == "db"`.
32. **Given** a `Question` with `key="name"`, `question_type=QuestionType.STRING`, and `validation=ValidationRule(pattern=r"^[a-z]+$")`, **when** `validate_plugin_config("myplugin", {"name": "INVALID"}, [question])` is called, **then** the returned list contains a `ValidationError` where `error.field == "name"`.
33. **Given** a `Question` with `key="features"`, `question_type=QuestionType.MULTI_SELECT`, and `options=["auth","admin","api"]`, **when** `validate_plugin_config("myplugin", {"features": ["auth","billing"]}, [question])` is called, **then** the returned list contains a `ValidationError` where `error.field == "features"`.
34. **Given** an empty questions list, **when** `validate_plugin_config("myplugin", {"key": "val"}, [])` is called, **then** an empty list is returned (no validation applies).

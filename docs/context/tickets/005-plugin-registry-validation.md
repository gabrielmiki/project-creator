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

## Files to create

- `src/forge/generation/__init__.py`
- `src/forge/generation/registry.py`
- `src/forge/generation/validation.py`

## API Spec

```python
class PluginRegistry:
    def __init__(self, strict: bool = False): ...
    def discover(self) -> dict[str, PluginBase]: ...
    def resolve(self, plugin_id: str) -> PluginBase: ...
    def resolve_many(self, plugin_ids: list[str]) -> list[PluginBase]: ...
    def get_available_backends(self) -> list[TemplateDefinition]: ...
    def get_available_frontends(self) -> list[TemplateDefinition]: ...
    def get_missing_dependencies(self, plugin_id: str) -> list[str]: ...
    def topological_sort(self, plugin_ids: list[str]) -> list[PluginBase]: ...

class ValidationEngine:
    def validate_spec(self, spec: ProjectSpec) -> list[ValidationError]: ...
    def validate_plugin_config(self, plugin_id: str, config: dict[str, Any], questions: list[Question]) -> list[ValidationError]: ...

@dataclass
class ValidationError:
    field: str
    message: str
    severity: Literal["error", "warning"]
```

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

## Acceptance Criteria

1. **Given** an installed plugin with an entry point, **when** `discover()` is called, **then** the plugin is found with priority 10.
2. **Given** a conflict between entry_points and `.plugins/` for the same ID, **when** `discover()` is called, **then** entry_points wins and a warning is logged.
3. **Given** `strict=True` and a conflict, **when** `discover()` is called, **then** `DiscoveryError` is raised.
4. **Given** `requires=["a"]` and `requires=["b"]` and no cycle, **when** `topological_sort(["b","a"])` is called, **then** `a` comes before `b`.
5. **Given** a circular dependency (A requires B, B requires A), **when** `topological_sort(["A","B"])` is called, **then** `CycleDependencyError` is raised.
6. **Given** a valid `ProjectSpec`, **when** `validate_spec()` is called, **then** an empty list is returned.
7. **Given** a `ProjectSpec` with missing required field, **when** `validate_spec()` is called, **then** the error list includes that field.
8. **Given** a config value outside question bounds, **when** `validate_plugin_config()` is called, **then** a `ValidationError` is returned.

from __future__ import annotations

import pytest

from forge.domain import Domain, ProjectSpec, TemplateDefinition
from forge.generation.registry import PluginRegistry
from forge.generation.validation import ValidationEngine


def _make_spec(
    project_name: str = "test-proj",
    backend_id: str = "fastapi",
    frontend_id: str | None = None,
) -> ProjectSpec:
    return ProjectSpec(
        project_name=project_name,
        template=TemplateDefinition(
            id="test",
            display_name="Test Template",
            description="",
            backend_id=backend_id,
            frontend_id=frontend_id,
        ),
        domains=[Domain(name="Web")],
        config={},
    )


@pytest.fixture(scope="module")
def real_registry() -> PluginRegistry:
    reg = PluginRegistry()
    reg.discover()
    return reg


class TestIntegration_SpecValidation:
    @pytest.fixture
    def engine(self, real_registry: PluginRegistry) -> ValidationEngine:
        return ValidationEngine(real_registry)

    def test_valid_spec_returns_no_errors(self, engine: ValidationEngine) -> None:
        spec = _make_spec()
        errors = engine.validate_spec(spec)
        assert errors == []

    def test_empty_project_name_returns_error(self, engine: ValidationEngine) -> None:
        spec = _make_spec(project_name="")
        errors = engine.validate_spec(spec)
        assert any(e.field == "project_name" for e in errors)

    def test_unresolvable_backend_id_returns_error(
        self, engine: ValidationEngine
    ) -> None:
        spec = _make_spec(backend_id="nonexistent")
        errors = engine.validate_spec(spec)
        assert any("backend_id" in e.field for e in errors)


class TestIntegration_PluginConfigValidation:
    @pytest.fixture
    def engine(self, real_registry: PluginRegistry) -> ValidationEngine:
        return ValidationEngine(real_registry)

    def test_config_outside_bounds_returns_error(
        self, engine: ValidationEngine
    ) -> None:
        from forge.domain import Question, QuestionType, ValidationRule

        questions = [
            Question(
                key="port",
                label="Port",
                question_type=QuestionType.INTEGER,
                validation=ValidationRule(min=1024, max=65535),
            ),
        ]
        errors = engine.validate_plugin_config("fastapi", {"port": 80}, questions)
        assert any(e.field == "port" for e in errors)

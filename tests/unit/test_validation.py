from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from forge.domain import (
    Domain,
    ProjectSpec,
    Question,
    QuestionType,
    TemplateDefinition,
    ValidationRule,
)
from forge.generation.validation import ValidationEngine
from forge.plugins.base import PluginBase

# ── Fixtures ──


@pytest.fixture
def mock_registry():
    reg = MagicMock()

    def resolve_side_effect(plugin_id: str) -> PluginBase:
        if plugin_id in ("fastapi", "react"):
            mock = MagicMock(spec=PluginBase)
            mock.name = plugin_id
            return mock
        raise KeyError(plugin_id)

    reg.resolve.side_effect = resolve_side_effect
    return reg


@pytest.fixture
def engine(mock_registry: MagicMock) -> ValidationEngine:
    return ValidationEngine(mock_registry)


@pytest.fixture
def valid_spec() -> ProjectSpec:
    return ProjectSpec(
        project_name="myproject",
        template=TemplateDefinition(
            id="fastapi",
            display_name="FastAPI",
            description="",
            backend_id="fastapi",
        ),
        domains=[Domain(name="users")],
        config={},
    )


@pytest.fixture
def valid_spec_with_frontend() -> ProjectSpec:
    return ProjectSpec(
        project_name="myproject",
        template=TemplateDefinition(
            id="fullstack",
            display_name="Full Stack",
            description="",
            backend_id="fastapi",
            frontend_id="react",
        ),
        domains=[Domain(name="users")],
        config={},
    )


# ── Spec Validation (AC-24 through AC-28) ──


class TestAC24_28_SpecValidation:
    def test_valid_spec_returns_empty_errors(
        self,
        engine: ValidationEngine,
        valid_spec: ProjectSpec,
    ) -> None:
        errors = engine.validate_spec(valid_spec)
        assert errors == []

    def test_valid_spec_with_frontend(
        self,
        engine: ValidationEngine,
        valid_spec_with_frontend: ProjectSpec,
    ) -> None:
        errors = engine.validate_spec(valid_spec_with_frontend)
        assert errors == []

    def test_empty_project_name(
        self,
        engine: ValidationEngine,
        valid_spec: ProjectSpec,
    ) -> None:
        spec = ProjectSpec(
            project_name="",
            template=valid_spec.template,
            domains=valid_spec.domains,
            config=valid_spec.config,
        )
        errors = engine.validate_spec(spec)
        assert len(errors) >= 1
        assert any(e.field == "project_name" for e in errors)
        assert any(e.severity == "error" for e in errors)

    def test_empty_domains(
        self,
        engine: ValidationEngine,
        valid_spec: ProjectSpec,
    ) -> None:
        spec = ProjectSpec(
            project_name=valid_spec.project_name,
            template=valid_spec.template,
            domains=[],
            config=valid_spec.config,
        )
        errors = engine.validate_spec(spec)
        assert len(errors) >= 1
        assert any(e.field == "domains" for e in errors)

    def test_unresolvable_backend_id(
        self,
        engine: ValidationEngine,
    ) -> None:
        spec = ProjectSpec(
            project_name="myproject",
            template=TemplateDefinition(
                id="unknown",
                display_name="Unknown",
                description="",
                backend_id="nonexistent",
            ),
            domains=[Domain(name="users")],
            config={},
        )
        errors = engine.validate_spec(spec)
        assert len(errors) >= 1
        assert any(e.field == "template.backend_id" for e in errors)

    def test_multiple_violations(
        self,
        engine: ValidationEngine,
    ) -> None:
        spec = ProjectSpec(
            project_name="",
            template=TemplateDefinition(
                id="fastapi",
                display_name="FastAPI",
                description="",
                backend_id="fastapi",
            ),
            domains=[],
            config={},
        )
        errors = engine.validate_spec(spec)
        fields = {e.field for e in errors}
        assert "project_name" in fields
        assert "domains" in fields
        assert len(errors) >= 2


# ── Plugin Config Validation (AC-29 through AC-34) ──


class TestAC29_34_PluginConfigValidation:
    def test_missing_required_key(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(key="host", label="Host", question_type=QuestionType.STRING, required=True),
        ]
        errors = engine.validate_plugin_config("myplugin", {}, questions)
        assert len(errors) >= 1
        assert any(e.field == "host" for e in errors)

    def test_integer_below_min(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="port",
                label="Port",
                question_type=QuestionType.INTEGER,
                validation=ValidationRule(min=1024, max=65535),
            ),
        ]
        errors = engine.validate_plugin_config("myplugin", {"port": 80}, questions)
        assert len(errors) >= 1
        assert any(e.field == "port" for e in errors)

    def test_integer_above_max(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="port",
                label="Port",
                question_type=QuestionType.INTEGER,
                validation=ValidationRule(min=1024, max=65535),
            ),
        ]
        errors = engine.validate_plugin_config("myplugin", {"port": 70000}, questions)
        assert len(errors) >= 1
        assert any(e.field == "port" for e in errors)

    def test_integer_valid_range(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="port",
                label="Port",
                question_type=QuestionType.INTEGER,
                validation=ValidationRule(min=1024, max=65535),
            ),
        ]
        errors = engine.validate_plugin_config("myplugin", {"port": 8080}, questions)
        assert errors == []

    def test_choice_invalid_option(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="db",
                label="Database",
                question_type=QuestionType.CHOICE,
                options=["sqlite", "postgres"],
            ),
        ]
        errors = engine.validate_plugin_config("myplugin", {"db": "mysql"}, questions)
        assert len(errors) >= 1
        assert any(e.field == "db" for e in errors)

    def test_choice_valid_option(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="db",
                label="Database",
                question_type=QuestionType.CHOICE,
                options=["sqlite", "postgres"],
            ),
        ]
        errors = engine.validate_plugin_config("myplugin", {"db": "sqlite"}, questions)
        assert errors == []

    def test_string_pattern_mismatch(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="name",
                label="Name",
                question_type=QuestionType.STRING,
                validation=ValidationRule(pattern=r"^[a-z]+$"),
            ),
        ]
        errors = engine.validate_plugin_config("myplugin", {"name": "INVALID"}, questions)
        assert len(errors) >= 1
        assert any(e.field == "name" for e in errors)

    def test_string_valid_pattern(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="name",
                label="Name",
                question_type=QuestionType.STRING,
                validation=ValidationRule(pattern=r"^[a-z]+$"),
            ),
        ]
        errors = engine.validate_plugin_config("myplugin", {"name": "valid"}, questions)
        assert errors == []

    def test_multi_select_invalid_option(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="features",
                label="Features",
                question_type=QuestionType.MULTI_SELECT,
                options=["auth", "admin", "api"],
            ),
        ]
        errors = engine.validate_plugin_config(
            "myplugin",
            {"features": ["auth", "billing"]},
            questions,
        )
        assert len(errors) >= 1
        assert any(e.field == "features" for e in errors)

    def test_multi_select_all_valid(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="features",
                label="Features",
                question_type=QuestionType.MULTI_SELECT,
                options=["auth", "admin", "api"],
            ),
        ]
        errors = engine.validate_plugin_config(
            "myplugin",
            {"features": ["auth", "admin"]},
            questions,
        )
        assert errors == []

    def test_empty_questions_returns_empty(
        self,
        engine: ValidationEngine,
    ) -> None:
        errors = engine.validate_plugin_config("myplugin", {"key": "val"}, [])
        assert errors == []

    # ── AC-10: FastAPI orm invalid option ──

    def test_orm_invalid_option_for_fastapi(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="orm",
                label="ORM",
                question_type=QuestionType.CHOICE,
                options=["sqlalchemy", "none"],
            ),
        ]
        errors = engine.validate_plugin_config("fastapi", {"orm": "invalid"}, questions)
        assert len(errors) >= 1
        assert any(e.field == "orm" for e in errors)

    def test_orm_valid_option_for_fastapi(
        self,
        engine: ValidationEngine,
    ) -> None:
        questions = [
            Question(
                key="orm",
                label="ORM",
                question_type=QuestionType.CHOICE,
                options=["sqlalchemy", "none"],
            ),
        ]
        errors = engine.validate_plugin_config("fastapi", {"orm": "sqlalchemy"}, questions)
        assert errors == []

from __future__ import annotations

import ast
import dataclasses
import pathlib
from pathlib import Path

import pytest

from forge.domain import (
    Domain,
    DurationEstimate,
    GeneratedFile,
    ProjectSpec,
    Question,
    QuestionType,
    TemplateDefinition,
    ValidationRule,
)


class TestAC1_Importability:
    def test_all_models_importable(self) -> None:
        from forge.domain import (  # noqa: F811
            Domain,
            DurationEstimate,
            GeneratedFile,
            ProjectSpec,
            Question,
            QuestionType,
            TemplateDefinition,
            ValidationRule,
        )

        assert Domain.__name__ == "Domain"
        assert DurationEstimate.__name__ == "DurationEstimate"
        assert GeneratedFile.__name__ == "GeneratedFile"
        assert ProjectSpec.__name__ == "ProjectSpec"
        assert Question.__name__ == "Question"
        assert QuestionType.__name__ == "QuestionType"
        assert TemplateDefinition.__name__ == "TemplateDefinition"
        assert ValidationRule.__name__ == "ValidationRule"


class TestAC2_PluginConfigHappyPath:
    def test_returns_config_for_existing_plugin(self) -> None:
        spec = ProjectSpec(
            project_name="test",
            template=TemplateDefinition(
                id="t1", display_name="T1", description="", backend_id="fastapi"
            ),
            domains=[],
            config={"fastapi": {"orm": "sqlalchemy"}},
        )
        assert spec.plugin_config("fastapi") == {"orm": "sqlalchemy"}


class TestAC3_PluginConfigKeyError:
    def test_raises_key_error_for_missing_plugin(self) -> None:
        spec = ProjectSpec(
            project_name="test",
            template=TemplateDefinition(
                id="t1", display_name="T1", description="", backend_id="fastapi"
            ),
            domains=[],
            config={"fastapi": {"orm": "sqlalchemy"}},
        )
        with pytest.raises(KeyError) as exc:
            spec.plugin_config("django")
        assert "django" in str(exc.value)


class TestAC4_DomainSlug:
    def test_basic_slug_generation(self) -> None:
        assert Domain(name="User Management").slug == "user-management"

    def test_strips_leading_trailing_spaces(self) -> None:
        assert Domain(name="  API V2  ").slug == "api-v2"

    def test_collapses_consecutive_whitespace(self) -> None:
        assert Domain(name="a  b").slug == "a-b"

    def test_respects_explicit_slug_override(self) -> None:
        assert Domain(name="X", slug="custom").slug == "custom"

    def test_empty_name_produces_empty_slug(self) -> None:
        assert Domain(name="").slug == ""


class TestAC5_QuestionRoundTrip:
    def test_round_trip_with_none_validation(self) -> None:
        q = Question(
            key="orm",
            label="ORM",
            question_type=QuestionType.CHOICE,
            options=["a", "b"],
        )
        d = dataclasses.asdict(q)
        restored = Question(**d)
        assert restored == q

    def test_round_trip_with_validation_rule_needs_custom_serializer(self) -> None:
        q = Question(
            key="port",
            label="Port",
            question_type=QuestionType.INTEGER,
            validation=ValidationRule(min=1024, max=65535),
        )
        d = dataclasses.asdict(q)
        assert d["validation"] == {"min": 1024, "max": 65535, "pattern": None}
        restored = Question(
            key=d["key"],
            label=d["label"],
            question_type=d["question_type"],
            validation=ValidationRule(**d["validation"]),
        )
        assert restored == q


class TestAC6_TemplateDefinition:
    def test_all_fields_match_and_frontend_defaults_to_none(self) -> None:
        t = TemplateDefinition(
            id="fastapi-react",
            display_name="FastAPI + React",
            description="Full-stack template",
            backend_id="fastapi",
        )
        assert t.id == "fastapi-react"
        assert t.display_name == "FastAPI + React"
        assert t.description == "Full-stack template"
        assert t.backend_id == "fastapi"
        assert t.frontend_id is None

    def test_frontend_id_when_provided(self) -> None:
        t = TemplateDefinition(
            id="fastapi-react",
            display_name="FastAPI + React",
            description="Full-stack template",
            backend_id="fastapi",
            frontend_id="react",
        )
        assert t.frontend_id == "react"


class TestAC7_NoCrossLayerImports:
    FORBIDDEN_PREFIXES = (
        "forge.plugins",
        "forge.ui",
        "forge.generation",
        "forge.infrastructure",
    )

    def _domain_source_files(self) -> list[pathlib.Path]:
        here = pathlib.Path(__file__).resolve().parent.parent.parent
        domain_dir = here / "src" / "forge" / "domain"
        return sorted(domain_dir.glob("*.py"))

    def test_no_imports_from_other_forge_layers(self) -> None:
        for source_file in self._domain_source_files():
            tree = ast.parse(source_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._check_forbidden(alias.name, source_file.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self._check_forbidden(node.module, source_file.name)

    def _check_forbidden(self, module_name: str, filename: str) -> None:
        for prefix in self.FORBIDDEN_PREFIXES:
            if module_name == prefix or module_name.startswith(prefix + "."):
                pytest.fail(f"{filename} imports forbidden module: {module_name}")


class TestAC8_GeneratedFile:
    def test_all_fields_match(self) -> None:
        gf = GeneratedFile(
            path=Path("src/main.py"), content="print('hello')", executable=True
        )
        assert gf.path == Path("src/main.py")
        assert gf.content == "print('hello')"
        assert gf.executable is True

    def test_executable_defaults_to_false(self) -> None:
        gf = GeneratedFile(path=Path("README.md"), content="# Project")
        assert gf.executable is False


class TestAC9_DurationEstimate:
    def test_all_fields_match(self) -> None:
        de = DurationEstimate(
            estimated_seconds=30,
            has_slow_steps=True,
            slow_step_details=["npm install"],
        )
        assert de.estimated_seconds == 30
        assert de.has_slow_steps is True
        assert de.slow_step_details == ["npm install"]

    def test_empty_slow_step_details(self) -> None:
        de = DurationEstimate(
            estimated_seconds=10, has_slow_steps=False, slow_step_details=[]
        )
        assert de.slow_step_details == []


class TestEdgeCases:
    def test_domain_slug_replaces_whitespace_not_special_chars(self) -> None:
        assert Domain(name="Hello World! @#$").slug == "hello-world!-@#$"

    def test_project_spec_empty_config(self) -> None:
        spec = ProjectSpec(
            project_name="empty",
            template=TemplateDefinition(
                id="t1", display_name="T1", description="", backend_id="x"
            ),
            domains=[],
            config={},
        )
        with pytest.raises(KeyError):
            spec.plugin_config("anything")

    def test_template_definition_frontend_defaults_to_none(self) -> None:
        t = TemplateDefinition(
            id="minimal", display_name="Min", description="Minimal template", backend_id="a"
        )
        assert t.frontend_id is None

    def test_question_defaults(self) -> None:
        q = Question(key="k", label="L", question_type=QuestionType.STRING)
        assert q.required is True
        assert q.default is None
        assert q.description == ""
        assert q.options is None
        assert q.placeholder is None
        assert q.validation is None
        assert q.group is None

    def test_generated_file_repr(self) -> None:
        gf = GeneratedFile(path=Path("script.sh"), content="echo hi", executable=True)
        d = dataclasses.asdict(gf)
        assert d["path"] == Path("script.sh")
        assert d["content"] == "echo hi"
        assert d["executable"] is True

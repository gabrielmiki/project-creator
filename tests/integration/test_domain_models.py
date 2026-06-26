from __future__ import annotations

import ast
import dataclasses
import pathlib

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


class TestIntegration_DomainSerialization:
    def test_all_models_round_trip(self) -> None:
        question = Question(
            key="port",
            label="Port number",
            question_type=QuestionType.INTEGER,
            required=True,
            default=8000,
            description="The port to run on",
            validation=ValidationRule(min=1024, max=65535),
        )
        d = dataclasses.asdict(question)
        assert d["key"] == "port"
        assert d["question_type"] == QuestionType.INTEGER
        assert d["validation"] == {"min": 1024, "max": 65535, "pattern": None}

        restored = Question(
            key=d["key"],
            label=d["label"],
            question_type=d["question_type"],
            required=d["required"],
            default=d["default"],
            description=d["description"],
            validation=ValidationRule(**d["validation"]) if d["validation"] else None,
        )
        assert restored == question

        spec = ProjectSpec(
            project_name="my-app",
            template=TemplateDefinition(
                id="fullstack",
                display_name="Full Stack",
                description="A full stack app",
                backend_id="fastapi",
                frontend_id="react",
            ),
            domains=[Domain(name="Auth"), Domain(name="Payments")],
            config={"fastapi": {"orm": "sqlalchemy"}},
        )
        sd = dataclasses.asdict(spec)
        assert sd["project_name"] == "my-app"
        assert sd["template"]["backend_id"] == "fastapi"
        assert sd["domains"][0]["slug"] == "auth"

        gf = GeneratedFile(path=pathlib.Path("src/main.py"), content="print('hello')")
        gd = dataclasses.asdict(gf)
        assert gd["path"] == pathlib.Path("src/main.py")
        assert gd["content"] == "print('hello')"
        assert gd["executable"] is False

        td = TemplateDefinition(
            id="base", display_name="Base", description="", backend_id=""
        )
        tdd = dataclasses.asdict(td)
        assert tdd["frontend_id"] is None

        domain = Domain(name="  My   Domain  ")
        dd = dataclasses.asdict(domain)
        assert dd["slug"] == "my-domain"

        de = DurationEstimate(
            estimated_seconds=30,
            has_slow_steps=True,
            slow_step_details=["npm install"],
        )
        ded = dataclasses.asdict(de)
        assert ded["estimated_seconds"] == 30
        assert ded["slow_step_details"] == ["npm install"]


class TestIntegration_AC4InitExclusion:
    """Deferred from T-002 post-mortem: AST scanner must exclude __init__.py
    from the domain-import check."""

    FORBIDDEN_PREFIXES = ("forge.ui",)

    def _integration_source_files(self) -> list[pathlib.Path]:
        here = pathlib.Path(__file__).resolve().parent
        return sorted(
            f for f in here.glob("*.py")
            if f.name != "conftest.py"
            and not f.name.startswith("test_gui_")
            and not f.name.startswith("test_overwrite_")
        )

    def test_init_py_excluded_from_domain_import_check(self) -> None:
        files = self._integration_source_files()
        init_py = [f for f in files if f.name == "__init__.py"]
        assert len(init_py) == 1

        # __init__.py should be skipped entirely by the scanner
        for source_file in files:
            if source_file.name == "__init__.py":
                continue
            tree = ast.parse(source_file.read_text())
            self._verify_no_forbidden_imports(tree, source_file.name)

    def _verify_no_forbidden_imports(self, tree: ast.AST, filename: str) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_forbidden(alias.name, filename)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._check_forbidden(node.module, filename)

    def _has_forbidden_prefix(self, module_name: str) -> bool:
        for prefix in self.FORBIDDEN_PREFIXES:
            if module_name == prefix or module_name.startswith(prefix + "."):
                return True
        return False

    def _check_forbidden(self, module_name: str, filename: str) -> None:
        if self._has_forbidden_prefix(module_name):
            pytest.fail(f"{filename} imports forbidden module: {module_name}")

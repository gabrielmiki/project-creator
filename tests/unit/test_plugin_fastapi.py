from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from forge.domain import GeneratedFile, ProjectSpec, QuestionType


# ── Local Helpers (no cross-layer imports) ──


class _MockTransaction:
    """Duck-typed GenerationTransaction — no forge.generation import needed."""

    def __init__(self) -> None:
        self.stage_file_calls: list[tuple[str, str]] = []
        self.stage_directory_calls: list[str] = []
        self.requirements: list[str] = []

    def stage_file(self, path: str, content: str) -> Path:
        self.stage_file_calls.append((path, content))
        return Path(path)

    def stage_directory(self, path: str) -> Path:
        self.stage_directory_calls.append(path)
        return Path(path)


def _make_fastapi_spec(config: dict | None = None) -> ProjectSpec:
    """Build a ProjectSpec with backend_id='fastapi' and given config."""
    from forge.domain import Domain, TemplateDefinition

    return ProjectSpec(
        project_name="test-proj",
        template=TemplateDefinition(
            id="test",
            display_name="Test Template",
            description="",
            backend_id="fastapi",
        ),
        domains=[Domain(name="Web")],
        config=config or {},
    )


# ====================================================================
# AC-1: name
# ====================================================================
# Happy path only — name is a class attribute, can't error


class TestAC1_Name:
    def test_name_returns_fastapi(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        assert plugin.name == "fastapi"


# ====================================================================
# AC-2a: files() core file paths
# ====================================================================


class TestAC2a_FilesCorePaths:
    def test_files_contains_core_files(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {}})
        files = plugin.files(spec)
        paths = {str(f.path) for f in files}
        assert "app/__init__.py" in paths
        assert "app/main.py" in paths
        assert "requirements.txt" in paths

    def test_files_returns_list_of_generated_files(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {}})
        files = plugin.files(spec)
        assert isinstance(files, list)
        assert all(isinstance(f, GeneratedFile) for f in files)

    def test_file_paths_are_path_objects(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {}})
        files = plugin.files(spec)
        for f in files:
            assert isinstance(f.path, Path)


# ====================================================================
# AC-2b: engine integration (simulated)
# ====================================================================


class TestAC2b_EngineIntegration:
    def test_engine_stages_core_files_and_deps(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {}})
        txn = _MockTransaction()

        for f in plugin.files(spec):
            txn.stage_file(str(f.path), f.content)
        for d in plugin.directories(spec):
            txn.stage_directory(d)
        for dep in plugin.dependencies(spec):
            txn.requirements.append(dep)

        staged = {call[0] for call in txn.stage_file_calls}
        assert "app/__init__.py" in staged
        assert "app/main.py" in staged
        assert "requirements.txt" in staged
        assert "fastapi>=0.115" in txn.requirements

    def test_engine_empty_config_no_error(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={})
        txn = _MockTransaction()

        for f in plugin.files(spec):
            txn.stage_file(str(f.path), f.content)
        for d in plugin.directories(spec):
            txn.stage_directory(d)
        for dep in plugin.dependencies(spec):
            txn.requirements.append(dep)

        staged = {call[0] for call in txn.stage_file_calls}
        assert "app/__init__.py" in staged
        assert "app/main.py" in staged
        assert "requirements.txt" in staged
        assert "fastapi>=0.115" in txn.requirements


# ====================================================================
# AC-3: questions()
# ====================================================================


class TestAC3_Questions:
    def test_questions_keys_include_orm_auth_alembic(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        keys = {q.key for q in plugin.questions()}
        assert "orm" in keys
        assert "auth" in keys
        assert "include_alembic" in keys

    def test_orm_question_type_and_options(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        qs = plugin.questions()
        orm_q = next(q for q in qs if q.key == "orm")
        assert orm_q.question_type == QuestionType.CHOICE
        assert orm_q.options == ["sqlalchemy", "none"]

    def test_auth_and_alembic_are_boolean(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        qs = plugin.questions()
        auth_q = next(q for q in qs if q.key == "auth")
        alembic_q = next(q for q in qs if q.key == "include_alembic")
        assert auth_q.question_type == QuestionType.BOOLEAN
        assert alembic_q.question_type == QuestionType.BOOLEAN

    def test_question_keys_are_unique(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        keys = [q.key for q in plugin.questions()]
        assert len(keys) == len(set(keys))


# ====================================================================
# AC-4: orm=sqlalchemy → requirements.txt includes sqlalchemy
# ====================================================================


class TestAC4_OrmSqlalchemy:
    def test_orm_sqlalchemy_adds_sqlalchemy_to_requirements(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {"orm": "sqlalchemy"}})
        reqs = next(f for f in plugin.files(spec) if f.path.name == "requirements.txt")
        assert "sqlalchemy" in reqs.content

    def test_orm_sqlalchemy_requirements_format(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {"orm": "sqlalchemy"}})
        reqs = next(f for f in plugin.files(spec) if f.path.name == "requirements.txt")
        assert "sqlalchemy" in reqs.content
        assert "fastapi" in reqs.content


# ====================================================================
# AC-5: include_alembic=True → "alembic/" in directories()
# ====================================================================


class TestAC5_AlembicTrue:
    def test_alembic_dir_included_when_true(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {"include_alembic": True}})
        dirs = plugin.directories(spec)
        assert "alembic/" in dirs


# ====================================================================
# AC-6: dependencies() base set
# ====================================================================


class TestAC6_BaseDependencies:
    def test_base_dependencies_includes_fastapi_and_uvicorn(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {}})
        deps = plugin.dependencies(spec)
        assert "fastapi>=0.115" in deps
        assert "uvicorn[standard]>=0.34" in deps

    def test_base_dependencies_excludes_auth_packages(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {}})
        deps = plugin.dependencies(spec)
        assert all("jose" not in d for d in deps)
        assert all("passlib" not in d for d in deps)


# ====================================================================
# AC-7: generate() calls executor.run()
# ====================================================================


class TestAC7_Generate:
    def test_generate_calls_executor_run_with_uv_add(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_called_once()
        cmd = executor.run.call_args[0][0]
        assert cmd == ["uv", "add", "fastapi>=0.115", "uvicorn[standard]>=0.34", "sqlalchemy>=2.0", "aiosqlite>=0.20"]

    def test_generate_passes_cwd_to_executor(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_called_once()
        assert executor.run.call_args[1].get("cwd") == target_dir


class TestAC7b_GenerateConditionalDeps:
    @pytest.mark.parametrize(
        "config,expected_in,expected_not_in",
        [
            (
                {"fastapi": {"orm": "none"}},
                [],
                ["sqlalchemy>=2.0", "aiosqlite>=0.20"],
            ),
            (
                {"fastapi": {"auth": True}},
                ["python-jose[cryptography]>=3.3", "passlib[bcrypt]>=1.7"],
                [],
            ),
            (
                {"fastapi": {"orm": "none", "auth": False}},
                [],
                [
                    "sqlalchemy>=2.0",
                    "aiosqlite>=0.20",
                    "python-jose[cryptography]>=3.3",
                    "passlib[bcrypt]>=1.7",
                ],
            ),
        ],
    )
    def test_generate_command_includes_conditional_deps(
        self, config: dict, expected_in: list[str], expected_not_in: list[str]
    ) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config=config)
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_called_once()
        cmd = executor.run.call_args[0][0]
        for dep in expected_in:
            assert dep in cmd, f"Expected {dep!r} in command {cmd}"
        for dep in expected_not_in:
            assert dep not in cmd, f"Expected {dep!r} not in command {cmd}"


# ====================================================================
# AC-8: include_alembic=False → "alembic/" NOT in directories()
# ====================================================================


class TestAC8_AlembicFalse:
    def test_alembic_dir_not_included_when_false(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {"include_alembic": False}})
        dirs = plugin.directories(spec)
        assert "alembic/" not in dirs


# ====================================================================
# AC-9: orm="none" → requirements.txt omits sqlalchemy
# ====================================================================


class TestAC9_OrmNone:
    def test_orm_none_omits_sqlalchemy_from_requirements(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {"orm": "none"}})
        reqs = next(f for f in plugin.files(spec) if f.path.name == "requirements.txt")
        assert "sqlalchemy" not in reqs.content

    def test_orm_none_omits_orm_source_files(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {"orm": "none"}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "app/models.py" not in paths
        assert "app/database.py" not in paths

    def test_orm_none_still_has_framework_deps(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {"orm": "none"}})
        reqs = next(f for f in plugin.files(spec) if f.path.name == "requirements.txt")
        assert "fastapi" in reqs.content
        assert "uvicorn" in reqs.content


# ====================================================================
# AC-11: empty config defaults → sqlalchemy, no alembic
# ====================================================================


class TestAC11_EmptyConfigDefaults:
    def test_empty_config_uses_defaults(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {}})
        files = plugin.files(spec)
        dirs = plugin.directories(spec)
        reqs = next(f for f in files if f.path.name == "requirements.txt")
        assert "sqlalchemy" in reqs.content
        assert "alembic/" not in dirs


# ====================================================================
# AC-12: missing "fastapi" key → no exception, defaults
# ====================================================================


class TestAC12_MissingConfigKey:
    def test_missing_fastapi_key_uses_defaults(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={})
        files = plugin.files(spec)
        dirs = plugin.directories(spec)
        reqs = next(f for f in files if f.path.name == "requirements.txt")
        assert "sqlalchemy" in reqs.content
        assert "alembic/" not in dirs

    def test_missing_fastapi_key_does_not_raise(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={})
        plugin.files(spec)
        plugin.directories(spec)
        plugin.dependencies(spec)


# ====================================================================
# AC-13: auth=True → deps include python-jose and passlib
# ====================================================================


class TestAC13_AuthTrueDeps:
    def test_auth_true_deps_include_auth_packages(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {"auth": True}})
        deps = plugin.dependencies(spec)
        assert "python-jose[cryptography]>=3.3" in deps
        assert "passlib[bcrypt]>=1.7" in deps


# ====================================================================
# AC-14: auth=True → middleware/auth.py and routes/auth.py
# ====================================================================


class TestAC14_AuthTrueFiles:
    def test_auth_true_includes_auth_files(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config={"fastapi": {"auth": True}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "app/middleware/auth.py" in paths
        assert "app/routes/auth.py" in paths


# ====================================================================
# AC-15: auth=False or absent → no auth deps
# ====================================================================


class TestAC15_AuthFalseOrAbsentDeps:
    @pytest.mark.parametrize(
        "config",
        [
            {"fastapi": {"auth": False}},
            {"fastapi": {}},
        ],
    )
    def test_auth_false_or_absent_excludes_auth_deps(self, config: dict) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        spec = _make_fastapi_spec(config=config)
        deps = plugin.dependencies(spec)
        assert "python-jose[cryptography]>=3.3" not in deps
        assert "passlib[bcrypt]>=1.7" not in deps
        assert "fastapi>=0.115" in deps


# ====================================================================
# AC-16: display_name and description
# ====================================================================


class TestAC16_DisplayNameAndDescription:
    def test_display_name(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        assert plugin.display_name == "FastAPI"

    def test_description_is_non_empty(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        plugin = FastapiPlugin()
        assert isinstance(plugin.description, str) and len(plugin.description) > 0


# ====================================================================
# AC-17: module export
# ====================================================================


class TestAC17_ModuleExport:
    def test_module_export(self) -> None:
        from forge.plugins.fastapi import FastapiPlugin

        assert FastapiPlugin is not None

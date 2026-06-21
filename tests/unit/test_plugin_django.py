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


def _make_django_spec(config: dict | None = None) -> ProjectSpec:
    """Build a ProjectSpec with backend_id='django' and given config."""
    from forge.domain import Domain, TemplateDefinition

    return ProjectSpec(
        project_name="test-proj",
        template=TemplateDefinition(
            id="test",
            display_name="Test Template",
            description="",
            backend_id="django",
        ),
        domains=[Domain(name="Web")],
        config=config or {},
    )


# ====================================================================
# AC-1: name
# ====================================================================
# Happy path only — name is a class attribute, can't error


class TestAC1_Name:
    def test_name_returns_django(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        assert plugin.name == "django"


# ====================================================================
# AC-2a: files() core file paths
# ====================================================================
# Happy path + type assertions
# Error case: empty files() — no error, just empty list
# Edge case: all paths are Path objects


class TestAC2a_FilesCorePaths:
    def test_files_contains_core_files(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {}})
        files = plugin.files(spec)
        paths = {str(f.path) for f in files}
        assert "manage.py" in paths
        assert "config/settings.py" in paths
        assert "config/urls.py" in paths
        assert "config/wsgi.py" in paths
        assert "requirements.txt" in paths

    def test_files_returns_list_of_generated_files(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {}})
        files = plugin.files(spec)
        assert isinstance(files, list)
        assert all(isinstance(f, GeneratedFile) for f in files)

    def test_file_paths_are_path_objects(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {}})
        files = plugin.files(spec)
        for f in files:
            assert isinstance(f.path, Path)


# ====================================================================
# AC-2b: engine integration (simulated)
# ====================================================================
# Happy path: files staged, deps appended
# Error case: empty config → no exception


class TestAC2b_EngineIntegration:
    def test_engine_stages_core_files_and_deps(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {}})
        txn = _MockTransaction()

        for f in plugin.files(spec):
            txn.stage_file(str(f.path), f.content)
        for d in plugin.directories(spec):
            txn.stage_directory(d)
        for dep in plugin.dependencies(spec):
            txn.requirements.append(dep)

        staged = {call[0] for call in txn.stage_file_calls}
        assert "manage.py" in staged
        assert "config/settings.py" in staged
        assert "config/urls.py" in staged
        assert "config/wsgi.py" in staged
        assert "requirements.txt" in staged
        assert "django>=5.1" in txn.requirements

    def test_engine_empty_config_no_error(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={})
        txn = _MockTransaction()

        for f in plugin.files(spec):
            txn.stage_file(str(f.path), f.content)
        for d in plugin.directories(spec):
            txn.stage_directory(d)
        for dep in plugin.dependencies(spec):
            txn.requirements.append(dep)

        staged = {call[0] for call in txn.stage_file_calls}
        assert "manage.py" in staged
        assert "requirements.txt" in staged
        assert "django>=5.1" in txn.requirements


# ====================================================================
# AC-3: questions()
# ====================================================================


class TestAC3_Questions:
    def test_questions_keys_include_database_and_drf(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        keys = {q.key for q in plugin.questions()}
        assert "database" in keys
        assert "include_drf" in keys

    def test_database_question_type_and_options(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        qs = plugin.questions()
        database_q = next(q for q in qs if q.key == "database")
        assert database_q.question_type == QuestionType.CHOICE
        assert database_q.options == ["postgresql", "sqlite", "mysql"]

    def test_include_drf_is_boolean(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        qs = plugin.questions()
        drf_q = next(q for q in qs if q.key == "include_drf")
        assert drf_q.question_type == QuestionType.BOOLEAN

    def test_question_keys_are_unique(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        keys = [q.key for q in plugin.questions()]
        assert len(keys) == len(set(keys))


# ====================================================================
# AC-4: database=postgresql → settings ENGINE + requirements
# ====================================================================


class TestAC4_DatabasePostgresql:
    def test_settings_engine_is_postgresql(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"database": "postgresql"}})
        settings = next(f for f in plugin.files(spec) if f.path.name == "settings.py")
        assert '"ENGINE": "django.db.backends.postgresql"' in settings.content

    def test_requirements_includes_psycopg2(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"database": "postgresql"}})
        reqs = next(f for f in plugin.files(spec) if f.path.name == "requirements.txt")
        assert "psycopg2-binary>=2.9" in reqs.content


# ====================================================================
# AC-5: database=sqlite → sqlite3 ENGINE, no extra db packages
# ====================================================================


class TestAC5_DatabaseSqlite:
    def test_settings_engine_is_sqlite3(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"database": "sqlite"}})
        settings = next(f for f in plugin.files(spec) if f.path.name == "settings.py")
        assert '"ENGINE": "django.db.backends.sqlite3"' in settings.content

    def test_requirements_excludes_db_packages(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"database": "sqlite"}})
        reqs = next(f for f in plugin.files(spec) if f.path.name == "requirements.txt")
        assert "psycopg2-binary" not in reqs.content
        assert "mysqlclient" not in reqs.content


# ====================================================================
# AC-6: database=mysql → mysql ENGINE + mysqlclient in requirements
# ====================================================================


class TestAC6_DatabaseMysql:
    def test_settings_engine_is_mysql(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"database": "mysql"}})
        settings = next(f for f in plugin.files(spec) if f.path.name == "settings.py")
        assert '"ENGINE": "django.db.backends.mysql"' in settings.content

    def test_requirements_includes_mysqlclient(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"database": "mysql"}})
        reqs = next(f for f in plugin.files(spec) if f.path.name == "requirements.txt")
        assert "mysqlclient>=2.2" in reqs.content


# ====================================================================
# AC-7: include_drf=True → rest_framework in INSTALLED_APPS + drf in reqs
# ====================================================================


class TestAC7_DrfTrue:
    def test_settings_includes_rest_framework(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"include_drf": True}})
        settings = next(f for f in plugin.files(spec) if f.path.name == "settings.py")
        assert "rest_framework" in settings.content

    def test_requirements_includes_drf(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"include_drf": True}})
        reqs = next(f for f in plugin.files(spec) if f.path.name == "requirements.txt")
        assert "djangorestframework>=3.15" in reqs.content


# ====================================================================
# AC-8: include_drf=False or absent → no rest_framework
# ====================================================================


class TestAC8_DrfFalseOrAbsent:
    @pytest.mark.parametrize(
        "config",
        [
            {"django": {"include_drf": False}},
            {"django": {}},
        ],
    )
    def test_settings_excludes_rest_framework(self, config: dict) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config=config)
        settings = next(f for f in plugin.files(spec) if f.path.name == "settings.py")
        assert "rest_framework" not in settings.content

    def test_requirements_excludes_drf(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"include_drf": False}})
        reqs = next(f for f in plugin.files(spec) if f.path.name == "requirements.txt")
        assert "djangorestframework" not in reqs.content


# ====================================================================
# AC-9: directories()
# ====================================================================


class TestAC9_Directories:
    def test_directories_contains_expected_dirs(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {}})
        dirs = plugin.directories(spec)
        assert "config/" in dirs
        assert "apps/" in dirs
        assert "static/" in dirs
        assert "templates/" in dirs


# ====================================================================
# AC-10: dependencies() base set (SQLite default, no DRF)
# ====================================================================


class TestAC10_BaseDependencies:
    def test_base_deps_includes_django(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {}})
        deps = plugin.dependencies(spec)
        assert "django>=5.1" in deps

    def test_base_deps_excludes_drf_and_db_packages(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {}})
        deps = plugin.dependencies(spec)
        assert all("djangorestframework" not in d for d in deps)
        assert all("psycopg2" not in d for d in deps)
        assert all("mysqlclient" not in d for d in deps)


# ====================================================================
# AC-11: dependencies() with DRF
# ====================================================================


class TestAC11_DepsDrfTrue:
    def test_deps_include_drf_when_enabled(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"include_drf": True}})
        deps = plugin.dependencies(spec)
        assert "djangorestframework>=3.15" in deps
        assert "django>=5.1" in deps


# ====================================================================
# AC-12: dependencies() with postgresql
# ====================================================================


class TestAC12_DepsPostgresql:
    def test_deps_include_psycopg2(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"database": "postgresql"}})
        deps = plugin.dependencies(spec)
        assert "psycopg2-binary>=2.9" in deps
        assert "django>=5.1" in deps


# ====================================================================
# AC-13: generate() default config
# ====================================================================


class TestAC13_GenerateDefault:
    def test_generate_calls_executor_run_with_uv_add(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_called_once()
        cmd = executor.run.call_args[0][0]
        assert "uv" in cmd
        assert "add" in cmd
        assert "django>=5.1" in cmd

    def test_generate_passes_cwd_to_executor(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_called_once()
        assert executor.run.call_args[1].get("cwd") == target_dir


# ====================================================================
# AC-14: generate() with DRF
# ====================================================================


class TestAC14_GenerateDrf:
    def test_generate_includes_drf(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"include_drf": True}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_called_once()
        cmd = executor.run.call_args[0][0]
        assert "djangorestframework>=3.15" in cmd


# ====================================================================
# AC-15: generate() with postgresql
# ====================================================================


class TestAC15_GeneratePostgresql:
    def test_generate_includes_psycopg2(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"database": "postgresql"}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_called_once()
        cmd = executor.run.call_args[0][0]
        assert "psycopg2-binary>=2.9" in cmd


# ====================================================================
# AC-16: generate() with mysql
# ====================================================================


class TestAC16_GenerateMysql:
    def test_generate_includes_mysqlclient(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {"database": "mysql"}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_called_once()
        cmd = executor.run.call_args[0][0]
        assert "mysqlclient>=2.2" in cmd


# ====================================================================
# AC-17: empty config defaults → SQLite, no DRF
# ====================================================================


class TestAC17_EmptyConfigDefaults:
    def test_empty_config_uses_defaults(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={"django": {}})
        files = plugin.files(spec)
        deps = plugin.dependencies(spec)

        reqs = next(f for f in files if f.path.name == "requirements.txt")
        assert "psycopg2-binary>=2.9" not in reqs.content
        assert "mysqlclient>=2.2" not in reqs.content

        assert deps == ["django>=5.1"]

        settings = next(f for f in files if f.path.name == "settings.py")
        assert "sqlite3" in settings.content


# ====================================================================
# AC-18: missing "django" key → no exception, defaults
# ====================================================================


class TestAC18_MissingConfigKey:
    def test_missing_django_key_uses_defaults(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={})
        files = plugin.files(spec)
        deps = plugin.dependencies(spec)

        reqs = next(f for f in files if f.path.name == "requirements.txt")
        assert "psycopg2-binary>=2.9" not in reqs.content
        assert "mysqlclient>=2.2" not in reqs.content

        assert deps == ["django>=5.1"]

        settings = next(f for f in files if f.path.name == "settings.py")
        assert "sqlite3" in settings.content

    def test_missing_django_key_does_not_raise(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        spec = _make_django_spec(config={})
        plugin.files(spec)
        plugin.directories(spec)
        plugin.dependencies(spec)


# ====================================================================
# AC-20: display_name and description
# ====================================================================


class TestAC20_DisplayNameAndDescription:
    def test_display_name(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        assert plugin.display_name == "Django"

    def test_description_is_non_empty(self) -> None:
        from forge.plugins.django import DjangoPlugin

        plugin = DjangoPlugin()
        assert isinstance(plugin.description, str) and len(plugin.description) > 0


# ====================================================================
# AC-21: module export
# ====================================================================


class TestAC21_ModuleExport:
    def test_module_export(self) -> None:
        from forge.plugins.django import DjangoPlugin

        assert DjangoPlugin is not None

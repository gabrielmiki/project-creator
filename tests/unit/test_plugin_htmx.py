from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from forge.domain import GeneratedFile, ProjectSpec, Question, QuestionType


# ── Local Helpers (no cross-layer imports) ──


class _MockTransaction:
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


def _make_htmx_spec(config: dict | None = None) -> ProjectSpec:
    from forge.domain import Domain, TemplateDefinition

    return ProjectSpec(
        project_name="test-proj",
        template=TemplateDefinition(
            id="test",
            display_name="Test Template",
            description="",
            backend_id="",
            frontend_id="htmx",
        ),
        domains=[Domain(name="Web")],
        config=config or {},
    )


# ====================================================================
# AC-01: plugin.name
# ====================================================================


class TestAC1_Name:
    def test_name_returns_htmx(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        assert plugin.name == "htmx"

    def test_name_is_string(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        assert isinstance(plugin.name, str)


# ====================================================================
# AC-02a: files() core paths
# ====================================================================


class TestAC2a_FilesCorePaths:
    def test_core_paths_present(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "templates/base.html" in paths
        assert "templates/index.html" in paths
        assert "static/css/style.css" in paths

    def test_returns_generated_file_list(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        files = plugin.files(spec)
        assert isinstance(files, list)
        assert all(isinstance(f, GeneratedFile) for f in files)

    def test_paths_are_path_objects(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        files = plugin.files(spec)
        for f in files:
            assert isinstance(f.path, Path)


# ====================================================================
# AC-02b: engine integration (simulated)
# ====================================================================


class TestAC2b_EngineIntegration:
    def test_stages_core_files(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        txn = _MockTransaction()

        for f in plugin.files(spec):
            txn.stage_file(str(f.path), f.content)
        for d in plugin.directories(spec):
            txn.stage_directory(d)
        for dep in plugin.dependencies(spec):
            txn.requirements.append(dep)

        staged = {call[0] for call in txn.stage_file_calls}
        assert "templates/base.html" in staged
        assert "templates/index.html" in staged
        assert "static/css/style.css" in staged
        assert txn.requirements == []

    def test_empty_config_no_error(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={})
        txn = _MockTransaction()

        for f in plugin.files(spec):
            txn.stage_file(str(f.path), f.content)
        for d in plugin.directories(spec):
            txn.stage_directory(d)
        for dep in plugin.dependencies(spec):
            txn.requirements.append(dep)

        staged = {call[0] for call in txn.stage_file_calls}
        assert "templates/base.html" in staged
        assert "templates/index.html" in staged
        assert "static/css/style.css" in staged
        assert txn.requirements == []


# ====================================================================
# AC-03: questions()
# ====================================================================


class TestAC3_Questions:
    def test_keys_include_all_three(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        keys = {q.key for q in plugin.questions()}
        assert "include_alpine" in keys
        assert "include_tailwind" in keys
        assert "css_framework" in keys

    def test_boolean_questions(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        qs = plugin.questions()
        alpine_q = next(q for q in qs if q.key == "include_alpine")
        tailwind_q = next(q for q in qs if q.key == "include_tailwind")
        assert alpine_q.question_type == QuestionType.BOOLEAN
        assert tailwind_q.question_type == QuestionType.BOOLEAN

    def test_css_framework_choice(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        qs = plugin.questions()
        css_q = next(q for q in qs if q.key == "css_framework")
        assert css_q.question_type == QuestionType.CHOICE
        assert css_q.options == ["tailwind", "bootstrap", "none"]

    def test_keys_are_unique(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        keys = [q.key for q in plugin.questions()]
        assert len(keys) == len(set(keys))


# ====================================================================
# AC-04: base.html includes HTMX CDN
# ====================================================================


class TestAC4_HtmxScript:
    def test_includes_htmx_script(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "htmx.org@2.0.4" in base.content
        assert "<script" in base.content

    def test_includes_htmx_any_config(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {"include_alpine": True}})
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "htmx.org@2.0.4" in base.content


# ====================================================================
# AC-05: include_alpine=True
# ====================================================================


class TestAC5_AlpineTrue:
    def test_includes_alpine_script(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {"include_alpine": True}})
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "alpinejs@3.14.8" in base.content
        assert "<script" in base.content

    def test_includes_alpine_keeps_core_files(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {"include_alpine": True}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "templates/base.html" in paths
        assert "templates/index.html" in paths
        assert "static/css/style.css" in paths


# ====================================================================
# AC-06: include_alpine=False or absent
# ====================================================================


class TestAC6_AlpineFalseOrAbsent:
    def test_false_excludes_alpine(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {"include_alpine": False}})
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "alpinejs" not in base.content

    def test_absent_excludes_alpine(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "alpinejs" not in base.content


# ====================================================================
# AC-07: include_tailwind=True
# ====================================================================


class TestAC7_TailwindTrue:
    def test_includes_build_files(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {"include_tailwind": True}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "tailwind.config.js" in paths
        assert "postcss.config.js" in paths

    def test_tailwind_content_paths(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {"include_tailwind": True}})
        files = plugin.files(spec)
        tw = next(f for f in files if str(f.path) == "tailwind.config.js")
        assert "./templates/**/*.html" in tw.content

    def test_includes_tailwind_cdn(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {"include_tailwind": True}})
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "cdn.tailwindcss.com" in base.content


# ====================================================================
# AC-08: include_tailwind=False or absent
# ====================================================================


class TestAC8_TailwindFalseOrAbsent:
    def test_false_excludes_build_files(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {"include_tailwind": False}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "tailwind.config.js" not in paths

    def test_absent_excludes_build_files(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "tailwind.config.js" not in paths


# ====================================================================
# AC-09: css_framework="tailwind" (CDN-only, no build files)
# ====================================================================


class TestAC9_CssFrameworkTailwind:
    def test_cdn_tailwind_script(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(
            config={"htmx": {"css_framework": "tailwind", "include_tailwind": False}}
        )
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "cdn.tailwindcss.com" in base.content

    def test_no_build_files(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(
            config={"htmx": {"css_framework": "tailwind", "include_tailwind": False}}
        )
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "tailwind.config.js" not in paths
        assert "postcss.config.js" not in paths


# ====================================================================
# AC-10: css_framework="bootstrap"
# ====================================================================


class TestAC10_CssFrameworkBootstrap:
    def test_cdn_bootstrap_link(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(
            config={"htmx": {"css_framework": "bootstrap", "include_tailwind": False}}
        )
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "bootstrap@5.3.3" in base.content
        assert "<link" in base.content
        assert "cdn.tailwindcss.com" not in base.content


# ====================================================================
# AC-11: css_framework="none"
# ====================================================================


class TestAC11_CssFrameworkNone:
    def test_no_css_framework_cdn(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(
            config={"htmx": {"css_framework": "none", "include_tailwind": False}}
        )
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "cdn.tailwindcss.com" not in base.content
        assert "cdn.jsdelivr.net/npm/bootstrap" not in base.content


# ====================================================================
# AC-12a: include_tailwind=True + css_framework="bootstrap"
# ====================================================================


class TestAC12a_TailwindWithBootstrap:
    def test_both_cdns_present(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(
            config={"htmx": {"include_tailwind": True, "css_framework": "bootstrap"}}
        )
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "cdn.tailwindcss.com" in base.content
        assert "bootstrap@5.3.3" in base.content

    def test_build_files_present(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(
            config={"htmx": {"include_tailwind": True, "css_framework": "bootstrap"}}
        )
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "tailwind.config.js" in paths
        assert "postcss.config.js" in paths


# ====================================================================
# AC-12b: include_tailwind=True + css_framework="tailwind" (no dup)
# ====================================================================


class TestAC12b_TailwindDedup:
    def test_tailwind_cdn_once_only(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(
            config={"htmx": {"include_tailwind": True, "css_framework": "tailwind"}}
        )
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert base.content.count("cdn.tailwindcss.com") == 1


# ====================================================================
# AC-13: directories()
# ====================================================================


class TestAC13_Directories:
    def test_directories(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        dirs = plugin.directories(spec)
        assert "templates/" in dirs
        assert "static/css/" in dirs
        assert "static/js/" in dirs


# ====================================================================
# AC-14: dependencies() is empty
# ====================================================================


class TestAC14_DependenciesEmpty:
    @pytest.mark.parametrize(
        "config",
        [
            {"htmx": {}},
            {"htmx": {"include_alpine": True}},
            {"htmx": {"include_tailwind": True}},
            {"htmx": {"css_framework": "bootstrap"}},
            {"htmx": {"include_tailwind": True, "css_framework": "bootstrap"}},
        ],
    )
    def test_deps_empty_for_all_configs(self, config: dict) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config=config)
        assert plugin.dependencies(spec) == []


# ====================================================================
# AC-15: generate() is no-op
# ====================================================================


class TestAC15_GenerateNoop:
    def test_noop_does_not_call_executor(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_not_called()


# ====================================================================
# AC-16: empty config dict
# ====================================================================


class TestAC16_EmptyConfigDefaults:
    def test_default_alpine_false(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "alpinejs" not in base.content

    def test_default_tailwind_false(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "tailwind.config.js" not in paths

    def test_default_css_framework_none(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        files = plugin.files(spec)
        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "cdn.tailwindcss.com" not in base.content
        assert "cdn.jsdelivr.net/npm/bootstrap" not in base.content

    def test_no_exception(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={"htmx": {}})
        plugin.files(spec)
        plugin.directories(spec)
        plugin.dependencies(spec)


# ====================================================================
# AC-17: missing "htmx" config key
# ====================================================================


class TestAC17_MissingConfigKey:
    def test_missing_key_defaults(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={})
        files = plugin.files(spec)
        paths = {str(f.path) for f in files}

        assert "templates/base.html" in paths
        assert "templates/index.html" in paths
        assert "static/css/style.css" in paths

        base = next(f for f in files if str(f.path) == "templates/base.html")
        assert "alpinejs" not in base.content
        assert "cdn.tailwindcss.com" not in base.content

    def test_missing_key_no_exception(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={})
        plugin.files(spec)
        plugin.directories(spec)
        plugin.dependencies(spec)

    def test_missing_key_core_paths(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        spec = _make_htmx_spec(config={})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "templates/base.html" in paths
        assert "templates/index.html" in paths
        assert "static/css/style.css" in paths


# ====================================================================
# AC-18: invalid css_framework value
# ====================================================================


class TestAC18_InvalidCssFramework:
    def test_invalid_choice_validation_error(self) -> None:
        from unittest.mock import MagicMock as _Mock

        from forge.generation.validation import ValidationEngine

        questions = [
            Question(
                key="css_framework",
                label="CSS Framework",
                question_type=QuestionType.CHOICE,
                options=["tailwind", "bootstrap", "none"],
            ),
        ]
        registry = _Mock()
        registry.resolve.return_value = _Mock()
        engine = ValidationEngine(registry)

        errors = engine.validate_plugin_config(
            "htmx", {"css_framework": "invalid"}, questions
        )
        assert len(errors) >= 1
        assert any(e.field == "css_framework" for e in errors)


# ====================================================================
# AC-19: display_name and description
# ====================================================================


class TestAC19_DisplayNameDescription:
    def test_display_name(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        assert plugin.display_name == "HTMX"

    def test_description_non_empty(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        plugin = HtmxPlugin()
        assert isinstance(plugin.description, str) and len(plugin.description) > 0


# ====================================================================
# AC-20: module export
# ====================================================================


class TestAC20_ModuleExport:
    def test_module_export(self) -> None:
        from forge.plugins.htmx import HtmxPlugin

        assert HtmxPlugin is not None

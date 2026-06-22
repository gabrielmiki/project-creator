from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from forge.domain import GeneratedFile, ProjectSpec, Question, QuestionType


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


def _make_react_spec(config: dict | None = None) -> ProjectSpec:
    """Build a ProjectSpec with frontend_id='react' and given config."""
    from forge.domain import Domain, TemplateDefinition

    return ProjectSpec(
        project_name="test-proj",
        template=TemplateDefinition(
            id="test",
            display_name="Test Template",
            description="",
            backend_id="fastapi",
            frontend_id="react",
        ),
        domains=[Domain(name="Web")],
        config=config or {},
    )


# ====================================================================
# AC-01: plugin.name
# ====================================================================


class TestAC1_Name:
    def test_name_returns_react(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        assert plugin.name == "react"

    def test_name_is_string(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        assert isinstance(plugin.name, str)


# ====================================================================
# AC-02a: files() core file paths
# ====================================================================


class TestAC2a_FilesCorePaths:
    def test_files_core_paths_present(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "src/App.tsx" in paths
        assert "src/main.tsx" in paths
        assert "public/index.html" in paths

    def test_files_returns_generated_file_list(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        files = plugin.files(spec)
        assert isinstance(files, list)
        assert all(isinstance(f, GeneratedFile) for f in files)

    def test_file_paths_are_path_objects(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        files = plugin.files(spec)
        for f in files:
            assert isinstance(f.path, Path)


# ====================================================================
# AC-02b: engine integration (simulated)
# ====================================================================


class TestAC2b_EngineIntegration:
    def test_engine_stages_core_files_and_deps(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        txn = _MockTransaction()

        for f in plugin.files(spec):
            txn.stage_file(str(f.path), f.content)
        for d in plugin.directories(spec):
            txn.stage_directory(d)
        for dep in plugin.dependencies(spec):
            txn.requirements.append(dep)

        staged = {call[0] for call in txn.stage_file_calls}
        assert "src/App.tsx" in staged
        assert "src/main.tsx" in staged
        assert "public/index.html" in staged
        assert "react" in txn.requirements
        assert "react-dom" in txn.requirements

    def test_engine_empty_config_no_error(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={})
        txn = _MockTransaction()

        for f in plugin.files(spec):
            txn.stage_file(str(f.path), f.content)
        for d in plugin.directories(spec):
            txn.stage_directory(d)
        for dep in plugin.dependencies(spec):
            txn.requirements.append(dep)

        staged = {call[0] for call in txn.stage_file_calls}
        assert "src/App.tsx" in staged
        assert "src/main.tsx" in staged
        assert "public/index.html" in staged
        assert "react" in txn.requirements
        assert "react-dom" in txn.requirements


# ====================================================================
# AC-03: questions()
# ====================================================================


class TestAC3_Questions:
    def test_questions_keys_include_all_five(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        keys = {q.key for q in plugin.questions()}
        assert "bundler" in keys
        assert "include_typescript" in keys
        assert "include_router" in keys
        assert "include_tailwind" in keys
        assert "state_management" in keys

    def test_bundler_question_type_and_options(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        qs = plugin.questions()
        bundler_q = next(q for q in qs if q.key == "bundler")
        assert bundler_q.question_type == QuestionType.CHOICE
        assert bundler_q.options == ["vite", "webpack"]

    def test_boolean_questions_are_boolean(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        qs = plugin.questions()
        ts_q = next(q for q in qs if q.key == "include_typescript")
        router_q = next(q for q in qs if q.key == "include_router")
        tailwind_q = next(q for q in qs if q.key == "include_tailwind")
        assert ts_q.question_type == QuestionType.BOOLEAN
        assert router_q.question_type == QuestionType.BOOLEAN
        assert tailwind_q.question_type == QuestionType.BOOLEAN

    def test_state_management_type_and_options(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        qs = plugin.questions()
        sm_q = next(q for q in qs if q.key == "state_management")
        assert sm_q.question_type == QuestionType.CHOICE
        assert sm_q.options == ["none", "zustand", "redux"]

    def test_question_keys_are_unique(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        keys = [q.key for q in plugin.questions()]
        assert len(keys) == len(set(keys))


# ====================================================================
# AC-04: bundler=vite
# ====================================================================


class TestAC4_BundlerVite:
    def test_bundler_vite_includes_vite_config(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"bundler": "vite"}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "vite.config.ts" in paths

    def test_bundler_vite_excludes_webpack_config(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"bundler": "vite"}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "webpack.config.js" not in paths


# ====================================================================
# AC-05: bundler=webpack
# ====================================================================


class TestAC5_BundlerWebpack:
    def test_bundler_webpack_includes_webpack_config(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"bundler": "webpack"}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "webpack.config.js" in paths

    def test_bundler_webpack_excludes_vite_config(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"bundler": "webpack"}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "vite.config.ts" not in paths


# ====================================================================
# AC-06: include_tailwind=True
# ====================================================================


class TestAC6_TailwindTrue:
    def test_tailwind_true_includes_config_files(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_tailwind": True}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "tailwind.config.js" in paths
        assert "postcss.config.js" in paths

    def test_tailwind_true_content_paths_ts(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(
            config={"react": {"include_tailwind": True, "include_typescript": True}}
        )
        tw_file = next(f for f in plugin.files(spec) if f.path.name == "tailwind.config.js")
        assert "./index.html" in tw_file.content
        assert "./src/**/*.{ts,tsx}" in tw_file.content

    def test_tailwind_true_content_paths_js(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(
            config={"react": {"include_tailwind": True, "include_typescript": False}}
        )
        tw_file = next(f for f in plugin.files(spec) if f.path.name == "tailwind.config.js")
        assert "./index.html" in tw_file.content
        assert "./src/**/*.{js,jsx}" in tw_file.content


# ====================================================================
# AC-07: include_tailwind=False or absent
# ====================================================================


class TestAC7_TailwindFalseOrAbsent:
    def test_tailwind_false_excludes_config(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_tailwind": False}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "tailwind.config.js" not in paths

    def test_tailwind_absent_excludes_config(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "tailwind.config.js" not in paths


# ====================================================================
# AC-08: include_typescript=True
# ====================================================================


class TestAC8_TypeScriptTrue:
    def test_ts_true_has_tsx_files(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_typescript": True}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "src/App.tsx" in paths
        assert "src/main.tsx" in paths

    def test_ts_true_no_jsx_files(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_typescript": True}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert all(".jsx" not in str(p) for p in paths)

    def test_ts_true_deps_include_typescript(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_typescript": True}})
        deps = plugin.dependencies(spec)
        assert "typescript" in deps
        assert "@types/react" in deps
        assert "@types/react-dom" in deps


# ====================================================================
# AC-09: include_typescript=False
# ====================================================================


class TestAC9_TypeScriptFalse:
    def test_ts_false_has_jsx_files(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_typescript": False}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "src/App.jsx" in paths
        assert "src/main.jsx" in paths

    def test_ts_false_no_tsx_or_ts_source_files(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_typescript": False}})
        paths = {str(f.path) for f in plugin.files(spec)}
        tsx_files = [p for p in paths if p.endswith(".tsx")]
        assert len(tsx_files) == 0
        ts_source = [p for p in paths if p.endswith(".ts") and "vite.config" not in p]
        assert len(ts_source) == 0

    def test_ts_false_deps_exclude_typescript(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_typescript": False}})
        deps = plugin.dependencies(spec)
        assert "typescript" not in deps
        assert "@types/react" not in deps
        assert "@types/react-dom" not in deps


# ====================================================================
# AC-10a: include_router=True
# ====================================================================


class TestAC10a_RouterTrue:
    def test_router_true_deps_include_router(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_router": True}})
        deps = plugin.dependencies(spec)
        assert "react-router-dom" in deps

    def test_router_true_generate_includes_router(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_router": True, "bundler": "vite"}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        calls = [call[0][0] for call in executor.run.call_args_list]
        assert any("react-router-dom" in cmd for cmd in calls)


# ====================================================================
# AC-10b: include_router=False or absent
# ====================================================================


class TestAC10b_RouterFalseOrAbsent:
    def test_router_false_excludes_router_dep(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"include_router": False}})
        deps = plugin.dependencies(spec)
        assert "react-router-dom" not in deps

    def test_router_absent_excludes_router_dep(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        deps = plugin.dependencies(spec)
        assert "react-router-dom" not in deps


# ====================================================================
# AC-11: directories()
# ====================================================================


class TestAC11_Directories:
    def test_directories_returns_expected_dirs(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        dirs = plugin.directories(spec)
        assert "src/" in dirs
        assert "src/components/" in dirs
        assert "src/pages/" in dirs
        assert "public/" in dirs


# ====================================================================
# AC-12a: dependencies() base set
# ====================================================================


class TestAC12a_DepsBaseSet:
    def test_deps_base_includes_react_and_typescript(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        deps = plugin.dependencies(spec)
        assert "react" in deps
        assert "react-dom" in deps
        assert "typescript" in deps
        assert "@types/react" in deps
        assert "@types/react-dom" in deps

    def test_deps_base_excludes_extras(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        deps = plugin.dependencies(spec)
        assert "react-router-dom" not in deps
        assert "tailwindcss" not in deps
        assert "zustand" not in deps
        assert "@reduxjs/toolkit" not in deps


# ====================================================================
# AC-12b: dependencies() with zustand
# ====================================================================


class TestAC12b_DepsZustand:
    def test_deps_zustand_includes_zustand(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"state_management": "zustand"}})
        deps = plugin.dependencies(spec)
        assert "zustand" in deps

    def test_deps_zustand_preserves_base(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"state_management": "zustand"}})
        deps = plugin.dependencies(spec)
        assert "react" in deps
        assert "react-dom" in deps


# ====================================================================
# AC-12c: dependencies() with redux
# ====================================================================


class TestAC12c_DepsRedux:
    def test_deps_redux_includes_redux_packages(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"state_management": "redux"}})
        deps = plugin.dependencies(spec)
        assert "@reduxjs/toolkit" in deps
        assert "react-redux" in deps

    def test_deps_redux_preserves_base(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"state_management": "redux"}})
        deps = plugin.dependencies(spec)
        assert "react" in deps
        assert "react-dom" in deps


# ====================================================================
# AC-13: generate() default config
# ====================================================================


class TestAC13_GenerateDefault:
    def test_generate_default_calls_scaffold(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"bundler": "vite"}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        calls = [call[0][0] for call in executor.run.call_args_list]
        assert any("npm" in cmd and "create" in cmd and "vite" in cmd for cmd in calls)

    def test_generate_default_template_is_react_ts(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"bundler": "vite"}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        calls = [call[0][0] for call in executor.run.call_args_list]
        assert any("--template" in cmd and "react-ts" in cmd for cmd in calls)

    def test_generate_passes_cwd(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"bundler": "vite"}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        assert any(
            call[1].get("cwd") == target_dir for call in executor.run.call_args_list
        )


# ====================================================================
# AC-14a: generate() with router
# ====================================================================


class TestAC14a_GenerateRouter:
    def test_generate_router_includes_router_dom(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(
            config={"react": {"include_router": True, "bundler": "vite"}}
        )
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        calls = [call[0][0] for call in executor.run.call_args_list]
        assert any("react-router-dom" in cmd for cmd in calls)


# ====================================================================
# AC-14b: generate() with tailwind
# ====================================================================


class TestAC14b_GenerateTailwind:
    def test_generate_tailwind_includes_tailwindcss(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(
            config={"react": {"include_tailwind": True, "bundler": "vite"}}
        )
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        calls = [call[0][0] for call in executor.run.call_args_list]
        assert any("tailwindcss" in cmd for cmd in calls)


# ====================================================================
# AC-14c: generate() with zustand
# ====================================================================


class TestAC14c_GenerateZustand:
    def test_generate_zustand_includes_zustand(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(
            config={"react": {"state_management": "zustand", "bundler": "vite"}}
        )
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        calls = [call[0][0] for call in executor.run.call_args_list]
        assert any("zustand" in cmd for cmd in calls)


# ====================================================================
# AC-14d: generate() with redux
# ====================================================================


class TestAC14d_GenerateRedux:
    def test_generate_redux_includes_redux_toolkit(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(
            config={"react": {"state_management": "redux", "bundler": "vite"}}
        )
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        calls = [call[0][0] for call in executor.run.call_args_list]
        assert any("@reduxjs/toolkit" in cmd for cmd in calls)


# ====================================================================
# AC-14e: generate() with no TypeScript
# ====================================================================


class TestAC14e_GenerateNoTypeScript:
    def test_generate_no_ts_uses_react_template(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(
            config={"react": {"include_typescript": False, "bundler": "vite"}}
        )
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        calls = [call[0][0] for call in executor.run.call_args_list]
        assert any("--template" in cmd and "react" in cmd for cmd in calls)

    def test_generate_no_ts_does_not_use_react_ts(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(
            config={"react": {"include_typescript": False, "bundler": "vite"}}
        )
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        calls = [call[0][0] for call in executor.run.call_args_list]
        assert all("react-ts" not in cmd for cmd in calls)


# ====================================================================
# AC-14f: generate() with webpack is no-op
# ====================================================================


class TestAC14f_GenerateWebpackNoop:
    def test_generate_webpack_does_not_call_executor(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {"bundler": "webpack"}})
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_not_called()

    def test_generate_webpack_with_ts_false_does_not_call_executor(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(
            config={"react": {"bundler": "webpack", "include_typescript": False}}
        )
        executor: MagicMock = MagicMock()
        target_dir = Path("/tmp")

        plugin.generate(spec, target_dir, executor)

        executor.run.assert_not_called()


# ====================================================================
# AC-15: empty config dict → defaults
# ====================================================================


class TestAC15_EmptyConfigDefaults:
    def test_empty_config_defaults_vite(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "vite.config.ts" in paths

    def test_empty_config_defaults_typescript_true(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "src/App.tsx" in paths

    def test_empty_config_defaults_tailwind_false(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "tailwind.config.js" not in paths

    def test_empty_config_defaults_state_management_none(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        deps = plugin.dependencies(spec)
        assert "zustand" not in deps
        assert "@reduxjs/toolkit" not in deps

    def test_empty_config_no_exception(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={"react": {}})
        plugin.files(spec)
        plugin.directories(spec)
        plugin.dependencies(spec)


# ====================================================================
# AC-16: missing "react" config key
# ====================================================================


class TestAC16_MissingConfigKey:
    def test_missing_key_defaults_vite(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "vite.config.ts" in paths

    def test_missing_key_defaults_typescript(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={})
        paths = {str(f.path) for f in plugin.files(spec)}
        assert "src/App.tsx" in paths

    def test_missing_key_does_not_raise(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        spec = _make_react_spec(config={})
        plugin.files(spec)
        plugin.directories(spec)
        plugin.dependencies(spec)


# ====================================================================
# AC-17: invalid bundler value → ValidationEngine error
# ====================================================================


class TestAC17_InvalidBundler:
    def test_invalid_bundler_validation_error(self) -> None:
        from unittest.mock import MagicMock as _Mock

        from forge.generation.validation import ValidationEngine

        questions = [
            Question(
                key="bundler",
                label="Bundler",
                question_type=QuestionType.CHOICE,
                options=["vite", "webpack"],
            ),
        ]
        registry = _Mock()
        registry.resolve.return_value = _Mock()
        engine = ValidationEngine(registry)

        errors = engine.validate_plugin_config("react", {"bundler": "invalid"}, questions)
        assert len(errors) >= 1
        assert any(e.field == "bundler" for e in errors)


# ====================================================================
# AC-18: display_name and description
# ====================================================================


class TestAC18_DisplayNameDescription:
    def test_display_name(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        assert plugin.display_name == "React"

    def test_description_is_non_empty(self) -> None:
        from forge.plugins.react import ReactPlugin

        plugin = ReactPlugin()
        assert isinstance(plugin.description, str) and len(plugin.description) > 0


# ====================================================================
# AC-19: module export
# ====================================================================


class TestAC19_ModuleExport:
    def test_module_export(self) -> None:
        from forge.plugins.react import ReactPlugin

        assert ReactPlugin is not None

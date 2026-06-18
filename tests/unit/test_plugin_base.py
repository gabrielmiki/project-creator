from __future__ import annotations

import ast
import pathlib

import pytest

from forge.domain import GeneratedFile, ProjectSpec, Question
from forge.infrastructure import ProcessExecutor
from forge.plugins.base import (
    CommandRunner,
    Configurable,
    DependencyProvider,
    FileProvider,
    PluginBase,
)


class TestAC1_FileProviderMixin:
    def test_file_only_plugin_instantiates(self) -> None:
        class FileOnlyPlugin(PluginBase, FileProvider):
            name = "file-only"
            display_name = "File Only"
            description = "A plugin that only provides files"

            def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
                return []

            def directories(self, spec: ProjectSpec) -> list[str]:
                return []

        p = FileOnlyPlugin()
        assert isinstance(p, PluginBase)
        assert isinstance(p, FileProvider)

    def test_isinstance_false_for_uninherited_mixins(self) -> None:
        class FileOnlyPlugin(PluginBase, FileProvider):
            name = "file-only"
            display_name = "File Only"
            description = "A plugin that only provides files"

            def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
                return []

            def directories(self, spec: ProjectSpec) -> list[str]:
                return []

        p = FileOnlyPlugin()
        assert not isinstance(p, CommandRunner)
        assert not isinstance(p, Configurable)
        assert not isinstance(p, DependencyProvider)

    def test_requires_and_run_after_defaults(self) -> None:
        class FileOnlyPlugin(PluginBase, FileProvider):
            name = "file-only"
            display_name = "File Only"
            description = "A plugin that only provides files"

            def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
                return []

            def directories(self, spec: ProjectSpec) -> list[str]:
                return []

        p = FileOnlyPlugin()
        assert p.requires == []
        assert p.run_after == []

    def test_type_error_when_file_provider_method_missing(self) -> None:
        class MissingFiles(PluginBase, FileProvider):
            name = "missing-files"
            display_name = "Missing Files"
            description = "Missing files() method"

            def directories(self, spec: ProjectSpec) -> list[str]:
                return []

        with pytest.raises(TypeError):
            MissingFiles()


class TestAC2_IsInstanceUninherited:
    def test_not_instance_of_command_runner(self) -> None:
        class NoCommandPlugin(PluginBase, FileProvider):
            name = "no-command"
            display_name = "No Command"
            description = "Does not inherit CommandRunner"

            def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
                return []

            def directories(self, spec: ProjectSpec) -> list[str]:
                return []

        p = NoCommandPlugin()
        assert not isinstance(p, CommandRunner)

    def test_instance_of_inherited_mixin(self) -> None:
        class FullPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
            name = "full"
            display_name = "Full Plugin"
            description = "Implements all mixins"

            def questions(self) -> list[Question]:
                return []

            def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
                return []

            def directories(self, spec: ProjectSpec) -> list[str]:
                return []

            def generate(self, spec: ProjectSpec, target_dir: pathlib.Path, executor: ProcessExecutor) -> None:
                pass

            def dependencies(self, spec: ProjectSpec) -> list[str]:
                return []

        p = FullPlugin()
        assert isinstance(p, CommandRunner)

    def test_instance_of_plugin_base(self) -> None:
        class BarePlugin(PluginBase, FileProvider):
            name = "bare"
            display_name = "Bare"
            description = "Minimal plugin"

            def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
                return []

            def directories(self, spec: ProjectSpec) -> list[str]:
                return []

        p = BarePlugin()
        assert isinstance(p, PluginBase)


class TestAC3_PluginBaseAbstract:
    def test_cannot_instantiate_plugin_base_directly(self) -> None:
        with pytest.raises(TypeError):
            PluginBase()  # type: ignore[abstract]

    def test_concrete_subclass_instantiates(self) -> None:
        class ConcretePlugin(PluginBase, FileProvider):
            name = "concrete"
            display_name = "Concrete"
            description = "A concrete plugin"

            def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
                return []

            def directories(self, spec: ProjectSpec) -> list[str]:
                return []

        p = ConcretePlugin()
        assert p.name == "concrete"

    def test_error_message_mentions_abstract_methods(self) -> None:
        with pytest.raises(TypeError) as exc:
            PluginBase()  # type: ignore[abstract]
        assert "abstract" in str(exc.value).lower()


class TestAC4_NoCrossLayerImports:
    FORBIDDEN_PREFIXES = (
        "forge.ui",
        "forge.generation",
        "forge.infrastructure",
    )

    ALLOWED_PREFIXES = ("forge.domain",)

    # base.py defines the CommandRunner mixin whose generate() signature
    # references ProcessExecutor. This is the only file exempted from the
    # infrastructure import ban — concrete plugins must NOT import infrastructure.
    INFRA_EXEMPT_FILES = {"base.py"}

    def _plugins_source_files(self) -> list[pathlib.Path]:
        here = pathlib.Path(__file__).resolve().parent.parent.parent
        plugins_dir = here / "src" / "forge" / "plugins"
        files = sorted(plugins_dir.rglob("*.py"))
        assert files, (
            f"No source files found in {plugins_dir}. Expected at least base.py and __init__.py."
        )
        return files

    def test_no_forbidden_imports(self) -> None:
        for source_file in self._plugins_source_files():
            tree = ast.parse(source_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._check_forbidden(alias.name, source_file.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self._check_forbidden(node.module, source_file.name)

    def test_allowed_domain_imports_are_permitted(self) -> None:
        for source_file in self._plugins_source_files():
            tree = ast.parse(source_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("forge.domain"):
                        break
            else:
                pytest.fail(
                    f"{source_file.name} does not import from forge.domain "
                    f"— mixin signatures require Question, ProjectSpec, GeneratedFile"
                )

    def _check_forbidden(self, module_name: str, filename: str) -> None:
        for prefix in self.FORBIDDEN_PREFIXES:
            if module_name == prefix or module_name.startswith(prefix + "."):
                if prefix == "forge.infrastructure" and filename in self.INFRA_EXEMPT_FILES:
                    continue
                pytest.fail(f"{filename} imports forbidden module: {module_name}")

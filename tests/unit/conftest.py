from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from forge.domain import GeneratedFile, ProjectSpec, Question
from forge.infrastructure import ProcessExecutor
from forge.plugins.base import (
    CommandRunner,
    Configurable,
    DependencyProvider,
    FileProvider,
    PluginBase,
)
from tests.unit._shared import (
    MockTransaction,
    make_empty_spec,
    make_spec,
)

# ── Shared Fixtures ─────────────────────────────────────────────────


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Session-scoped QApplication for UI tests."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    return tmp_path / "output"


@pytest.fixture
def txn() -> MockTransaction:
    return MockTransaction()


@pytest.fixture
def progress() -> MagicMock:
    p: MagicMock = MagicMock()
    p.should_cancel.return_value = False
    return p


@pytest.fixture
def spec() -> ProjectSpec:
    return make_spec(backend_id="")


@pytest.fixture
def empty_spec() -> ProjectSpec:
    return make_empty_spec()


# ── Conftest Plugin Classes (pre-existing) ──────────────────────────


class FileOnlyPlugin(PluginBase, FileProvider):
    name = "file-only"
    display_name = "File Only"
    description = "A plugin that only provides files"

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        return []

    def directories(self, spec: ProjectSpec) -> list[str]:
        return []


class ConfigOnlyPlugin(PluginBase, Configurable):
    name = "config-only"
    display_name = "Config Only"
    description = "A plugin that only provides config questions"

    def questions(self) -> list[Question]:
        return []


class CommandOnlyPlugin(PluginBase, CommandRunner):
    name = "command-only"
    display_name = "Command Only"
    description = "A plugin that only runs commands"

    def generate(self, spec: ProjectSpec, target_dir: Path, executor: ProcessExecutor) -> None:
        pass


class DependencyOnlyPlugin(PluginBase, DependencyProvider):
    name = "dep-only"
    display_name = "Dependency Only"
    description = "A plugin that only provides dependencies"

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        return []


class FullPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "full"
    display_name = "Full Plugin"
    description = "A plugin that implements all mixins"

    def questions(self) -> list[Question]:
        return []

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        return []

    def directories(self, spec: ProjectSpec) -> list[str]:
        return []

    def generate(self, spec: ProjectSpec, target_dir: Path, executor: ProcessExecutor) -> None:
        pass

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        return []


@pytest.fixture
def file_plugin() -> FileOnlyPlugin:
    return FileOnlyPlugin()


@pytest.fixture
def config_plugin() -> ConfigOnlyPlugin:
    return ConfigOnlyPlugin()


@pytest.fixture
def command_plugin() -> CommandOnlyPlugin:
    return CommandOnlyPlugin()


@pytest.fixture
def dependency_plugin() -> DependencyOnlyPlugin:
    return DependencyOnlyPlugin()


@pytest.fixture
def full_plugin() -> FullPlugin:
    return FullPlugin()

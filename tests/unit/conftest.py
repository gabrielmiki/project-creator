from __future__ import annotations

from pathlib import Path

import pytest

from forge.domain import GeneratedFile, ProjectSpec, Question
from forge.plugins.base import (
    CommandRunner,
    Configurable,
    DependencyProvider,
    FileProvider,
    PluginBase,
)


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

    def generate(self, spec: ProjectSpec, target_dir: Path) -> None:
        pass


class DependencyOnlyPlugin(PluginBase, DependencyProvider):
    name = "dep-only"
    display_name = "Dependency Only"
    description = "A plugin that only provides dependencies"

    def dependencies(self) -> list[str]:
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

    def generate(self, spec: ProjectSpec, target_dir: Path) -> None:
        pass

    def dependencies(self) -> list[str]:
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

from __future__ import annotations

from pathlib import Path

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
from tests.unit._shared import make_spec


class AllMixinsPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "all-mixins"
    display_name = "All Mixins"
    description = "Implements all 4 capability mixins"

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


# ── Shared Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def minimal_plugin() -> AllMixinsPlugin:
    return AllMixinsPlugin()


@pytest.fixture
def spec_factory():
    return make_spec


@pytest.fixture
def user_plugin_dir(temp_dir: Path) -> Path:
    plugins_dir = temp_dir / ".plugins"
    plugins_dir.mkdir()

    # Format 1: flat .py file
    (plugins_dir / "user_plugin.py").write_text(
        "from forge.plugins.base import PluginBase\n"
        "class _UserPlugin(PluginBase):\n"
        '    name = "user-plugin"\n'
        '    display_name = "User Plugin"\n'
        '    description = ""\n'
        "    def files(self, spec): return []\n"
        "    def directories(self, spec): return []\n"
        "plugin = _UserPlugin()\n"
    )

    # Format 2: subdirectory with plugin.py (T-005 deferred)
    sub_dir = plugins_dir / "sub_plugin"
    sub_dir.mkdir()
    (sub_dir / "plugin.py").write_text(
        "from forge.plugins.base import PluginBase\n"
        "class _SubPlugin(PluginBase):\n"
        '    name = "sub-plugin"\n'
        '    display_name = "Sub Plugin"\n'
        '    description = ""\n'
        "    def files(self, spec): return []\n"
        "    def directories(self, spec): return []\n"
        "plugin = _SubPlugin()\n"
    )

    return plugins_dir


@pytest.fixture
def txn(temp_dir: Path):
    from forge.infrastructure.transaction import GenerationTransaction

    output = temp_dir / "output"
    output.mkdir(exist_ok=True)
    return GenerationTransaction(output)

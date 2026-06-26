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


# ── T-017 Pipeline Fixtures ──────────────────────────────────────────


@pytest.fixture(scope="module")
def pipeline_registry():
    """Module-scoped real registry. Named pipeline_registry to avoid
    collision with test_validation.py's module-scoped real_registry."""
    from forge.generation.registry import PluginRegistry

    reg = PluginRegistry()
    reg.discover()
    return reg


@pytest.fixture
def validation(pipeline_registry) -> object:
    from forge.generation.validation import ValidationEngine

    return ValidationEngine(pipeline_registry)


@pytest.fixture
def mock_executor():
    """Mock ProcessExecutor — avoids real uv add subprocess calls
    during integration tests."""
    from unittest.mock import MagicMock

    return MagicMock()


@pytest.fixture
def progress():
    from forge.generation.progress import MockProgressReporter

    return MockProgressReporter()


@pytest.fixture
def orchestrator(pipeline_registry, validation, mock_executor):
    from forge.generation.orchestrator import Orchestrator

    return Orchestrator(pipeline_registry, validation, executor=mock_executor)


@pytest.fixture(scope="session")
def qapp() -> object:
    """Session-scoped QApplication for GUI integration tests."""
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def full_spec(spec_factory) -> ProjectSpec:
    spec = spec_factory(backend_id="fastapi", frontend_id="react")
    spec.config = {
        "fastapi": {"orm": "sqlalchemy", "auth": False, "include_alembic": False},
        "react": {},
    }
    return spec


@pytest.fixture
def django_htmx_spec(spec_factory) -> ProjectSpec:
    spec = spec_factory(backend_id="django", frontend_id="htmx")
    spec.config = {
        "django": {"database": "sqlite", "include_drf": False},
        "htmx": {},
    }
    return spec


@pytest.fixture
def worker(qapp, orchestrator, full_spec, temp_dir) -> object:  # noqa: ARG001
    from forge.ui.workers import GenerationWorker

    return GenerationWorker(
        orchestrator=orchestrator,
        spec=full_spec,
        output_dir=temp_dir / "output",
    )


@pytest.fixture
def fastapi_spec(spec_factory):
    spec = spec_factory(backend_id="fastapi")
    spec.config = {"fastapi": {}}
    return spec


@pytest.fixture
def cli_spec_json(temp_dir: Path) -> Path:
    import json

    spec = {
        "project_name": "test-project",
        "template": {
            "id": "fastapi-only",
            "display_name": "FastAPI Only",
            "description": "",
            "backend_id": "fastapi",
            "frontend_id": None,
        },
        "domains": [{"name": "users"}],
        "config": {"fastapi": {"orm": "sqlalchemy", "auth": False, "include_alembic": False}},
    }
    path = temp_dir / "spec.json"
    path.write_text(json.dumps(spec))
    return path

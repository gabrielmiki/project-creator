from pathlib import Path
from typing import Any

from forge.domain import ProjectSpec
from forge.generation.progress import ProgressReporter
from forge.infrastructure import GenerationTransaction as _  # noqa: F401


class SharedStructureScaffolder:
    name = "shared-structure-scaffolder"

    def run(
        self,
        spec: ProjectSpec,
        output_dir: Path,
        txn: Any,
        progress: ProgressReporter,
    ) -> None:
        readme = f"# {spec.project_name}\n\n"
        txn.stage_file("README.md", readme)

        pyproject = f"""[project]
name = "{spec.project_name}"
version = "0.1.0"
description = ""
requires-python = ">=3.12"
"""
        txn.stage_file("pyproject.toml", pyproject)

        gitignore = """__pycache__/
*.py[cod]
*.egg-info/
.env
.venv/
venv/
dist/
build/
"""
        txn.stage_file(".gitignore", gitignore)

        env_example = """APP_ENV=development
APP_DEBUG=true
DATABASE_URL=sqlite:///app.db
"""
        txn.stage_file(".env.example", env_example)

        python_version = "3.12"
        txn.stage_file(".python-version", python_version)

        txn.stage_file("docs/index.md", f"# {spec.project_name}\n\nProject documentation.\n")
        txn.stage_file("docs/architecture.md", "# Architecture\n\nArchitecture documentation.\n")

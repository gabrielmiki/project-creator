from pathlib import Path
from typing import Any

from forge.domain import ProjectSpec
from forge.generation.progress import ProgressReporter
from forge.infrastructure import GenerationTransaction as _  # noqa: F401


class JustfileGenerator:
    name = "justfile-generator"

    def run(
        self,
        spec: ProjectSpec,
        output_dir: Path,
        txn: Any,
        progress: ProgressReporter,
    ) -> None:
        content = """# Justfile for {{ project_name }}
# Default commands for development

setup:
    echo "Setting up project..."

dev:
    echo "Starting development server..."

test:
    echo "Running tests..."

lint:
    echo "Running linter..."

format:
    echo "Formatting code..."

build:
    echo "Building project..."
"""
        content = content.replace("{{ project_name }}", spec.project_name)
        txn.stage_file("justfile", content)

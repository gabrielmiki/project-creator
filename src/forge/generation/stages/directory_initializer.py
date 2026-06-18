from pathlib import Path
from typing import Any

from forge.domain import ProjectSpec
from forge.generation.errors import DirectoryNotEmptyError
from forge.generation.progress import ProgressReporter
from forge.infrastructure import GenerationTransaction as _  # noqa: F401


class DirectoryInitializer:
    name = "directory-initializer"

    def run(
        self,
        spec: ProjectSpec,
        output_dir: Path,
        txn: Any,
        progress: ProgressReporter,
    ) -> None:
        if not output_dir.exists():
            return

        entries = [e for e in output_dir.iterdir() if not e.name.startswith(".")]
        if entries:
            raise DirectoryNotEmptyError(f"Output directory '{output_dir}' exists and is not empty")

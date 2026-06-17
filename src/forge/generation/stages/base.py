from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from forge.domain import ProjectSpec
from forge.generation.progress import ProgressReporter
from forge.infrastructure import GenerationTransaction as _  # noqa: F401


class GenerationStage(ABC):
    name: str

    @abstractmethod
    def run(
        self,
        spec: ProjectSpec,
        output_dir: Path,
        txn: Any,
        progress: ProgressReporter,
    ) -> None: ...

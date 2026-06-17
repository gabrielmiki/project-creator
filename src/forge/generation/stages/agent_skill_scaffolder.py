from pathlib import Path
from typing import Any

from forge.domain import ProjectSpec
from forge.generation.progress import ProgressReporter
from forge.infrastructure import GenerationTransaction as _  # noqa: F401


class AgentSkillScaffolder:
    name = "agent-skill-scaffolder"

    def run(
        self,
        spec: ProjectSpec,
        output_dir: Path,
        txn: Any,
        progress: ProgressReporter,
    ) -> None:
        txn.stage_directory(".opencode/skills/")
        txn.stage_directory(".opencode/agents/")
        txn.stage_directory(".opencode/handoffs/")

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class GeneratedFile:
    path: Path
    content: str
    executable: bool = False


@dataclass
class DurationEstimate:
    estimated_seconds: int
    has_slow_steps: bool
    slow_step_details: list[str]

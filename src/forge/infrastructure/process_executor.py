from __future__ import annotations

import subprocess
from pathlib import Path


class ProcessExecutor:
    def run(self, cmd: list[str], cwd: Path | None = None) -> None:
        subprocess.check_call(cmd, cwd=cwd)

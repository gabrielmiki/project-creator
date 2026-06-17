from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Literal


class GenerationTransaction:
    def __init__(self, output_dir: Path) -> None:
        self.staging: Path = output_dir / ".forge-staging"
        self.manifest: list[Path] = []
        self.requirements: list[str] = []
        self._output_dir: Path = output_dir
        self._checkpoints: list[Path] = []
        self._committed: bool = False

    def stage_file(self, relative_path: str, content: str) -> Path:
        rel = Path(relative_path)
        dst = self.staging / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content)
        if rel not in self.manifest:
            self.manifest.append(rel)
        return dst

    def stage_directory(self, relative_path: str) -> Path:
        rel = Path(relative_path)
        dst = self.staging / rel
        dst.mkdir(parents=True, exist_ok=True)
        if rel not in self.manifest:
            self.manifest.append(rel)
        return dst

    def add_checkpoint(self, paths: list[Path]) -> None:
        self._checkpoints.extend(paths)

    @staticmethod
    def _is_subpath(child: Path, parent: Path) -> bool:
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    def commit(self) -> None:
        if self._committed:
            raise RuntimeError("Transaction has already been committed")

        for rel in self.manifest:
            dst = self._output_dir / rel
            if dst.exists():
                raise FileExistsError(f"Target already exists: {dst}")

        dir_rels = {rel for rel in self.manifest if (self.staging / rel).is_dir()}

        for rel in self.manifest:
            src = self.staging / rel
            if src.is_file():
                if any(self._is_subpath(rel, d) for d in dir_rels):
                    continue
                dst = self._output_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.rename(str(src), str(dst))

        for rel in self.manifest:
            src = self.staging / rel
            if src.is_dir():
                dst = self._output_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.rename(str(src), str(dst))

        if self.staging.exists():
            shutil.rmtree(self.staging)

        self._committed = True

    def rollback(self) -> None:
        if self.staging.exists():
            shutil.rmtree(self.staging)

        for path in self._checkpoints:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

    def __enter__(self) -> GenerationTransaction:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> Literal[False]:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False

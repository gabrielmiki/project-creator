from abc import ABC, abstractmethod
from pathlib import Path

from forge.domain import GeneratedFile, ProjectSpec, Question


class PluginBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def display_name(self) -> str: ...
    @property
    @abstractmethod
    def description(self) -> str: ...

    requires: list[str] = []
    run_after: list[str] = []

    def __init__(self) -> None:
        self.requires = list(self.__class__.requires or [])
        self.run_after = list(self.__class__.run_after or [])


class Configurable(ABC):
    @abstractmethod
    def questions(self) -> list[Question]: ...


class FileProvider(ABC):
    @abstractmethod
    def files(self, spec: ProjectSpec) -> list[GeneratedFile]: ...
    @abstractmethod
    def directories(self, spec: ProjectSpec) -> list[str]: ...


class CommandRunner(ABC):
    @abstractmethod
    def generate(self, spec: ProjectSpec, target_dir: Path) -> None: ...


class DependencyProvider(ABC):
    @abstractmethod
    def dependencies(self) -> list[str]: ...

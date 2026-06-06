from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Domain:
    name: str
    slug: str = ""

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = re.sub(r"\s+", "-", self.name.strip().lower())


@dataclass
class TemplateDefinition:
    id: str
    display_name: str
    description: str
    backend_id: str
    frontend_id: str | None = None


@dataclass
class ProjectSpec:
    project_name: str
    template: TemplateDefinition
    domains: list[Domain]
    config: dict[str, dict[str, Any]]

    def plugin_config(self, plugin_id: str) -> dict[str, Any]:
        if plugin_id not in self.config:
            raise KeyError(f"Plugin '{plugin_id}' has no configuration")
        return self.config[plugin_id]

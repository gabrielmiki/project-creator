from __future__ import annotations

from pathlib import Path
from typing import Any

from forge.domain import GeneratedFile, ProjectSpec, Question, QuestionType
from forge.plugins.base import (
    CommandRunner,
    Configurable,
    DependencyProvider,
    FileProvider,
    PluginBase,
)

_BASE_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{% block title %}}My App{{% endblock %}}</title>
    {cdn_section}
</head>
<body>
    {{% block content %}}{{% endblock %}}
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    {{% block scripts %}}{{% endblock %}}
</body>
</html>
"""

_INDEX_HTML = """\
{% extends "base.html" %}
{% block content %}
<h1 class="text-3xl font-bold">Hello World</h1>
{% endblock %}
"""

_STYLE_CSS = """\
/* Custom styles */
"""

_TAILWIND_CONFIG_JS = """\
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./templates/**/*.html'],
  theme: {
    extend: {},
  },
  plugins: [],
};
"""

_POSTCSS_CONFIG_JS = """\
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""


class HtmxPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "htmx"
    display_name = "HTMX"
    description = "HTMX + Alpine.js frontend with Jinja2 templates"
    requires: list[str] = []

    @staticmethod
    def _config(spec: ProjectSpec) -> dict[str, Any]:
        return spec.config.get("htmx", {})

    def questions(self) -> list[Question]:
        return [
            Question(
                key="include_alpine",
                label="Include Alpine.js",
                question_type=QuestionType.BOOLEAN,
                required=True,
                default=False,
                description="Include Alpine.js for interactive components",
            ),
            Question(
                key="include_tailwind",
                label="Include Tailwind CSS build tooling",
                question_type=QuestionType.BOOLEAN,
                required=True,
                default=False,
                description="Include Tailwind CSS build tooling (tailwind.config.js, postcss)",
            ),
            Question(
                key="css_framework",
                label="CSS Framework",
                question_type=QuestionType.CHOICE,
                required=True,
                default="none",
                description="CSS framework CDN to include in base.html",
                options=["tailwind", "bootstrap", "none"],
            ),
        ]

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        config = self._config(spec)
        include_alpine = config.get("include_alpine", False)
        include_tailwind = config.get("include_tailwind", False)
        css_framework = config.get("css_framework", "none")

        cdn_tags: list[str] = []
        tailwind_cdn_added = False

        if include_alpine:
            cdn_tags.append(
                '<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js"></script>'
            )

        if include_tailwind:
            cdn_tags.append('<script src="https://cdn.tailwindcss.com"></script>')
            tailwind_cdn_added = True

        if css_framework == "tailwind" and not tailwind_cdn_added:
            cdn_tags.append('<script src="https://cdn.tailwindcss.com"></script>')
        elif css_framework == "bootstrap":
            cdn_tags.append(
                '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">'
            )

        cdn_section = "\n    ".join(cdn_tags)
        base_content = _BASE_HTML_TEMPLATE.format(cdn_section=cdn_section)

        files = [
            GeneratedFile(path=Path("templates/base.html"), content=base_content),
            GeneratedFile(path=Path("templates/index.html"), content=_INDEX_HTML),
            GeneratedFile(path=Path("static/css/style.css"), content=_STYLE_CSS),
        ]

        if include_tailwind:
            files.append(
                GeneratedFile(path=Path("tailwind.config.js"), content=_TAILWIND_CONFIG_JS)
            )
            files.append(GeneratedFile(path=Path("postcss.config.js"), content=_POSTCSS_CONFIG_JS))

        return files

    def directories(self, spec: ProjectSpec) -> list[str]:
        return ["templates/", "static/css/", "static/js/"]

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        return []

    def generate(self, spec: ProjectSpec, target_dir: Path, executor: Any) -> None:
        pass

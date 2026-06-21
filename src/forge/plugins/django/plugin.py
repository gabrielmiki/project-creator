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

_MANAGE_PY = """\
#!/usr/bin/env python
\"\"\"Django's command-line utility for administrative tasks.\"\"\"

import os
import sys


def main():
    \"\"\"Run administrative tasks.\"\"\"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
"""

_CONFIG_INIT_PY = '"""Configuration package."""\n'

_URLS_PY = """\
\"\"\"URL configuration.\"\"\"

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
"""

_WSGI_PY = """\
\"\"\"WSGI application.\"\"\"

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
"""


def _build_settings(database: str, include_drf: bool) -> str:
    """Build the Django settings.py content based on configuration."""
    drf_app = '    "rest_framework",' if include_drf else ""

    engine_map = {
        "postgresql": "django.db.backends.postgresql",
        "sqlite": "django.db.backends.sqlite3",
        "mysql": "django.db.backends.mysql",
    }
    engine = engine_map.get(database, "django.db.backends.sqlite3")

    if database == "sqlite":
        db_config = f"""\
DATABASES = {{
    "default": {{
        "ENGINE": "{engine}",
        "NAME": BASE_DIR / "db.sqlite3",
    }}
}}"""
    else:
        db_config = f"""\
DATABASES = {{
    "default": {{
        "ENGINE": "{engine}",
        "NAME": "test_proj",
        "USER": "{"postgres" if database == "postgresql" else "root"}",
        "PASSWORD": "{"postgres" if database == "postgresql" else "root"}",
        "HOST": "localhost",
        "PORT": "{"5432" if database == "postgresql" else "3306"}",
    }}
}}"""

    return f"""\
\"\"\"Django settings.\"\"\"

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-change-me-in-production"

DEBUG = True

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
{drf_app}
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {{
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        }},
    }},
]

WSGI_APPLICATION = "config.wsgi.application"

{db_config}

AUTH_PASSWORD_VALIDATORS = [
    {{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}},
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
"""


class DjangoPlugin(PluginBase, Configurable, FileProvider, CommandRunner, DependencyProvider):
    name = "django"
    display_name = "Django"
    description = "Django backend with choice of database + DRF"
    requires: list[str] = []

    @staticmethod
    def _config(spec: ProjectSpec) -> dict[str, Any]:
        return spec.config.get("django", {})

    def questions(self) -> list[Question]:
        return [
            Question(
                key="database",
                label="Database",
                question_type=QuestionType.CHOICE,
                required=True,
                default="sqlite",
                description="Database backend for Django",
                options=["postgresql", "sqlite", "mysql"],
            ),
            Question(
                key="include_drf",
                label="Include Django REST Framework",
                question_type=QuestionType.BOOLEAN,
                required=True,
                default=False,
                description="Include Django REST Framework for building APIs",
            ),
        ]

    def files(self, spec: ProjectSpec) -> list[GeneratedFile]:
        config = self._config(spec)
        database = config.get("database", "sqlite")
        include_drf = config.get("include_drf", False)

        reqs = ["django>=5.1"]
        if database == "postgresql":
            reqs.append("psycopg2-binary>=2.9")
        elif database == "mysql":
            reqs.append("mysqlclient>=2.2")
        if include_drf:
            reqs.append("djangorestframework>=3.15")

        settings_content = _build_settings(database, include_drf)

        return [
            GeneratedFile(path=Path("manage.py"), content=_MANAGE_PY, executable=True),
            GeneratedFile(path=Path("config/__init__.py"), content=_CONFIG_INIT_PY),
            GeneratedFile(path=Path("config/settings.py"), content=settings_content),
            GeneratedFile(path=Path("config/urls.py"), content=_URLS_PY),
            GeneratedFile(path=Path("config/wsgi.py"), content=_WSGI_PY),
            GeneratedFile(path=Path("requirements.txt"), content="\n".join(reqs) + "\n"),
        ]

    def directories(self, spec: ProjectSpec) -> list[str]:
        return ["config/", "apps/", "static/", "templates/"]

    def dependencies(self, spec: ProjectSpec) -> list[str]:
        config = self._config(spec)
        database = config.get("database", "sqlite")
        include_drf = config.get("include_drf", False)

        deps = ["django>=5.1"]
        if database == "postgresql":
            deps.append("psycopg2-binary>=2.9")
        elif database == "mysql":
            deps.append("mysqlclient>=2.2")
        if include_drf:
            deps.append("djangorestframework>=3.15")
        return deps

    def generate(self, spec: ProjectSpec, target_dir: Path, executor: Any) -> None:
        config = self._config(spec)
        database = config.get("database", "sqlite")
        include_drf = config.get("include_drf", False)

        deps = ["uv", "add", "django>=5.1"]
        if database == "postgresql":
            deps.append("psycopg2-binary>=2.9")
        elif database == "mysql":
            deps.append("mysqlclient>=2.2")
        if include_drf:
            deps.append("djangorestframework>=3.15")
        executor.run(deps, cwd=target_dir)

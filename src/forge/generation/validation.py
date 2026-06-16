from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from forge.domain import ProjectSpec, Question, QuestionType
from forge.generation.registry import PluginRegistry
from forge.infrastructure import GenerationTransaction as _  # noqa: F401


@dataclass
class ValidationError:
    field: str
    message: str
    severity: Literal["error", "warning"]


class ValidationEngine:
    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def validate_spec(self, spec: ProjectSpec) -> list[ValidationError]:
        errors: list[ValidationError] = []

        if not spec.project_name:
            errors.append(ValidationError(
                field="project_name",
                message="Project name must not be empty",
                severity="error",
            ))

        tpl = spec.template
        if not tpl.id or not tpl.display_name or not tpl.backend_id:
            errors.append(ValidationError(
                field="template",
                message="Template must have non-empty id, display_name, "
                        "and backend_id",
                severity="error",
            ))

        if tpl.backend_id:
            try:
                self._registry.resolve(tpl.backend_id)
            except KeyError:
                errors.append(ValidationError(
                    field="template.backend_id",
                    message=f"Backend plugin '{tpl.backend_id}' not found",
                    severity="error",
                ))

        if tpl.frontend_id is not None:
            try:
                self._registry.resolve(tpl.frontend_id)
            except KeyError:
                errors.append(ValidationError(
                    field="template.frontend_id",
                    message=f"Frontend plugin '{tpl.frontend_id}' not found",
                    severity="error",
                ))

        if not spec.domains:
            errors.append(ValidationError(
                field="domains",
                message="At least one domain must be specified",
                severity="error",
            ))

        return errors

    def validate_plugin_config(
        self,
        plugin_id: str,
        config: dict[str, Any],
        questions: list[Question],
    ) -> list[ValidationError]:
        errors: list[ValidationError] = []

        for question in questions:
            key = question.key

            if question.required and key not in config:
                errors.append(ValidationError(
                    field=key,
                    message=f"Required field '{key}' is missing",
                    severity="error",
                ))
                continue

            if key not in config:
                continue

            value = config[key]

            if question.question_type == QuestionType.INTEGER:
                if not isinstance(value, int):
                    errors.append(ValidationError(
                        field=key,
                        message=f"Value '{value}' is not a valid integer",
                        severity="error",
                    ))
                    continue
                validation = question.validation
                if validation is not None:
                    if validation.min is not None and value < validation.min:
                        errors.append(ValidationError(
                            field=key,
                            message=f"Value {value} is below minimum "
                                    f"{validation.min}",
                            severity="error",
                        ))
                    if validation.max is not None and value > validation.max:
                        errors.append(ValidationError(
                            field=key,
                            message=f"Value {value} exceeds maximum "
                                    f"{validation.max}",
                            severity="error",
                        ))

            elif question.question_type == QuestionType.STRING:
                validation = question.validation
                if validation is not None and validation.pattern is not None:
                    if not re.match(validation.pattern, str(value)):
                        errors.append(ValidationError(
                            field=key,
                            message=f"Value '{value}' does not match pattern "
                                    f"'{validation.pattern}'",
                            severity="error",
                        ))

            elif question.question_type == QuestionType.CHOICE:
                if question.options is not None and value not in question.options:
                    errors.append(ValidationError(
                        field=key,
                        message=f"Value '{value}' is not a valid choice. "
                                f"Valid options: {question.options}",
                        severity="error",
                    ))

            elif question.question_type == QuestionType.MULTI_SELECT:
                if question.options is not None:
                    if not isinstance(value, list):
                        errors.append(ValidationError(
                            field=key,
                            message=f"Value '{value}' is not a valid list",
                            severity="error",
                        ))
                        continue
                    invalid = [v for v in value if v not in question.options]
                    if invalid:
                        errors.append(ValidationError(
                            field=key,
                            message=f"Values {invalid} are not valid options. "
                                    f"Valid options: {question.options}",
                            severity="error",
                        ))

        return errors

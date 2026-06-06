from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class QuestionType(Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    MULTI_SELECT = "multi_select"
    INTEGER = "integer"


@dataclass
class ValidationRule:
    min: int | None = None
    max: int | None = None
    pattern: str | None = None


@dataclass
class Question:
    key: str
    label: str
    question_type: QuestionType
    required: bool = True
    default: Any = None
    description: str = ""
    options: list[str] | None = None
    placeholder: str | None = None
    validation: ValidationRule | None = None
    group: str | None = None

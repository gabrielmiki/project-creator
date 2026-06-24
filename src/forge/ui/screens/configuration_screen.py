from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from forge.domain import QuestionType
from forge.ui.screens.base import WizardScreen

if TYPE_CHECKING:
    from forge.domain import Question
    from forge.generation.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

_WIDGET_TYPE = (
    QLineEdit
    | QCheckBox
    | QComboBox
    | QListWidget
    | QSpinBox
)


class ConfigurationScreen(WizardScreen):
    def __init__(self, orchestrator: Orchestrator) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self.backend_id: str = ""
        self.frontend_id: str | None = None

        self._questions: list[tuple[str, Question]] = []
        self._widgets: dict[str, _WIDGET_TYPE] = {}
        self._error_labels: dict[str, QLabel] = {}

        self._load_error_label = QLabel("")
        self._load_error_label.setStyleSheet("color: red;")
        self._load_error_label.setVisible(False)
        self._load_error_label.setWordWrap(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self._form_layout = QFormLayout(container)
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._load_error_label)
        main_layout.addWidget(scroll)

    def on_enter(self) -> None:
        self._clear_form()
        self._load_error_label.setVisible(False)

        try:
            global_questions = self._orchestrator.get_global_questions()
            domain_questions = self._orchestrator.get_domain_questions(
                self.backend_id, self.frontend_id
            )
        except Exception:
            logger.exception("Failed to load configuration questions")
            self._load_error_label.setText("Failed to load configuration options")
            self._load_error_label.setVisible(True)
            global_questions = []
            domain_questions = {}

        self._questions = []
        for q in global_questions:
            self._questions.append(("_global", q))
        for plugin_id, plugin_questions in domain_questions.items():
            for q in plugin_questions:
                self._questions.append((plugin_id, q))

        self._build_form()
        self.validate()

    def _clear_form(self) -> None:
        while self._form_layout.count():
            child = self._form_layout.takeAt(0)
            if child:
                widget = child.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
        self._widgets.clear()
        self._error_labels.clear()
        self._questions.clear()

    def _build_form(self) -> None:
        current_group: str | None = None
        group_box: QGroupBox | None = None
        group_layout: QFormLayout | None = None

        for plugin_id, question in self._questions:
            if question.group != current_group:
                current_group = question.group
                group_box = None
                group_layout = None
                if current_group is not None:
                    group_box = QGroupBox(current_group)
                    group_layout = QFormLayout(group_box)
                    self._form_layout.addRow(group_box)

            widget = self._create_widget(question)
            if widget is None:
                continue

            self._setup_default(question, widget)
            self._connect_widget_signal(widget)
            self._widgets[question.key] = widget

            error_label = QLabel("")
            error_label.setStyleSheet("color: red;")
            error_label.setVisible(False)
            error_label.setObjectName(f"error_{question.key}")
            self._error_labels[question.key] = error_label

            label_text = question.label
            if question.required:
                label_text += " *"

            if group_layout is not None:
                group_layout.addRow(label_text, widget)
                group_layout.addRow("", error_label)
            else:
                self._form_layout.addRow(label_text, widget)
                self._form_layout.addRow("", error_label)

    def _create_widget(self, question: Question) -> _WIDGET_TYPE | None:
        qtype = question.question_type
        if qtype == QuestionType.STRING:
            w = QLineEdit()
            if question.placeholder:
                w.setPlaceholderText(question.placeholder)
            return w
        elif qtype == QuestionType.BOOLEAN:
            return QCheckBox()
        elif qtype == QuestionType.CHOICE:
            w = QComboBox()
            if question.options:
                for opt in question.options:
                    w.addItem(opt)
            if question.required:
                w.insertItem(0, "")
                w.setCurrentIndex(0)
            return w
        elif qtype == QuestionType.MULTI_SELECT:
            w = QListWidget()
            w.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
            if question.options:
                for opt in question.options:
                    item = QListWidgetItem(opt)
                    w.addItem(item)
            return w
        elif qtype == QuestionType.INTEGER:
            w = QSpinBox()
            if question.validation:
                if question.validation.min is not None:
                    w.setMinimum(question.validation.min)
                if question.validation.max is not None:
                    w.setMaximum(question.validation.max)
            return w
        else:
            logger.warning("Unknown QuestionType %s for question %s", qtype, question.key)
            return None

    def _setup_default(self, question: Question, widget: _WIDGET_TYPE) -> None:
        if question.default is None:
            return
        qtype = question.question_type
        if qtype == QuestionType.STRING:
            assert isinstance(widget, QLineEdit)
            widget.setText(str(question.default))
        elif qtype == QuestionType.BOOLEAN:
            assert isinstance(widget, QCheckBox)
            widget.setChecked(bool(question.default))
        elif qtype == QuestionType.CHOICE:
            assert isinstance(widget, QComboBox)
            idx = widget.findText(str(question.default))
            if idx >= 0:
                widget.setCurrentIndex(idx)
        elif qtype == QuestionType.INTEGER:
            assert isinstance(widget, QSpinBox)
            widget.setValue(int(question.default))

    def _connect_widget_signal(self, widget: _WIDGET_TYPE) -> None:
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(self._on_field_changed)
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(self._on_field_changed)
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self._on_field_changed)
        elif isinstance(widget, QListWidget):
            widget.itemSelectionChanged.connect(self._on_field_changed)
        elif isinstance(widget, QSpinBox):
            widget.valueChanged.connect(self._on_field_changed)

    def _on_field_changed(self) -> None:
        self.validate()

    def _get_widget_value(self, question: Question) -> Any:
        widget = self._widgets.get(question.key)
        if widget is None:
            return None

        qtype = question.question_type
        if qtype == QuestionType.STRING:
            assert isinstance(widget, QLineEdit)
            return widget.text()
        elif qtype == QuestionType.BOOLEAN:
            assert isinstance(widget, QCheckBox)
            return widget.isChecked()
        elif qtype == QuestionType.CHOICE:
            assert isinstance(widget, QComboBox)
            text = widget.currentText()
            return text if text else ""
        elif qtype == QuestionType.MULTI_SELECT:
            assert isinstance(widget, QListWidget)
            return [item.text() for item in widget.selectedItems()]
        elif qtype == QuestionType.INTEGER:
            assert isinstance(widget, QSpinBox)
            return widget.value()
        return None

    def validate(self) -> list[str]:
        errors: list[str] = []
        for _plugin_id, question in self._questions:
            widget = self._widgets.get(question.key)
            if widget is None:
                continue

            field_errors: list[str] = []
            value = self._get_widget_value(question)

            if question.required:
                if question.question_type == QuestionType.STRING:
                    if not value:
                        field_errors.append(f"{question.label} is required")
                elif question.question_type == QuestionType.BOOLEAN:
                    pass
                elif question.question_type == QuestionType.CHOICE:
                    if not value:
                        field_errors.append(f"{question.label} is required")
                elif question.question_type == QuestionType.MULTI_SELECT:
                    assert isinstance(widget, QListWidget)
                    if widget.selectedItems():
                        pass
                    else:
                        field_errors.append(f"{question.label} is required")
                elif question.question_type == QuestionType.INTEGER:
                    pass

            if question.validation:
                rule = question.validation
                if question.question_type == QuestionType.STRING and rule.pattern:
                    assert isinstance(widget, QLineEdit)
                    if value and not re.fullmatch(rule.pattern, value):
                        field_errors.append(
                            f"{question.label} does not match required pattern"
                        )

            error_label = self._error_labels.get(question.key)
            if field_errors:
                errors.extend(field_errors)
                if error_label:
                    error_label.setText(field_errors[0])
                    error_label.setVisible(True)
            else:
                if error_label:
                    error_label.setText("")
                    error_label.setVisible(False)

        self.can_proceed = len(errors) == 0
        self.proceed_changed.emit(self.can_proceed)
        return errors

    def get_spec_update(self) -> dict:
        config: dict[str, dict[str, Any]] = {}
        for plugin_id, question in self._questions:
            value = self._get_widget_value(question)
            if question.question_type == QuestionType.MULTI_SELECT:
                value = value if value else []
            if plugin_id == "_global":
                if "_global" not in config:
                    config["_global"] = {}
                config["_global"][question.key] = value
            else:
                if plugin_id not in config:
                    config[plugin_id] = {}
                config[plugin_id][question.key] = value
        return {"config": config}

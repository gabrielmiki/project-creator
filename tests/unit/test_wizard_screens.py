from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLineEdit,
    QListWidget,
    QSpinBox,
    QStackedWidget,
)

from forge.domain import ProjectSpec, Question, QuestionType, ValidationRule
from forge.generation.orchestrator import Orchestrator
from forge.plugins.base import PluginBase


def _mock_plugin(display_name: str, name: str, description: str = "") -> MagicMock:
    p: MagicMock = MagicMock(spec=PluginBase)
    p.display_name = display_name
    p.name = name
    p.description = description
    return p

# ====================================================================
# Fixtures
# ====================================================================

_MOCK_QUESTIONS = [
    Question(
        key="project_description",
        label="Project Description",
        question_type=QuestionType.STRING,
        required=False,
        validation=ValidationRule(pattern=r".+"),
    ),
    Question(
        key="license",
        label="License",
        question_type=QuestionType.CHOICE,
        required=True,
        default="MIT",
        options=["MIT", "Apache-2.0", "GPL-3.0"],
    ),
]


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    orch: MagicMock = MagicMock(spec=Orchestrator)
    orch.get_available_backends.return_value = []
    orch.get_available_frontends.return_value = []
    orch.get_global_questions.return_value = list(_MOCK_QUESTIONS)
    orch.get_domain_questions.return_value = {}
    return orch


@pytest.fixture
def welcome_screen(qapp: QApplication) -> object:
    from forge.ui.screens.welcome_screen import WelcomeScreen

    screen = WelcomeScreen()
    screen.show()
    yield screen
    screen.close()


@pytest.fixture
def domain_screen(qapp: QApplication, mock_orchestrator: MagicMock) -> object:
    from forge.ui.screens.domain_selection_screen import DomainSelectionScreen

    screen = DomainSelectionScreen(mock_orchestrator)
    screen.show()
    yield screen
    screen.close()


@pytest.fixture
def config_screen(qapp: QApplication, mock_orchestrator: MagicMock) -> object:
    from forge.ui.screens.configuration_screen import ConfigurationScreen

    screen = ConfigurationScreen(mock_orchestrator)
    screen.backend_id = "test"
    screen.frontend_id = None
    screen.show()
    yield screen
    screen.close()


# ====================================================================
# WizardScreen base class (AC-1, AC-2, AC-3)
# ====================================================================


@pytest.mark.gui
class TestWizardScreenBase:
    def test_default_can_proceed_is_false(self, qapp: QApplication) -> None:
        from forge.ui.screens.base import WizardScreen

        screen = WizardScreen()
        assert screen.can_proceed is False

    def test_default_can_go_back_is_true(self, qapp: QApplication) -> None:
        from forge.ui.screens.base import WizardScreen

        screen = WizardScreen()
        assert screen.can_go_back is True

    def test_proceed_changed_signal_emitted(self, qapp: QApplication) -> None:
        from forge.ui.screens.base import WizardScreen

        screen = WizardScreen()
        spy = QSignalSpy(screen.proceed_changed)
        screen.can_proceed = True
        screen.proceed_changed.emit(True)
        assert spy.count() == 1
        assert spy.at(0)[0] is True

    def test_default_methods_return_sensible_values(self, qapp: QApplication) -> None:
        from forge.ui.screens.base import WizardScreen

        screen = WizardScreen()
        assert screen.get_spec_update() == {}
        assert screen.validate() == []


# ====================================================================
# WelcomeScreen (AC-4, AC-5)
# ====================================================================


@pytest.mark.gui
class TestWelcomeScreen:
    def test_get_spec_update_returns_project_name(self, welcome_screen: object) -> None:
        name_edit = welcome_screen.findChild(QLineEdit)
        assert name_edit is not None
        name_edit.setText("my-project")
        assert welcome_screen.get_spec_update() == {"project_name": "my-project"}

    def test_empty_name_disables_proceed(self, welcome_screen: object) -> None:
        name_edit = welcome_screen.findChild(QLineEdit)
        assert name_edit is not None
        name_edit.setText("")
        assert welcome_screen.can_proceed is False

    def test_non_empty_name_enables_proceed(self, welcome_screen: object) -> None:
        name_edit = welcome_screen.findChild(QLineEdit)
        assert name_edit is not None
        name_edit.setText("my-project")
        assert welcome_screen.can_proceed is True

    def test_validate_empty_returns_error(self, welcome_screen: object) -> None:
        name_edit = welcome_screen.findChild(QLineEdit)
        assert name_edit is not None
        name_edit.setText("")
        errors = welcome_screen.validate()
        assert len(errors) == 1
        assert "required" in errors[0].lower()

    def test_validate_non_empty_returns_no_errors(self, welcome_screen: object) -> None:
        name_edit = welcome_screen.findChild(QLineEdit)
        assert name_edit is not None
        name_edit.setText("my-project")
        errors = welcome_screen.validate()
        assert errors == []


# ====================================================================
# DomainSelectionScreen (AC-6, AC-7, AC-8, AC-9)
# ====================================================================


@pytest.mark.gui
class TestDomainSelectionScreen:
    def test_can_proceed_false_when_no_backend_selected(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.domain_selection_screen import DomainSelectionScreen

        mock_orchestrator.get_available_backends.return_value = [
            _mock_plugin("FastAPI", "fastapi"),
        ]
        mock_orchestrator.get_available_frontends.return_value = []

        screen = DomainSelectionScreen(mock_orchestrator)
        screen.on_enter()

        assert screen.can_proceed is False

    def test_can_proceed_true_when_backend_selected(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.domain_selection_screen import DomainSelectionScreen

        mock_orchestrator.get_available_backends.return_value = [
            _mock_plugin("FastAPI", "fastapi"),
        ]
        mock_orchestrator.get_available_frontends.return_value = []

        screen = DomainSelectionScreen(mock_orchestrator)
        screen.on_enter()

        backend_list = screen.findChild(QListWidget, "")
        assert backend_list is not None
        backend_list.item(0).setSelected(True)

        assert screen.can_proceed is True

    def test_no_plugins_allows_proceed(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.domain_selection_screen import DomainSelectionScreen

        mock_orchestrator.get_available_backends.return_value = []
        mock_orchestrator.get_available_frontends.return_value = []

        screen = DomainSelectionScreen(mock_orchestrator)
        screen.on_enter()

        assert screen.can_proceed is True

    def test_on_enter_populates_lists(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.domain_selection_screen import DomainSelectionScreen

        mock_orchestrator.get_available_backends.return_value = [
            _mock_plugin("FastAPI", "fastapi"),
        ]
        mock_orchestrator.get_available_frontends.return_value = []

        screen = DomainSelectionScreen(mock_orchestrator)
        screen.on_enter()

        lists = screen.findChildren(QListWidget)
        backend_list = lists[0]
        assert backend_list.count() >= 1
        assert backend_list.item(0).text() == "FastAPI"

    def test_get_spec_update_returns_ids(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.domain_selection_screen import DomainSelectionScreen

        mock_orchestrator.get_available_backends.return_value = [
            _mock_plugin("FastAPI", "fastapi"),
        ]
        mock_orchestrator.get_available_frontends.return_value = []

        screen = DomainSelectionScreen(mock_orchestrator)
        screen.on_enter()
        backend_list = screen.findChild(QListWidget, "")
        assert backend_list is not None
        backend_list.item(0).setSelected(True)

        update = screen.get_spec_update()
        assert update["backend_id"] == "fastapi"
        assert update["frontend_id"] is None


# ====================================================================
# ConfigurationScreen — Widget mapping (AC-10..AC-14, AC-18, AC-19)
# ====================================================================


@pytest.mark.gui
class TestConfigurationScreenWidgetMapping:
    def _make_question(
        self,
        key: str,
        qtype: QuestionType,
        label: str | None = None,
        options: list[str] | None = None,
        required: bool = True,
        default: object = None,
        validation: ValidationRule | None = None,
        group: str | None = None,
    ) -> Question:
        return Question(
            key=key,
            label=label or key,
            question_type=qtype,
            required=required,
            default=default,
            options=options,
            validation=validation,
            group=group,
        )

    def test_string_creates_qlineedit(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q = self._make_question("name", QuestionType.STRING)
        mock_orchestrator.get_global_questions.return_value = [q]
        screen = ConfigurationScreen(mock_orchestrator)
        screen.backend_id = "test"
        screen.on_enter()

        assert screen._widgets.get("name") is not None
        assert isinstance(screen._widgets["name"], QLineEdit)

    def test_boolean_creates_qcheckbox(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q = self._make_question("flag", QuestionType.BOOLEAN)
        mock_orchestrator.get_global_questions.return_value = [q]
        screen = ConfigurationScreen(mock_orchestrator)
        screen.backend_id = "test"
        screen.on_enter()

        assert isinstance(screen._widgets.get("flag"), QCheckBox)

    def test_choice_creates_qcombobox(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q = self._make_question("color", QuestionType.CHOICE, options=["red", "blue"])
        mock_orch = MagicMock(spec=Orchestrator)
        mock_orch.get_global_questions.return_value = [q]
        mock_orch.get_domain_questions.return_value = {}
        screen = ConfigurationScreen(mock_orch)
        screen.backend_id = "test"
        screen.on_enter()

        assert isinstance(screen._widgets.get("color"), QComboBox)

    def test_multi_select_creates_qlistwidget(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q = self._make_question("features", QuestionType.MULTI_SELECT, options=["a", "b"])
        mock_orch = MagicMock(spec=Orchestrator)
        mock_orch.get_global_questions.return_value = [q]
        mock_orch.get_domain_questions.return_value = {}
        screen = ConfigurationScreen(mock_orch)
        screen.backend_id = "test"
        screen.on_enter()

        assert isinstance(screen._widgets.get("features"), QListWidget)

    def test_integer_creates_qspinbox(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q = self._make_question("port", QuestionType.INTEGER)
        mock_orch = MagicMock(spec=Orchestrator)
        mock_orch.get_global_questions.return_value = [q]
        mock_orch.get_domain_questions.return_value = {}
        screen = ConfigurationScreen(mock_orch)
        screen.backend_id = "test"
        screen.on_enter()

        assert isinstance(screen._widgets.get("port"), QSpinBox)


# ====================================================================
# ConfigurationScreen — Validation (AC-15, AC-16, AC-17)
# ====================================================================


@pytest.mark.gui
class TestConfigurationScreenValidation:
    def _make_q(self, **kw: object) -> Question:
        return Question(
            key=str(kw.get("key", "k")),
            label=str(kw.get("label", "Field")),
            question_type=kw.get("question_type", QuestionType.STRING),  # type: ignore[arg-type]
            required=kw.get("required", True),  # type: ignore[arg-type]
            validation=kw.get("validation"),
            options=kw.get("options"),
        )

    def test_string_pattern_validation_fails(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q = self._make_q(
            key="code",
            label="Code",
            question_type=QuestionType.STRING,
            validation=ValidationRule(pattern=r"^[A-Z]+$"),
        )
        mock_orchestrator.get_global_questions.return_value = [q]
        mock_orch = MagicMock(spec=Orchestrator)
        mock_orch.get_global_questions.return_value = [q]
        mock_orch.get_domain_questions.return_value = {}
        screen = ConfigurationScreen(mock_orch)
        screen.backend_id = "test"
        screen.on_enter()

        line_edit = screen._widgets["code"]
        assert isinstance(line_edit, QLineEdit)
        line_edit.setText("abc")

        assert not screen.can_proceed

    def test_string_pattern_validation_passes(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q = self._make_q(
            key="code",
            question_type=QuestionType.STRING,
            validation=ValidationRule(pattern=r"^[A-Z]+$"),
        )
        mock_orch = MagicMock(spec=Orchestrator)
        mock_orch.get_global_questions.return_value = [q]
        mock_orch.get_domain_questions.return_value = {}
        screen = ConfigurationScreen(mock_orch)
        screen.backend_id = "test"
        screen.on_enter()

        line_edit = screen._widgets["code"]
        assert isinstance(line_edit, QLineEdit)
        line_edit.setText("ABC")

        assert screen.can_proceed

    def test_required_choice_no_selection_fails(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q = self._make_q(
            key="opt",
            question_type=QuestionType.CHOICE,
            options=["x", "y"],
        )
        mock_orch = MagicMock(spec=Orchestrator)
        mock_orch.get_global_questions.return_value = [q]
        mock_orch.get_domain_questions.return_value = {}
        screen = ConfigurationScreen(mock_orch)
        screen.backend_id = "test"
        screen.on_enter()

        assert not screen.can_proceed

    def test_required_choice_with_selection_passes(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q = self._make_q(
            key="opt",
            question_type=QuestionType.CHOICE,
            options=["x", "y"],
        )
        mock_orch = MagicMock(spec=Orchestrator)
        mock_orch.get_global_questions.return_value = [q]
        mock_orch.get_domain_questions.return_value = {}
        screen = ConfigurationScreen(mock_orch)
        screen.backend_id = "test"
        screen.on_enter()

        combo = screen._widgets["opt"]
        assert isinstance(combo, QComboBox)
        combo.setCurrentIndex(combo.findText("x"))

        assert screen.can_proceed


# ====================================================================
# ConfigurationScreen — Grouping (AC-18)
# ====================================================================


@pytest.mark.gui
class TestConfigurationScreenGrouping:
    def test_questions_in_same_group_inside_qgroupbox(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q1 = Question(key="a", label="A", question_type=QuestionType.STRING, group="Database")
        q2 = Question(key="b", label="B", question_type=QuestionType.STRING, group="Database")
        mock_orch = MagicMock(spec=Orchestrator)
        mock_orch.get_global_questions.return_value = [q1, q2]
        mock_orch.get_domain_questions.return_value = {}
        screen = ConfigurationScreen(mock_orch)
        screen.backend_id = "test"
        screen.on_enter()

        group_boxes = screen.findChildren(QGroupBox)
        assert any(gb.title() == "Database" for gb in group_boxes)


# ====================================================================
# ConfigurationScreen — get_spec_update output (AC-20)
# ====================================================================


@pytest.mark.gui
class TestConfigurationScreenOutput:
    def test_get_spec_update_returns_full_config(
        self, qapp: QApplication, mock_orchestrator: MagicMock
    ) -> None:
        from forge.ui.screens.configuration_screen import ConfigurationScreen

        q_str = Question(key="desc", label="Desc", question_type=QuestionType.STRING, required=False)
        q_bool = Question(key="flag", label="Flag", question_type=QuestionType.BOOLEAN, required=False)
        q_choice = Question(key="opt", label="Opt", question_type=QuestionType.CHOICE, options=["a", "b"], required=False)
        q_multi = Question(key="multi", label="Multi", question_type=QuestionType.MULTI_SELECT, options=["x", "y"], required=False)
        q_int = Question(key="port", label="Port", question_type=QuestionType.INTEGER, required=False)

        mock_orch = MagicMock(spec=Orchestrator)
        mock_orch.get_global_questions.return_value = [q_str, q_bool, q_choice, q_multi, q_int]
        mock_orch.get_domain_questions.return_value = {}
        screen = ConfigurationScreen(mock_orch)
        screen.backend_id = "test"
        screen.on_enter()

        update = screen.get_spec_update()
        assert "config" in update
        assert "_global" in update["config"]
        cfg = update["config"]["_global"]
        assert "multi" in cfg
        assert isinstance(cfg["multi"], list)


# ====================================================================
# MainWindow integration (AC-21, AC-22, AC-23)
# ====================================================================


@pytest.mark.gui
class TestMainWindowIntegration:
    @pytest.fixture
    def main_window(self, qapp: QApplication, mock_orchestrator: MagicMock) -> object:
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.welcome_screen import WelcomeScreen
        from forge.ui.screens.domain_selection_screen import DomainSelectionScreen
        from forge.ui.screens.configuration_screen import ConfigurationScreen
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.ui.screens.generation_screen import GenerationScreen

        screens = [
            WelcomeScreen(),
            DomainSelectionScreen(mock_orchestrator),
            ConfigurationScreen(mock_orchestrator),
            ReviewScreen(mock_orchestrator),
            GenerationScreen(),
        ]

        window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
        window.show()
        yield window
        window.close()

    def test_build_spec_assembles_project_spec(
        self, main_window: object,
    ) -> None:
        name_edit = main_window.findChild(QLineEdit)
        assert name_edit is not None
        name_edit.setText("test-project")

        spec = main_window._build_spec()
        assert isinstance(spec, ProjectSpec)
        assert spec.project_name == "test-project"

    def test_navigate_to_calls_on_enter(
        self, qapp: QApplication, mock_orchestrator: MagicMock,
    ) -> None:
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.welcome_screen import WelcomeScreen
        from forge.ui.screens.domain_selection_screen import DomainSelectionScreen
        from forge.ui.screens.configuration_screen import ConfigurationScreen
        from forge.ui.screens.review_screen import ReviewScreen
        from forge.ui.screens.generation_screen import GenerationScreen

        screens = [
            WelcomeScreen(),
            DomainSelectionScreen(mock_orchestrator),
            ConfigurationScreen(mock_orchestrator),
            ReviewScreen(mock_orchestrator),
            GenerationScreen(),
        ]

        window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
        window.show()

        # Spies after construction so __init__ lifecycle isn't recorded
        for s in screens:
            if hasattr(s, "on_enter"):
                s.on_enter = MagicMock(wraps=s.on_enter)
            if hasattr(s, "on_exit"):
                s.on_exit = MagicMock(wraps=s.on_exit)

        stacked = window.findChild(QStackedWidget)
        assert stacked is not None
        assert stacked.currentIndex() == 0

        window.navigate_to(1)
        assert stacked.currentIndex() == 1
        screens[0].on_exit.assert_called_once()
        screens[1].on_enter.assert_called_once()

        window.navigate_to(0)
        assert stacked.currentIndex() == 0
        screens[1].on_exit.assert_called_once()
        screens[0].on_enter.assert_called_once()

        window.close()

    def test_next_screen_guard_with_can_proceed_false(
        self, qapp: QApplication, mock_orchestrator: MagicMock,
    ) -> None:
        from forge.ui.main_window import MainWindow
        from forge.ui.screens.welcome_screen import WelcomeScreen

        screens = [
            WelcomeScreen(),
            QStackedWidget(),
            QStackedWidget(),
            QStackedWidget(),
            QStackedWidget(),
        ]

        window = MainWindow(orchestrator=mock_orchestrator, screens=screens)
        window.show()

        stacked = window.findChild(QStackedWidget)
        assert stacked is not None
        assert stacked.currentIndex() == 0

        window.next_screen()
        assert stacked.currentIndex() == 0

        window.close()

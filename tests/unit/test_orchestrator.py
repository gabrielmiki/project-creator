from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forge.domain import (
    DurationEstimate,
    ProjectSpec,
    Question,
    QuestionType,
)
from forge.plugins.base import Configurable, PluginBase
from tests.unit._shared import (
    MockCommandPlugin,
    MockFilePlugin,
    build_registry,
    make_spec,
)

# ====================================================================
# Helpers
# ====================================================================


def _make_question(key: str = "q") -> Question:
    return Question(key=key, label=key, question_type=QuestionType.STRING)


def _get_question_keys(questions: list[Question]) -> set[str]:
    return {q.key for q in questions}


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def orch_txn() -> MagicMock:
    txn: MagicMock = MagicMock()
    txn.requirements = []
    return txn


@pytest.fixture
def mock_registry() -> MagicMock:
    reg: MagicMock = MagicMock()
    reg.get_available_backends.return_value = []
    reg.get_available_frontends.return_value = []
    reg.resolve_many.return_value = []
    reg.topological_sort.return_value = []
    return reg


@pytest.fixture
def mock_validation() -> MagicMock:
    return MagicMock()


# ====================================================================
# AC-1a (unit): Stage ordering + commit on success
# AC-2: Error → rollback
# AC-7: Empty spec
# ====================================================================


class TestOrchestratorGenerate:
    """Orchestrator.generate() behaviour."""

    def test_all_stages_called_in_order(
        self,
        output_dir: Path,
        orch_txn: MagicMock,
        mock_registry: MagicMock,
        mock_validation: MagicMock,
        progress: MagicMock,
        spec: ProjectSpec,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        s1, s2, s3, s4, s5, s6 = (MagicMock() for _ in range(6))
        stages = [s1, s2, s3, s4, s5, s6]
        orch = Orchestrator(mock_registry, mock_validation, stages=stages)

        result = orch.generate(spec, output_dir, orch_txn, progress)

        for i, stage in enumerate(stages):
            stage.run.assert_called_once_with(spec, output_dir, orch_txn, progress)
        orch_txn.commit.assert_called_once()
        orch_txn.rollback.assert_not_called()
        assert result.success is True
        assert result.output_path == output_dir

    def test_stage_exception_triggers_rollback(
        self,
        output_dir: Path,
        orch_txn: MagicMock,
        mock_registry: MagicMock,
        mock_validation: MagicMock,
        progress: MagicMock,
        spec: ProjectSpec,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        s1 = MagicMock()
        s2 = MagicMock()
        s3 = MagicMock()
        s3.run.side_effect = RuntimeError("boom")
        s4 = MagicMock()
        s5 = MagicMock()
        s6 = MagicMock()
        stages = [s1, s2, s3, s4, s5, s6]
        orch = Orchestrator(mock_registry, mock_validation, stages=stages)

        result = orch.generate(spec, output_dir, orch_txn, progress)

        s1.run.assert_called_once()
        s2.run.assert_called_once()
        s3.run.assert_called_once()
        s4.run.assert_not_called()
        s5.run.assert_not_called()
        s6.run.assert_not_called()
        orch_txn.rollback.assert_called_once()
        progress.on_error.assert_called_once()
        args, _ = progress.on_error.call_args
        assert isinstance(args[0], RuntimeError)
        assert str(args[0]) == "boom"
        assert args[1] is False
        orch_txn.commit.assert_not_called()
        assert result.success is False
        assert result.error == "boom"

    def test_empty_spec_completes(
        self,
        output_dir: Path,
        orch_txn: MagicMock,
        mock_registry: MagicMock,
        mock_validation: MagicMock,
        progress: MagicMock,
        empty_spec: ProjectSpec,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        s1, s2, s3, s4, s5, s6 = (MagicMock() for _ in range(6))
        stages = [s1, s2, s3, s4, s5, s6]
        orch = Orchestrator(mock_registry, mock_validation, stages=stages)

        result = orch.generate(empty_spec, output_dir, orch_txn, progress)

        for stage in stages:
            stage.run.assert_called_once()
        orch_txn.commit.assert_called_once()
        orch_txn.rollback.assert_not_called()
        assert result.success is True


# ====================================================================
# Edge: overwrite_confirmed
# ====================================================================


class TestOrchestratorOverwrite:
    """overwrite_confirmed parameter behaviour (AC-1a implicit assumption)."""

    def test_overwrite_confirmed_excludes_directory_initializer(
        self,
        output_dir: Path,
        orch_txn: MagicMock,
        mock_registry: MagicMock,
        mock_validation: MagicMock,
        progress: MagicMock,
        spec: ProjectSpec,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        s1, s2, s3, s4, s5, s6 = (MagicMock() for _ in range(6))
        stages = [s1, s2, s3, s4, s5, s6]
        orch = Orchestrator(mock_registry, mock_validation, stages=stages)

        orch.generate(spec, output_dir, orch_txn, progress, overwrite_confirmed=True)

        s1.run.assert_not_called()

    def test_overwrite_confirmed_default_includes_all(
        self,
        output_dir: Path,
        orch_txn: MagicMock,
        mock_registry: MagicMock,
        mock_validation: MagicMock,
        progress: MagicMock,
        spec: ProjectSpec,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        s1, s2, s3, s4, s5, s6 = (MagicMock() for _ in range(6))
        stages = [s1, s2, s3, s4, s5, s6]
        orch = Orchestrator(mock_registry, mock_validation, stages=stages)

        orch.generate(spec, output_dir, orch_txn, progress)

        for stage in stages:
            stage.run.assert_called_once()


# ====================================================================
# AC-6: get_domain_questions
# ====================================================================


class _CfgPlugin(PluginBase, Configurable):
    name = "cfg"
    display_name = "Cfg"
    description = ""

    def __init__(self, questions_list: list[Question] | None = None) -> None:
        super().__init__()
        self._questions = questions_list or []

    def questions(self) -> list[Question]:
        return self._questions


class _NonCfgPlugin(PluginBase):
    name = "non-cfg"
    display_name = "NonCfg"
    description = ""


class TestGetDomainQuestions:
    """Covers AC-6."""

    def test_configurable_returns_questions(
        self,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        q = _make_question("orm")
        plugin = _CfgPlugin([q])
        registry = build_registry([plugin])
        registry.get_available_backends.return_value = [plugin]
        registry.get_available_frontends.return_value = []

        orch = Orchestrator(registry, mock_validation)
        spec = make_spec(backend_id="cfg")

        result = orch.get_domain_questions(spec.template.backend_id, spec.template.frontend_id)

        assert "cfg" in result
        assert result["cfg"] == [q]

    def test_non_configurable_skipped(
        self,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        plugin = _NonCfgPlugin()
        registry = build_registry([plugin])
        registry.get_available_backends.return_value = [plugin]
        registry.get_available_frontends.return_value = []

        orch = Orchestrator(registry, mock_validation)
        spec = make_spec(backend_id="non-cfg")

        result = orch.get_domain_questions(spec.template.backend_id, spec.template.frontend_id)

        assert "non-cfg" not in result

    def test_mixed_plugins_filtered(
        self,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        q = _make_question("orm")
        cfg_plugin = _CfgPlugin([q])
        non_cfg = _NonCfgPlugin()
        registry = build_registry([cfg_plugin, non_cfg])
        registry.get_available_backends.return_value = [cfg_plugin, non_cfg]
        registry.get_available_frontends.return_value = []

        orch = Orchestrator(registry, mock_validation)
        spec = make_spec(backend_id="cfg", frontend_id="non-cfg")

        result = orch.get_domain_questions(spec.template.backend_id, spec.template.frontend_id)

        assert "cfg" in result
        assert "non-cfg" not in result
        assert result["cfg"] == [q]

    def test_frontend_none_skipped(
        self,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        q = _make_question("orm")
        plugin = _CfgPlugin([q])
        registry = build_registry([plugin])
        registry.get_available_backends.return_value = [plugin]
        registry.get_available_frontends.return_value = []

        orch = Orchestrator(registry, mock_validation)
        spec = make_spec(backend_id="cfg", frontend_id=None)

        result = orch.get_domain_questions(spec.template.backend_id, spec.template.frontend_id)

        assert "cfg" in result
        assert result["cfg"] == [q]


# ====================================================================
# AC-8: get_global_questions
# ====================================================================


class TestGetGlobalQuestions:
    """Covers AC-8."""

    def test_returns_question_list(
        self,
        mock_registry: MagicMock,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        orch = Orchestrator(mock_registry, mock_validation)
        questions = orch.get_global_questions()

        assert isinstance(questions, list)
        assert len(questions) > 0
        for q in questions:
            assert isinstance(q, Question)

    def test_contains_required_keys(
        self,
        mock_registry: MagicMock,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        orch = Orchestrator(mock_registry, mock_validation)
        keys = _get_question_keys(orch.get_global_questions())

        assert "project_description" in keys
        assert "license" in keys


# ====================================================================
# AC-9: estimate_duration
# ====================================================================


class TestEstimateDuration:
    """Covers AC-9."""

    def test_with_command_runner(
        self,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        cmd_plugin = MockCommandPlugin()
        registry = build_registry([cmd_plugin])
        registry.get_available_backends.return_value = [cmd_plugin]
        registry.resolve_many.return_value = [cmd_plugin]
        registry.topological_sort.return_value = [cmd_plugin]

        orch = Orchestrator(registry, mock_validation)
        spec = make_spec(backend_id="mock-command")

        estimate = orch.estimate_duration(spec)

        assert isinstance(estimate, DurationEstimate)
        assert estimate.has_slow_steps is True
        assert estimate.estimated_seconds == 4
        assert isinstance(estimate.slow_step_details, list)

    def test_no_command_runner_no_file_provider(
        self,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        # Empty registry — zero plugins overall
        registry = build_registry([])
        registry.get_available_backends.return_value = []

        orch = Orchestrator(registry, mock_validation)
        spec = make_spec(backend_id="")  # no plugins selected

        estimate = orch.estimate_duration(spec)

        assert isinstance(estimate, DurationEstimate)
        assert estimate.has_slow_steps is False
        assert estimate.estimated_seconds == 1
        assert isinstance(estimate.slow_step_details, list)

    def test_file_provider_only(
        self,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        fp_plugin = MockFilePlugin()
        registry = build_registry([fp_plugin])
        registry.get_available_backends.return_value = [fp_plugin]
        registry.resolve_many.return_value = [fp_plugin]
        registry.topological_sort.return_value = [fp_plugin]

        orch = Orchestrator(registry, mock_validation)
        spec = make_spec(backend_id="mock-file")

        estimate = orch.estimate_duration(spec)

        assert isinstance(estimate, DurationEstimate)
        assert estimate.has_slow_steps is False
        assert estimate.estimated_seconds == 1


# ====================================================================
# AC-10, AC-11: get_available_backends / get_available_frontends
# ====================================================================


class TestAvailablePlugins:
    """Covers AC-10 and AC-11."""

    def test_backends_with_discovered(
        self,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        p1 = _NonCfgPlugin()
        p2 = _NonCfgPlugin()
        p2.name = "p2"
        p2.display_name = "P2"
        registry = build_registry([p1, p2])
        registry.get_available_backends.return_value = [p1, p2]

        orch = Orchestrator(registry, mock_validation)
        backends = orch.get_available_backends()

        assert len(backends) == 2
        assert p1 in backends
        assert p2 in backends

    def test_backends_empty_registry(
        self,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        registry = build_registry([])
        registry.get_available_backends.return_value = []

        orch = Orchestrator(registry, mock_validation)
        backends = orch.get_available_backends()

        assert backends == []

    def test_frontends_empty(
        self,
        mock_validation: MagicMock,
    ) -> None:
        from forge.generation.orchestrator import Orchestrator

        registry = build_registry([])
        registry.get_available_frontends.return_value = []

        orch = Orchestrator(registry, mock_validation)
        frontends = orch.get_available_frontends()

        assert frontends == []


# ====================================================================
# AC-3, AC-4a, AC-4b, AC-4c, AC-5: CLI headless / display detection
# ====================================================================


class TestHeadlessCLI:
    """Covers AC-3, AC-4a, AC-4b, AC-4c, AC-5."""

    def _run_headless(
        self,
        args: list[str],
        spec_content: str,
        tmp_path: Path,
    ) -> int:
        spec_path = tmp_path / "spec.json"
        spec_path.write_text(spec_content)
        output_dir = tmp_path / "output"

        full_args = ["forge"] + args + [str(spec_path), str(output_dir)]
        with patch.object(sys, "argv", full_args):
            from forge.app import main as app_main

            try:
                app_main()
                return 0
            except SystemExit as e:
                return e.code

    def test_valid_spec_exit_0(self, tmp_path: Path) -> None:
        spec = json.dumps(
            {
                "project_name": "my-proj",
                "template": {
                    "id": "base",
                    "display_name": "Base",
                    "description": "",
                    "backend_id": "",
                    "frontend_id": None,
                },
                "domains": [],
                "config": {},
            }
        )
        code = self._run_headless(["--headless"], spec, tmp_path)
        assert code == 0

    def test_invalid_json_exit_1(self, tmp_path: Path) -> None:
        code = self._run_headless(["--headless"], "{bad json", tmp_path)
        assert code == 1

    def test_missing_project_name_exit_1(self, tmp_path: Path) -> None:
        spec = json.dumps(
            {
                "template": {
                    "id": "base",
                    "display_name": "Base",
                    "description": "",
                    "backend_id": "",
                    "frontend_id": None,
                },
                "domains": [],
                "config": {},
            }
        )
        code = self._run_headless(["--headless"], spec, tmp_path)
        assert code == 1

    def test_unknown_backend_id_exit_1(self, tmp_path: Path) -> None:
        spec = json.dumps(
            {
                "project_name": "my-proj",
                "template": {
                    "id": "base",
                    "display_name": "Base",
                    "description": "",
                    "backend_id": "nonexistent",
                    "frontend_id": None,
                },
                "domains": [],
                "config": {},
            }
        )
        code = self._run_headless(["--headless"], spec, tmp_path)
        assert code == 1

    def test_no_display_no_headless_error(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        full_args = ["forge"]

        with patch.object(sys, "argv", full_args):
            with patch("forge.app.detect_display", return_value=False):
                from forge.app import main as app_main

                with pytest.raises(SystemExit) as exc_info:
                    app_main()
                assert exc_info.value.code == 1

        out, err = capsys.readouterr()
        assert "No display available" in out

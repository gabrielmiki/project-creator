from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ====================================================================
# CLI Headless — Integration Tests
# ====================================================================
# All tests use --headless mode exclusively (no QApplication, no display).
# ProcessExecutor is patched to avoid real subprocess calls.
# ====================================================================


class TestCLIHeadless:
    def test_cli_headless_generation(
        self, cli_spec_json: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], mock_executor
    ) -> None:
        output_dir = tmp_path / "output"
        args = ["forge", "--headless", str(cli_spec_json), str(output_dir)]

        with patch.object(sys, "argv", args):
            with patch("forge.generation.orchestrator.ProcessExecutor", return_value=mock_executor):
                from forge.app import main as app_main

                try:
                    app_main()
                except SystemExit as e:
                    assert e.code == 0

        assert (output_dir / "app/main.py").exists()
        assert (output_dir / "requirements.txt").exists()
        assert (output_dir / "app/__init__.py").exists()
        assert (output_dir / "README.md").exists()
        assert not (output_dir / ".forge-staging").exists()

    def test_cli_malformed_spec(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        spec_path = tmp_path / "spec.json"
        spec_path.write_text("{bad json")
        output_dir = tmp_path / "output"
        args = ["forge", "--headless", str(spec_path), str(output_dir)]

        with patch.object(sys, "argv", args):
            from forge.app import main as app_main

            with pytest.raises(SystemExit) as exc_info:
                app_main()

        assert exc_info.value.code == 1

        out, _ = capsys.readouterr()
        assert "Invalid JSON" in out

    def test_cli_output_dir_created_if_missing(
        self, cli_spec_json: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], mock_executor
    ) -> None:
        output_dir = tmp_path / "output"
        assert not output_dir.exists()

        args = ["forge", "--headless", str(cli_spec_json), str(output_dir)]

        with patch.object(sys, "argv", args):
            with patch("forge.generation.orchestrator.ProcessExecutor", return_value=mock_executor):
                from forge.app import main as app_main

                try:
                    app_main()
                except SystemExit as e:
                    assert e.code == 0

        assert output_dir.exists()
        assert (output_dir / "app/main.py").exists()

    def test_cli_no_display_message(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        args = ["forge"]

        with patch.object(sys, "argv", args):
            with patch("forge.app.detect_display", return_value=False):
                from forge.app import main as app_main

                with pytest.raises(SystemExit) as exc_info:
                    app_main()

        assert exc_info.value.code == 1

        out, _ = capsys.readouterr()
        assert "No display available" in out

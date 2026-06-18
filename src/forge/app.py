from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from forge.domain import Domain, ProjectSpec, TemplateDefinition
from forge.generation.orchestrator import Orchestrator
from forge.generation.progress import StdoutProgressReporter
from forge.generation.registry import PluginRegistry
from forge.generation.validation import ValidationEngine
from forge.infrastructure import GenerationTransaction
from forge.plugins.base import Configurable


def detect_display() -> bool:
    if sys.platform == "darwin" or sys.platform == "win32":
        return True
    return bool(os.environ.get("DISPLAY"))


def main() -> None:
    args = list(sys.argv[1:])

    if args and args[0] == "--headless":
        _run_headless(args[1:])
        return

    if not detect_display():
        print("No display available. Use --headless mode for headless environments.")
        sys.exit(1)

    _launch_gui()


def _run_headless(args: list[str]) -> None:
    if len(args) < 2:
        print("Usage: python -m forge --headless <spec.json> <output_dir>")
        sys.exit(1)

    spec_path = Path(args[0])
    output_dir = Path(args[1])

    try:
        data = json.loads(spec_path.read_text())
    except FileNotFoundError:
        print(f"Spec file not found: {spec_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        sys.exit(1)

    try:
        spec = ProjectSpec(
            project_name=data["project_name"],
            template=TemplateDefinition(
                id=data["template"]["id"],
                display_name=data["template"]["display_name"],
                description=data["template"].get("description", ""),
                backend_id=data["template"]["backend_id"],
                frontend_id=data["template"].get("frontend_id"),
            ),
            domains=[Domain(name=d["name"]) for d in data.get("domains", [])],
            config=data.get("config", {}),
        )
    except KeyError as e:
        print(f"Missing required field: {e}")
        sys.exit(1)

    registry = PluginRegistry()
    registry.discover()

    validation = ValidationEngine(registry)
    errors = validation.validate_spec(spec)

    for pid in [spec.template.backend_id, spec.template.frontend_id]:
        if pid:
            try:
                plugin = registry.resolve(pid)
                if isinstance(plugin, Configurable):
                    plugin_errors = validation.validate_plugin_config(
                        pid, spec.config.get(pid, {}), plugin.questions()
                    )
                    errors.extend(plugin_errors)
            except KeyError:
                pass

    error_errors = [e for e in errors if e.severity == "error"]
    if error_errors:
        print(f"Validation error: {error_errors[0].message}")
        sys.exit(1)

    orch = Orchestrator(registry, validation)
    txn = GenerationTransaction(output_dir)
    progress = StdoutProgressReporter()
    result = orch.generate(spec, output_dir, txn, progress)

    if result.success:
        print(f"Project generated at {result.output_path}")
    else:
        print(f"Generation failed: {result.error}")
        sys.exit(1)


def _launch_gui() -> None:
    try:
        from PySide6.QtWidgets import QApplication  # noqa: F401
    except ImportError:
        print("PySide6 is required for GUI mode")
        sys.exit(1)
    print("GUI mode not yet implemented")
    sys.exit(0)

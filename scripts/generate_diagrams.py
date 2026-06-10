#!/usr/bin/env python3
"""Static architecture diagram generator for Forge.

Uses the `diagrams` library (https://diagrams.mingrammer.com/)
to generate PNG/SVG architecture and pipeline diagrams.

Dependencies: diagrams, graphviz (system binary)

Usage:
  python scripts/generate_diagrams.py          # generate all PNGs
  python scripts/generate_diagrams.py --svg     # generate SVGs instead

Output directory: docs/assets/
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"


def check_dot() -> None:
    if not shutil.which("dot"):
        print(
            "Warning: graphviz 'dot' binary not found. "
            "Install graphviz (brew install graphviz, apt install graphviz, etc.) "
            "to generate diagrams.",
            file=sys.stderr,
        )
        sys.exit(1)


def generate_architecture(out_format: str = "png") -> None:
    from diagrams import Diagram
    from diagrams.onpremise.client import User
    from diagrams.programming.flowchart import Action, Database, InputOutput
    from diagrams.programming.language import Python

    ASSETS.mkdir(parents=True, exist_ok=True)

    with Diagram(
        "Forge Architecture — 5-Layer Model",
        filename=str(ASSETS / "architecture"),
        show=False,
        outformat=out_format,
        direction="TB",
    ):
        from diagrams import Edge

        ui = User("UI Layer\nPySide6")
        generation = Python("Generation Layer\nFacade")
        plugins = Action("Plugin Layer\nCapability Mixins")
        domain = Database("Domain Layer\nPure Leaf Models")
        infra = InputOutput("Infrastructure Layer\nI/O Only")

        ui >> Edge(label="queries") >> generation
        generation >> Edge(label="discovers") >> plugins
        domain << Edge(label="imported by all", style="dotted") >> generation
        domain << Edge(label="imported by all", style="dotted") >> plugins
        generation >> Edge(label="uses") >> infra
        plugins >> Edge(label="uses") >> infra

    print(f"  ✓ architecture.{out_format}")


def generate_pipeline(out_format: str = "png") -> None:
    from diagrams import Diagram
    from diagrams.onpremise.workflow import Airflow
    from diagrams.programming.flowchart import Action, Database, Decision, InputOutput

    ASSETS.mkdir(parents=True, exist_ok=True)

    with Diagram(
        "Forge Generation Pipeline",
        filename=str(ASSETS / "generation-pipeline"),
        show=False,
        outformat=out_format,
        direction="LR",
    ):
        from diagrams import Edge

        orchestrator = Airflow("Orchestrator")

        s1 = Action("Stage 1\nDirectory\nInitializer")
        s2 = Action("Stage 2\nShared\nStructure")
        s3 = Decision("Stage 3\nPlugin\nExecution")
        s4 = Action("Stage 4\nJustfile\nGenerator")
        s5 = Action("Stage 5\nProject Doc\nWriter")
        s6 = Action("Stage 6\nAgent Skill\nScaffolder")

        transaction = InputOutput("Generation\nTransaction")
        progress = Database("Progress\nReporter")

        orchestrator >> s1 >> s2 >> s3 >> s4 >> s5 >> s6

        s2 >> Edge(style="dashed", label="stages") >> transaction
        s4 >> Edge(style="dashed") >> transaction
        s5 >> Edge(style="dashed") >> transaction
        s6 >> Edge(style="dashed") >> transaction
        s3 >> Edge(style="dashed", label="+ checkpoints") >> transaction

        orchestrator >> Edge(style="dotted", label="emits") >> progress

    print(f"  ✓ generation-pipeline.{out_format}")


def generate_ticket_graph(out_format: str = "png") -> None:
    from diagrams import Diagram
    from diagrams.custom import Custom

    try:
        ticket_map_path = ROOT / "scripts" / "ticket_map.yaml"
        with open(ticket_map_path) as f:
            data = yaml.safe_load(f)
        tickets = data["tickets"]
    except Exception as e:
        print(f"  Skipping ticket graph: {e}", file=sys.stderr)
        return

    ASSETS.mkdir(parents=True, exist_ok=True)

    with Diagram(
        "Ticket Dependency Graph",
        filename=str(ASSETS / "ticket-dependency-graph"),
        show=False,
        outformat=out_format,
        direction="TB",
    ):
        from diagrams import Edge

        nodes: dict[str, Custom] = {}
        for tid in sorted(tickets):
            t = tickets[tid]
            label = f"{tid}\n{t['title']}"
            nodes[tid] = Custom(label, "")

        for tid, t in tickets.items():
            for dep in t.get("depends_on", []):
                if dep in nodes:
                    nodes[dep] >> Edge() >> nodes[tid]

    print(f"  ✓ ticket-dependency-graph.{out_format}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Forge architecture diagrams",
    )
    parser.add_argument(
        "--svg",
        action="store_true",
        help="Generate SVG instead of PNG",
    )
    args = parser.parse_args()

    fmt = "svg" if args.svg else "png"

    check_dot()

    print(f"Generating {fmt.upper()} diagrams...")
    generate_architecture(fmt)
    generate_pipeline(fmt)
    generate_ticket_graph(fmt)
    print(f"\nSaved to {ASSETS}/")


if __name__ == "__main__":
    main()

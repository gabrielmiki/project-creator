#!/usr/bin/env python3
"""Ticket visualization CLI.

Reads scripts/ticket_map.yaml and generates:
  - Plain text per-ticket scope views (default)
  - PNG dependency graph via `diagrams` library (--png)

Usage:
  python scripts/ticket_viz.py                    # list all tickets
  python scripts/ticket_viz.py T-005              # single ticket details
  python scripts/ticket_viz.py T-005 --downstream  # with downstream impacts
  python scripts/ticket_viz.py --png              # full dependency graph PNG
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("PyYAML required: uv add pyyaml")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent
TICKET_MAP = ROOT / "scripts" / "ticket_map.yaml"
ASSETS = ROOT / "docs" / "assets"
TICKETS_DIR = ROOT / "docs" / "context" / "tickets"

LAYER_COLORS: dict[str, str] = {
    "domain": "\033[32m",
    "plugins": "\033[33m",
    "generation": "\033[35m",
    "infrastructure": "\033[31m",
    "ui": "\033[34m",
    "tests/integration": "\033[36m",
}
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"


def load_ticket_map() -> dict[str, Any]:
    if not TICKET_MAP.exists():
        print(f"Error: {TICKET_MAP} not found", file=sys.stderr)
        sys.exit(1)
    with open(TICKET_MAP) as f:
        data = yaml.safe_load(f)
    return data["tickets"]


def load_ticket_markdown(ticket_id: str) -> str | None:
    for f in TICKETS_DIR.glob("*.md"):
        numeric_id = re.search(r"\d+", ticket_id)
        if numeric_id and f.name.startswith(numeric_id.group()):
            with open(f) as fh:
                lines = fh.readlines()
            header_lines = []
            in_header = True
            for line in lines:
                if in_header and line.startswith("- **"):
                    header_lines.append(line.strip())
                elif in_header and line.strip() == "":
                    in_header = False
                    break
            return "\n".join(header_lines)
    return None


def color_layer(layer: str) -> str:
    c = LAYER_COLORS.get(layer, "")
    return f"{c}{layer}{RESET}" if c else layer


def build_downstream_map(
    tickets: dict[str, Any],
) -> dict[str, list[str]]:
    downstream: dict[str, list[str]] = {tid: [] for tid in tickets}
    for tid, info in tickets.items():
        for dep in info.get("depends_on", []):
            if dep in downstream:
                downstream[dep].append(tid)
    return downstream


def format_text(
    width: int = 72,
    indent: int = 4,
) -> str:
    return " " * indent


def show_all_tickets(tickets: dict[str, Any]) -> None:
    downstream = build_downstream_map(tickets)
    phases = sorted(set(t["phase"] for t in tickets.values()))

    for phase in phases:
        print(f"\n{BOLD}{phase.upper()}{RESET}")
        print("-" * 60)
        phase_tickets = {tid: t for tid, t in tickets.items() if t["phase"] == phase}
        for tid in sorted(phase_tickets):
            t = phase_tickets[tid]
            deps = t.get("depends_on", [])
            dep_str = ", ".join(deps) if deps else "\033[2m(none)\033[0m"
            down = downstream.get(tid, [])
            down_str = ", ".join(down) if down else ""
            print(f"  {BOLD}{tid}{RESET} {t['title']}  [{color_layer(t['layer'])}]")
            print(f"       deps: {dep_str}")
            if down_str:
                print(f"       downstream: {down_str}")
            print()


def show_ticket_detail(
    tickets: dict[str, Any],
    ticket_id: str,
    show_downstream: bool = False,
) -> None:
    if ticket_id not in tickets:
        print(f"Error: {ticket_id} not found in ticket map", file=sys.stderr)
        sys.exit(1)

    t = tickets[ticket_id]
    downstream = build_downstream_map(tickets) if show_downstream else {}

    print(f"\n{BOLD}{ticket_id}: {t['title']}{RESET}")
    print("=" * 60)

    meta = load_ticket_markdown(ticket_id)
    if meta:
        for line in meta.split("\n"):
            print(f"  {DIM}{line}{RESET}")

    print(f"\n  {BOLD}Layer:{RESET}          {color_layer(t['layer'])}")
    print(f"  {BOLD}Phase:{RESET}          {t['phase']}")
    print(f"  {BOLD}Complexity:{RESET}      {t['complexity']}")

    deps = t.get("depends_on", [])
    print(f"\n  {BOLD}Dependencies:{RESET}")
    if deps:
        for dep in deps:
            dt = tickets.get(dep, {})
            print(f"    {dep} {dt.get('title', '')}")
    else:
        print(f"    {DIM}(leaf — zero deps){RESET}")

    if show_downstream and downstream.get(ticket_id):
        print(f"\n  {BOLD}Downstream Impacts:{RESET}")
        for down_id in sorted(downstream[ticket_id]):
            dt = tickets.get(down_id, {})
            print(f"    {down_id} {dt.get('title', '')}")

    files = t.get("files", [])
    print(f"\n  {BOLD}Files ({len(files)}):{RESET}")
    for f in files:
        print(f"    {'📄' if f.endswith('.py') else '📁'} {f}")

    domain_imports = t.get("domain_imports", [])
    if domain_imports:
        print(f"\n  {BOLD}Domain imports:{RESET}")
        for imp in domain_imports:
            print(f"    {imp}")

    risks = t.get("risks", [])
    if risks:
        print(f"\n  {BOLD}Risks / Delicate Points:{RESET}")
        for r in risks:
            print(f"    ⚠ {r}")

    print()


def generate_png(tickets: dict[str, Any]) -> None:
    try:
        from diagrams import Diagram
        from diagrams.custom import Custom
    except ImportError:
        print(
            "diagrams library not available. Install with: uv add --dev diagrams",
            file=sys.stderr,
        )
        sys.exit(1)

    ASSETS.mkdir(parents=True, exist_ok=True)
    output_path = ASSETS / "ticket-dependency-graph"

    with Diagram(
        "Ticket Dependency Graph",
        filename=str(output_path),
        show=False,
        direction="TB",
    ):
        from diagrams import Edge

        nodes: dict[str, Any] = {}
        for tid in sorted(tickets):
            t = tickets[tid]
            label = f"{tid}\n{t['title']}"
            nodes[tid] = Custom(label)

        for tid, t in tickets.items():
            for dep in t.get("depends_on", []):
                if dep in nodes:
                    nodes[dep] >> Edge() >> nodes[tid]

    print(f"PNG saved to {output_path}.png")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Forge ticket visualization tool",
    )
    parser.add_argument(
        "ticket",
        nargs="?",
        help="Ticket ID to show details (e.g. T-005)",
    )
    parser.add_argument(
        "--downstream",
        action="store_true",
        help="Show downstream impacts (reverse dependencies)",
    )
    parser.add_argument(
        "--png",
        action="store_true",
        help="Generate PNG dependency graph via diagrams library",
    )
    args = parser.parse_args()

    tickets = load_ticket_map()

    if args.png:
        generate_png(tickets)
        return

    if args.ticket:
        show_ticket_detail(tickets, args.ticket, args.downstream)
    else:
        show_all_tickets(tickets)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from apps.cli.cli_common import (
    DATA_DIR,
    INDEX_DIR,
    REPORT_DIR,
    PROJECT_ROOT,
    env_hint,
    file_info,
    human_mtime,
    human_size,
    load_status,
    read_json,
)
from apps.cli.registry import get_tools

console = Console()


def _artifact_rows() -> List[Tuple[str, Path]]:
    return [
        ("resource_index", INDEX_DIR / "wagstaff_resource_index_v1.json"),
        ("catalog_v2", INDEX_DIR / "wagstaff_catalog_v2.json"),
        ("catalog_index", INDEX_DIR / "wagstaff_catalog_index_v1.json"),
        ("icon_index", INDEX_DIR / "wagstaff_icon_index_v1.json"),
        ("i18n_index", INDEX_DIR / "wagstaff_i18n_v1.json"),
        ("tuning_trace", INDEX_DIR / "wagstaff_tuning_trace_v1.json"),
        ("catalog_quality", REPORT_DIR / "catalog_quality_report.md"),
        ("quality_gate", REPORT_DIR / "quality_gate_report.md"),
    ]


def _render_artifacts() -> None:
    table = Table(title="Artifacts", box=None, show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("Updated", style="dim")
    table.add_column("Size", style="green")
    table.add_column("Path", style="dim")

    for name, path in _artifact_rows():
        info = file_info(path)
        status = "[green]OK[/green]" if info["exists"] else "[red]MISSING[/red]"
        table.add_row(
            name,
            status,
            human_mtime(info["mtime"]),
            human_size(info["size"]),
            str(path.relative_to(PROJECT_ROOT)),
        )
    console.print(table)


def _render_quality() -> None:
    qpath = REPORT_DIR / "catalog_quality_report.json"
    doc = read_json(qpath) or {}

    counts = doc.get("counts") if isinstance(doc, dict) else None
    counts = counts if isinstance(counts, dict) else {}
    trace = doc.get("tuning_trace") if isinstance(doc, dict) else None
    trace = trace if isinstance(trace, dict) else {}
    i18n = doc.get("i18n") if isinstance(doc, dict) else None
    i18n = i18n if isinstance(i18n, dict) else {}

    items_total = int(counts.get("items_total") or 0)
    items_with_stats = int(counts.get("items_with_stats") or 0)
    stats_ratio = (items_with_stats / items_total) if items_total else 0.0
    t_items = (trace.get("items") or {}).get("with_trace", 0)
    t_cook = (trace.get("cooking") or {}).get("with_trace", 0)
    i18n_cov = i18n.get("coverage") or {}

    table = Table(title="Quality Snapshot", box=None, show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("items_total", str(items_total))
    table.add_row("items_with_stats", f"{items_with_stats} ({stats_ratio:.1%})")
    table.add_row("tuning_trace", f"items={t_items} cooking={t_cook}")
    if i18n_cov:
        for lang, row in i18n_cov.items():
            try:
                names = row.get("names", 0)
                covered = row.get("coverage_items", {}).get("covered", 0)
                total = row.get("coverage_items", {}).get("total", 0)
                ratio = (covered / total) if total else 0.0
                table.add_row(f"i18n:{lang}", f"{names} names ({ratio:.1%})")
            except Exception:
                continue
    console.print(table)


def _render_tasks(status: Dict[str, Any]) -> None:
    todo = status.get("TASKS_TODO") or []
    done = status.get("TASKS_DONE") or []
    logs = status.get("RECENT_LOGS") or []

    table = Table(title="Tasks", box=None, show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("todo", str(len(todo)))
    table.add_row("done", str(len(done)))
    console.print(table)

    if todo:
        console.print("[bold yellow]Todo (top 6)[/bold yellow]")
        for t in todo[:6]:
            console.print(f"- {t}")
    if logs:
        console.print("\n[bold cyan]Recent Logs[/bold cyan]")
        for line in logs[-6:]:
            console.print(f"- {line}")


def _render_docs() -> None:
    table = Table(title="Docs", box=None, show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Updated", style="dim")
    table.add_column("Path", style="dim")

    docs = [
        ("DEV_GUIDE", PROJECT_ROOT / "docs" / "guides" / "DEV_GUIDE.md"),
        ("PROJECT_MANAGEMENT", PROJECT_ROOT / "docs" / "management" / "PROJECT_MANAGEMENT.md"),
        ("CATALOG_V2_SPEC", PROJECT_ROOT / "docs" / "specs" / "CATALOG_V2_SPEC.md"),
        ("ROADMAP", PROJECT_ROOT / "docs" / "management" / "ROADMAP.md"),
    ]

    for name, path in docs:
        info = file_info(path)
        table.add_row(name, human_mtime(info["mtime"]), str(path.relative_to(PROJECT_ROOT)))
    console.print(table)


def _render_tools() -> None:
    table = Table(title="Toolbox", box=None, show_header=True, header_style="bold cyan")
    table.add_column("Command", style="bold")
    table.add_column("Desc")
    table.add_column("Usage", style="green")
    for tool in get_tools():
        name = tool.get("alias") or tool.get("file") or "-"
        cmd = f"wagstaff {name}" if tool.get("alias") else "wagstaff"
        table.add_row(cmd, tool.get("desc", "-"), tool.get("usage", "-"))
    console.print(table)


def main() -> None:
    status = load_status()
    objective = status.get("OBJECTIVE") or status.get("objective") or "-"
    env_name, env_kind = env_hint()

    header = f"[bold white on blue] Wagstaff-Lab Dashboard (v3) [/bold white on blue]"
    console.print(Panel(header, border_style="blue"))
    console.print(f"[bold green]Objective:[/bold green] {objective}")
    console.print(f"[dim]Root: {PROJECT_ROOT} | Env: {env_name} ({env_kind}) | Data: {DATA_DIR}[/dim]")

    console.print("")
    _render_tasks(status)
    console.print("")
    _render_docs()
    console.print("")
    _render_quality()
    console.print("")
    _render_artifacts()
    console.print("")
    _render_tools()
    console.print("\n[dim]Tips: wagstaff quality | wagstaff catqa | wagstaff catindex | wagstaff snap[/dim]")


if __name__ == "__main__":
    main()

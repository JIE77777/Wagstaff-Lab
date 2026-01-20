#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
from core.version import project_version
from apps.cli.registry import get_tools

console = Console()


def _artifact_rows() -> List[Tuple[str, Path]]:
    return [
        ("resource_index", INDEX_DIR / "wagstaff_resource_index_v1.json"),
        ("catalog_v2", INDEX_DIR / "wagstaff_catalog_v2.json"),
        ("catalog_sqlite", INDEX_DIR / "wagstaff_catalog_v2.sqlite"),
        ("catalog_index", INDEX_DIR / "wagstaff_catalog_index_v1.json"),
        ("icon_index", INDEX_DIR / "wagstaff_icon_index_v1.json"),
        ("i18n_index", INDEX_DIR / "wagstaff_i18n_v1.json"),
        ("tuning_trace", INDEX_DIR / "wagstaff_tuning_trace_v1.json"),
        ("farming_defs", INDEX_DIR / "wagstaff_farming_defs_v1.json"),
        ("mechanism_index", INDEX_DIR / "wagstaff_mechanism_index_v1.json"),
        ("mechanism_sqlite", INDEX_DIR / "wagstaff_mechanism_index_v1.sqlite"),
        ("index_manifest", INDEX_DIR / "wagstaff_index_manifest.json"),
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
    qpath = REPORT_DIR / "quality_gate_report.json"
    doc = read_json(qpath) or {}
    summary = doc.get("summary") if isinstance(doc, dict) else None
    summary = summary if isinstance(summary, dict) else {}

    table = Table(title="Quality Snapshot", box=None, show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")

    issues_total = summary.get("issues_total")
    issues_fail = summary.get("issues_fail")
    issues_warn = summary.get("issues_warn")
    table.add_row("issues", f"total={issues_total} fail={issues_fail} warn={issues_warn}")

    items_total = summary.get("catalog_items_total")
    items_stats = summary.get("catalog_items_with_stats")
    stats_ratio = summary.get("catalog_stats_ratio")
    if items_total is not None:
        ratio_str = f"{float(stats_ratio):.1%}" if isinstance(stats_ratio, (int, float)) else "-"
        table.add_row("catalog", f"items={items_total} stats={items_stats} ({ratio_str})")

    trace_items = summary.get("trace_items")
    trace_cooking = summary.get("trace_cooking")
    if trace_items is not None:
        table.add_row("tuning_trace", f"items={trace_items} cooking={trace_cooking}")

    i18n_cov = summary.get("i18n_coverage") if isinstance(summary.get("i18n_coverage"), dict) else {}
    for lang, row in (i18n_cov or {}).items():
        try:
            ratio = row.get("ratio")
            ratio_str = f"{float(ratio):.1%}" if isinstance(ratio, (int, float)) else "-"
            table.add_row(f"i18n:{lang}", f"names={row.get('names')} ({ratio_str})")
        except Exception:
            continue

    mech_components = summary.get("mechanism_components_total")
    mech_prefabs = summary.get("mechanism_prefabs_total")
    if mech_components is not None:
        table.add_row("mechanism", f"components={mech_components} prefabs={mech_prefabs}")

    sqlite_catalog = summary.get("sqlite_catalog_db_schema_version")
    sqlite_mechanism = summary.get("sqlite_mechanism_db_schema_version")
    if sqlite_catalog or sqlite_mechanism:
        table.add_row("sqlite_v4", f"catalog={sqlite_catalog} mechanism={sqlite_mechanism}")

    console.print(table)


def _render_tasks(status: Dict[str, Any]) -> None:
    todo = status.get("TASKS_TODO") or []
    done = status.get("TASKS_DONE") or []
    logs = status.get("RECENT_LOGS") or []

    focus = str(todo[0]) if todo else "-"
    table = Table(title="Tasks", box=None, show_header=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("todo", str(len(todo)))
    table.add_row("done", str(len(done)))
    table.add_row("focus", focus)
    console.print(table)

    if todo:
        console.print("[bold yellow]Active Tasks (top 8)[/bold yellow]")
        for t in todo[:8]:
            console.print(f"- {t}")
    if done:
        console.print("\n[bold green]Done (recent 5)[/bold green]")
        for t in done[-5:]:
            console.print(f"- {t}")
    if logs:
        console.print("\n[bold cyan]Recent Logs (last 6)[/bold cyan]")
        for line in logs[-6:]:
            console.print(f"- {line}")


def _render_docs() -> None:
    table = Table(title="Docs", box=None, show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Updated", style="dim")
    table.add_column("Path", style="dim")

    docs = [
        ("DEV_GUIDE", PROJECT_ROOT / "docs" / "guides" / "DEV_GUIDE.md"),
        ("CLI_GUIDE", PROJECT_ROOT / "docs" / "guides" / "CLI_GUIDE.md"),
        ("PROJECT_MANAGEMENT", PROJECT_ROOT / "docs" / "management" / "PROJECT_MANAGEMENT.md"),
        ("CATALOG_V2_SPEC", PROJECT_ROOT / "docs" / "specs" / "CATALOG_V2_SPEC.md"),
        ("MECHANISM_INDEX_SPEC", PROJECT_ROOT / "docs" / "specs" / "MECHANISM_INDEX_SPEC.md"),
        ("SQLITE_V4_SPEC", PROJECT_ROOT / "docs" / "specs" / "SQLITE_V4_SPEC.md"),
        ("ROADMAP", PROJECT_ROOT / "docs" / "management" / "ROADMAP.md"),
    ]

    for name, path in docs:
        info = file_info(path)
        table.add_row(name, human_mtime(info["mtime"]), str(path.relative_to(PROJECT_ROOT)))
    console.print(table)


def _status_badge(status: str) -> str:
    if status == "ok":
        return "[green]OK[/green]"
    if status == "partial":
        return "[yellow]PARTIAL[/yellow]"
    if status == "missing":
        return "[red]MISSING[/red]"
    if status == "skipped":
        return "[dim]SKIPPED[/dim]"
    return status or "-"


def _render_reports() -> None:
    manifest_path = REPORT_DIR / "wagstaff_report_manifest.json"
    manifest = read_json(manifest_path) or {}
    counts = manifest.get("counts") if isinstance(manifest, dict) else None
    counts = counts if isinstance(counts, dict) else {}

    summary = Table(title="Reports Summary", box=None, show_header=False)
    summary.add_column("Key", style="bold")
    summary.add_column("Value")
    summary.add_row("reports", str(counts.get("reports", 0)))
    summary.add_row("missing", str(counts.get("missing", 0)))
    summary.add_row("partial", str(counts.get("partial", 0)))
    summary.add_row("manifest", str(manifest_path.relative_to(PROJECT_ROOT)))
    console.print(summary)

    reports = manifest.get("reports") if isinstance(manifest, dict) else None
    reports = reports if isinstance(reports, list) else []
    table = Table(title="Report Inventory", box=None, show_header=True, header_style="bold cyan")
    table.add_column("Report", style="bold")
    table.add_column("Status")
    table.add_column("Updated", style="dim")
    table.add_column("Files", style="green")

    for rep in reports:
        if not isinstance(rep, dict):
            continue
        status = rep.get("status") or "-"
        updated = rep.get("updated")
        files = rep.get("files") if isinstance(rep.get("files"), list) else []
        names = ", ".join(Path(str(f.get("path"))).name for f in files if isinstance(f, dict))
        table.add_row(
            str(rep.get("title") or "-"),
            _status_badge(str(status)),
            human_mtime(float(updated)) if updated else "-",
            names or "-",
        )
    console.print(table)

    portal_path = REPORT_DIR / "portal_index.html"
    portal_info = file_info(portal_path)
    portal_row = Table(title="Report UI", box=None, show_header=False)
    portal_row.add_column("Key", style="bold")
    portal_row.add_column("Value")
    portal_row.add_row("report_hub", str((REPORT_DIR / "index.html").relative_to(PROJECT_ROOT)))
    portal_row.add_row("portal", str(portal_path.relative_to(PROJECT_ROOT)))
    portal_row.add_row("portal_updated", human_mtime(portal_info["mtime"]))
    console.print(portal_row)


def _render_tools() -> None:
    tools = get_tools()
    order = [
        "Entry",
        "Health",
        "Query",
        "Explore",
        "Mgmt",
        "Build",
        "Quality",
        "Reports",
        "Ops",
        "Server",
        "Utility",
        "Other",
    ]
    mapping = {
        "Entry": {"dash"},
        "Health": {"doctor"},
        "Query": {"wiki"},
        "Explore": {"exp"},
        "Mgmt": {"mgmt"},
        "Build": {
            "resindex",
            "catalog2",
            "catalog-sqlite",
            "catindex",
            "i18n",
            "icons",
            "farming-defs",
            "mechanism-index",
            "index-manifest",
        },
        "Quality": {"quality"},
        "Reports": {"report", "portal"},
        "Ops": {"web"},
        "Server": {"server"},
        "Utility": {"snap", "samples"},
    }

    grouped: Dict[str, List[Dict[str, Any]]] = {k: [] for k in order}
    for tool in tools:
        alias = tool.get("alias") or tool.get("file") or ""
        bucket = "Other"
        for label, names in mapping.items():
            if alias in names:
                bucket = label
                break
        grouped[bucket].append(tool)

    for label in order:
        rows = grouped.get(label) or []
        if not rows:
            continue
        table = Table(title=f"Commands · {label}", box=None, show_header=True, header_style="bold cyan")
        table.add_column("Command", style="bold")
        table.add_column("Desc")
        table.add_column("Usage", style="green")
        for tool in rows:
            name = tool.get("alias") or tool.get("file") or "-"
            cmd = f"wagstaff {name}" if tool.get("alias") else "wagstaff"
            table.add_row(cmd, tool.get("desc", "-"), tool.get("usage", "-"))
        console.print(table)


def main() -> None:
    status = load_status()
    objective = status.get("OBJECTIVE") or status.get("objective") or "-"
    env_name, env_kind = env_hint()
    ver = project_version()

    header = f"[bold white on blue] Wagstaff-Lab Dashboard ({ver}) [/bold white on blue]"
    console.print(Panel(header, border_style="blue"))
    console.print(f"[bold green]Objective:[/bold green] {objective}")
    console.print(f"[dim]Root: {PROJECT_ROOT} | Env: {env_name} ({env_kind}) | Data: {DATA_DIR}[/dim]")

    console.print("")
    _render_tasks(status)
    console.print("")
    _render_quality()
    console.print("")
    _render_reports()
    console.print("")
    _render_docs()
    console.print("")
    _render_artifacts()
    console.print("")
    _render_tools()
    console.print("\n[dim]Tips: wagstaff quality | wagstaff report build --quality | wagstaff catindex | wagstaff snap[/dim]")


if __name__ == "__main__":
    main()

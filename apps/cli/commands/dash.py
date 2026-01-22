#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from apps.cli.cli_common import (
    CONF_DIR,
    DATA_DIR,
    INDEX_DIR,
    REPORT_DIR,
    PROJECT_ROOT,
    env_hint,
    file_info,
    human_mtime,
    load_status,
    read_json,
)
from core.version import project_version
from apps.cli.registry import get_tools

console = Console()

PALETTE = {
    "accent": "cyan",
    "muted": "grey70",
    "good": "green",
    "warn": "yellow",
    "bad": "red",
    "info": "blue",
}


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
        ("behavior_graph", INDEX_DIR / "wagstaff_behavior_graph_v1.json"),
        ("index_manifest", INDEX_DIR / "wagstaff_index_manifest.json"),
    ]


def _panel(title: str, body: Any, *, border: str = "cyan") -> Panel:
    return Panel(
        body,
        title=title,
        title_align="left",
        border_style=border,
        box=box.MINIMAL,
        padding=(1, 1),
    )


def _kv_table(rows: List[Tuple[str, Any]]) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_column(justify="right", style="bold", no_wrap=True)
    table.add_column(ratio=1)
    for key, value in rows:
        table.add_row(str(key), value if value is not None else "-")
    return table


def _badge(label: str, level: str) -> Text:
    color = PALETTE.get(level, "white")
    return Text(label, style=f"bold {color}")


def _ratio(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.1%}"
    return "-"


def _bullets(items: List[str], limit: int) -> Text:
    if not items:
        return Text("-", style=f"dim {PALETTE['muted']}")
    trimmed = items[:limit] if limit > 0 else items
    return Text("\n".join(f"- {item}" for item in trimmed))


def _panel_header(ver: str, index_ver: str, env_name: str, env_kind: str) -> Panel:
    title = Text("Wagstaff-Lab Dashboard", style="bold white")
    meta = Text(f"version {ver} | index {index_ver} | env {env_name} ({env_kind})", style="dim")
    content = Group(Align.center(title), Align.center(meta))
    return Panel(content, border_style=PALETTE["accent"], box=box.MINIMAL_DOUBLE_HEAD, padding=(1, 1))


def _panel_overview(objective: str, ver: str, index_ver: str, env_name: str, env_kind: str) -> Panel:
    rows = [
        ("Objective", objective),
        ("Version", ver),
        ("Index", index_ver),
        ("Env", f"{env_name} ({env_kind})"),
        ("Root", str(PROJECT_ROOT)),
        ("Data", str(DATA_DIR)),
    ]
    return _panel("Overview", _kv_table(rows), border=PALETTE["accent"])


def _panel_quality(summary: Dict[str, Any]) -> Panel:
    if not summary:
        body = Text("quality_gate_report.json missing", style="dim")
        return _panel("Quality", body, border=PALETTE["warn"])

    issues_total = summary.get("issues_total")
    issues_fail = summary.get("issues_fail")
    issues_warn = summary.get("issues_warn")
    if issues_fail:
        gate = _badge("FAIL", "bad")
    elif issues_warn:
        gate = _badge("WARN", "warn")
    else:
        gate = _badge("OK", "good")

    items_total = summary.get("catalog_items_total")
    items_stats = summary.get("catalog_items_with_stats")
    stats_ratio = _ratio(summary.get("catalog_stats_ratio"))

    trace_items = summary.get("trace_items")
    trace_cooking = summary.get("trace_cooking")

    mech_components = summary.get("mechanism_components_total")
    mech_prefabs = summary.get("mechanism_prefabs_total")

    sqlite_catalog = summary.get("sqlite_catalog_db_schema_version")
    sqlite_mechanism = summary.get("sqlite_mechanism_db_schema_version")

    rows: List[Tuple[str, Any]] = [
        ("Gate", gate),
        ("Issues", f"total={issues_total} fail={issues_fail} warn={issues_warn}"),
    ]
    if items_total is not None:
        rows.append(("Catalog", f"items={items_total} stats={items_stats} ({stats_ratio})"))
    if trace_items is not None:
        rows.append(("Trace", f"items={trace_items} cooking={trace_cooking}"))
    i18n_cov = summary.get("i18n_coverage") if isinstance(summary.get("i18n_coverage"), dict) else {}
    for lang, row in (i18n_cov or {}).items():
        ratio_str = _ratio(row.get("ratio"))
        rows.append((f"i18n:{lang}", f"names={row.get('names')} ({ratio_str})"))
    if mech_components is not None:
        rows.append(("Mechanism", f"components={mech_components} prefabs={mech_prefabs}"))
    if sqlite_catalog or sqlite_mechanism:
        rows.append(("SQLite v4", f"catalog={sqlite_catalog} mechanism={sqlite_mechanism}"))

    return _panel("Quality", _kv_table(rows), border=PALETTE["good"])


def _panel_tasks(status: Dict[str, Any]) -> Panel:
    todo = status.get("TASKS_TODO") or []
    done = status.get("TASKS_DONE") or []
    logs = status.get("RECENT_LOGS") or []
    focus = str(todo[0]) if todo else "-"

    summary = _kv_table(
        [
            ("Todo", str(len(todo))),
            ("Done", str(len(done))),
            ("Focus", focus),
        ]
    )

    columns = Columns(
        [
            Group(Text(f"Todo ({len(todo)})", style="bold"), _bullets(todo, 5)),
            Group(Text(f"Done ({len(done)})", style="bold"), _bullets(done[-4:], 4)),
            Group(Text("Logs", style="bold"), _bullets(logs[-3:], 3)),
        ],
        equal=True,
        expand=True,
    )

    body = Group(summary, Rule(style="dim"), columns)
    return _panel("Tasks", body, border=PALETTE["warn"])


def _panel_reports() -> Panel:
    manifest_path = REPORT_DIR / "wagstaff_report_manifest.json"
    manifest = read_json(manifest_path) or {}
    counts = manifest.get("counts") if isinstance(manifest, dict) else None
    counts = counts if isinstance(counts, dict) else {}
    reports = manifest.get("reports") if isinstance(manifest, dict) else None
    reports = reports if isinstance(reports, list) else []

    manifest_info = file_info(manifest_path)
    report_hub_path = REPORT_DIR / "index.html"
    portal_path = REPORT_DIR / "portal_index.html"
    report_info = file_info(report_hub_path)
    portal_info = file_info(portal_path)

    rows = [
        ("Reports", f"{counts.get('reports', 0)} total"),
        ("Missing", str(counts.get("missing", 0))),
        ("Partial", str(counts.get("partial", 0))),
        ("Manifest", f"{manifest_path.relative_to(PROJECT_ROOT)} ({human_mtime(manifest_info['mtime'])})"),
        ("Report UI", f"{report_hub_path.relative_to(PROJECT_ROOT)} ({human_mtime(report_info['mtime'])})"),
        ("Portal UI", f"{portal_path.relative_to(PROJECT_ROOT)} ({human_mtime(portal_info['mtime'])})"),
    ]

    attention = []
    for rep in reports:
        if not isinstance(rep, dict):
            continue
        status = str(rep.get("status") or "missing")
        if status in {"missing", "partial"}:
            attention.append(f"- {rep.get('title') or rep.get('id')} ({status})")

    attention_block = Text("\n".join(attention), style="dim") if attention else Text("No missing reports.", style="dim")
    body = Group(_kv_table(rows), Rule(style="dim"), attention_block)
    return _panel("Reports", body, border=PALETTE["info"])


def _panel_artifacts() -> Panel:
    rows = _artifact_rows()
    missing = []
    latest = None
    for name, path in rows:
        info = file_info(path)
        if not info["exists"]:
            missing.append(name)
        if info["mtime"]:
            latest = max(latest or 0, info["mtime"])

    ok_count = len(rows) - len(missing)
    index_manifest = INDEX_DIR / "wagstaff_index_manifest.json"
    manifest_info = file_info(index_manifest)

    summary = _kv_table(
        [
            ("Artifacts", f"{ok_count}/{len(rows)} ok"),
            ("Missing", str(len(missing))),
            ("Latest", human_mtime(latest)),
            ("Manifest", f"{index_manifest.relative_to(PROJECT_ROOT)} ({human_mtime(manifest_info['mtime'])})"),
        ]
    )

    missing_block = Text("\n".join(f"- {name}" for name in missing), style="dim") if missing else Text(
        "No missing artifacts.", style="dim"
    )
    body = Group(summary, Rule(style="dim"), missing_block)
    return _panel("Artifacts", body, border=PALETTE["accent"])


def _panel_docs() -> Panel:
    table = Table(box=box.MINIMAL, show_header=True, header_style="bold cyan")
    table.add_column("Doc", style="bold", no_wrap=True)
    table.add_column("Updated", style="dim", no_wrap=True)
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

    return _panel("Docs", table, border=PALETTE["accent"])


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
            "behavior-graph",
            "index-manifest",
        },
        "Quality": {"quality"},
        "Reports": {"report", "portal"},
        "Ops": {"web"},
        "Server": {"server"},
        "Utility": {"snap", "samples", "farming-sim"},
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

    table = Table(title="Commands", box=box.MINIMAL, show_header=True, header_style="bold cyan")
    table.add_column("Group", style="bold", no_wrap=True)
    table.add_column("Command", style="bold", no_wrap=True)
    table.add_column("Details", ratio=1)

    for label in order:
        rows = grouped.get(label) or []
        if not rows:
            continue
        for idx, tool in enumerate(rows):
            name = tool.get("alias") or tool.get("file") or "-"
            cmd = f"wagstaff {name}" if tool.get("alias") else "wagstaff"
            desc = tool.get("desc", "-")
            usage = tool.get("usage") or ""
            details = Text(desc)
            if usage:
                details.append("\n")
                details.append(usage, style="dim")
            table.add_row(label if idx == 0 else "", cmd, details)

    console.print(table)


def main() -> None:
    status = load_status()
    objective = status.get("OBJECTIVE") or status.get("objective") or "-"
    env_name, env_kind = env_hint()
    ver = project_version()
    version_doc = read_json(CONF_DIR / "version.json") or {}
    index_ver = str(version_doc.get("index_version") or "-")

    qdoc = read_json(REPORT_DIR / "quality_gate_report.json") or {}
    summary = qdoc.get("summary") if isinstance(qdoc, dict) else None
    summary = summary if isinstance(summary, dict) else {}

    console.print(_panel_header(ver, index_ver, env_name, env_kind))
    console.print(
        Columns(
            [
                _panel_overview(objective, ver, index_ver, env_name, env_kind),
                _panel_quality(summary),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print(
        Columns(
            [
                _panel_tasks(status),
                _panel_reports(),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print(
        Columns(
            [
                _panel_artifacts(),
                _panel_docs(),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print("")
    _render_tools()
    console.print("\n[dim]Tips: wagstaff quality | wagstaff report build --quality | wagstaff catindex | wagstaff snap[/dim]")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project management tools (docs + status sync)."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from apps.cli.cli_common import PROJECT_ROOT, load_status

try:
    from rich.console import Console
    from rich.table import Table
except Exception:  # pragma: no cover
    Console = None
    Table = None


@dataclass
class Task:
    key: str
    desc: str


@dataclass
class Milestone:
    key: str
    title: str
    status: str


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _extract_section(text: str, heading_prefix: str) -> str:
    lines = text.splitlines()
    out: List[str] = []
    in_section = False
    for line in lines:
        if line.startswith(heading_prefix):
            if in_section:
                break
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            out.append(line)
    return "\n".join(out)


def _parse_tasks(text: str) -> List[Task]:
    section = _extract_section(text, "## 4.")
    tasks: List[Task] = []
    for line in section.splitlines():
        m = re.match(r"\s*-\s*\*\*(T-\d+)\*\*[：:]?\s*(.+)$", line.strip())
        if not m:
            continue
        key = m.group(1).strip()
        desc = m.group(2).strip()
        tasks.append(Task(key=key, desc=desc))
    return tasks


def _normalize_status(raw: str) -> str:
    r = (raw or "").strip().lower()
    if not r:
        return "unknown"
    if any(x in r for x in ("完成", "done", "complete")):
        return "done"
    if any(x in r for x in ("进行中", "in progress", "ongoing")):
        return "in_progress"
    if any(x in r for x in ("规划中", "planned", "plan")):
        return "planned"
    return r


def _parse_milestones(text: str) -> List[Milestone]:
    section = _extract_section(text, "## 2.")
    out: List[Milestone] = []
    for line in section.splitlines():
        m = re.match(r"\s*-\s*\*\*(M[0-9.]+)\s+([^*]+)\*\*（?([^）)]*)", line.strip())
        if not m:
            continue
        key = m.group(1).strip()
        title = m.group(2).strip()
        status = _normalize_status(m.group(3).strip())
        out.append(Milestone(key=key, title=title, status=status))
    return out


def _default_mgmt_path() -> Path:
    status = load_status()
    doc = status.get("MANAGEMENT_DOC")
    if isinstance(doc, str) and doc:
        return (PROJECT_ROOT / doc).resolve()
    return PROJECT_ROOT / "docs" / "management" / "PROJECT_MANAGEMENT.md"


def _render_status(tasks: List[Task], milestones: List[Milestone], doc_path: Path) -> None:
    if Console is None or Table is None:
        print(f"management: {doc_path}")
        print(f"milestones: {len(milestones)}")
        print(f"tasks: {len(tasks)}")
        for t in tasks:
            print(f"- {t.key} {t.desc}")
        return

    console = Console()
    console.print(f"[bold]Management Doc:[/bold] {doc_path}")

    counts = {"done": 0, "in_progress": 0, "planned": 0, "unknown": 0}
    for m in milestones:
        counts[m.status] = counts.get(m.status, 0) + 1

    table = Table(title="Milestones", box=None, show_header=True, header_style="bold cyan")
    table.add_column("Key", style="bold")
    table.add_column("Title")
    table.add_column("Status", style="green")
    for m in milestones:
        table.add_row(m.key, m.title, m.status)
    console.print(table)

    summary = f"done={counts.get('done',0)} in_progress={counts.get('in_progress',0)} planned={counts.get('planned',0)}"
    console.print(f"[dim]{summary}[/dim]")

    if tasks:
        console.print("[bold]Active Tasks[/bold]")
        for t in tasks:
            console.print(f"- {t.key}: {t.desc}")


def _sync_tasks(status_path: Path, tasks: List[Task], write: bool) -> int:
    status_doc = load_status()
    new_tasks = [f"{t.key}：{t.desc}" for t in tasks]

    old_tasks = status_doc.get("TASKS_TODO") if isinstance(status_doc, dict) else None
    old_tasks = list(old_tasks) if isinstance(old_tasks, list) else []

    if new_tasks == old_tasks:
        print("No changes.")
        return 0

    if not write:
        print("Pending TASKS_TODO update (dry-run):")
        print(json.dumps({"old": old_tasks, "new": new_tasks}, ensure_ascii=False, indent=2))
        return 0

    status_doc["TASKS_TODO"] = new_tasks
    logs = status_doc.get("RECENT_LOGS")
    if not isinstance(logs, list):
        logs = []
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    logs.append(f"[{stamp}] Mgmt: sync TASKS_TODO from PROJECT_MANAGEMENT.md")
    status_doc["RECENT_LOGS"] = logs

    status_path.write_text(json.dumps(status_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("TASKS_TODO updated.")
    return 0


def _dump_json(tasks: List[Task], milestones: List[Milestone], doc_path: Path) -> None:
    payload = {
        "doc": str(doc_path),
        "milestones": [m.__dict__ for m in milestones],
        "tasks": [t.__dict__ for t in tasks],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _file_age_days(path: Path) -> Optional[int]:
    try:
        mtime = path.stat().st_mtime
    except Exception:
        return None
    delta = datetime.now() - datetime.fromtimestamp(mtime)
    return int(delta.total_seconds() // 86400)


def _check_dev_guide() -> int:
    guide_path = PROJECT_ROOT / "docs" / "guides" / "DEV_GUIDE.md"
    readme_path = PROJECT_ROOT / "README.md"
    mgmt_path = _default_mgmt_path()

    if not guide_path.exists():
        print(f"DEV_GUIDE missing: {guide_path}")
        return 2

    text = _read_text(guide_path)
    meta_ok = "DEV_GUIDE_META" in text
    age_days = _file_age_days(guide_path)
    age_note = f"{age_days}d" if age_days is not None else "unknown"
    age_ok = (age_days is None) or (age_days <= 30)

    readme_text = _read_text(readme_path)
    readme_ok = "DEV_GUIDE" in readme_text

    mgmt_ok = mgmt_path.exists()

    if Console is None or Table is None:
        print(f"DEV_GUIDE: {'OK' if meta_ok else 'WARN'} meta")
        print(f"DEV_GUIDE age: {age_note}")
        print(f"README mentions DEV_GUIDE: {readme_ok}")
        print(f"PROJECT_MANAGEMENT exists: {mgmt_ok}")
        return 0

    console = Console()
    table = Table(title="DEV_GUIDE Check", box=None, show_header=True, header_style="bold cyan")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Details", style="dim")
    table.add_row("dev_guide_meta", "[green]OK[/green]" if meta_ok else "[yellow]WARN[/yellow]", "DEV_GUIDE_META block")
    table.add_row("dev_guide_age", "[green]OK[/green]" if age_ok else "[yellow]WARN[/yellow]", f"mtime age {age_note}")
    table.add_row("readme_link", "[green]OK[/green]" if readme_ok else "[yellow]WARN[/yellow]", "README mentions DEV_GUIDE")
    table.add_row("mgmt_doc", "[green]OK[/green]" if mgmt_ok else "[yellow]WARN[/yellow]", str(mgmt_path))
    console.print(table)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Project management tools (docs + status sync)")
    p.add_argument("--doc", default=None, help="Override management doc path")

    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("status", help="Show milestones + active tasks")
    p_sync = sub.add_parser("sync", help="Sync TASKS_TODO from management doc")
    p_sync.add_argument("--write", action="store_true", help="Write changes to PROJECT_STATUS.json")
    sub.add_parser("dump", help="Dump management doc as JSON")
    sub.add_parser("check", help="Check DEV_GUIDE emphasis + freshness")

    args = p.parse_args()

    doc_path = Path(args.doc).resolve() if args.doc else _default_mgmt_path()
    text = _read_text(doc_path)
    if not text:
        raise SystemExit(f"Management doc not found: {doc_path}")

    tasks = _parse_tasks(text)
    milestones = _parse_milestones(text)

    if args.action == "status":
        _render_status(tasks, milestones, doc_path)
        return 0
    if args.action == "sync":
        status_path = PROJECT_ROOT / "PROJECT_STATUS.json"
        return _sync_tasks(status_path, tasks, write=bool(args.write))
    if args.action == "dump":
        _dump_json(tasks, milestones, doc_path)
        return 0
    if args.action == "check":
        return _check_dev_guide()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

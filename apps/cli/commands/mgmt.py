#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project management tools (docs + status sync)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from apps.cli.cli_common import PROJECT_ROOT, load_status
from apps.cli.i18n import resolve_lang, status_label, t
from apps.cli.mgmt_parser import Milestone, Task, parse_milestones, parse_tasks, read_text

try:
    from rich.console import Console
    from rich.table import Table
except Exception:  # pragma: no cover
    Console = None
    Table = None


def _default_mgmt_path() -> Path:
    status = load_status()
    doc = status.get("MANAGEMENT_DOC")
    if isinstance(doc, str) and doc:
        return (PROJECT_ROOT / doc).resolve()
    return PROJECT_ROOT / "docs" / "management" / "PROJECT_MANAGEMENT.md"


def _render_status(tasks: List[Task], milestones: List[Milestone], doc_path: Path, lang: str) -> None:
    if Console is None or Table is None:
        print(f"{t('mgmt.doc_label', lang)}: {doc_path}")
        print(f"{t('mgmt.milestones_count', lang)}: {len(milestones)}")
        print(f"{t('mgmt.tasks_count', lang)}: {len(tasks)}")
        for task in tasks:
            print(f"- {task.key} {task.desc}")
        return

    console = Console()
    console.print(f"[bold]{t('mgmt.doc_label', lang)}:[/bold] {doc_path}")

    counts = {"done": 0, "in_progress": 0, "planned": 0, "unknown": 0}
    for m in milestones:
        counts[m.status] = counts.get(m.status, 0) + 1

    table = Table(title=t("mgmt.milestones_title", lang), box=None, show_header=True, header_style="bold cyan")
    table.add_column(t("mgmt.key", lang), style="bold")
    table.add_column(t("mgmt.title", lang))
    table.add_column(t("mgmt.status", lang), style="green")
    for m in milestones:
        table.add_row(m.key, m.title, status_label(m.status, lang))
    console.print(table)

    summary = (
        f"{t('status.done', lang)}={counts.get('done',0)} "
        f"{t('status.in_progress', lang)}={counts.get('in_progress',0)} "
        f"{t('status.planned', lang)}={counts.get('planned',0)}"
    )
    console.print(f"[dim]{summary}[/dim]")

    if tasks:
        console.print(f"[bold]{t('mgmt.tasks_title', lang)}[/bold]")
        for task in tasks:
            console.print(f"- {task.key}: {task.desc}")


def _sync_tasks(status_path: Path, tasks: List[Task], write: bool, lang: str) -> int:
    status_doc = load_status()
    new_tasks = [f"{t.key}：{t.desc}" for t in tasks]

    old_tasks = status_doc.get("TASKS_TODO") if isinstance(status_doc, dict) else None
    old_tasks = list(old_tasks) if isinstance(old_tasks, list) else []

    if new_tasks == old_tasks:
        print(t("mgmt.no_changes", lang))
        return 0

    if not write:
        print(t("mgmt.pending_update", lang))
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
    print(t("mgmt.tasks_updated", lang))
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


def _check_dev_guide(lang: str) -> int:
    guide_path = PROJECT_ROOT / "docs" / "guides" / "DEV_GUIDE.md"
    readme_path = PROJECT_ROOT / "README.md"
    mgmt_path = _default_mgmt_path()

    if not guide_path.exists():
        print(t("mgmt.devguide_missing", lang).format(path=guide_path))
        return 2

    text = read_text(guide_path)
    meta_ok = "DEV_GUIDE_META" in text
    age_days = _file_age_days(guide_path)
    age_note = f"{age_days}d" if age_days is not None else "unknown"
    age_ok = (age_days is None) or (age_days <= 30)

    readme_text = read_text(readme_path)
    readme_ok = "DEV_GUIDE" in readme_text

    mgmt_ok = mgmt_path.exists()

    if Console is None or Table is None:
        ok_label = t("status.ok", lang)
        warn_label = t("status.warn", lang)
        print(f"{t('mgmt.devguide_meta', lang)}: {ok_label if meta_ok else warn_label}")
        print(f"{t('mgmt.devguide_age', lang)}: {age_note}")
        print(f"{t('mgmt.readme_link', lang)}: {readme_ok}")
        print(f"{t('mgmt.mgmt_doc', lang)}: {mgmt_ok}")
        return 0

    console = Console()
    ok_label = t("status.ok", lang)
    warn_label = t("status.warn", lang)
    table = Table(title=t("mgmt.devguide_check", lang), box=None, show_header=True, header_style="bold cyan")
    table.add_column(t("mgmt.check", lang), style="bold")
    table.add_column(t("mgmt.status", lang))
    table.add_column(t("mgmt.details", lang), style="dim")
    table.add_row(
        t("mgmt.devguide_meta", lang),
        f"[green]{ok_label}[/green]" if meta_ok else f"[yellow]{warn_label}[/yellow]",
        t("mgmt.devguide_meta_hint", lang),
    )
    table.add_row(
        t("mgmt.devguide_age", lang),
        f"[green]{ok_label}[/green]" if age_ok else f"[yellow]{warn_label}[/yellow]",
        t("mgmt.devguide_age_hint", lang).format(age=age_note),
    )
    table.add_row(
        t("mgmt.readme_link", lang),
        f"[green]{ok_label}[/green]" if readme_ok else f"[yellow]{warn_label}[/yellow]",
        t("mgmt.readme_link_hint", lang),
    )
    table.add_row(
        t("mgmt.mgmt_doc", lang),
        f"[green]{ok_label}[/green]" if mgmt_ok else f"[yellow]{warn_label}[/yellow]",
        t("mgmt.mgmt_doc_hint", lang).format(path=str(mgmt_path)),
    )
    console.print(table)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Project management tools (docs + status sync)")
    p.add_argument("--doc", default=None, help="Override management doc path")
    p.add_argument("--lang", default=None, help="Language override (default: WAGSTAFF_LANG)")

    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("status", help="Show milestones + active tasks")
    p_sync = sub.add_parser("sync", help="Sync TASKS_TODO from management doc")
    p_sync.add_argument("--write", action="store_true", help="Write changes to PROJECT_STATUS.json")
    sub.add_parser("dump", help="Dump management doc as JSON")
    sub.add_parser("check", help="Check DEV_GUIDE emphasis + freshness")

    args = p.parse_args()

    lang = resolve_lang(args.lang)
    doc_path = Path(args.doc).resolve() if args.doc else _default_mgmt_path()
    text = read_text(doc_path)
    if not text:
        raise SystemExit(t("mgmt.doc_missing", lang).format(path=doc_path))

    tasks = parse_tasks(text)
    milestones = parse_milestones(text)

    if args.action == "status":
        _render_status(tasks, milestones, doc_path, lang)
        return 0
    if args.action == "sync":
        status_path = PROJECT_ROOT / "PROJECT_STATUS.json"
        return _sync_tasks(status_path, tasks, write=bool(args.write), lang=lang)
    if args.action == "dump":
        _dump_json(tasks, milestones, doc_path)
        return 0
    if args.action == "check":
        return _check_dev_guide(lang)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

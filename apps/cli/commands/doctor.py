#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import configparser
import os
import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from apps.cli.cli_common import (
    CONF_DIR,
    INDEX_DIR,
    PROJECT_ROOT,
    env_hint,
    file_info,
    human_mtime,
    human_size,
)

console = Console()
CONFIG_PATH = CONF_DIR / "settings.ini"


def _expand(p: str) -> str:
    return os.path.expanduser(p.strip())


def _cfg_get(cfg: configparser.ConfigParser, section: str, key: str) -> str:
    try:
        v = cfg.get(section, key, fallback="").strip()
    except Exception:
        v = ""
    return _expand(v) if v else ""


def _status(level: str) -> str:
    if level == "PASS":
        return "[green]PASS[/green]"
    if level == "WARN":
        return "[yellow]WARN[/yellow]"
    return "[red]FAIL[/red]"


def _check_path_exists(path: Path, kind: str, fix: str = ""):
    if kind == "file":
        ok = path.is_file()
    elif kind == "dir":
        ok = path.is_dir()
    else:
        ok = path.exists()
    level = "PASS" if ok else "WARN"
    return ok, level, str(path), fix


def main() -> int:
    p = argparse.ArgumentParser(description="Wagstaff Doctor (environment + data health check)")
    p.add_argument("--enforce", action="store_true", help="exit non-zero on failures (CI)")
    p.add_argument("--strict", action="store_true", help="treat WARN as FAIL (only when --enforce)")
    args = p.parse_args()

    env_name, env_kind = env_hint()
    console.print(Panel(f"[bold cyan]Wagstaff Doctor[/bold cyan]\nEnv: {env_name} ({env_kind})", border_style="cyan"))

    table = Table(title="Health Checks", box=None, show_header=True, header_style="bold cyan")
    table.add_column("Check", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")
    table.add_column("Fix Hint", style="green")

    fail = 0
    warn = 0

    # 1) config file (optional)
    ok, level, details, fix = _check_path_exists(CONFIG_PATH, "file", "Optional: configure conf/settings.ini to enable DST path checks")
    table.add_row("conf/settings.ini", _status(level), details, fix if not ok else "")
    if not ok:
        warn += 1

    cfg = configparser.ConfigParser()
    if ok:
        try:
            cfg.read(CONFIG_PATH)
        except Exception as e:
            table.add_row("parse settings.ini", _status("WARN"), str(e), "Check ini format")
            warn += 1

    dst_root = _cfg_get(cfg, "PATHS", "DST_ROOT") if ok else ""
    steamcmd_dir = _cfg_get(cfg, "PATHS", "STEAMCMD_DIR") if ok else ""
    backup_dir = _cfg_get(cfg, "PATHS", "BACKUP_DIR") if ok else ""

    # 2) data artifacts
    artifacts = [
        ("catalog_v2", INDEX_DIR / "wagstaff_catalog_v2.json"),
        ("catalog_index", INDEX_DIR / "wagstaff_catalog_index_v1.json"),
        ("icon_index", INDEX_DIR / "wagstaff_icon_index_v1.json"),
        ("i18n_index", INDEX_DIR / "wagstaff_i18n_v1.json"),
        ("tuning_trace", INDEX_DIR / "wagstaff_tuning_trace_v1.json"),
    ]
    for name, path in artifacts:
        info = file_info(path)
        level = "PASS" if info["exists"] else "WARN"
        details = f"{human_mtime(info['mtime'])} | {human_size(info['size'])}"
        table.add_row(
            f"data/{name}",
            _status(level),
            details if info["exists"] else "missing",
            "Run the matching build_* script" if not info["exists"] else "",
        )
        if not info["exists"]:
            warn += 1

    # 3) DST root + scripts source (optional)
    if dst_root:
        dst_root_p = Path(dst_root)
        ok, level, details, fix = _check_path_exists(dst_root_p, "dir", "Ensure DST is installed at this path")
        table.add_row("DST_ROOT exists", _status(level), details, fix if level != "PASS" else "")
        if not ok:
            warn += 1

        scripts_zip = dst_root_p / "data" / "databundles" / "scripts.zip"
        scripts_dir = dst_root_p / "data" / "scripts"
        ok_zip = scripts_zip.is_file()
        ok_dir = scripts_dir.is_dir()
        level = "PASS" if (ok_zip or ok_dir) else "WARN"
        details = f"zip={scripts_zip} ({'ok' if ok_zip else 'missing'}), dir={scripts_dir} ({'ok' if ok_dir else 'missing'})"
        table.add_row("scripts source", _status(level), details, "Ensure scripts.zip exists or data/scripts is available" if level != "PASS" else "")
        if level != "PASS":
            warn += 1

    # 4) steamcmd (optional)
    if steamcmd_dir:
        steamcmd = Path(steamcmd_dir) / "steamcmd.sh"
        ok, level, details, fix = _check_path_exists(steamcmd, "file", "Ensure SteamCMD is installed and steamcmd.sh exists")
        table.add_row("steamcmd.sh", _status(level), details, fix if level != "PASS" else "")
        if not ok:
            warn += 1

    # 5) screen (optional)
    screen_path = shutil.which("screen")
    if not screen_path:
        table.add_row("screen installed", _status("WARN"), "(not found)", "sudo apt-get install screen")
        warn += 1
    else:
        try:
            r = subprocess.run(["screen", "-version"], capture_output=True, text=True)
            level = "PASS" if (r.returncode == 0) else "WARN"
            table.add_row("screen installed", _status(level), screen_path, "")
            if level == "WARN":
                warn += 1
        except Exception as e:
            table.add_row("screen installed", _status("WARN"), str(e), "Verify screen is executable")
            warn += 1

    # 6) backup dir (optional)
    if backup_dir:
        bdir = Path(backup_dir)
        level = "PASS" if bdir.exists() else "WARN"
        table.add_row("BACKUP_DIR exists", _status(level), str(bdir), "mkdir -p this directory" if not bdir.exists() else "")
        if level != "PASS":
            warn += 1

    console.print(table)
    console.print(f"[dim]Root: {PROJECT_ROOT} | Summary: FAIL={fail}, WARN={warn}[/dim]")

    if not args.enforce:
        return 0
    if fail:
        return 2
    if args.strict and warn:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

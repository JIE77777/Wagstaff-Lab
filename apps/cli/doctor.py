#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import configparser
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "conf" / "settings.ini"


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
    level = "PASS" if ok else "FAIL"
    return ok, level, str(path), fix


def main() -> int:
    console.print(Panel("[bold cyan]Wagstaff Doctor[/bold cyan]\n环境与配置健康检查", border_style="cyan"))

    table = Table(title="Health Checks", box=None, show_header=True, header_style="bold cyan")
    table.add_column("Check", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")
    table.add_column("Fix Hint", style="green")

    fail = 0
    warn = 0

    # 1) config file
    ok, level, details, fix = _check_path_exists(CONFIG_PATH, "file", "确认 conf/settings.ini 存在并可读")
    table.add_row("conf/settings.ini", _status(level), details, fix)
    if not ok:
        fail += 1
        console.print(table)
        return 1

    cfg = configparser.ConfigParser()
    try:
        cfg.read(CONFIG_PATH)
    except Exception as e:
        table.add_row("parse settings.ini", _status("FAIL"), str(e), "检查 ini 格式")
        console.print(table)
        return 1

    dst_root = _cfg_get(cfg, "PATHS", "DST_ROOT")
    steamcmd_dir = _cfg_get(cfg, "PATHS", "STEAMCMD_DIR")
    backup_dir = _cfg_get(cfg, "PATHS", "BACKUP_DIR")
    cluster = _cfg_get(cfg, "SERVER", "CLUSTER_NAME")
    klei_home = _cfg_get(cfg, "SERVER", "KLEI_HOME")

    # 2) key fields present
    for k, v, hint in [
        ("DST_ROOT", dst_root, "在 conf/settings.ini 配置 PATHS.DST_ROOT"),
        ("STEAMCMD_DIR", steamcmd_dir, "在 conf/settings.ini 配置 PATHS.STEAMCMD_DIR"),
        ("BACKUP_DIR", backup_dir, "在 conf/settings.ini 配置 PATHS.BACKUP_DIR"),
        ("CLUSTER_NAME", cluster, "在 conf/settings.ini 配置 SERVER.CLUSTER_NAME"),
        ("KLEI_HOME", klei_home, "在 conf/settings.ini 配置 SERVER.KLEI_HOME"),
    ]:
        ok = bool(v)
        level = "PASS" if ok else "FAIL"
        table.add_row(f"config: {k}", _status(level), v or "(empty)", hint if not ok else "")
        if not ok:
            fail += 1

    # 3) DST root + binaries
    if dst_root:
        dst_root_p = Path(dst_root)
        ok, level, details, fix = _check_path_exists(dst_root_p, "dir", "确认 DST 已安装到该目录")
        table.add_row("DST_ROOT exists", _status(level), details, fix if level != "PASS" else "")
        if not ok:
            fail += 1

        bin_exe = dst_root_p / "bin" / "dontstarve_dedicated_server_nullrenderer"
        ok, level, details, fix = _check_path_exists(bin_exe, "file", "DST_ROOT/bin 下应存在 dedicated server 可执行文件")
        table.add_row("DST binary", _status(level), details, fix if level != "PASS" else "")
        if not ok:
            fail += 1

        scripts_zip = dst_root_p / "data" / "databundles" / "scripts.zip"
        scripts_dir = dst_root_p / "data" / "scripts"
        ok_zip = scripts_zip.is_file()
        ok_dir = scripts_dir.is_dir()
        level = "PASS" if (ok_zip or ok_dir) else "FAIL"
        details = f"zip={scripts_zip} ({'ok' if ok_zip else 'missing'}), dir={scripts_dir} ({'ok' if ok_dir else 'missing'})"
        table.add_row("scripts source", _status(level), details, "确保 scripts.zip 存在或 data/scripts 可用" if level != "PASS" else "")
        if level != "PASS":
            fail += 1

    # 4) steamcmd
    if steamcmd_dir:
        steamcmd = Path(steamcmd_dir) / "steamcmd.sh"
        ok, level, details, fix = _check_path_exists(steamcmd, "file", "确认 SteamCMD 已安装且 steamcmd.sh 存在")
        table.add_row("steamcmd.sh", _status(level), details, fix if level != "PASS" else "")
        if not ok:
            fail += 1

    # 5) screen
    screen_path = shutil.which("screen")
    if not screen_path:
        table.add_row("screen installed", _status("FAIL"), "(not found)", "sudo apt-get install screen")
        fail += 1
    else:
        try:
            r = subprocess.run(["screen", "-version"], capture_output=True, text=True)
            ok = (r.returncode == 0)
            level = "PASS" if ok else "WARN"
            table.add_row("screen installed", _status(level), screen_path, "")
            if level == "WARN":
                warn += 1
        except Exception as e:
            table.add_row("screen installed", _status("WARN"), str(e), "确认 screen 可执行")
            warn += 1

    # 6) Klei cluster paths
    if klei_home and cluster:
        klei_p = Path(klei_home)
        ok, level, details, fix = _check_path_exists(klei_p, "dir", "确保 KLEI_HOME 存在（通常是 ~/.klei/DoNotStarveTogether）")
        table.add_row("KLEI_HOME exists", _status(level), details, fix if level != "PASS" else "")
        if not ok:
            warn += 1

        cluster_dir = klei_p / cluster
        ok, level, details, fix = _check_path_exists(cluster_dir, "dir", "第一次开服前目录可能不存在；开服一次后应出现")
        table.add_row("Cluster dir", _status("PASS" if ok else "WARN"), details, fix if not ok else "")
        if not ok:
            warn += 1

        master_log = cluster_dir / "Master" / "server_log.txt"
        caves_log = cluster_dir / "Caves" / "server_log.txt"
        # logs may not exist yet -> WARN
        table.add_row("Master log", _status("PASS" if master_log.exists() else "WARN"), str(master_log), "开服后生成" if not master_log.exists() else "")
        table.add_row("Caves log", _status("PASS" if caves_log.exists() else "WARN"), str(caves_log), "开服后生成" if not caves_log.exists() else "")

    # 7) backup dir (do not create; just check)
    if backup_dir:
        bdir = Path(backup_dir)
        if bdir.exists():
            table.add_row("BACKUP_DIR exists", _status("PASS"), str(bdir), "")
        else:
            table.add_row("BACKUP_DIR exists", _status("WARN"), str(bdir), "mkdir -p 该目录")
            warn += 1

    console.print(table)
    console.print(f"[dim]Summary: FAIL={fail}, WARN={warn}[/dim]")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

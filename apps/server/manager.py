#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server operations (screen-based)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from apps.server.config import ServerConfig


def _require_screen() -> None:
    if not shutil.which("screen"):
        raise SystemExit("screen not found (install screen to manage DST sessions).")


def _screen_list() -> str:
    r = subprocess.run(["screen", "-ls"], capture_output=True, text=True)
    return r.stdout or ""


def _screen_has(name: str) -> bool:
    return name in _screen_list()


def _send_screen_cmd(name: str, cmd: str) -> None:
    subprocess.run(["screen", "-S", name, "-p", "0", "-X", "stuff", f"{cmd}\015"], check=False)


def _quit_screen(name: str) -> None:
    subprocess.run(["screen", "-S", name, "-X", "quit"], check=False)


def _dst_env(cfg: ServerConfig) -> dict:
    env = os.environ.copy()
    bin_dir = cfg.bin_dir
    ld = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = f"{bin_dir}/lib32:{bin_dir}:{ld}"
    return env


def status(cfg: ServerConfig) -> int:
    master, caves = get_status(cfg)
    print(f"master: {'running' if master else 'stopped'}")
    print(f"caves:  {'running' if caves else 'stopped'}")
    return 0


def get_status(cfg: ServerConfig) -> tuple[bool, bool]:
    _require_screen()
    master = _screen_has("DST_Master")
    caves = _screen_has("DST_Caves")
    return master, caves


def start(cfg: ServerConfig, *, start_caves: bool = True) -> int:
    _require_screen()
    if _screen_has("DST_Master") or _screen_has("DST_Caves"):
        print("Server already running.")
        return 1

    bin_dir = cfg.bin_dir
    exe = bin_dir / "dontstarve_dedicated_server_nullrenderer"
    if not exe.exists():
        raise SystemExit(f"Missing server binary: {exe}")

    env = _dst_env(cfg)
    subprocess.run(
        ["screen", "-dmS", "DST_Master", "./dontstarve_dedicated_server_nullrenderer", "-console", "-cluster", cfg.cluster_name, "-shard", "Master"],
        cwd=bin_dir,
        env=env,
        check=False,
    )
    print("Master started.")

    if start_caves:
        subprocess.run(
            ["screen", "-dmS", "DST_Caves", "./dontstarve_dedicated_server_nullrenderer", "-console", "-cluster", cfg.cluster_name, "-shard", "Caves"],
            cwd=bin_dir,
            env=env,
            check=False,
        )
        print("Caves started.")
    return 0


def stop(cfg: ServerConfig, *, timeout: float = 40.0, force: bool = False) -> int:
    _require_screen()
    if not (_screen_has("DST_Master") or _screen_has("DST_Caves")):
        print("Server not running.")
        return 1

    for shard in ("DST_Master", "DST_Caves"):
        if _screen_has(shard):
            _send_screen_cmd(shard, "c_shutdown(true)")

    end_at = time.time() + timeout
    while time.time() < end_at:
        if not (_screen_has("DST_Master") or _screen_has("DST_Caves")):
            print("Server stopped.")
            return 0
        time.sleep(0.5)

    if force:
        for shard in ("DST_Master", "DST_Caves"):
            if _screen_has(shard):
                _quit_screen(shard)
        print("Server force-stopped.")
        return 0

    print("Timeout waiting for shutdown. Use --force to kill sessions.")
    return 2


def restart(cfg: ServerConfig, *, start_caves: bool = True, update: bool = False) -> int:
    stop(cfg, timeout=40.0, force=True)
    if update:
        update_game(cfg)
    return start(cfg, start_caves=start_caves)


def update_game(cfg: ServerConfig) -> int:
    if not cfg.steamcmd_dir:
        raise SystemExit("STEAMCMD_DIR missing (conf/settings.ini or --steamcmd-dir).")
    steamcmd = cfg.steamcmd_dir / "steamcmd.sh"
    if not steamcmd.exists():
        raise SystemExit(f"steamcmd.sh not found: {steamcmd}")

    subprocess.run(
        [
            str(steamcmd),
            "+force_install_dir",
            str(cfg.dst_root),
            "+login",
            "anonymous",
            "+app_update",
            "343050",
            "validate",
            "+quit",
        ],
        check=False,
    )
    print("Update completed.")
    return 0


def backup(cfg: ServerConfig, *, out_path: Optional[Path] = None) -> int:
    cfg.backup_dir.mkdir(parents=True, exist_ok=True)
    if not cfg.cluster_dir.exists():
        raise SystemExit(f"Cluster dir missing: {cfg.cluster_dir}")

    if out_path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = cfg.backup_dir / f"backup_{stamp}.tar.gz"

    with tarfile.open(out_path, "w:gz") as tar:
        tar.add(cfg.cluster_dir, arcname=cfg.cluster_name)
    print(f"Backup created: {out_path}")
    return 0


def _safe_delete_cluster(cfg: ServerConfig) -> None:
    target = cfg.cluster_dir.resolve()
    base = cfg.klei_home.resolve()

    if str(target) in ("/", str(Path.home()), str(base)):
        raise SystemExit(f"Refuse to delete unsafe path: {target}")
    if not str(target).startswith(str(base)):
        raise SystemExit("Cluster path is outside KLEI_HOME.")

    shutil.rmtree(target)


def _list_backups(cfg: ServerConfig) -> list[Path]:
    if not cfg.backup_dir.exists():
        return []
    backups = sorted(cfg.backup_dir.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    return backups


def list_backups(cfg: ServerConfig) -> list[Path]:
    return _list_backups(cfg)


def restore(
    cfg: ServerConfig,
    *,
    file_path: Optional[Path] = None,
    index: Optional[int] = None,
    latest: bool = False,
    yes: bool = False,
    start_after: bool = False,
) -> int:
    backups = _list_backups(cfg)
    if not backups:
        raise SystemExit(f"No backups found in {cfg.backup_dir}")

    chosen: Optional[Path] = None
    if file_path:
        chosen = Path(file_path)
    elif index is not None:
        if index < 0 or index >= len(backups):
            raise SystemExit("Backup index out of range.")
        chosen = backups[index]
    elif latest:
        chosen = backups[0]
    else:
        chosen = backups[0]

    if not chosen.exists():
        raise SystemExit(f"Backup not found: {chosen}")
    if not yes:
        raise SystemExit("Restore requires --yes to confirm destructive overwrite.")

    if _screen_has("DST_Master") or _screen_has("DST_Caves"):
        stop(cfg, timeout=40.0, force=True)

    if cfg.cluster_dir.exists():
        _safe_delete_cluster(cfg)

    with tarfile.open(chosen, "r:gz") as tar:
        tar.extractall(cfg.klei_home)
    print(f"Restore completed: {chosen}")

    if start_after:
        return start(cfg, start_caves=True)
    return 0


def logs(cfg: ServerConfig, *, shard: str = "master", follow: bool = False, lines: int = 120) -> int:
    log_path = cfg.master_log if shard == "master" else cfg.caves_log
    if not log_path.exists():
        raise SystemExit(f"Log not found: {log_path}")
    cmd = ["tail", "-n", str(lines), str(log_path)]
    if follow:
        cmd = ["tail", "-f", "-n", str(lines), str(log_path)]
    subprocess.run(cmd, check=False)
    return 0


def send_cmd(cfg: ServerConfig, *, shard: str = "master", command: str = "") -> int:
    _require_screen()
    target = "DST_Master" if shard == "master" else "DST_Caves"
    if not _screen_has(target):
        raise SystemExit(f"{target} is not running.")
    _send_screen_cmd(target, command)
    print("Command sent.")
    return 0

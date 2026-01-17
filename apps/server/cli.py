#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server CLI entrypoint (no data analysis dependency)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

from apps.server.config import DEFAULT_CONFIG_PATH, resolve_config
from apps.server import manager
from apps.server.ui import run_ui


def _add_common_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to conf/settings.ini")
    p.add_argument("--dst-root", default=None)
    p.add_argument("--steamcmd-dir", default=None)
    p.add_argument("--backup-dir", default=None)
    p.add_argument("--cluster-name", default=None)
    p.add_argument("--klei-home", default=None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="DST server management (screen-based)")
    sub = parser.add_subparsers(dest="action", required=True)

    p_status = sub.add_parser("status", help="Show server status")
    _add_common_flags(p_status)

    p_start = sub.add_parser("start", help="Start server")
    _add_common_flags(p_start)
    p_start.add_argument("--no-caves", action="store_true", help="Start Master only")

    p_stop = sub.add_parser("stop", help="Stop server")
    _add_common_flags(p_stop)
    p_stop.add_argument("--timeout", type=float, default=40.0)
    p_stop.add_argument("--force", action="store_true", help="Kill screen sessions if graceful stop times out")

    p_restart = sub.add_parser("restart", help="Restart server")
    _add_common_flags(p_restart)
    p_restart.add_argument("--no-caves", action="store_true")
    p_restart.add_argument("--update", action="store_true")

    p_update = sub.add_parser("update", help="Update DST via SteamCMD")
    _add_common_flags(p_update)

    p_backup = sub.add_parser("backup", help="Create backup tar.gz")
    _add_common_flags(p_backup)
    p_backup.add_argument("--out", default=None, help="Output tar.gz path")

    p_restore = sub.add_parser("restore", help="Restore from backup")
    _add_common_flags(p_restore)
    p_restore.add_argument("--file", default=None, help="Backup tar.gz path")
    p_restore.add_argument("--index", type=int, default=None, help="Backup index (newest=0)")
    p_restore.add_argument("--latest", action="store_true")
    p_restore.add_argument("--yes", action="store_true", help="Confirm destructive overwrite")
    p_restore.add_argument("--start", action="store_true", help="Start after restore")

    p_logs = sub.add_parser("logs", help="Tail server logs")
    _add_common_flags(p_logs)
    p_logs.add_argument("--shard", choices=["master", "caves"], default="master")
    p_logs.add_argument("--follow", action="store_true")
    p_logs.add_argument("--lines", type=int, default=120)

    p_cmd = sub.add_parser("cmd", help="Send console command")
    _add_common_flags(p_cmd)
    p_cmd.add_argument("--shard", choices=["master", "caves"], default="master")
    p_cmd.add_argument("cmd", help="Console command to send")

    p_ui = sub.add_parser("ui", help="Interactive server menu")
    _add_common_flags(p_ui)

    args = parser.parse_args(list(argv) if argv is not None else None)
    cfg = resolve_config(
        config_path=Path(args.config),
        dst_root=args.dst_root,
        steamcmd_dir=args.steamcmd_dir,
        backup_dir=args.backup_dir,
        cluster_name=args.cluster_name,
        klei_home=args.klei_home,
    )

    if args.action == "status":
        return manager.status(cfg)
    if args.action == "start":
        return manager.start(cfg, start_caves=not args.no_caves)
    if args.action == "stop":
        return manager.stop(cfg, timeout=args.timeout, force=args.force)
    if args.action == "restart":
        return manager.restart(cfg, start_caves=not args.no_caves, update=args.update)
    if args.action == "update":
        return manager.update_game(cfg)
    if args.action == "backup":
        out = Path(args.out) if args.out else None
        return manager.backup(cfg, out_path=out)
    if args.action == "restore":
        return manager.restore(
            cfg,
            file_path=Path(args.file) if args.file else None,
            index=args.index,
            latest=args.latest,
            yes=args.yes,
            start_after=args.start,
        )
    if args.action == "logs":
        return manager.logs(cfg, shard=args.shard, follow=args.follow, lines=args.lines)
    if args.action == "cmd":
        return manager.send_cmd(cfg, shard=args.shard, command=args.cmd)
    if args.action == "ui":
        return run_ui(cfg)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

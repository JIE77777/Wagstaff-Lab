#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server config loader (isolated from data analysis)."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "conf" / "settings.ini"


@dataclass(frozen=True)
class ServerConfig:
    dst_root: Path
    steamcmd_dir: Optional[Path]
    backup_dir: Path
    cluster_name: str
    klei_home: Path

    @property
    def bin_dir(self) -> Path:
        return self.dst_root / "bin"

    @property
    def cluster_dir(self) -> Path:
        return self.klei_home / self.cluster_name

    @property
    def master_log(self) -> Path:
        return self.cluster_dir / "Master" / "server_log.txt"

    @property
    def caves_log(self) -> Path:
        return self.cluster_dir / "Caves" / "server_log.txt"


def _expand(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    return os.path.expanduser(val.strip())


def _cfg_get(cfg: configparser.ConfigParser, section: str, key: str) -> Optional[str]:
    try:
        val = cfg.get(section, key, fallback="").strip()
    except Exception:
        val = ""
    return _expand(val) if val else None


def load_ini(path: Path) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not path.exists():
        raise SystemExit(f"Missing config: {path}")
    cfg.read(path)
    return cfg


def resolve_config(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    dst_root: Optional[str] = None,
    steamcmd_dir: Optional[str] = None,
    backup_dir: Optional[str] = None,
    cluster_name: Optional[str] = None,
    klei_home: Optional[str] = None,
) -> ServerConfig:
    cfg = load_ini(config_path)

    dst_root = dst_root or os.environ.get("DST_ROOT") or _cfg_get(cfg, "PATHS", "DST_ROOT")
    steamcmd_dir = steamcmd_dir or os.environ.get("STEAMCMD_DIR") or _cfg_get(cfg, "PATHS", "STEAMCMD_DIR")
    backup_dir = backup_dir or os.environ.get("BACKUP_DIR") or _cfg_get(cfg, "PATHS", "BACKUP_DIR")
    cluster_name = cluster_name or os.environ.get("CLUSTER_NAME") or _cfg_get(cfg, "SERVER", "CLUSTER_NAME")
    klei_home = klei_home or os.environ.get("KLEI_HOME") or _cfg_get(cfg, "SERVER", "KLEI_HOME")

    if not dst_root:
        raise SystemExit("DST_ROOT missing (conf/settings.ini or --dst-root).")
    if not cluster_name:
        raise SystemExit("CLUSTER_NAME missing (conf/settings.ini or --cluster-name).")
    if not klei_home:
        raise SystemExit("KLEI_HOME missing (conf/settings.ini or --klei-home).")

    if not backup_dir:
        backup_dir = str(Path.home() / "dst_backups")

    return ServerConfig(
        dst_root=Path(dst_root),
        steamcmd_dir=Path(steamcmd_dir) if steamcmd_dir else None,
        backup_dir=Path(backup_dir),
        cluster_name=str(cluster_name),
        klei_home=Path(klei_home),
    )

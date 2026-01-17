#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for CLI tools."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
INDEX_DIR = DATA_DIR / "index"
REPORT_DIR = DATA_DIR / "reports"
CONF_DIR = PROJECT_ROOT / "conf"


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def load_status() -> Dict[str, Any]:
    status_path = PROJECT_ROOT / "PROJECT_STATUS.json"
    doc = read_json(status_path)
    return doc if isinstance(doc, dict) else {}


def file_info(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"exists": False, "size": 0, "mtime": None}
    st = path.stat()
    return {"exists": True, "size": int(st.st_size), "mtime": float(st.st_mtime)}


def human_size(num: int) -> str:
    if num <= 0:
        return "-"
    for unit in ("B", "KiB", "MiB", "GiB"):
        if num < 1024.0:
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TiB"


def human_mtime(ts: Optional[float]) -> str:
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def env_hint() -> Tuple[str, str]:
    env = os.environ.get("CONDA_DEFAULT_ENV", "").strip()
    if env:
        return env, "conda"
    venv = os.environ.get("VIRTUAL_ENV", "").strip()
    if venv:
        return venv, "venv"
    return "system", "system"

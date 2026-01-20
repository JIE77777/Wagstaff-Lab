# -*- coding: utf-8 -*-
"""Project version helpers."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _load_version_file() -> Dict[str, str]:
    path = _project_root() / "conf" / "version.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, str] = {}
    for key in ("project_version", "index_version"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()
    return out


def project_version() -> str:
    return _load_version_file().get("project_version", "unknown")


def index_version() -> str:
    ver = _load_version_file().get("index_version")
    if ver:
        return ver
    return project_version()


def versions() -> Dict[str, str]:
    return {
        "project_version": project_version(),
        "index_version": index_version(),
    }

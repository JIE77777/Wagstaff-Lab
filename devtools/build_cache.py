#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE_PATH = PROJECT_ROOT / "data" / "index" / ".build_cache.json"


def load_cache(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or DEFAULT_CACHE_PATH
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}


def save_cache(cache: Dict[str, Any], path: Optional[Path] = None) -> None:
    p = path or DEFAULT_CACHE_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def file_sig(path: Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"path": str(p), "exists": False}
    try:
        st = p.stat()
        return {
            "path": str(p),
            "exists": True,
            "mtime_ns": int(st.st_mtime_ns),
            "size": int(st.st_size),
        }
    except Exception:
        return {"path": str(p), "exists": False}


def files_sig(paths: Iterable[Path], *, label: str = "") -> Dict[str, Any]:
    count = 0
    max_mtime = 0
    total_size = 0
    for p in paths:
        try:
            st = p.stat()
        except Exception:
            continue
        count += 1
        total_size += int(st.st_size)
        max_mtime = max(max_mtime, int(st.st_mtime_ns))
    return {
        "label": label,
        "count": count,
        "max_mtime_ns": max_mtime,
        "total_size": total_size,
    }


def paths_sig(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    rows = [file_sig(p) for p in paths]
    rows.sort(key=lambda x: x.get("path") or "")
    return rows


def dir_sig(
    path: Path,
    *,
    suffixes: Optional[Iterable[str]] = None,
    glob: str = "**/*",
    label: str = "",
) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return {"path": str(p), "exists": False, "label": label}
    suffixes_lc = {s.lower() for s in (suffixes or [])}
    files = []
    for fp in p.rglob(glob):
        if not fp.is_file():
            continue
        if suffixes_lc and fp.suffix.lower() not in suffixes_lc:
            continue
        files.append(fp)
    base = files_sig(files, label=label)
    base["path"] = str(p)
    base["exists"] = True
    return base

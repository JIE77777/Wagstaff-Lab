# -*- coding: utf-8 -*-
"""Extract layouts/set pieces from map/layouts.lua and static_layouts/."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Tuple


_STATIC_LAYOUT_RE = re.compile(
    r'\["(?P<id>[^"]+)"\]\s*=\s*StaticLayout\.Get\(\s*["\'](?P<path>[^"\']+)["\']',
    flags=re.MULTILINE,
)


def _normalize_source(path: str) -> str:
    path = (path or "").strip()
    if path.startswith("scripts/"):
        return path
    if path.startswith("map/"):
        return f"scripts/{path}"
    return path


def extract_layouts(engine: Any) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    layouts: Dict[str, Dict[str, Any]] = {}
    set_pieces: Dict[str, Dict[str, Any]] = {}

    content = engine.read_file("scripts/map/layouts.lua") or ""
    if content:
        for m in _STATIC_LAYOUT_RE.finditer(content):
            lid = m.group("id").strip()
            src = _normalize_source(m.group("path"))
            if lid:
                layouts[lid] = {
                    "type": "layout",
                    "id": lid,
                    "source": src,
                    "layout_type": "STATIC",
                    "raw": {"expr": m.group(0)},
                }
                set_pieces.setdefault(lid, {"id": lid, "layout_id": lid, "source": src})

    for path in getattr(engine, "file_list", []) or []:
        if not str(path).startswith("scripts/map/static_layouts/"):
            continue
        if not str(path).endswith(".lua"):
            continue
        lid = Path(str(path)).stem
        if lid in layouts:
            continue
        layouts[lid] = {
            "type": "layout",
            "id": lid,
            "source": str(path),
            "layout_type": "STATIC",
            "raw": {"expr": "static_layout_file"},
        }
        set_pieces.setdefault(lid, {"id": lid, "layout_id": lid, "source": str(path)})

    return layouts, set_pieces

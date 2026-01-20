# -*- coding: utf-8 -*-
"""Shared helpers for indexers and scans."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Optional

from core.lua import find_matching, parse_lua_table


_ID_RE = re.compile(r"^[a-z0-9_]+$")


def _sha256_12_file(path: Path, chunk_size: int = 1024 * 1024) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()[:12]
    except Exception:
        return None


def _is_simple_id(s: str) -> bool:
    return bool(s) and bool(_ID_RE.match(s))


def _extract_strings_names(engine: Any) -> Dict[str, str]:
    """Extract STRINGS.NAMES mapping from scripts/strings.lua."""
    src = (
        engine.read_file("scripts/strings.lua")
        or engine.read_file("strings.lua")
        or ""
    )
    if not src:
        return {}

    m = re.search(r"\bSTRINGS\s*=\s*\{", src)
    if not m:
        return {}
    strings_open = src.find("{", m.end() - 1)
    if strings_open < 0:
        return {}
    strings_close = find_matching(src, strings_open, "{", "}")
    if strings_close is None:
        return {}

    block = src[strings_open: strings_close + 1]
    m2 = re.search(r"(?<![A-Za-z0-9_])NAMES\s*=\s*\{", block)
    if not m2:
        return {}

    names_open = strings_open + m2.end() - 1
    names_close = find_matching(src, names_open, "{", "}")
    if names_close is None:
        return {}

    inner = src[names_open + 1 : names_close]
    try:
        names_tbl = parse_lua_table(inner)
    except Exception:
        return {}

    out: Dict[str, str] = {}
    for k, v in (names_tbl.map or {}).items():
        if not isinstance(k, str):
            continue
        if not isinstance(v, str):
            continue
        kid = k.strip().lower()
        if not _is_simple_id(kid):
            continue
        out[kid] = v
    return out

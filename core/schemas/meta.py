#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared metadata helpers for index artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from core.version import versions


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_meta(
    *,
    schema: int,
    tool: str,
    sources: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "schema": int(schema),
        "generated": now_iso(),
        "tool": str(tool),
    }
    try:
        meta.update(versions())
    except Exception:
        pass
    if sources:
        meta["sources"] = sources
    if extra:
        meta.update(extra)
    return meta

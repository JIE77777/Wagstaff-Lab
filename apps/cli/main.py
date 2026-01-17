#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified CLI dispatcher for Wagstaff-Lab."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path
from typing import List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _tool_path(tool: dict) -> Path:
    folder = tool.get("folder") or "apps/cli"
    if folder == "apps/cli":
        base = PROJECT_ROOT / "apps" / "cli"
    elif folder == "devtools":
        base = PROJECT_ROOT / "devtools"
    else:
        base = PROJECT_ROOT / folder
    return base / str(tool.get("file"))


def _resolve_tool(alias: Optional[str]) -> Tuple[Path, List[str]]:
    from apps.cli.registry import get_tools

    tools = get_tools()
    dash = next((t for t in tools if t.get("alias") == "dash"), None)
    default_path = _tool_path(dash) if dash else (PROJECT_ROOT / "apps" / "cli" / "commands" / "dash.py")

    if not alias:
        return default_path, []

    key = str(alias).strip()
    if not key:
        return default_path, []

    for tool in tools:
        if tool.get("alias") == key or tool.get("file") == key:
            return _tool_path(tool), []

    # fallback: show dashboard, pass through as arg to help locate typos
    return default_path, [key]


def main(argv: Optional[List[str]] = None) -> None:
    argv = list(argv) if argv is not None else list(sys.argv[1:])
    alias = argv[0] if argv else None
    path, injected = _resolve_tool(alias)

    if argv and alias:
        argv = argv[1:]
    argv = injected + argv

    sys.argv = [str(path)] + argv
    runpy.run_path(str(path), run_name="__main__")


if __name__ == "__main__":
    main()

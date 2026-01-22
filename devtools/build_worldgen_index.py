#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build worldgen index (structure only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.engine import WagstaffEngine  # noqa: E402
from core.indexers.worldgen_index import build_worldgen_index  # noqa: E402

try:
    from core.config import wagstaff_config  # type: ignore
except Exception:
    wagstaff_config = None  # type: ignore


def _resolve_dst_root(arg: Optional[str]) -> Optional[str]:
    if arg:
        return str(arg)
    if wagstaff_config is None:
        return None
    try:
        return wagstaff_config.get("PATHS", "DST_ROOT")
    except Exception:
        return None


def build_index(dst_root: Optional[str], scripts_zip: Optional[str]) -> dict:
    with WagstaffEngine(load_db=False, dst_root=dst_root, scripts_zip=scripts_zip, silent=True) as engine:
        return build_worldgen_index(engine)


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Build worldgen index (structure only).")
    parser.add_argument("--dst-root", default=None, help="DST root path (optional).")
    parser.add_argument("--scripts-zip", default=None, help="Scripts zip path (optional).")
    parser.add_argument(
        "--out",
        default=str(PROJECT_ROOT / "data" / "index" / "wagstaff_worldgen_index_v1.json"),
        help="Output JSON path.",
    )
    args = parser.parse_args(argv)

    dst_root = _resolve_dst_root(args.dst_root)
    doc = build_index(dst_root, args.scripts_zip)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[worldgen-index] wrote: {out}")


if __name__ == "__main__":
    main()

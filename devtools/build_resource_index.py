#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build resource index from DST scripts + data folders."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.engine import WagstaffEngine  # noqa: E402
from core.indexers.resource_index import build_resource_index, render_resource_index_summary  # noqa: E402

try:
    from core.utils import wagstaff_config  # type: ignore
except Exception:
    wagstaff_config = None  # type: ignore


def _resolve_dst_root(arg: str | None) -> str | None:
    if arg:
        return str(arg)
    if wagstaff_config is None:
        return None
    try:
        return wagstaff_config.get("PATHS", "DST_ROOT")
    except Exception:
        return None


def main() -> int:
    p = argparse.ArgumentParser(description="Build Wagstaff resource index (scripts + data).")
    p.add_argument("--out", default="data/index/wagstaff_resource_index_v1.json", help="Output JSON path")
    p.add_argument("--summary", default="data/reports/resource_index_summary.md", help="Output summary Markdown")
    p.add_argument("--data-full", action="store_true", help="Include data/ file list in JSON")
    p.add_argument("--data-max-files", type=int, default=0, help="Limit data file list length (0 = no limit)")
    p.add_argument("--bundle-full", action="store_true", help="Include bundle entry lists in JSON")
    p.add_argument("--bundle-max-files", type=int, default=0, help="Limit bundle entry list length (0 = no limit)")
    p.add_argument("--scripts-zip", default=None, help="Override scripts zip path")
    p.add_argument("--scripts-dir", default=None, help="Override scripts folder path")
    p.add_argument("--dst-root", default=None, help="Override DST root (default from config)")
    p.add_argument("--silent", action="store_true", help="Suppress engine logs")

    args = p.parse_args()

    dst_root = _resolve_dst_root(args.dst_root)
    if not dst_root:
        raise SystemExit("DST_ROOT missing. Set conf/settings.ini or pass --dst-root.")

    engine = WagstaffEngine(
        load_db=False,
        silent=bool(args.silent),
        dst_root=dst_root,
        scripts_zip=args.scripts_zip,
        scripts_dir=args.scripts_dir,
    )

    index = build_resource_index(
        engine=engine,
        dst_root=Path(dst_root).expanduser().resolve(),
        include_data_files=bool(args.data_full),
        max_data_files=int(args.data_max_files or 0),
        include_bundle_files=bool(args.bundle_full),
        max_bundle_files=int(args.bundle_max_files or 0),
    )

    out_path = (PROJECT_ROOT / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = (PROJECT_ROOT / args.summary).resolve()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(render_resource_index_summary(index), encoding="utf-8")

    print(f"✅ Resource index written: {out_path}")
    print(f"✅ Summary written: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

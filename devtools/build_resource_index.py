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
from devtools.build_cache import dir_sig, file_sig, load_cache, paths_sig, save_cache, files_sig  # noqa: E402

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
    p.add_argument("--icon-trace", action="append", default=[], help="Trace icon id (substring match) and record atlas.")
    p.add_argument("--data-full", action="store_true", help="Include data/ file list in JSON")
    p.add_argument("--data-max-files", type=int, default=0, help="Limit data file list length (0 = no limit)")
    p.add_argument("--bundle-full", action="store_true", help="Include bundle entry lists in JSON")
    p.add_argument("--bundle-max-files", type=int, default=0, help="Limit bundle entry list length (0 = no limit)")
    p.add_argument("--scripts-zip", default=None, help="Override scripts zip path")
    p.add_argument("--scripts-dir", default=None, help="Override scripts folder path")
    p.add_argument("--dst-root", default=None, help="Override DST root (default from config)")
    p.add_argument("--force", action="store_true", help="Force rebuild even if cache matches")
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

    dst_root_path = Path(dst_root).expanduser().resolve()

    trace_ids = {x.strip().lower() for x in (args.icon_trace or []) if str(x or "").strip()}

    scripts_sig = {}
    if engine.mode == "zip" and hasattr(engine.source, "filename"):
        scripts_sig = {"mode": "zip", "source": file_sig(Path(engine.source.filename))}
    elif engine.mode == "folder" and engine.source:
        base = Path(str(engine.source))
        files = [base / p for p in (engine.file_list or [])]
        scripts_sig = {"mode": "folder", "source": files_sig(files, label=str(base))}

    bundles_dir = dst_root_path / "data" / "databundles"
    bundle_paths = sorted([p for p in bundles_dir.glob("*.zip") if p.is_file() and p.name.lower() != "scripts.zip"])

    inputs_sig = {
        "dst_root": str(dst_root_path),
        "scripts": scripts_sig,
        "bundles": paths_sig(bundle_paths),
        "images_xml": dir_sig(dst_root_path / "data" / "images", suffixes=[".xml"], glob="**/*.xml", label="images_xml"),
        "icon_trace": sorted(trace_ids),
        "data_full": bool(args.data_full),
        "bundle_full": bool(args.bundle_full),
    }

    out_path = (PROJECT_ROOT / args.out).resolve()
    summary_path = (PROJECT_ROOT / args.summary).resolve()
    outputs_sig = {
        "out": file_sig(out_path),
        "summary": file_sig(summary_path),
    }

    cache = load_cache()
    cache_key = "resource_index"
    if not args.force:
        entry = cache.get(cache_key) or {}
        if entry.get("signature") == inputs_sig and entry.get("outputs") == outputs_sig:
            print("✅ Resource index up-to-date; skip rebuild")
            return 0

    index = build_resource_index(
        engine=engine,
        dst_root=dst_root_path,
        include_data_files=bool(args.data_full),
        max_data_files=int(args.data_max_files or 0),
        include_bundle_files=bool(args.bundle_full),
        max_bundle_files=int(args.bundle_max_files or 0),
        icon_trace_ids=trace_ids,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(render_resource_index_summary(index), encoding="utf-8")

    outputs_sig = {
        "out": file_sig(out_path),
        "summary": file_sig(summary_path),
    }
    cache[cache_key] = {"signature": inputs_sig, "outputs": outputs_sig}
    save_cache(cache)

    print(f"✅ Resource index written: {out_path}")
    print(f"✅ Summary written: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build farming defs index from DST scripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.engine import WagstaffEngine  # noqa: E402
from core.indexers.farming_defs import build_farming_defs  # noqa: E402
from devtools.build_cache import file_sig, files_sig, load_cache, save_cache  # noqa: E402

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
    p = argparse.ArgumentParser(description="Build Wagstaff farming defs index.")
    p.add_argument("--out", default="data/index/wagstaff_farming_defs_v1.json", help="Output JSON path")
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

    scripts_sig = {}
    if engine.mode == "zip" and hasattr(engine.source, "filename"):
        scripts_sig = {"mode": "zip", "source": file_sig(Path(engine.source.filename))}
    elif engine.mode == "folder" and engine.source:
        base = Path(str(engine.source))
        files = [base / p for p in (engine.file_list or [])]
        scripts_sig = {"mode": "folder", "source": files_sig(files, label=str(base))}

    inputs_sig = {
        "dst_root": str(Path(dst_root).expanduser().resolve()),
        "scripts": scripts_sig,
    }

    out_path = (PROJECT_ROOT / args.out).resolve()
    outputs_sig = {
        "out": file_sig(out_path),
    }

    cache = load_cache()
    cache_key = "farming_defs"
    if not args.force:
        entry = cache.get(cache_key) or {}
        if entry.get("signature") == inputs_sig and entry.get("outputs") == outputs_sig:
            print("✅ Farming defs up-to-date; skip rebuild")
            return 0

    doc = build_farming_defs(engine)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs_sig = {
        "out": file_sig(out_path),
    }
    cache[cache_key] = {"signature": inputs_sig, "outputs": outputs_sig}
    save_cache(cache)

    print(f"✅ Farming defs written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

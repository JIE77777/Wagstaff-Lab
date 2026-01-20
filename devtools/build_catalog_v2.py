#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Wagstaff catalog v2 (item-centric)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.indexers.catalog_v2 import build_catalog_v2  # noqa: E402
from core.schemas.catalog_v2 import WagstaffCatalogV2  # noqa: E402
from core.engine import WagstaffEngine  # noqa: E402
from devtools.build_cache import file_sig, load_cache, save_cache, files_sig  # noqa: E402

try:
    from core.config import wagstaff_config  # type: ignore
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


def _load_resource_index(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description="Build Wagstaff catalog v2")
    p.add_argument("--out", default="data/index/wagstaff_catalog_v2.json", help="Output JSON path")
    p.add_argument("--summary", default="data/reports/catalog_v2_summary.md", help="Output summary Markdown")
    p.add_argument("--resource-index", default="data/index/wagstaff_resource_index_v1.json", help="Resource index path")
    p.add_argument("--tag-overrides", default="data/index/tag_overrides_v1.json", help="Tag override path")
    p.add_argument("--tuning-mode", choices=["value_only", "full"], default="value_only")
    p.add_argument("--tuning-trace-out", default="data/index/wagstaff_tuning_trace_v1.json", help="Tuning trace output JSON path")
    p.add_argument("--no-tuning-trace", action="store_true", help="Disable tuning trace output")
    p.add_argument("--scripts-zip", default=None, help="Override scripts zip path")
    p.add_argument("--scripts-dir", default=None, help="Override scripts folder path")
    p.add_argument("--dst-root", default=None, help="Override DST root (default from config)")
    p.add_argument("--force", action="store_true", help="Force rebuild even if cache matches")
    p.add_argument("--silent", action="store_true")

    args = p.parse_args()

    dst_root = _resolve_dst_root(args.dst_root)
    if not dst_root:
        raise SystemExit("DST_ROOT missing. Set conf/settings.ini or pass --dst-root.")

    engine = WagstaffEngine(
        load_db=True,
        silent=bool(args.silent),
        dst_root=dst_root,
        scripts_zip=args.scripts_zip,
        scripts_dir=args.scripts_dir,
    )

    res_path = (PROJECT_ROOT / args.resource_index).resolve()
    if not res_path.exists():
        raise SystemExit(f"Resource index not found: {res_path}")

    scripts_sig = {}
    if engine.mode == "zip" and hasattr(engine.source, "filename"):
        scripts_sig = {"mode": "zip", "source": file_sig(Path(engine.source.filename))}
    elif engine.mode == "folder" and engine.source:
        base = Path(str(engine.source))
        files = [base / p for p in (engine.file_list or [])]
        scripts_sig = {"mode": "folder", "source": files_sig(files, label=str(base))}

    resource_index = _load_resource_index(res_path)

    overrides_path = (PROJECT_ROOT / args.tag_overrides).resolve()
    tag_overrides = str(overrides_path) if overrides_path.exists() else None

    trace_out = "" if args.no_tuning_trace else str(args.tuning_trace_out or "")

    out_path = (PROJECT_ROOT / args.out).resolve()
    summary_path = (PROJECT_ROOT / args.summary).resolve()
    trace_path = (PROJECT_ROOT / trace_out).resolve() if trace_out else None

    inputs_sig = {
        "dst_root": str(dst_root),
        "resource_index": file_sig(res_path),
        "tag_overrides": file_sig(overrides_path),
        "scripts": scripts_sig,
        "tuning_mode": str(args.tuning_mode),
        "tuning_trace": bool(trace_out),
    }
    outputs_sig = {
        "out": file_sig(out_path),
        "summary": file_sig(summary_path),
        "trace": file_sig(trace_path) if trace_path else {"path": "", "exists": False},
    }
    cache = load_cache()
    cache_key = "catalog_v2"
    if not args.force:
        entry = cache.get(cache_key) or {}
        if entry.get("signature") == inputs_sig and entry.get("outputs") == outputs_sig:
            print("✅ Catalog v2 up-to-date; skip rebuild")
            return 0

    catalog, tuning_trace = build_catalog_v2(
        engine=engine,
        resource_index=resource_index,
        tag_overrides_path=tag_overrides,
        tuning_mode=args.tuning_mode,
        include_tuning_trace=bool(trace_out),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(catalog.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(_render_summary(catalog), encoding="utf-8")

    if trace_out and tuning_trace is not None:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text(json.dumps(tuning_trace, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ Tuning trace written: {trace_path}")

    outputs_sig = {
        "out": file_sig(out_path),
        "summary": file_sig(summary_path),
        "trace": file_sig(trace_path) if trace_out else {"path": "", "exists": False},
    }
    cache[cache_key] = {"signature": inputs_sig, "outputs": outputs_sig}
    save_cache(cache)

    print(f"✅ Catalog v2 written: {out_path}")
    print(f"✅ Summary written: {summary_path}")
    return 0


def _render_summary(catalog: WagstaffCatalogV2) -> str:
    stats = catalog.stats
    meta = catalog.meta
    lines = []
    lines.append("# Wagstaff Catalog v2 Summary")
    lines.append("")
    lines.append("## Meta")
    lines.append("```yaml")
    lines.append(f"schema_version: {catalog.schema_version}")
    lines.append(f"tuning_mode: {meta.get('tuning_mode')}")
    lines.append(f"scripts_zip: {meta.get('scripts_zip')}")
    lines.append(f"scripts_dir: {meta.get('scripts_dir')}")
    lines.append("```")
    lines.append("")
    lines.append("## Counts")
    lines.append("```yaml")
    for k, v in stats.items():
        lines.append(f"{k}: {v}")
    lines.append("```")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

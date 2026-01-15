#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wagstaff-Lab DST Code Map (Report)

Goal
- Systematically summarize DST scripts structure:
  - directory distribution
  - category counts
  - hotspot files (by size)

Outputs
- data/reports/dst_codemap.md
- data/reports/dst_codemap.json

Data source is mounted via WagstaffEngine (zip or folder).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Mount src/ (for repo usage). If you place this script elsewhere, ensure engine.py is importable.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from engine import WagstaffEngine  # type: ignore

REPORT_DIR = PROJECT_ROOT / "data" / "reports"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _file_size(engine: WagstaffEngine, path: str) -> int:
    try:
        if engine.mode == "zip":
            return engine.source.getinfo(path).file_size  # type: ignore[attr-defined]
        # folder
        base = engine.source  # type: ignore[assignment]
        real = os.path.join(base, path.replace("scripts/", "", 1))
        return os.path.getsize(real)
    except Exception:
        return -1


def build_codemap(engine: WagstaffEngine) -> Dict[str, object]:
    files = list(engine.file_list)
    lua_files = [f for f in files if f.endswith(".lua")]

    top_dir = Counter()
    second_dir = Counter()

    for f in lua_files:
        clean = f[8:] if f.startswith("scripts/") else f
        parts = clean.split("/")
        if len(parts) == 1:
            top_dir["[Root]"] += 1
        else:
            top_dir[parts[0]] += 1
            if len(parts) >= 2:
                second_dir[f"{parts[0]}/{parts[1]}"] += 1

    categories: Dict[str, List[str]] = {
        "Prefabs": [f for f in lua_files if f.startswith("scripts/prefabs/")],
        "Components": [f for f in lua_files if f.startswith("scripts/components/")],
        "Stategraphs": [f for f in lua_files if f.startswith("scripts/stategraphs/")],
        "Brains": [f for f in lua_files if f.startswith("scripts/brains/")],
        "Behaviours": [f for f in lua_files if f.startswith("scripts/behaviours/")],
        "Widgets": [f for f in lua_files if f.startswith("scripts/widgets/")],
        "Screens": [f for f in lua_files if f.startswith("scripts/screens/")],
        "Strings": [f for f in lua_files if "strings" in f and f.startswith("scripts/")],
        "Recipes": [f for f in lua_files if f.endswith("recipes.lua") or f.endswith("recipes2.lua")],
        "Tuning": [f for f in lua_files if f.endswith("tuning.lua")],
    }
    cat_counts = {k: len(v) for k, v in categories.items()}

    size_list: List[Tuple[int, str]] = [(_file_size(engine, f), f) for f in lua_files]
    size_list.sort(key=lambda x: x[0], reverse=True)

    largest = [{"path": p, "bytes": s} for s, p in size_list[:50] if s >= 0]
    top_dirs = [{"dir": d, "count": c} for d, c in top_dir.most_common(40)]
    top_second = [{"dir": d, "count": c} for d, c in second_dir.most_common(60)]

    return {
        "generated": _now_iso(),
        "engine_mode": engine.mode,
        "total_files": len(files),
        "lua_files": len(lua_files),
        "categories": cat_counts,
        "top_dirs": top_dirs,
        "top_second_level": top_second,
        "largest_lua_files": largest,
    }


def render_md(doc: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# DST Scripts Code Map")
    lines.append("")
    lines.append("## Meta")
    lines.append("```yaml")
    lines.append(f"generated: {doc.get('generated')}")
    lines.append(f"engine_mode: {doc.get('engine_mode')}")
    lines.append(f"total_files: {doc.get('total_files')}")
    lines.append(f"lua_files: {doc.get('lua_files')}")
    lines.append("```")

    lines.append("")
    lines.append("## Category Counts")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|---|---:|")
    for k, v in sorted((doc.get("categories") or {}).items(), key=lambda x: x[0]):
        lines.append(f"| {k} | {v} |")

    lines.append("")
    lines.append("## Top Directories (Lua)")
    lines.append("")
    lines.append("| Dir | Files |")
    lines.append("|---|---:|")
    for item in doc.get("top_dirs") or []:
        lines.append(f"| {item['dir']} | {item['count']} |")

    lines.append("")
    lines.append("## Hotspots: Largest Lua Files")
    lines.append("")
    lines.append("| Bytes | Path |")
    lines.append("|---:|---|")
    for item in doc.get("largest_lua_files") or []:
        lines.append(f"| {item['bytes']} | `{item['path']}` |")

    lines.append("")
    lines.append("## Top 2nd-level Directories")
    lines.append("")
    lines.append("| Dir | Files |")
    lines.append("|---|---:|")
    for item in doc.get("top_second_level") or []:
        lines.append(f"| {item['dir']} | {item['count']} |")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DST scripts code map report.")
    parser.add_argument("--out-md", default=str(REPORT_DIR / "dst_codemap.md"))
    parser.add_argument("--out-json", default=str(REPORT_DIR / "dst_codemap.json"))

    # Source overrides (optional)
    parser.add_argument("--scripts-zip", default=None, help="Override scripts zip path")
    parser.add_argument("--scripts-dir", default=None, help="Override scripts folder path")
    parser.add_argument("--dst-root", default=None, help="Override DST root (fallback search)")

    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    engine = WagstaffEngine(
        load_db=False,
        silent=True,
        scripts_zip=args.scripts_zip,
        scripts_dir=args.scripts_dir,
        dst_root=args.dst_root,
    )
    doc = build_codemap(engine)

    md_path = Path(args.out_md)
    json_path = Path(args.out_json)

    md_path.write_text(render_md(doc), encoding="utf-8")
    json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Code map written: {md_path}")
    print(f"✅ JSON written: {json_path}")


if __name__ == "__main__":
    main()

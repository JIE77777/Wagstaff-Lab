#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""devtools/build_catalog.py

Build a persistent Wagstaff catalog index (JSON).

Outputs (default)
- data/index/wagstaff_catalog_v1.json
- data/reports/catalog_summary.md

Usage
- python devtools/build_catalog.py build
- python devtools/build_catalog.py build --scripts-zip scripts-no-language-pac.zip
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from engine import WagstaffEngine  # noqa: E402
from catalog import WagstaffCatalog  # noqa: E402


def _write_summary(path: Path, catalog: WagstaffCatalog) -> None:
    craft = catalog.craft
    cooking = catalog.cooking or {}

    # Simple stats
    n_craft = len(craft.recipes)
    n_cooking = len(cooking)
    n_filters = len(getattr(craft, "filter_order", []) or [])
    n_tabs = len(getattr(craft, "tab_order", []) or [])

    # Hot ingredients (top 30)
    by_ing = getattr(craft, "by_ingredient", {}) or {}
    ing_counts = sorted(((k, len(v)) for k, v in by_ing.items()), key=lambda x: x[1], reverse=True)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("# Wagstaff Catalog Summary\n\n")
        f.write(f"- schema_version: {catalog.schema_version}\n")
        f.write(f"- scripts_file_count: {catalog.meta.get('scripts_file_count')}\n")
        if catalog.meta.get("scripts_sha256_12"):
            f.write(f"- scripts_sha256_12: {catalog.meta.get('scripts_sha256_12')}\n")
        f.write("\n")

        f.write("## Counts\n")
        f.write(f"- Craft recipes: **{n_craft}**\n")
        f.write(f"- Cooking recipes: **{n_cooking}**\n")
        f.write(f"- Filters: **{n_filters}**\n")
        f.write(f"- Tabs: **{n_tabs}**\n")
        f.write("\n")

        f.write("## Filters (order)\n")
        for x in getattr(craft, "filter_order", []) or []:
            f.write(f"- {x}\n")
        f.write("\n")

        f.write("## Tabs (order)\n")
        for x in getattr(craft, "tab_order", []) or []:
            f.write(f"- {x}\n")
        f.write("\n")

        f.write("## Ingredients hotspots (top 30 by recipe count)\n")
        for ing, cnt in ing_counts[:30]:
            f.write(f"- `{ing}`: {cnt}\n")


def cmd_build(args: argparse.Namespace) -> int:
    engine = WagstaffEngine(
        load_db=True,
        silent=args.silent,
        dst_root=args.dst_root,
        scripts_zip=args.scripts_zip,
        scripts_dir=args.scripts_dir,
    )
    catalog = WagstaffCatalog.build(engine=engine)

    out_json = (PROJECT_ROOT / args.out).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(catalog.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    if args.summary:
        out_md = (PROJECT_ROOT / args.summary).resolve()
        _write_summary(out_md, catalog)

    print(f"OK: {out_json}")
    if args.summary:
        print(f"OK: {PROJECT_ROOT / args.summary}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="build_catalog", description="Build Wagstaff catalog index")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Build catalog")
    b.add_argument("--out", default="data/index/wagstaff_catalog_v1.json", help="Output JSON path (relative to repo)")
    b.add_argument("--summary", default="data/reports/catalog_summary.md", help="Write a Markdown summary")

    b.add_argument("--scripts-zip", default=None, help="Explicit scripts zip path")
    b.add_argument("--scripts-dir", default=None, help="Explicit scripts folder path")
    b.add_argument("--dst-root", default=None, help="DST root (if reading from install)")
    b.add_argument("--silent", action="store_true", help="Suppress logs")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "build":
        return cmd_build(args)
    raise SystemExit("Unknown cmd")


if __name__ == "__main__":
    raise SystemExit(main())

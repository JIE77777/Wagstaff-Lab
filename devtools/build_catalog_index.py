#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build catalog index (compact listing + indexes)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.indexers.catalog_index import build_catalog_index, load_icon_index, render_index_summary  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Build Wagstaff catalog index (compact listing + indexes)")
    p.add_argument("--catalog", default="data/index/wagstaff_catalog_v2.json", help="Catalog JSON path")
    p.add_argument("--icon-index", default="data/index/wagstaff_icon_index_v1.json", help="Icon index JSON path")
    p.add_argument("--out", default="data/index/wagstaff_catalog_index_v1.json", help="Output JSON path")
    p.add_argument("--summary", default="data/reports/catalog_index_summary.md", help="Output summary Markdown")

    args = p.parse_args()

    catalog_path = (PROJECT_ROOT / args.catalog).resolve()
    if not catalog_path.exists():
        raise SystemExit(f"Catalog not found: {catalog_path}")

    icon_index_path = (PROJECT_ROOT / args.icon_index).resolve() if args.icon_index else None
    icon_index = load_icon_index(icon_index_path) if icon_index_path else {}

    doc = json.loads(catalog_path.read_text(encoding="utf-8"))
    index_doc = build_catalog_index(doc, icon_index=icon_index)

    out_path = (PROJECT_ROOT / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = (PROJECT_ROOT / args.summary).resolve()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(render_index_summary(index_doc), encoding="utf-8")

    print(f"OK: Catalog index written: {out_path}")
    print(f"OK: Summary written: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

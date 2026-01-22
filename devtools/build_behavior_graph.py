#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build behavior graph index (stategraph + brain)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.engine import WagstaffEngine  # noqa: E402
from core.indexers.behavior_graph import build_behavior_graph  # noqa: E402


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    p = argparse.ArgumentParser(description="Build behavior graph index (stategraph + brain)")
    p.add_argument("--dst-root", default=None, help="Override DST root")
    p.add_argument("--out", default="data/index/wagstaff_behavior_graph_v1.json", help="Output JSON path")
    args = p.parse_args()

    with WagstaffEngine(load_db=False, silent=True, dst_root=args.dst_root) as engine:
        resource_index = _load_json(PROJECT_ROOT / "data/index/wagstaff_resource_index_v1.json")
        doc = build_behavior_graph(engine=engine, resource_index=resource_index)

    out_path = (PROJECT_ROOT / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Behavior graph index written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

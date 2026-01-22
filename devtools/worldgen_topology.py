#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build topology skeleton (S3) from worldgen structures."""

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
from core.schemas.meta import build_meta  # noqa: E402
from core.worldgen.render import render_topology_dot, render_topology_json  # noqa: E402
from core.worldgen.topology import build_topology_graph  # noqa: E402

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


def _load_or_build(index_path: Path, dst_root: Optional[str], scripts_zip: Optional[str]) -> dict:
    if index_path.exists():
        return json.loads(index_path.read_text(encoding="utf-8"))
    with WagstaffEngine(load_db=False, dst_root=dst_root, scripts_zip=scripts_zip, silent=True) as engine:
        return build_worldgen_index(engine)


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Build worldgen topology skeleton (S3).")
    parser.add_argument("--dst-root", default=None, help="DST root path (optional).")
    parser.add_argument("--scripts-zip", default=None, help="Scripts zip path (optional).")
    parser.add_argument(
        "--index",
        default=str(PROJECT_ROOT / "data" / "index" / "wagstaff_worldgen_index_v1.json"),
        help="Worldgen index path (optional).",
    )
    parser.add_argument(
        "--out-json",
        default=str(PROJECT_ROOT / "data" / "reports" / "worldgen_topology_report.json"),
        help="Output topology JSON path.",
    )
    parser.add_argument(
        "--out-dot",
        default=str(PROJECT_ROOT / "data" / "reports" / "worldgen_topology_graph.dot"),
        help="Output DOT path.",
    )
    args = parser.parse_args(argv)

    dst_root = _resolve_dst_root(args.dst_root)
    index_path = Path(args.index)
    data = _load_or_build(index_path, dst_root, args.scripts_zip)
    graph = build_topology_graph(data)

    meta = build_meta(schema=1, tool="worldgen-topology", sources={"index": str(index_path)})
    report = render_topology_json(graph, meta)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    out_dot = Path(args.out_dot)
    out_dot.parent.mkdir(parents=True, exist_ok=True)
    out_dot.write_text(render_topology_dot(graph), encoding="utf-8")

    print(f"[worldgen-topology] wrote: {out_json}")
    print(f"[worldgen-topology] wrote: {out_dot}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build fixed farming solutions index (perfect complement layouts)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.indexers.farming_fixed import build_farming_fixed  # noqa: E402
from devtools.build_cache import file_sig, load_cache, save_cache  # noqa: E402


def _parse_tile_shapes(text: str) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for item in (text or "").split(","):
        item = item.strip()
        if not item:
            continue
        if "x" not in item:
            continue
        parts = item.split("x")
        if len(parts) != 2:
            continue
        try:
            w = int(parts[0])
            h = int(parts[1])
        except ValueError:
            continue
        if w > 0 and h > 0:
            out.append((w, h))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Build fixed farming solutions index.")
    p.add_argument("--defs", default="data/index/wagstaff_farming_defs_v1.json", help="Farming defs JSON path")
    p.add_argument("--out", default="data/index/wagstaff_farming_fixed_v1.json", help="Output JSON path")
    p.add_argument("--tile-shapes", default="1x1,1x2", help="Comma-separated tile shapes")
    p.add_argument("--pit-modes", default="8,9,10", help="Comma-separated pit modes")
    p.add_argument("--max-kinds", default=3, type=int, help="Max plant kinds per plan")
    p.add_argument("--force", action="store_true", help="Force rebuild even if cache matches")
    args = p.parse_args()

    defs_path = (PROJECT_ROOT / args.defs).resolve()
    if not defs_path.exists():
        raise SystemExit(f"ERR: farming defs missing: {defs_path}")

    out_path = (PROJECT_ROOT / args.out).resolve()
    tile_shapes = _parse_tile_shapes(args.tile_shapes)
    pit_modes = [s.strip() for s in (args.pit_modes or "").split(",") if s.strip()]

    inputs_sig = {
        "defs": file_sig(defs_path),
        "tile_shapes": tile_shapes,
        "pit_modes": pit_modes,
        "max_kinds": int(args.max_kinds),
    }
    outputs_sig = {"out": file_sig(out_path)}

    cache = load_cache()
    cache_key = "farming_fixed"
    if not args.force:
        entry = cache.get(cache_key) or {}
        if entry.get("signature") == inputs_sig and entry.get("outputs") == outputs_sig:
            print("OK: farming fixed solutions up-to-date; skip rebuild")
            return 0

    farming_defs = json.loads(defs_path.read_text(encoding="utf-8"))
    doc = build_farming_fixed(
        farming_defs,
        tile_shapes=tile_shapes,
        pit_modes=pit_modes,
        max_kinds=max(1, int(args.max_kinds)),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    cache[cache_key] = {"signature": inputs_sig, "outputs": {"out": file_sig(out_path)}}
    save_cache(cache)
    print(f"OK: farming fixed solutions written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

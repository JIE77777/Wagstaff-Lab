#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight farming simulation CLI (data-driven)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.sim.farming import list_plants, load_farming_defs, simulate_farming  # noqa: E402


def _parse_stage_points(value: str) -> List[int]:
    parts = [p.strip() for p in (value or "").split(",") if p.strip()]
    if not parts:
        return []
    points = [int(p) for p in parts]
    if len(points) == 1:
        return points * 4
    if len(points) != 4:
        raise ValueError("stage-stress expects 4 values: sprout,small,med,full")
    return points


def _print_human(doc: dict) -> None:
    plant = doc.get("plant") or {}
    stress = doc.get("stress") or {}
    times = doc.get("times") or {}
    loot = doc.get("loot") or {}

    print(f"Plant: {plant.get('id')} (prefab={plant.get('prefab')})")
    print(f"Season: {doc.get('season')} good={doc.get('good_season')} multiplier={doc.get('season_multiplier')}")
    print(
        "Stress: num_stressors={num} stage_points={stage} total={total} final={final}".format(
            num=stress.get("num_stressors"),
            stage=stress.get("stage_points"),
            total=stress.get("total_points"),
            final=stress.get("final_state"),
        )
    )
    print(f"Oversized: {doc.get('oversized')}")
    print("Times (seconds):")
    for key in ("seed", "sprout", "small", "med", "spoil_full", "spoil_oversized", "regrow"):
        if key in times:
            print(f"  {key}: {times.get(key)}")
    print(f"Harvest loot: {loot.get('harvest')}")
    print(f"Rotten loot: {loot.get('rotten')}")


def main() -> int:
    p = argparse.ArgumentParser(description="Farming simulation (lightweight).")
    p.add_argument("plant", nargs="?", help="Plant id (carrot / farm_plant_carrot / carrot_seeds)")
    p.add_argument("--defs", default="data/index/wagstaff_farming_defs_v1.json", help="Farming defs JSON path")
    p.add_argument("--list", action="store_true", help="List available plant ids")
    p.add_argument("--season", default="autumn", help="Season (autumn/winter/spring/summer)")
    p.add_argument("--stress", type=int, default=0, help="Stress points per stage (default 0)")
    p.add_argument("--stage-stress", default="", help="Comma list for sprout,small,med,full")
    p.add_argument("--long-life", action="store_true", help="Apply long-life multiplier to spoil time")
    p.add_argument("--no-oversized", action="store_true", help="Disable oversized result")
    p.add_argument("--json", action="store_true", help="Output JSON")
    args = p.parse_args()

    defs_path = (PROJECT_ROOT / args.defs).resolve()
    farming_defs = load_farming_defs(defs_path)
    if not farming_defs:
        print(f"ERR: farming defs missing or unreadable: {defs_path}")
        return 2

    if args.list:
        for pid in list_plants(farming_defs):
            print(pid)
        return 0

    if not args.plant:
        print("ERR: plant id required. Use --list to see options.")
        return 2

    try:
        stage_points = _parse_stage_points(args.stage_stress)
    except ValueError as exc:
        print(f"ERR: {exc}")
        return 2
    if not stage_points:
        stage_points = [int(args.stress)] * 4

    try:
        doc = simulate_farming(
            farming_defs=farming_defs,
            plant_id=args.plant,
            season=args.season,
            stage_stress_points=stage_points,
            long_life=bool(args.long_life),
            no_oversized=bool(args.no_oversized),
        )
    except Exception as exc:
        print(f"ERR: {exc}")
        return 2

    if args.json:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    else:
        _print_human(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


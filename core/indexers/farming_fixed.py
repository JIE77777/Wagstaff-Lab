# -*- coding: utf-8 -*-
"""Farming fixed solution indexer (perfect complement layouts)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.schemas.meta import build_meta
from core.sim.farming_planner import suggest_plans


SCHEMA_VERSION = 1


def _deficit_count(block: Optional[Dict[str, Any]]) -> int:
    if not isinstance(block, dict):
        return 0
    deficit = block.get("deficit") if isinstance(block.get("deficit"), dict) else {}
    return int(deficit.get("count") or 0)


def _is_perfect(plan: Dict[str, Any]) -> bool:
    nutrients = plan.get("nutrients") if isinstance(plan.get("nutrients"), dict) else {}
    overall = nutrients.get("overall") if isinstance(nutrients.get("overall"), dict) else nutrients
    if _deficit_count(overall):
        return False
    tile = nutrients.get("tile") if isinstance(nutrients.get("tile"), dict) else None
    if tile and _deficit_count(tile) != 0:
        return False
    return True


def _build_sources(farming_defs: Dict[str, Any]) -> Dict[str, Any]:
    meta = farming_defs.get("meta") if isinstance(farming_defs, dict) else {}
    if isinstance(meta, dict) and meta:
        return {"farming_defs": meta}
    return {}


def build_farming_fixed(
    farming_defs: Dict[str, Any],
    *,
    tile_shapes: Optional[Sequence[Tuple[int, int]]] = None,
    pit_modes: Optional[Sequence[str]] = None,
    max_kinds: int = 3,
) -> Dict[str, Any]:
    shapes = list(tile_shapes or [(1, 1), (1, 2)])
    modes = list(pit_modes or ["8", "9", "10"])

    solutions: List[Dict[str, Any]] = []
    for tile in shapes:
        for mode in modes:
            plans = suggest_plans(
                farming_defs,
                slots=1,
                max_kinds=max_kinds,
                tile_shape=tile,
                pit_mode=mode,
                top_n=0,
                prefer_fixed_layout=True,
            )
            for plan in plans:
                if not _is_perfect(plan):
                    continue
                family = plan.get("family") if isinstance(plan.get("family"), dict) else {}
                if family.get("layout_ok") is not True:
                    continue
                if plan.get("overcrowding_ok") is False:
                    continue
                solutions.append(
                    {
                        "mode": "fixed",
                        "tile": {"width": tile[0], "height": tile[1]},
                        "pit_mode": mode,
                        "plants": plan.get("plants"),
                        "counts": plan.get("counts"),
                        "ratio": plan.get("ratio"),
                        "slots": plan.get("slots"),
                        "nutrients": plan.get("nutrients"),
                        "water": plan.get("water"),
                        "family": plan.get("family"),
                        "overcrowding_ok": plan.get("overcrowding_ok"),
                        "layout": plan.get("layout"),
                    }
                )

    return {
        "schema_version": SCHEMA_VERSION,
        "meta": build_meta(
            schema=SCHEMA_VERSION,
            tool="build_farming_fixed",
            sources=_build_sources(farming_defs),
            extra={"tile_shapes": shapes, "pit_modes": modes},
        ),
        "count": len(solutions),
        "solutions": solutions,
    }

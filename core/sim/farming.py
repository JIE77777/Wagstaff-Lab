# -*- coding: utf-8 -*-
"""Lightweight farming simulation helpers (data-driven)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

STAGES = ("seed", "sprout", "small", "med")


def normalize_plant_id(plant_id: str) -> str:
    pid = str(plant_id or "").strip().lower()
    if pid.startswith("farm_plant_"):
        pid = pid[len("farm_plant_") :]
    if pid.endswith("_seeds"):
        pid = pid[: -len("_seeds")]
    return pid


def load_farming_defs(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def list_plants(farming_defs: Dict[str, Any]) -> List[str]:
    plants = farming_defs.get("plants") if isinstance(farming_defs, dict) else None
    plants = plants if isinstance(plants, dict) else {}
    return sorted([str(k) for k in plants.keys() if k])


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float))


def _mul(value: Any, factor: float) -> Any:
    if _is_number(value):
        return float(value) * factor
    return value


def _mul_range(value: Any, factor: float) -> Any:
    if isinstance(value, list) and len(value) == 2 and all(_is_number(v) for v in value):
        return [_mul(value[0], factor), _mul(value[1], factor)]
    if _is_number(value):
        return _mul(value, factor)
    return value


def _calc_grow_time_range(min_time: Any, max_time: Any, step: int, num_steps: int) -> Any:
    if not (_is_number(min_time) and _is_number(max_time)):
        return [min_time, max_time]
    if num_steps <= 0:
        return [float(min_time), float(max_time)]
    var_per_point = (float(max_time) - float(min_time)) / float(num_steps)
    lo = float(min_time) + step * var_per_point
    hi = float(min_time) + (step + 1) * var_per_point
    return [lo, hi]


def _final_stress_state(total: int, thresholds: Dict[str, Any]) -> str:
    none = int(thresholds.get("NONE") or 1)
    low = int(thresholds.get("LOW") or 6)
    moderate = int(thresholds.get("MODERATE") or 11)
    if total <= none:
        return "NONE"
    if total <= low:
        return "LOW"
    if total <= moderate:
        return "MODERATE"
    return "HIGH"


def _clamp_step(step: int, num_stressors: int) -> int:
    if num_stressors <= 0:
        return max(0, step)
    return max(0, min(step, num_stressors))


def _build_harvest_loot(plant: Dict[str, Any], stress_state: str, oversized: bool) -> List[str]:
    if oversized:
        product = plant.get("product_oversized")
        return [product] if product else []
    product = plant.get("product")
    seed = plant.get("seed")
    if not product:
        return []
    if stress_state in ("NONE", "LOW"):
        loot = [product]
        if seed:
            loot += [seed, seed]
        return loot
    if stress_state == "MODERATE":
        loot = [product]
        if seed:
            loot.append(seed)
        return loot
    return [product]


def _build_rotten_loot(plant: Dict[str, Any], oversized: bool) -> List[str]:
    if oversized:
        loot = plant.get("loot_oversized_rot")
        if isinstance(loot, list) and loot:
            return [str(x) for x in loot if x]
        seed = plant.get("seed")
        fallback = ["spoiled_food", "spoiled_food", "spoiled_food"]
        if seed:
            fallback.append(seed)
        fallback += ["fruitfly", "fruitfly"]
        return fallback
    return ["spoiled_food"]


def simulate_farming(
    *,
    farming_defs: Dict[str, Any],
    plant_id: str,
    season: str,
    stage_stress_points: List[int],
    long_life: bool = False,
    no_oversized: bool = False,
) -> Dict[str, Any]:
    plants = farming_defs.get("plants") if isinstance(farming_defs, dict) else None
    plants = plants if isinstance(plants, dict) else {}

    pid = normalize_plant_id(plant_id)
    plant = plants.get(pid)
    if not isinstance(plant, dict):
        raise ValueError(f"Unknown plant id: {plant_id}")

    mechanics = farming_defs.get("mechanics") if isinstance(farming_defs, dict) else {}
    mechanics = mechanics if isinstance(mechanics, dict) else {}
    stress_mech = mechanics.get("stress") if isinstance(mechanics.get("stress"), dict) else {}
    growth_mech = mechanics.get("growth") if isinstance(mechanics.get("growth"), dict) else {}

    categories = stress_mech.get("categories") if isinstance(stress_mech.get("categories"), list) else []
    num_stressors = int(stress_mech.get("num_stressors") or len(categories) or 0)
    thresholds = stress_mech.get("thresholds") if isinstance(stress_mech.get("thresholds"), dict) else {}

    stage_points: List[int] = []
    for point in stage_stress_points:
        step = _clamp_step(int(point), num_stressors)
        stage_points.append(step)
    if not stage_points:
        stage_points = [0, 0, 0, 0]
    if len(stage_points) < 4:
        stage_points += [stage_points[-1]] * (4 - len(stage_points))

    total_stress = sum(stage_points)
    final_stress = _final_stress_state(total_stress, thresholds)

    good_seasons = plant.get("good_seasons") if isinstance(plant.get("good_seasons"), dict) else {}
    season_key = str(season or "").strip().lower()
    is_good_season = bool(good_seasons.get(season_key)) if season_key else False
    base_multiplier = growth_mech.get("good_season_multiplier")
    season_multiplier = float(base_multiplier) if _is_number(base_multiplier) else 0.5
    season_multiplier = season_multiplier if is_good_season else 1.0

    grow_time = plant.get("grow_time") if isinstance(plant.get("grow_time"), dict) else {}

    seed_range = grow_time.get("seed")
    seed_range = _mul_range(seed_range, season_multiplier)

    num_steps = num_stressors + 1 if num_stressors > 0 else 1
    stage_ranges: Dict[str, Any] = {}
    for idx, stage in enumerate(("sprout", "small", "med")):
        bounds = grow_time.get(stage) if isinstance(grow_time.get(stage), list) else None
        if bounds and len(bounds) == 2:
            stage_range = _calc_grow_time_range(bounds[0], bounds[1], stage_points[min(idx, len(stage_points) - 1)], num_steps)
        else:
            stage_range = bounds
        stage_ranges[stage] = _mul_range(stage_range, season_multiplier)

    spoil_full = grow_time.get("full")
    spoil_oversized = grow_time.get("oversized")
    tuning = farming_defs.get("tuning") if isinstance(farming_defs.get("tuning"), dict) else {}
    if long_life:
        mult = tuning.get("FARM_PLANT_LONG_LIFE_MULT")
        long_mult = float(mult) if _is_number(mult) else None
        if long_mult:
            spoil_full = _mul(spoil_full, long_mult)
            spoil_oversized = _mul(spoil_oversized, long_mult)

    regrow_range = grow_time.get("regrow")
    if isinstance(regrow_range, list) and len(regrow_range) == 2:
        regrow_range = [regrow_range[0], regrow_range[1]]

    oversized = final_stress == "NONE" and not bool(no_oversized)

    return {
        "plant": {
            "id": pid,
            "prefab": plant.get("prefab"),
            "product": plant.get("product"),
            "seed": plant.get("seed"),
        },
        "season": season_key,
        "good_season": is_good_season,
        "season_multiplier": season_multiplier,
        "stress": {
            "num_stressors": num_stressors,
            "stage_points": stage_points,
            "total_points": total_stress,
            "final_state": final_stress,
        },
        "oversized": oversized,
        "times": {
            "seed": seed_range,
            **stage_ranges,
            "spoil_full": spoil_full,
            "spoil_oversized": spoil_oversized,
            "regrow": regrow_range if not oversized else None,
        },
        "loot": {
            "harvest": _build_harvest_loot(plant, final_stress, oversized),
            "rotten": _build_rotten_loot(plant, oversized),
        },
    }

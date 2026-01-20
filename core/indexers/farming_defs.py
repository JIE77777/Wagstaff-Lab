# -*- coding: utf-8 -*-
"""Farming defs indexer (farm plants + weeds + fertilizers)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.lua import (
    LuaRaw,
    LuaTableValue,
    find_matching,
    parse_lua_expr,
    parse_lua_table,
    split_top_level,
    strip_lua_comments,
)
from core.parsers import TuningResolver
from core.indexers.shared import _sha256_12_file
from core.schemas.meta import build_meta


SCHEMA_VERSION = 1


def _read(engine: Any, path: str) -> str:
    return engine.read_file(path) or ""


def _parse_locals(src: str) -> Dict[str, Any]:
    clean = strip_lua_comments(src or "")
    out: Dict[str, Any] = {}
    for m in re.finditer(r"^\s*local\s+([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$", clean, flags=re.MULTILINE):
        name = m.group(1)
        rhs = (m.group(2) or "").strip().rstrip(",")
        if not name or not rhs:
            continue
        val = parse_lua_expr(rhs)
        if isinstance(val, LuaRaw):
            out[name] = val.text
        else:
            out[name] = val
    return out


def _substitute_locals(expr: str, locals_map: Dict[str, Any]) -> str:
    if not expr or not locals_map:
        return expr

    def repl(m: re.Match) -> str:
        key = m.group(0)
        if key in locals_map:
            v = locals_map[key]
            if isinstance(v, (int, float)):
                return str(v)
            if isinstance(v, str):
                return v
        return key

    return re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", repl, expr)


def _convert_tuning_table_value(value: Any, *, tuning: Optional[TuningResolver], locals_map: Dict[str, Any]) -> Any:
    if isinstance(value, LuaTableValue):
        if value.map:
            return {str(k): _convert_tuning_table_value(v, tuning=tuning, locals_map=locals_map) for k, v in value.map.items()}
        return [_convert_tuning_table_value(v, tuning=tuning, locals_map=locals_map) for v in value.array]
    if isinstance(value, LuaRaw):
        return _resolve_expr(value.text, tuning=tuning, locals_map=locals_map, tuning_table=None)
    return value


def _resolve_expr(
    expr: Any,
    *,
    tuning: Optional[TuningResolver],
    locals_map: Dict[str, Any],
    tuning_table: Optional[Dict[str, Any]],
) -> Any:
    if expr is None:
        return None
    if isinstance(expr, (int, float, bool)):
        return expr
    if isinstance(expr, LuaRaw):
        expr = expr.text
    if not isinstance(expr, str):
        return expr

    parsed = parse_lua_expr(expr)
    if not isinstance(parsed, LuaRaw):
        return parsed

    raw = _substitute_locals(parsed.text, locals_map).strip()
    if not raw:
        return raw

    m = re.match(r"^TUNING\.([A-Za-z0-9_]+)$", raw)
    if m and tuning_table is not None:
        key = m.group(1)
        if key in tuning_table:
            return _convert_tuning_table_value(tuning_table[key], tuning=tuning, locals_map=locals_map)

    if tuning is not None:
        val = tuning._resolve_ref(raw)
        if val is not None:
            return val

    return raw


def _parse_table_expr(
    rhs: str,
    *,
    tuning: Optional[TuningResolver],
    locals_map: Dict[str, Any],
    tuning_table: Optional[Dict[str, Any]],
) -> Any:
    rhs = (rhs or "").strip().rstrip(",")
    if not (rhs.startswith("{") and rhs.endswith("}")):
        return _resolve_expr(rhs, tuning=tuning, locals_map=locals_map, tuning_table=tuning_table)
    inner = rhs[1:-1]
    tbl = parse_lua_table(inner)
    if tbl.map:
        return {
            str(k): _resolve_expr(v, tuning=tuning, locals_map=locals_map, tuning_table=tuning_table)
            for k, v in tbl.map.items()
        }
    return [_resolve_expr(v, tuning=tuning, locals_map=locals_map, tuning_table=tuning_table) for v in tbl.array]


def _extract_call_args(expr: str, fn_name: str) -> List[str]:
    expr = (expr or "").strip()
    if not expr.startswith(fn_name):
        return []
    open_idx = expr.find("(")
    if open_idx == -1:
        return []
    close_idx = find_matching(expr, open_idx, "(", ")")
    if close_idx is None:
        return []
    inner = expr[open_idx + 1 : close_idx]
    return [s.strip() for s in split_top_level(inner, sep=",") if s.strip()]


def _extract_tuning_tables(src: str, keys: Iterable[str]) -> Dict[str, Any]:
    clean = strip_lua_comments(src or "")
    out: Dict[str, Any] = {}
    for key in keys:
        if not key:
            continue
        m = re.search(rf"\b{re.escape(key)}\s*=\s*\{{", clean)
        if not m:
            continue
        open_idx = clean.find("{", m.end() - 1)
        close_idx = find_matching(clean, open_idx, "{", "}")
        if close_idx is None:
            continue
        inner = clean[open_idx + 1 : close_idx]
        try:
            tbl = parse_lua_table(inner)
        except Exception:
            continue
        out[key] = tbl
    return out


def _parse_top_level_tables(src: str, prefix: str) -> Dict[str, Dict[str, Any]]:
    clean = strip_lua_comments(src or "")
    out: Dict[str, Dict[str, Any]] = {}
    pat = re.compile(rf"\b{re.escape(prefix)}\.([A-Za-z0-9_]+)\s*=\s*\{{")
    for m in pat.finditer(clean):
        name = m.group(1)
        open_idx = clean.find("{", m.end() - 1)
        close_idx = find_matching(clean, open_idx, "{", "}")
        if close_idx is None:
            continue
        inner = clean[open_idx + 1 : close_idx]
        tbl = parse_lua_table(inner)
        row: Dict[str, Any] = {}
        for k, v in tbl.map.items():
            key = str(k)
            row[key] = v
        out[name] = row
    return out


def _parse_field_assignments(src: str, prefix: str) -> Iterable[Tuple[str, str, str]]:
    clean = strip_lua_comments(src or "")
    for line in clean.splitlines():
        if not line.strip():
            continue
        m = re.match(rf"^\s*{re.escape(prefix)}\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$", line)
        if not m:
            continue
        name, field, rhs = m.group(1), m.group(2), m.group(3)
        if not rhs or rhs.strip() == "":
            continue
        yield name, field, rhs.strip()


def _compute_plant_grow_time(
    args: List[str],
    *,
    tuning: Optional[TuningResolver],
    locals_map: Dict[str, Any],
    tuning_table: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if len(args) < 4:
        return {}
    germ_min = _resolve_expr(args[0], tuning=tuning, locals_map=locals_map, tuning_table=tuning_table)
    germ_max = _resolve_expr(args[1], tuning=tuning, locals_map=locals_map, tuning_table=tuning_table)
    full_min = _resolve_expr(args[2], tuning=tuning, locals_map=locals_map, tuning_table=tuning_table)
    full_max = _resolve_expr(args[3], tuning=tuning, locals_map=locals_map, tuning_table=tuning_table)

    def _mul(val: Any, factor: float) -> Any:
        if isinstance(val, (int, float)):
            return val * factor
        return val

    total_day = None
    if tuning is not None:
        total_day = tuning._resolve_ref("TUNING.TOTAL_DAY_TIME")
    total_day = total_day if isinstance(total_day, (int, float)) else None

    grow = {
        "seed": [germ_min, germ_max],
        "sprout": [_mul(full_min, 0.5), _mul(full_max, 0.5)],
        "small": [_mul(full_min, 0.3), _mul(full_max, 0.3)],
        "med": [_mul(full_min, 0.2), _mul(full_max, 0.2)],
    }
    if total_day is not None:
        grow["full"] = 4 * total_day
        grow["oversized"] = 6 * total_day
        grow["regrow"] = [4 * total_day, 5 * total_day]
    return grow


def _compute_weed_grow_time(
    args: List[str],
    *,
    tuning: Optional[TuningResolver],
    locals_map: Dict[str, Any],
    tuning_table: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if len(args) < 3:
        return {}
    full_min = _resolve_expr(args[0], tuning=tuning, locals_map=locals_map, tuning_table=tuning_table)
    full_max = _resolve_expr(args[1], tuning=tuning, locals_map=locals_map, tuning_table=tuning_table)
    bolting = _resolve_expr(args[2], tuning=tuning, locals_map=locals_map, tuning_table=tuning_table)

    def _mul(val: Any, factor: float) -> Any:
        if isinstance(val, (int, float)):
            return val * factor
        return val

    grow = {}
    if bolting:
        grow["small"] = [_mul(full_min, 0.3), _mul(full_max, 0.3)]
        grow["med"] = [_mul(full_min, 0.3), _mul(full_max, 0.3)]
        grow["full"] = [_mul(full_min, 0.4), _mul(full_max, 0.4)]
    else:
        grow["small"] = [_mul(full_min, 0.6), _mul(full_max, 0.6)]
        grow["med"] = [_mul(full_min, 0.4), _mul(full_max, 0.4)]
    return grow


def _parse_seed_weights(veggies_src: str, tuning: Optional[TuningResolver]) -> Dict[str, Any]:
    clean = strip_lua_comments(veggies_src or "")
    locals_map = _parse_locals(clean)
    m = re.search(r"\bVEGGIES\s*=\s*\{", clean)
    if not m:
        return {}
    open_idx = clean.find("{", m.end() - 1)
    close_idx = find_matching(clean, open_idx, "{", "}")
    if close_idx is None:
        return {}
    inner = clean[open_idx + 1 : close_idx]
    tbl = parse_lua_table(inner)
    out: Dict[str, Any] = {}
    for key, val in tbl.map.items():
        if not isinstance(key, str):
            continue
        if not isinstance(val, LuaRaw):
            continue
        args = _extract_call_args(val.text, "MakeVegStats")
        if not args:
            continue
        weight = _resolve_expr(args[0], tuning=tuning, locals_map=locals_map, tuning_table=None)
        out[key] = weight
    return out


def _parse_plants(
    src: str,
    *,
    tuning: Optional[TuningResolver],
    tuning_table: Optional[Dict[str, Any]],
    seed_weights: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    locals_map = _parse_locals(src)
    defs = _parse_top_level_tables(src, "PLANT_DEFS")

    allowed_fields = {
        "grow_time",
        "moisture",
        "good_seasons",
        "nutrient_consumption",
        "max_killjoys_tolerance",
        "is_randomseed",
        "fireproof",
        "weight_data",
    }

    for name, field, rhs in _parse_field_assignments(src, "PLANT_DEFS"):
        if field not in allowed_fields:
            continue
        defs.setdefault(name, {})
        if field == "grow_time":
            args = _extract_call_args(rhs, "MakeGrowTimes")
            defs[name][field] = _compute_plant_grow_time(
                args, tuning=tuning, locals_map=locals_map, tuning_table=tuning_table
            )
            continue
        defs[name][field] = _parse_table_expr(
            rhs, tuning=tuning, locals_map=locals_map, tuning_table=tuning_table
        )

    for name, data in defs.items():
        if "nutrient_consumption" in data and isinstance(data["nutrient_consumption"], list):
            data["nutrient_restoration"] = [
                True if v == 0 else None for v in data["nutrient_consumption"]
            ]

        data.setdefault("prefab", f"farm_plant_{name}")
        data.setdefault("bank", data.get("prefab"))
        data.setdefault("build", data.get("prefab"))

        if data.get("is_randomseed"):
            data["seed"] = "seeds"
            data["plant_type_tag"] = "farm_plant_randomseed"
            data.setdefault("family_min_count", 0)
        else:
            data["product"] = name
            data["product_oversized"] = f"{name}_oversized"
            data["seed"] = f"{name}_seeds"
            data["plant_type_tag"] = f"farm_plant_{name}"
            data.setdefault(
                "loot_oversized_rot",
                ["spoiled_food", "spoiled_food", "spoiled_food", data["seed"], "fruitfly", "fruitfly"],
            )
            if "family_min_count" not in data:
                data["family_min_count"] = (
                    tuning._resolve_ref("TUNING.FARM_PLANT_SAME_FAMILY_MIN") if tuning else None
                )
            if "family_check_dist" not in data:
                data["family_check_dist"] = (
                    tuning._resolve_ref("TUNING.FARM_PLANT_SAME_FAMILY_RADIUS") if tuning else None
                )

        if name in seed_weights:
            data["seed_weight"] = seed_weights[name]

    return defs


def _parse_weeds(
    src: str,
    *,
    tuning: Optional[TuningResolver],
    tuning_table: Optional[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    locals_map = _parse_locals(src)
    defs = _parse_top_level_tables(src, "WEED_DEFS")

    allowed_fields = {
        "grow_time",
        "spread",
        "seed_weight",
        "product",
        "nutrient_consumption",
        "moisture",
        "extra_tags",
        "prefab_deps",
    }

    for name, field, rhs in _parse_field_assignments(src, "WEED_DEFS"):
        if field not in allowed_fields:
            continue
        defs.setdefault(name, {})
        if field == "grow_time":
            args = _extract_call_args(rhs, "MakeGrowTimes")
            defs[name][field] = _compute_weed_grow_time(
                args, tuning=tuning, locals_map=locals_map, tuning_table=tuning_table
            )
            continue
        defs[name][field] = _parse_table_expr(
            rhs, tuning=tuning, locals_map=locals_map, tuning_table=tuning_table
        )

    return defs


def _parse_fertilizers(
    src: str,
    *,
    tuning: Optional[TuningResolver],
    tuning_table: Optional[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    locals_map = _parse_locals(src)
    defs = _parse_top_level_tables(src, "FERTILIZER_DEFS")

    for name, field, rhs in _parse_field_assignments(src, "FERTILIZER_DEFS"):
        defs.setdefault(name, {})
        defs[name][field] = _parse_table_expr(
            rhs, tuning=tuning, locals_map=locals_map, tuning_table=tuning_table
        )

    for data in defs.values():
        for field, val in list(data.items()):
            data[field] = _resolve_expr(
                val, tuning=tuning, locals_map=locals_map, tuning_table=tuning_table
            )

    return defs


def build_farming_defs(engine: Any) -> Dict[str, Any]:
    tuning_src = _read(engine, "scripts/tuning.lua") or _read(engine, "tuning.lua")
    tuning = engine.tuning if getattr(engine, "tuning", None) is not None else TuningResolver(tuning_src or "")
    tuning_table_keys = [
        "SEASONAL_WEED_SPAWN_CAHNCE",
        "POOP_NUTRIENTS",
        "FERTILIZER_NUTRIENTS",
        "GUANO_NUTRIENTS",
        "SPOILED_FOOD_NUTRIENTS",
        "ROTTENEGG_NUTRIENTS",
        "COMPOST_NUTRIENTS",
        "SPOILED_FISH_SMALL_NUTRIENTS",
        "SPOILED_FISH_NUTRIENTS",
        "SOILAMENDER_NUTRIENTS_LOW",
        "SOILAMENDER_NUTRIENTS_MED",
        "SOILAMENDER_NUTRIENTS_HIGH",
        "COMPOSTWRAP_NUTRIENTS",
        "GLOMMERFUEL_NUTRIENTS",
        "MOSQUITOFERTILIZER_NUTRIENTS",
        "TREEGROWTH_NUTRIENTS",
    ]
    tuning_table = _extract_tuning_tables(tuning_src or "", tuning_table_keys)

    plant_src = _read(engine, "scripts/prefabs/farm_plant_defs.lua")
    weed_src = _read(engine, "scripts/prefabs/weed_defs.lua")
    fert_src = _read(engine, "scripts/prefabs/fertilizer_nutrient_defs.lua")
    veggies_src = _read(engine, "scripts/prefabs/veggies.lua")

    seed_weights = _parse_seed_weights(veggies_src, tuning)
    plants = _parse_plants(
        plant_src, tuning=tuning, tuning_table=tuning_table, seed_weights=seed_weights
    )
    weeds = _parse_weeds(weed_src, tuning=tuning, tuning_table=tuning_table)
    fertilizers = _parse_fertilizers(fert_src, tuning=tuning, tuning_table=tuning_table)

    tuning_keys = [
        "FARM_PLANT_RANDOMSEED_WEED_CHANCE",
        "SEED_WEIGHT_SEASON_MOD",
        "SEED_CHANCE_VERYCOMMON",
        "SEED_CHANCE_COMMON",
        "SEED_CHANCE_UNCOMMON",
        "SEED_CHANCE_RARE",
        "FARM_PLANT_CONSUME_NUTRIENT_LOW",
        "FARM_PLANT_CONSUME_NUTRIENT_MED",
        "FARM_PLANT_CONSUME_NUTRIENT_HIGH",
        "FARM_PLANT_DRINK_LOW",
        "FARM_PLANT_DRINK_MED",
        "FARM_PLANT_DRINK_HIGH",
        "FARM_PLANT_DROUGHT_TOLERANCE",
        "FARM_PLANT_KILLJOY_RADIUS",
        "FARM_PLANT_KILLJOY_TOLERANCE",
        "FARM_PANT_OVERCROWDING_MAX_PLANTS",
        "FARM_PLANT_SAME_FAMILY_MIN",
        "FARM_PLANT_SAME_FAMILY_RADIUS",
        "FARM_PLANT_LONG_LIFE_MULT",
        "STARTING_NUTRIENTS_MIN",
        "STARTING_NUTRIENTS_MAX",
        "SOIL_MOISTURE_UPDATE_TIME",
        "SOIL_RAIN_MOD",
        "SOIL_MIN_DRYING_TEMP",
        "SOIL_MAX_DRYING_TEMP",
        "SOIL_MIN_TEMP_DRY_RATE",
        "SOIL_MAX_TEMP_DRY_RATE",
        "SOIL_MAX_MOISTURE_VALUE",
        "FARM_TILL_SPACING",
        "FARM_PLANT_PHYSICS_RADIUS",
        "FARM_PLOW_USES",
        "FARM_HOE_USES",
        "SEASONAL_WEED_SPAWN_CAHNCE",
        "FORGETMELOTS_RESPAWNER_MIN",
        "FORGETMELOTS_RESPAWNER_VAR",
        "FIRE_NETTLE_TOXIN_TEMP_MODIFIER",
        "FIRE_NETTLE_TOXIN_DURATION",
        "WEED_FIRENETTLE_DAMAGE",
        "WEED_TILLWEED_MAX_DEBRIS",
        "WEED_TILLWEED_DEBRIS_TIME_MIN",
        "WEED_TILLWEED_DEBRIS_TIME_VAR",
        "FORMULA_NUTRIENTS_INDEX",
        "COMPOST_NUTRIENTS_INDEX",
        "MANURE_NUTRIENTS_INDEX",
        "POOP_NUTRIENTS",
        "FERTILIZER_NUTRIENTS",
        "GUANO_NUTRIENTS",
        "SPOILED_FOOD_NUTRIENTS",
        "ROTTENEGG_NUTRIENTS",
        "COMPOST_NUTRIENTS",
        "SPOILED_FISH_SMALL_NUTRIENTS",
        "SPOILED_FISH_NUTRIENTS",
        "SOILAMENDER_NUTRIENTS_LOW",
        "SOILAMENDER_NUTRIENTS_MED",
        "SOILAMENDER_NUTRIENTS_HIGH",
        "COMPOSTWRAP_NUTRIENTS",
        "GLOMMERFUEL_NUTRIENTS",
        "MOSQUITOFERTILIZER_NUTRIENTS",
        "TREEGROWTH_NUTRIENTS",
    ]
    tuning_out: Dict[str, Any] = {}
    for key in tuning_keys:
        if key in tuning_table:
            tuning_out[key] = _convert_tuning_table_value(
                tuning_table[key], tuning=tuning, locals_map={}
            )
            continue
        tuning_out[key] = tuning._resolve_ref(f"TUNING.{key}") if tuning else None

    scripts_zip = getattr(getattr(engine, "source", None), "filename", None)
    scripts_sha = _sha256_12_file(Path(scripts_zip)) if scripts_zip else None
    scripts_dir = getattr(engine, "source", None) if getattr(engine, "mode", "") == "folder" else None
    sources = {
        "scripts_zip": scripts_zip,
        "scripts_dir": scripts_dir,
        "farm_plant_defs": "scripts/prefabs/farm_plant_defs.lua",
        "weed_defs": "scripts/prefabs/weed_defs.lua",
        "fertilizer_defs": "scripts/prefabs/fertilizer_nutrient_defs.lua",
        "veggies_defs": "scripts/prefabs/veggies.lua",
        "tuning": "scripts/tuning.lua",
    }
    meta = build_meta(
        schema=SCHEMA_VERSION,
        tool="build_farming_defs",
        sources=sources,
        extra={
            "scripts_sha256_12": scripts_sha,
            "scripts_zip": scripts_zip,
            "scripts_dir": scripts_dir,
        },
    )

    stats = {
        "plants_total": len(plants),
        "weeds_total": len(weeds),
        "fertilizers_total": len(fertilizers),
        "seed_weights_total": len(seed_weights),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "meta": meta,
        "tuning": tuning_out,
        "seed_weights": seed_weights,
        "plants": plants,
        "weeds": weeds,
        "fertilizers": fertilizers,
        "stats": stats,
    }

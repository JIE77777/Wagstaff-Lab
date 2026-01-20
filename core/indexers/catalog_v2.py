#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catalog v2 builder (core).

Generates an item-centric, taggable catalog from DST scripts and data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import re

from core.lua import LuaCallExtractor, strip_lua_comments, _skip_string_or_long_string
from core.parsers import LootParser, PrefabParser
from core.indexers.shared import _sha256_12_file
from core.craft_recipes import CraftRecipeDB
from core.tagging import TagProfile, apply_overrides, infer_tags, load_tag_overrides
from core.schemas.catalog_v2 import WagstaffCatalogV2
from core.schemas.meta import build_meta


SCHEMA_VERSION = 2
_ID_RE = re.compile(r"^[a-z0-9_]+$")

TUNING_FIELDS = (
    "hunger",
    "health",
    "sanity",
    "perishtime",
    "cooktime",
    "temperature",
    "temperatureduration",
    "fuelvalue",
    "maxsize",
)

_STAT_METHODS = {
    "weapon": {
        "SetDamage": [("weapon_damage", 0)],
        "SetRange": [("weapon_range_min", 0), ("weapon_range_max", 1)],
        "SetAttackRange": [("weapon_range", 0)],
    },
    "combat": {
        "SetDefaultDamage": [("combat_damage", 0)],
        "SetAttackPeriod": [("attack_period", 0)],
        "SetRange": [("attack_range", 0), ("attack_range_max", 1)],
        "SetAreaDamage": [("area_damage", 0)],
    },
    "finiteuses": {
        "SetMaxUses": [("uses_max", 0)],
        "SetUses": [("uses", 0)],
    },
    "armor": {
        "InitCondition": [("armor_condition", 0), ("armor_absorption", 1)],
        "SetCondition": [("armor_condition", 0)],
        "SetAbsorption": [("armor_absorption", 0)],
    },
    "edible": {
        "SetHealth": [("edible_health", 0)],
        "SetHunger": [("edible_hunger", 0)],
        "SetSanity": [("edible_sanity", 0)],
    },
    "perishable": {
        "SetPerishTime": [("perish_time", 0)],
    },
    "fueled": {
        "SetFuelLevel": [("fuel_level", 0)],
        "InitializeFuelLevel": [("fuel_level", 0)],
        "SetMaxFuel": [("fuel_max", 0)],
    },
    "equippable": {
        "SetDapperness": [("dapperness", 0)],
        "SetEquipSlot": [("equip_slot", 0)],
        "SetWalkSpeedMult": [("equip_walk_speed_mult", 0)],
        "SetRunSpeedMult": [("equip_run_speed_mult", 0)],
        "SetRestrictedTag": [("equip_restricted_tag", 0)],
        "SetPreventUnequipping": [("equip_prevent_unequip", 0)],
        "SetEquipStack": [("equip_stack", 0)],
        "SetInsulated": [("equip_insulated", 0)],
        "SetEquippedMoisture": [("equip_moisture", 0)],
        "SetMaxEquippedMoisture": [("equip_moisture_max", 0)],
    },
    "insulator": {
        "SetInsulation": [("insulation", 0)],
        "SetWinterInsulation": [("insulation_winter", 0)],
        "SetSummerInsulation": [("insulation_summer", 0)],
    },
    "waterproofer": {
        "SetEffectiveness": [("waterproof", 0)],
    },
    "light": {
        "SetRadius": [("light_radius", 0)],
        "SetIntensity": [("light_intensity", 0)],
        "SetFalloff": [("light_falloff", 0)],
    },
    "stackable": {
        "SetMaxSize": [("stack_size", 0)],
    },
    "health": {
        "SetMaxHealth": [("health_max", 0)],
    },
    "sanity": {
        "SetMax": [("sanity_max", 0)],
        "SetRate": [("sanity_rate", 0)],
    },
    "sanityaura": {
        "SetAura": [("sanity_aura", 0)],
    },
    "hunger": {
        "SetMax": [("hunger_max", 0)],
        "SetRate": [("hunger_rate", 0)],
    },
    "locomotor": {
        "SetWalkSpeed": [("walk_speed", 0)],
        "SetRunSpeed": [("run_speed", 0)],
        "SetExternalSpeedMultiplier": [("speed_multiplier", 2)],
        "SetSpeedMultiplier": [("speed_multiplier", 0)],
    },
    "rechargeable": {
        "SetRechargeTime": [("recharge_time", 0)],
        "SetChargeTime": [("recharge_time", 0)],
        "SetMaxCharge": [("recharge_max", 0)],
        "SetPercent": [("recharge_percent", 0)],
        "SetCharge": [("recharge_charge", 0)],
    },
    "heater": {
        "SetHeat": [("heat", 0)],
        "SetRadius": [("heat_radius", 0)],
        "SetThermics": [("heater_exothermic", 0), ("heater_endothermic", 1)],
        "SetShouldFalloff": [("heat_falloff", 0)],
        "SetHeatRadiusCutoff": [("heat_radius_cutoff", 0)],
        "SetEquippedHeat": [("equipped_heat", 0)],
        "SetCarriedHeat": [("carried_heat", 0)],
        "SetCarriedHeatMultiplier": [("carried_heat_multiplier", 0)],
        "SetHeatRate": [("heat_rate", 0)],
    },
    "planardamage": {
        "SetBaseDamage": [("planar_damage_base", 0)],
        "SetBonusDamage": [("planar_damage_bonus", 0)],
        "SetDamage": [("planar_damage", 0)],
    },
    "planararmor": {
        "SetAbsorption": [("planar_absorption", 0)],
        "SetBaseAbsorption": [("planar_absorption_base", 0)],
    },
    "workable": {
        "SetWorkLeft": [("work_left", 0)],
    },
}

_STAT_PROPERTIES = {
    "weapon": {"damage": "weapon_damage"},
    "combat": {"defaultdamage": "combat_damage"},
    "finiteuses": {"maxuses": "uses_max", "uses": "uses"},
    "armor": {"absorption": "armor_absorption", "condition": "armor_condition"},
    "edible": {
        "healthvalue": "edible_health",
        "hungervalue": "edible_hunger",
        "sanityvalue": "edible_sanity",
    },
    "perishable": {"perishtime": "perish_time"},
    "fueled": {"maxfuel": "fuel_max"},
    "equippable": {
        "dapperness": "dapperness",
        "equipslot": "equip_slot",
        "walkspeedmult": "equip_walk_speed_mult",
        "runspeedmult": "equip_run_speed_mult",
        "restrictedtag": "equip_restricted_tag",
        "preventunequipping": "equip_prevent_unequip",
        "equipstack": "equip_stack",
        "insulated": "equip_insulated",
        "equippedmoisture": "equip_moisture",
        "maxequippedmoisture": "equip_moisture_max",
        "is_magic_dapperness": "equip_magic_dapperness",
    },
    "insulator": {"insulation": "insulation"},
    "waterproofer": {"effectiveness": "waterproof"},
    "light": {"radius": "light_radius", "intensity": "light_intensity", "falloff": "light_falloff"},
    "stackable": {"maxsize": "stack_size"},
    "health": {"maxhealth": "health_max"},
    "sanity": {"max": "sanity_max", "rate": "sanity_rate"},
    "sanityaura": {"aura": "sanity_aura"},
    "hunger": {"max": "hunger_max", "rate": "hunger_rate"},
    "locomotor": {"walkspeed": "walk_speed", "runspeed": "run_speed"},
    "rechargeable": {
        "recharge_time": "recharge_time",
        "chargetime": "recharge_time",
        "percent": "recharge_percent",
        "charge": "recharge_charge",
        "maxcharge": "recharge_max",
        "maxrecharge": "recharge_max",
        "total": "recharge_max",
        "current": "recharge_charge",
    },
    "heater": {
        "heat": "heat",
        "radius": "heat_radius",
        "equippedheat": "equipped_heat",
        "carriedheat": "carried_heat",
        "carriedheatfn": "carried_heat",
        "carriedheatmultiplier": "carried_heat_multiplier",
        "heatrate": "heat_rate",
        "radius_cutoff": "heat_radius_cutoff",
        "exothermic": "heater_exothermic",
        "endothermic": "heater_endothermic",
    },
    "planardamage": {"basedamage": "planar_damage_base", "bonusdamage": "planar_damage_bonus", "damage": "planar_damage"},
    "planararmor": {"absorption": "planar_absorption", "baseabsorption": "planar_absorption_base"},
    "workable": {"workleft": "work_left"},
}


def _clean_id(x: Any) -> Optional[str]:
    if not isinstance(x, str):
        return None
    s = x.strip().lower()
    if not s or not _ID_RE.match(s):
        return None
    return s


def _collect_craft_sets(craft: CraftRecipeDB) -> Dict[str, Set[str]]:
    recipe_ids: Set[str] = set()
    product_ids: Set[str] = set()
    ingredient_ids: Set[str] = set()

    for name, rec in (getattr(craft, "recipes", {}) or {}).items():
        nm = _clean_id(name)
        if nm:
            recipe_ids.add(nm)
        if not isinstance(rec, dict):
            continue
        prod = _clean_id(rec.get("product"))
        if prod:
            product_ids.add(prod)
        for ing in rec.get("ingredients", []) or []:
            item = _clean_id((ing or {}).get("item"))
            if item:
                ingredient_ids.add(item)

    return {
        "recipe_ids": recipe_ids,
        "product_ids": product_ids,
        "ingredient_ids": ingredient_ids,
    }


def _collect_cooking_sets(cooking: Dict[str, Any]) -> Dict[str, Set[str]]:
    recipe_ids: Set[str] = set()
    ingredient_ids: Set[str] = set()

    for name, rec in (cooking or {}).items():
        nm = _clean_id(name)
        if nm:
            recipe_ids.add(nm)
        if not isinstance(rec, dict):
            continue
        for row in (rec.get("card_ingredients") or []):
            if not isinstance(row, (list, tuple)) or not row:
                continue
            item = _clean_id(row[0])
            if item:
                ingredient_ids.add(item)

    return {
        "recipe_ids": recipe_ids,
        "ingredient_ids": ingredient_ids,
    }


def _scan_loot_items(engine: Any) -> Set[str]:
    items: Set[str] = set()
    patterns = ("SetSharedLootTable", "AddChanceLoot", "AddRandomLoot", "AddRandomLootTable")

    for path in getattr(engine, "file_list", []) or []:
        if not str(path).endswith(".lua"):
            continue
        p = str(path)
        if "loot" not in p and "prefabs" not in p:
            continue
        content = engine.read_file(p) or ""
        if not content:
            continue
        if not any(tok in content for tok in patterns):
            continue
        try:
            rep = LootParser(content, path=p).parse()
        except Exception:
            continue
        for entry in rep.get("entries") or []:
            item = _clean_id(entry.get("item"))
            if item:
                items.add(item)

    return items


def _select_asset(prefab_assets: List[Dict[str, Any]]) -> Dict[str, str]:
    atlas = None
    image = None
    for a in prefab_assets:
        t = str(a.get("type") or "").upper()
        p = str(a.get("path") or "")
        if not p:
            continue
        if t == "ATLAS" and atlas is None:
            atlas = p
        if t == "IMAGE" and image is None:
            image = p
    out: Dict[str, str] = {}
    if atlas:
        out["atlas"] = atlas
    if image:
        out["image"] = image
    return out


def _resolve_tuning_field(
    value: Any,
    *,
    tuning: Any,
    mode: str,
    trace_sink: Optional[Dict[str, Any]] = None,
    trace_key: Optional[str] = None,
) -> Any:
    if not tuning or not isinstance(value, str) or "TUNING." not in value:
        return value
    try:
        trace = tuning.trace_expr(value)
    except Exception:
        return value

    if trace_sink is not None and trace_key:
        trace_sink[trace_key] = trace

    if mode == "full":
        return {"value": trace.get("value"), "expr": trace.get("expr"), "trace": trace}

    # value_only
    return trace.get("value") if trace.get("value") is not None else value


def _parse_number(expr: str) -> Optional[float]:
    if not expr:
        return None
    s = str(expr).strip()
    if not s:
        return None
    try:
        if re.match(r"^[+-]?\d+(\.\d+)?$", s):
            val = float(s)
            return int(val) if val.is_integer() else val
    except Exception:
        return None
    return None


def _resolve_stat_expr(
    expr: str,
    *,
    tuning: Any,
    mode: str,
    trace_sink: Optional[Dict[str, Any]] = None,
    trace_key: Optional[str] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {"expr": expr}
    if not expr:
        return out

    if tuning and isinstance(expr, str) and "TUNING." in expr:
        try:
            trace = tuning.trace_expr(expr)
        except Exception:
            trace = {"expr": expr, "value": None, "expr_resolved": expr, "refs": {}}
        if trace_sink is not None and trace_key:
            trace_sink[trace_key] = trace
        out["value"] = trace.get("value")
        out["expr_resolved"] = trace.get("expr_resolved") or expr
        if mode == "full":
            out["trace"] = trace
        if trace_key:
            out["trace_key"] = trace_key
        return out

    expr_norm = str(expr).strip()
    if expr_norm in ("true", "false"):
        out["value"] = expr_norm == "true"
        out["expr_resolved"] = expr_norm
        return out

    num = _parse_number(expr)
    if num is not None:
        out["value"] = num
    out["expr_resolved"] = expr
    return out


def _score_stat_expr(expr: str) -> int:
    if not expr:
        return 0
    if "TUNING." in expr:
        return 3
    if str(expr).strip() in ("true", "false"):
        return 2
    if _parse_number(expr) is not None:
        return 2
    return 1


def _scan_assignment_expr(text: str, start: int) -> str:
    n = len(text)
    i = start
    depth = 0
    started = False
    while i < n:
        nxt = _skip_string_or_long_string(text, i)
        if nxt is not None:
            started = True
            i = nxt
            continue
        ch = text[i]
        if not started and ch.isspace():
            i += 1
            continue
        started = True
        if ch == "\n" and depth == 0:
            break
        if ch == ";" and depth == 0:
            break
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        i += 1
    return text[start:i].strip().rstrip(",")


def _extract_component_aliases(clean: str) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for m in re.finditer(
        r"\blocal\s+([A-Za-z0-9_]+)\s*=\s*(?:inst|self)[.:]AddComponent\(\s*['\"]([A-Za-z0-9_]+)['\"]",
        clean,
    ):
        aliases[m.group(1)] = m.group(2).lower()
    for m in re.finditer(
        r"\b([A-Za-z0-9_]+)\s*=\s*(?:inst|self)[.:]AddComponent\(\s*['\"]([A-Za-z0-9_]+)['\"]",
        clean,
    ):
        if m.group(1) not in aliases:
            aliases[m.group(1)] = m.group(2).lower()
    for m in re.finditer(r"\blocal\s+([A-Za-z0-9_]+)\s*=\s*(?:inst|self)\.components\.([A-Za-z0-9_]+)", clean):
        aliases[m.group(1)] = m.group(2).lower()
    for m in re.finditer(r"\b([A-Za-z0-9_]+)\s*=\s*(?:inst|self)\.components\.([A-Za-z0-9_]+)", clean):
        if m.group(1) not in aliases:
            aliases[m.group(1)] = m.group(2).lower()
    return aliases


def _extract_component_stat_exprs(content: str) -> Dict[str, str]:
    rep = PrefabParser(content).parse()
    comp_names = {
        str((comp or {}).get("name") or "").strip().lower()
        for comp in (rep.get("components") or [])
    }
    comp_names.discard("")

    clean = strip_lua_comments(content or "")
    aliases = _extract_component_aliases(clean)
    if not comp_names:
        comp_names = {m.group(1).lower() for m in re.finditer(r"\bcomponents\.([A-Za-z0-9_]+)\b", clean)}

    out: Dict[str, str] = {}
    scores: Dict[str, int] = {}

    method_names = {m for cmap in _STAT_METHODS.values() for m in cmap.keys()}
    extractor = LuaCallExtractor(content)
    for call in extractor.iter_calls(method_names, include_member_calls=True):
        cname = None
        m = re.search(r"\bcomponents\.([A-Za-z0-9_]+)\b", call.full_name)
        if m:
            cname = m.group(1).lower()
        else:
            root = re.split(r"[.:]", call.full_name, 1)[0]
            cname = aliases.get(root)
        if not cname:
            continue
        if comp_names and cname not in comp_names:
            continue
        mapping = _STAT_METHODS.get(cname, {}).get(call.name)
        if not mapping:
            continue
        for stat_key, idx in mapping:
            if idx >= len(call.arg_list):
                continue
            expr = (call.arg_list[idx] or "").strip()
            if not expr:
                continue
            score = _score_stat_expr(expr)
            if (stat_key not in out) or (score >= scores.get(stat_key, 0)):
                out[stat_key] = expr
                scores[stat_key] = score

    for cname in sorted(comp_names):
        prop_map = _STAT_PROPERTIES.get(cname, {})
        if not prop_map:
            continue

        prop_pat = re.compile(rf"\bcomponents\.{re.escape(cname)}\.([A-Za-z0-9_]+)\s*=")
        for m in prop_pat.finditer(clean):
            prop = m.group(1).strip().lower()
            stat_key = prop_map.get(prop)
            if not stat_key:
                continue
            expr = _scan_assignment_expr(clean, m.end())
            if not expr:
                continue
            score = _score_stat_expr(expr)
            if (stat_key not in out) or (score >= scores.get(stat_key, 0)):
                out[stat_key] = expr
                scores[stat_key] = score

        for alias, comp in aliases.items():
            if comp != cname:
                continue
            alias_pat = re.compile(rf"\b{re.escape(alias)}\.([A-Za-z0-9_]+)\s*=")
            for m in alias_pat.finditer(clean):
                prop = m.group(1).strip().lower()
                stat_key = prop_map.get(prop)
                if not stat_key:
                    continue
                expr = _scan_assignment_expr(clean, m.end())
                if not expr:
                    continue
                score = _score_stat_expr(expr)
                if (stat_key not in out) or (score >= scores.get(stat_key, 0)):
                    out[stat_key] = expr
                    scores[stat_key] = score

    if "heat_radius" not in out and "heat_radius_cutoff" in out:
        out["heat_radius"] = out["heat_radius_cutoff"]
        scores["heat_radius"] = scores.get("heat_radius_cutoff", 0)

    return out


def _infer_sources(
    *,
    item_id: str,
    craft_products: Set[str],
    cooking_recipes: Set[str],
    loot_items: Set[str],
    components: Set[str],
    tags: Set[str],
) -> Set[str]:
    sources: Set[str] = set()
    if item_id in craft_products:
        sources.add("craft")
    if item_id in cooking_recipes:
        sources.add("cook")
    if item_id in loot_items:
        sources.add("loot")
    if tags & {"event", "festival"}:
        sources.add("event")
    if tags & {"plant", "tree"} or "pickable" in components:
        sources.add("natural")
    if tags & {"character", "monster", "animal", "smallcreature", "largecreature", "epic"}:
        sources.add("spawn")
    return sources


def build_catalog_v2(
    *,
    engine: Any,
    resource_index: Dict[str, Any],
    tag_overrides_path: Optional[str] = None,
    tuning_mode: str = "value_only",
    include_tuning_trace: bool = False,
) -> Tuple[WagstaffCatalogV2, Optional[Dict[str, Any]]]:

    prefabs = resource_index.get("prefabs") or {}
    prefab_items = prefabs.get("items") or {}
    icon_ids = set(resource_index.get("assets", {}).get("inventory_icons") or [])

    craft_sets = _collect_craft_sets(engine.recipes)
    cooking_sets = _collect_cooking_sets(engine.cooking_recipes or {})
    loot_items = _scan_loot_items(engine)

    cooking_ingredients_src = getattr(engine, "cooking_ingredients", {}) or {}
    cooking_ingredient_ids = {_clean_id(k) for k in cooking_ingredients_src.keys() if _clean_id(k)}

    all_ids = (
        set(prefab_items.keys())
        | icon_ids
        | craft_sets["product_ids"]
        | craft_sets["recipe_ids"]
        | craft_sets["ingredient_ids"]
        | cooking_sets["recipe_ids"]
        | cooking_sets["ingredient_ids"]
        | cooking_ingredient_ids
    )
    all_ids = {i for i in all_ids if _ID_RE.match(i)}

    overrides = load_tag_overrides(tag_overrides_path)
    prefab_stats_cache: Dict[str, Dict[str, str]] = {}

    tuning_trace: Optional[Dict[str, Any]] = {} if include_tuning_trace else None
    tuning = getattr(engine, "tuning", None)

    items_out: Dict[str, Any] = {}
    assets_out: Dict[str, Any] = {}

    for iid in sorted(all_ids):
        pf = prefab_items.get(iid) or {}
        components = set(pf.get("components") or [])
        tags = set(pf.get("tags") or [])
        prefab_files = sorted({str(x) for x in (pf.get("files") or []) if x})
        prefab_assets = [dict(a) for a in (pf.get("assets") or []) if isinstance(a, dict)]
        brains = sorted({str(x) for x in (pf.get("brains") or []) if x})
        stategraphs = sorted({str(x) for x in (pf.get("stategraphs") or []) if x})
        helpers = sorted({str(x) for x in (pf.get("helpers") or []) if x})
        sources = _infer_sources(
            item_id=iid,
            craft_products=craft_sets["product_ids"],
            cooking_recipes=cooking_sets["recipe_ids"],
            loot_items=loot_items,
            components=components,
            tags=tags,
        )
        profile = infer_tags(components=components, tags=tags, sources=sources)
        profile = apply_overrides(iid, profile, overrides)

        assets = _select_asset(pf.get("assets") or [])
        if iid in icon_ids:
            assets["icon"] = f"static/icons/{iid}.png"

        stat_exprs: Dict[str, str] = {}
        stat_scores: Dict[str, int] = {}
        for pfile in prefab_files:
            if pfile not in prefab_stats_cache:
                content = engine.read_file(pfile) or ""
                prefab_stats_cache[pfile] = _extract_component_stat_exprs(content) if content else {}
            for sk, sv in prefab_stats_cache.get(pfile, {}).items():
                score = _score_stat_expr(sv)
                if (sk not in stat_exprs) or (score >= stat_scores.get(sk, 0)):
                    stat_exprs[sk] = sv
                    stat_scores[sk] = score

        stats_out: Dict[str, Any] = {}
        for stat_key, expr in stat_exprs.items():
            trace_key = f"item:{iid}:stat:{stat_key}" if include_tuning_trace else None
            entry = _resolve_stat_expr(
                expr,
                tuning=tuning,
                mode=tuning_mode,
                trace_sink=tuning_trace,
                trace_key=trace_key,
            )
            entry["key"] = stat_key
            stats_out[stat_key] = entry

        items_out[iid] = {
            "id": iid,
            "kind": profile.kind,
            "categories": sorted(profile.categories),
            "behaviors": sorted(profile.behaviors),
            "sources": sorted(profile.sources),
            "slots": sorted(profile.slots),
            "components": sorted(components),
            "tags": sorted(tags),
            "assets": assets or {},
            "prefab_files": prefab_files,
            "prefab_assets": prefab_assets,
            "brains": brains,
            "stategraphs": stategraphs,
            "helpers": helpers,
            "stats": stats_out,
        }
        if assets:
            assets_out[iid] = dict(assets)

    # craft (enrich ingredients)
    craft_doc = engine.recipes.to_dict() if engine.recipes else {}
    craft_recipes = craft_doc.get("recipes") or {}

    for name, rec in craft_recipes.items():
        if not isinstance(rec, dict):
            continue
        for ing in rec.get("ingredients", []) or []:
            if not isinstance(ing, dict):
                continue
            expr = ing.get("amount")
            if isinstance(expr, str) and "TUNING." in expr and tuning is not None:
                key = f"craft:{name}:ingredient:{ing.get('item')}"
                val = _resolve_tuning_field(expr, tuning=tuning, mode=tuning_mode, trace_sink=tuning_trace, trace_key=key)
                ing["amount_value"] = val if isinstance(val, (int, float)) else None
                if tuning_mode == "full" and isinstance(val, dict):
                    ing["amount_trace"] = val.get("trace")
            elif ing.get("amount_num") is not None:
                ing["amount_value"] = ing.get("amount_num")

    # cooking (enrich tuning fields)
    cooking_doc: Dict[str, Any] = {}
    for name, rec in (engine.cooking_recipes or {}).items():
        if not isinstance(rec, dict):
            continue
        out = dict(rec)
        for field in TUNING_FIELDS:
            if field in out:
                key = f"cooking:{name}:{field}"
                out[field] = _resolve_tuning_field(
                    out[field], tuning=tuning, mode=tuning_mode, trace_sink=tuning_trace, trace_key=key
                )
        cooking_doc[name] = out

    cooking_ingredients_doc: Dict[str, Any] = {}
    for iid, raw in (cooking_ingredients_src or {}).items():
        if not isinstance(raw, dict):
            continue
        out = dict(raw)
        out.setdefault("id", str(iid))
        cooking_ingredients_doc[str(iid)] = out

    scripts_zip = getattr(getattr(engine, "source", None), "filename", None)
    scripts_sha = _sha256_12_file(Path(scripts_zip)) if scripts_zip else None

    scripts_dir = getattr(engine, "source", None) if getattr(engine, "mode", "") == "folder" else None
    sources = {
        "resource_index": "wagstaff_resource_index_v1.json",
        "scripts_zip": scripts_zip,
        "scripts_dir": scripts_dir,
    }
    meta = build_meta(
        schema=SCHEMA_VERSION,
        tool="build_catalog_v2",
        sources=sources,
        extra={
            "tuning_mode": tuning_mode,
            "scripts_sha256_12": scripts_sha,
            "scripts_zip": scripts_zip,
            "scripts_dir": scripts_dir,
        },
    )

    stats = {
        "items_total": len(items_out),
        "assets_total": len(assets_out),
        "craft_recipes": len(craft_recipes),
        "cooking_recipes": len(cooking_doc),
        "cooking_ingredients": len(cooking_ingredients_doc),
        "loot_items": len(loot_items),
    }

    catalog = WagstaffCatalogV2(
        schema_version=SCHEMA_VERSION,
        meta=meta,
        items=items_out,
        assets=assets_out,
        craft=craft_doc,
        cooking=cooking_doc,
        cooking_ingredients=cooking_ingredients_doc,
        stats=stats,
    )

    return catalog, tuning_trace

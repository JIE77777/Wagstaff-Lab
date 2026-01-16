#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catalog v2 builder (core).

Generates an item-centric, taggable catalog from DST scripts and data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import re

from analyzer import LootParser, PrefabParser, _split_top_level
from catalog import _sha256_12_file
from craft_recipes import CraftRecipeDB
from tagging import TagProfile, apply_overrides, infer_tags, load_tag_overrides


SCHEMA_VERSION = 2
_ID_RE = re.compile(r"^[a-z0-9_]+$")

TUNING_FIELDS = ("hunger", "health", "sanity", "perishtime", "cooktime")

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
    },
    "heater": {
        "SetHeat": [("heat", 0)],
        "SetRadius": [("heat_radius", 0)],
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
    "equippable": {"dapperness": "dapperness"},
    "insulator": {"insulation": "insulation"},
    "waterproofer": {"effectiveness": "waterproof"},
    "light": {"radius": "light_radius", "intensity": "light_intensity", "falloff": "light_falloff"},
    "stackable": {"maxsize": "stack_size"},
    "health": {"maxhealth": "health_max"},
    "sanity": {"max": "sanity_max", "rate": "sanity_rate"},
    "sanityaura": {"aura": "sanity_aura"},
    "hunger": {"max": "hunger_max", "rate": "hunger_rate"},
    "locomotor": {"walkspeed": "walk_speed", "runspeed": "run_speed"},
    "rechargeable": {"recharge_time": "recharge_time"},
    "heater": {"heat": "heat", "radius": "heat_radius"},
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

    num = _parse_number(expr)
    if num is not None:
        out["value"] = num
    out["expr_resolved"] = expr
    return out


def _extract_component_stat_exprs(content: str) -> Dict[str, str]:
    rep = PrefabParser(content).parse()
    out: Dict[str, str] = {}

    for comp in (rep.get("components") or []):
        cname = str((comp or {}).get("name") or "").strip().lower()
        if not cname:
            continue

        methods = comp.get("methods") or []
        for m in methods:
            s = str(m or "").strip()
            if not s:
                continue
            m2 = re.match(r"^([A-Za-z0-9_]+)\((.*)\)$", s)
            if not m2:
                continue
            m_name = m2.group(1)
            arg_str = m2.group(2)
            arg_list = [a.strip() for a in _split_top_level(arg_str, ",") if a.strip()]
            mapping = _STAT_METHODS.get(cname, {}).get(m_name)
            if not mapping:
                continue
            for stat_key, idx in mapping:
                if stat_key in out:
                    continue
                if idx < len(arg_list):
                    out[stat_key] = arg_list[idx]

        props = comp.get("properties") or []
        for p in props:
            s = str(p or "").strip()
            if not s or "=" not in s:
                continue
            left, right = s.split("=", 1)
            prop = left.strip().lower()
            expr = right.strip()
            stat_key = _STAT_PROPERTIES.get(cname, {}).get(prop)
            if not stat_key or stat_key in out:
                continue
            out[stat_key] = expr

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


@dataclass
class WagstaffCatalogV2:
    schema_version: int
    meta: Dict[str, Any]
    items: Dict[str, Any]
    assets: Dict[str, Any]
    craft: Dict[str, Any]
    cooking: Dict[str, Any]
    stats: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": int(self.schema_version),
            "meta": self.meta,
            "items": self.items,
            "assets": self.assets,
            "craft": self.craft,
            "cooking": self.cooking,
            "stats": self.stats,
        }

    @classmethod
    def build(
        cls,
        *,
        engine: Any,
        resource_index: Dict[str, Any],
        tag_overrides_path: Optional[str] = None,
        tuning_mode: str = "value_only",
        include_tuning_trace: bool = False,
    ) -> Tuple["WagstaffCatalogV2", Optional[Dict[str, Any]]]:

        prefabs = resource_index.get("prefabs") or {}
        prefab_items = prefabs.get("items") or {}
        icon_ids = set(resource_index.get("assets", {}).get("inventory_icons") or [])

        craft_sets = _collect_craft_sets(engine.recipes)
        cooking_sets = _collect_cooking_sets(engine.cooking_recipes or {})
        loot_items = _scan_loot_items(engine)

        all_ids = set(prefab_items.keys()) | icon_ids | craft_sets["product_ids"] | craft_sets["recipe_ids"] | craft_sets["ingredient_ids"] | cooking_sets["recipe_ids"] | cooking_sets["ingredient_ids"]
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
            for pfile in prefab_files:
                if pfile not in prefab_stats_cache:
                    content = engine.read_file(pfile) or ""
                    prefab_stats_cache[pfile] = _extract_component_stat_exprs(content) if content else {}
                for sk, sv in prefab_stats_cache.get(pfile, {}).items():
                    if sk not in stat_exprs:
                        stat_exprs[sk] = sv

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

        scripts_zip = getattr(getattr(engine, "source", None), "filename", None)
        scripts_sha = _sha256_12_file(Path(scripts_zip)) if scripts_zip else None

        meta = {
            "schema": SCHEMA_VERSION,
            "tuning_mode": tuning_mode,
            "resource_index": "wagstaff_resource_index_v1.json",
            "scripts_zip": scripts_zip,
            "scripts_sha256_12": scripts_sha,
            "scripts_dir": getattr(engine, "source", None) if getattr(engine, "mode", "") == "folder" else None,
        }

        stats = {
            "items_total": len(items_out),
            "assets_total": len(assets_out),
            "craft_recipes": len(craft_recipes),
            "cooking_recipes": len(cooking_doc),
            "loot_items": len(loot_items),
        }

        catalog = cls(
            schema_version=SCHEMA_VERSION,
            meta=meta,
            items=items_out,
            assets=assets_out,
            craft=craft_doc,
            cooking=cooking_doc,
            stats=stats,
        )

        return catalog, tuning_trace

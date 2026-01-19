#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build SQLite catalog from wagstaff_catalog_v2.json."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.indexers.catalog_index import build_catalog_index, load_icon_index  # noqa: E402
from devtools.build_cache import file_sig, load_cache, save_cache  # noqa: E402


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _as_list(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(x) for x in value if x]
    return []


def _iter_map_rows(obj: Any) -> Iterable[Tuple[str, str]]:
    if not isinstance(obj, dict):
        return []
    return [(str(k), _json_dumps(v)) for k, v in obj.items()]


def _iter_item_rows(items_obj: Any) -> Iterable[Tuple[str, str, str, str, str, str, str, str, str]]:
    if not isinstance(items_obj, dict):
        return []
    out = []
    for iid, raw in items_obj.items():
        if not iid:
            continue
        item = dict(raw) if isinstance(raw, dict) else {"id": iid}
        out.append(
            (
                str(item.get("id") or iid),
                str(item.get("kind") or ""),
                _json_dumps(_as_list(item.get("categories"))),
                _json_dumps(_as_list(item.get("behaviors"))),
                _json_dumps(_as_list(item.get("sources"))),
                _json_dumps(_as_list(item.get("tags"))),
                _json_dumps(_as_list(item.get("components"))),
                _json_dumps(_as_list(item.get("slots"))),
                _json_dumps(item),
            )
        )
    return out


def _iter_asset_rows(assets_obj: Any) -> Iterable[Tuple[str, str, str, str, str]]:
    if not isinstance(assets_obj, dict):
        return []
    out = []
    for iid, raw in assets_obj.items():
        if not iid or not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "")
        icon = str(raw.get("icon") or "")
        image = str(raw.get("image") or "")
        out.append((str(iid), name, icon, image, _json_dumps(raw)))
    return out


def _iter_item_list_rows(items_obj: Any) -> Iterable[Tuple[str, str]]:
    if not isinstance(items_obj, dict):
        return []
    for iid, raw in items_obj.items():
        if not iid:
            continue
        row = dict(raw) if isinstance(raw, dict) else {"id": iid}
        yield (str(iid), _json_dumps(row))


def _iter_item_stat_rows(items_obj: Any) -> Iterable[Tuple[str, str, str, str, str, str, str]]:
    if not isinstance(items_obj, dict):
        return []
    out = []
    for iid, raw in items_obj.items():
        if not iid or not isinstance(raw, dict):
            continue
        stats = raw.get("stats") or {}
        if not isinstance(stats, dict):
            continue
        for key, entry in stats.items():
            if not key:
                continue
            if not isinstance(entry, dict):
                entry = {"value": entry}
            expr = str(entry.get("expr") or "")
            expr_resolved = str(entry.get("expr_resolved") or "")
            trace_key = str(entry.get("trace_key") or "")
            value_json = _json_dumps(entry.get("value"))
            out.append((str(iid), str(key), expr, expr_resolved, trace_key, value_json, _json_dumps(entry)))
    return out


def _iter_join_rows(items_obj: Any, field: str) -> Iterable[Tuple[str, str]]:
    if not isinstance(items_obj, dict):
        return []
    out = []
    for iid, raw in items_obj.items():
        if not iid or not isinstance(raw, dict):
            continue
        for v in _as_list(raw.get(field)):
            if not v:
                continue
            out.append((str(iid), str(v)))
    return out


def _iter_craft_recipe_rows(craft_obj: Dict[str, Any]) -> Iterable[Tuple[str, str, str, str, str, str, str, str]]:
    recipes = craft_obj.get("recipes") if isinstance(craft_obj, dict) else None
    if not isinstance(recipes, dict):
        return []
    out = []
    for name, raw in recipes.items():
        if not isinstance(raw, dict):
            continue
        btags = _as_list(raw.get("builder_tags"))
        filters = _as_list(raw.get("filters"))
        out.append(
            (
                str(raw.get("name") or name),
                str(raw.get("product") or ""),
                str(raw.get("tab") or ""),
                str(raw.get("tech") or ""),
                str(raw.get("builder_skill") or ""),
                str(raw.get("station_tag") or ""),
                _json_dumps(filters),
                _json_dumps(btags),
            )
        )
    return out


def _iter_craft_ingredient_rows(craft_obj: Dict[str, Any]) -> Iterable[Tuple[str, str, Optional[float], Optional[float], str]]:
    recipes = craft_obj.get("recipes") if isinstance(craft_obj, dict) else None
    if not isinstance(recipes, dict):
        return []
    out = []
    for name, raw in recipes.items():
        if not isinstance(raw, dict):
            continue
        ings = raw.get("ingredients") or []
        if not isinstance(ings, list):
            continue
        rec_name = str(raw.get("name") or name)
        for ing in ings:
            if not isinstance(ing, dict):
                continue
            item = str(ing.get("item") or "").strip()
            if not item:
                continue
            amount_num = ing.get("amount_num")
            amount_value = ing.get("amount_value")
            out.append((rec_name, item, amount_num, amount_value, _json_dumps(ing)))
    return out


def _iter_cooking_rows(cooking_obj: Any) -> Iterable[Tuple[str, float, float, str, str, str, str, str, str, str, str]]:
    if not isinstance(cooking_obj, dict):
        return []
    out = []
    for name, raw in cooking_obj.items():
        if not isinstance(raw, dict):
            continue
        try:
            priority = float(raw.get("priority", 0))
        except Exception:
            priority = 0.0
        try:
            weight = float(raw.get("weight", 1))
        except Exception:
            weight = 1.0
        foodtype = str(raw.get("foodtype") or "")
        tags = _json_dumps(_as_list(raw.get("tags")))
        card_ings = _json_dumps(raw.get("card_ingredients") or [])
        out.append(
            (
                str(name),
                priority,
                weight,
                foodtype,
                _json_dumps(raw.get("hunger")),
                _json_dumps(raw.get("health")),
                _json_dumps(raw.get("sanity")),
                _json_dumps(raw.get("perishtime")),
                _json_dumps(raw.get("cooktime")),
                tags,
                card_ings,
                _json_dumps(raw),
            )
        )
    return out


def _iter_cooking_ingredient_rows(cooking_obj: Any) -> Iterable[Tuple[str, str, str]]:
    if not isinstance(cooking_obj, dict):
        return []
    out = []
    for item_id, raw in cooking_obj.items():
        if not isinstance(raw, dict):
            continue
        tags = _json_dumps(raw.get("tags") or {})
        out.append((str(item_id), tags, _json_dumps(raw)))
    return out


def _iter_catalog_index_rows(items: List[Dict[str, Any]]) -> Iterable[Tuple[str, str, str, str, int, int, str, str, str, str, str, str, str]]:
    out = []
    for row in items:
        iid = str(row.get("id") or "").strip()
        if not iid:
            continue
        out.append(
            (
                iid,
                str(row.get("name") or ""),
                str(row.get("icon") or ""),
                str(row.get("image") or ""),
                1 if row.get("has_icon") else 0,
                1 if row.get("icon_only") else 0,
                str(row.get("kind") or ""),
                _json_dumps(_as_list(row.get("categories"))),
                _json_dumps(_as_list(row.get("behaviors"))),
                _json_dumps(_as_list(row.get("sources"))),
                _json_dumps(_as_list(row.get("tags"))),
                _json_dumps(_as_list(row.get("components"))),
                _json_dumps(_as_list(row.get("slots"))),
            )
        )
    return out


def _build_sqlite(catalog_path: Path, out_path: Path, icon_index_path: Optional[Path]) -> None:
    doc = _load_json(catalog_path)
    schema_version = doc.get("schema_version") or (doc.get("meta") or {}).get("schema") or 0
    meta = doc.get("meta") or {}
    stats = doc.get("stats") or {}

    icon_index = load_icon_index(icon_index_path) if icon_index_path else {}
    index_doc = build_catalog_index(doc, icon_index=icon_index)

    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(tmp_path))
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            DROP TABLE IF EXISTS meta;
            DROP TABLE IF EXISTS items;
            DROP TABLE IF EXISTS item_stats;
            DROP TABLE IF EXISTS item_categories;
            DROP TABLE IF EXISTS item_behaviors;
            DROP TABLE IF EXISTS item_sources;
            DROP TABLE IF EXISTS item_tags;
            DROP TABLE IF EXISTS item_components;
            DROP TABLE IF EXISTS item_slots;
            DROP TABLE IF EXISTS assets;
            DROP TABLE IF EXISTS craft;
            DROP TABLE IF EXISTS craft_recipes;
            DROP TABLE IF EXISTS craft_ingredients;
            DROP TABLE IF EXISTS cooking;
            DROP TABLE IF EXISTS cooking_recipes;
            DROP TABLE IF EXISTS cooking_ingredients;
            DROP TABLE IF EXISTS catalog_index;

            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

            CREATE TABLE items (
                id TEXT PRIMARY KEY,
                kind TEXT,
                categories TEXT,
                behaviors TEXT,
                sources TEXT,
                tags TEXT,
                components TEXT,
                slots TEXT,
                data TEXT NOT NULL
            );

            CREATE TABLE item_stats (
                item_id TEXT NOT NULL,
                stat_key TEXT NOT NULL,
                expr TEXT,
                expr_resolved TEXT,
                trace_key TEXT,
                value_json TEXT,
                data TEXT
            );

            CREATE TABLE item_categories (item_id TEXT NOT NULL, category TEXT NOT NULL);
            CREATE TABLE item_behaviors (item_id TEXT NOT NULL, behavior TEXT NOT NULL);
            CREATE TABLE item_sources (item_id TEXT NOT NULL, source TEXT NOT NULL);
            CREATE TABLE item_tags (item_id TEXT NOT NULL, tag TEXT NOT NULL);
            CREATE TABLE item_components (item_id TEXT NOT NULL, component TEXT NOT NULL);
            CREATE TABLE item_slots (item_id TEXT NOT NULL, slot TEXT NOT NULL);

            CREATE TABLE assets (
                id TEXT PRIMARY KEY,
                name TEXT,
                icon TEXT,
                image TEXT,
                data TEXT NOT NULL
            );

            CREATE TABLE craft (key TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE craft_recipes (
                name TEXT PRIMARY KEY,
                product TEXT,
                tab TEXT,
                tech TEXT,
                builder_skill TEXT,
                station_tag TEXT,
                filters TEXT,
                builder_tags TEXT
            );
            CREATE TABLE craft_ingredients (
                recipe_name TEXT NOT NULL,
                item_id TEXT NOT NULL,
                amount_num REAL,
                amount_value REAL,
                data TEXT
            );

            CREATE TABLE cooking (name TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE cooking_recipes (
                name TEXT PRIMARY KEY,
                priority REAL,
                weight REAL,
                foodtype TEXT,
                hunger_json TEXT,
                health_json TEXT,
                sanity_json TEXT,
                perishtime_json TEXT,
                cooktime_json TEXT,
                tags TEXT,
                card_ingredients TEXT,
                data TEXT
            );
            CREATE TABLE cooking_ingredients (
                item_id TEXT PRIMARY KEY,
                tags TEXT,
                data TEXT NOT NULL
            );

            CREATE TABLE catalog_index (
                id TEXT PRIMARY KEY,
                name TEXT,
                icon TEXT,
                image TEXT,
                has_icon INTEGER,
                icon_only INTEGER,
                kind TEXT,
                categories TEXT,
                behaviors TEXT,
                sources TEXT,
                tags TEXT,
                components TEXT,
                slots TEXT
            );

            CREATE INDEX idx_items_kind ON items(kind);
            CREATE INDEX idx_item_stats_key ON item_stats(stat_key);
            CREATE INDEX idx_item_stats_item ON item_stats(item_id);

            CREATE INDEX idx_item_cat ON item_categories(category);
            CREATE INDEX idx_item_beh ON item_behaviors(behavior);
            CREATE INDEX idx_item_src ON item_sources(source);
            CREATE INDEX idx_item_tag ON item_tags(tag);
            CREATE INDEX idx_item_comp ON item_components(component);
            CREATE INDEX idx_item_slot ON item_slots(slot);

            CREATE INDEX idx_craft_product ON craft_recipes(product);
            CREATE INDEX idx_craft_tab ON craft_recipes(tab);
            CREATE INDEX idx_craft_ing_item ON craft_ingredients(item_id);
            CREATE INDEX idx_craft_ing_recipe ON craft_ingredients(recipe_name);

            CREATE INDEX idx_cooking_foodtype ON cooking_recipes(foodtype);

            CREATE INDEX idx_catalog_kind ON catalog_index(kind);
            CREATE INDEX idx_catalog_name ON catalog_index(name);
            """
        )
        cur.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [
                ("schema_version", _json_dumps(schema_version)),
                ("meta", _json_dumps(meta)),
                ("stats", _json_dumps(stats)),
                ("catalog_index_meta", _json_dumps(index_doc.get("meta") or {})),
                ("catalog_index_counts", _json_dumps(index_doc.get("counts") or {})),
            ],
        )

        items_obj = doc.get("items") or {}
        assets_obj = doc.get("assets") or {}
        craft_obj = doc.get("craft") or {}
        cooking_obj = doc.get("cooking") or {}
        cooking_ingredients_obj = doc.get("cooking_ingredients") or {}

        cur.executemany(
            "INSERT INTO items (id, kind, categories, behaviors, sources, tags, components, slots, data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            _iter_item_rows(items_obj),
        )
        cur.executemany(
            "INSERT INTO assets (id, name, icon, image, data) VALUES (?, ?, ?, ?, ?)",
            _iter_asset_rows(assets_obj),
        )
        cur.executemany(
            "INSERT INTO item_stats (item_id, stat_key, expr, expr_resolved, trace_key, value_json, data) VALUES (?, ?, ?, ?, ?, ?, ?)",
            _iter_item_stat_rows(items_obj),
        )
        cur.executemany("INSERT INTO item_categories (item_id, category) VALUES (?, ?)", _iter_join_rows(items_obj, "categories"))
        cur.executemany("INSERT INTO item_behaviors (item_id, behavior) VALUES (?, ?)", _iter_join_rows(items_obj, "behaviors"))
        cur.executemany("INSERT INTO item_sources (item_id, source) VALUES (?, ?)", _iter_join_rows(items_obj, "sources"))
        cur.executemany("INSERT INTO item_tags (item_id, tag) VALUES (?, ?)", _iter_join_rows(items_obj, "tags"))
        cur.executemany("INSERT INTO item_components (item_id, component) VALUES (?, ?)", _iter_join_rows(items_obj, "components"))
        cur.executemany("INSERT INTO item_slots (item_id, slot) VALUES (?, ?)", _iter_join_rows(items_obj, "slots"))

        cur.executemany("INSERT INTO craft (key, data) VALUES (?, ?)", _iter_map_rows(craft_obj))
        cur.executemany(
            "INSERT INTO craft_recipes (name, product, tab, tech, builder_skill, station_tag, filters, builder_tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            _iter_craft_recipe_rows(craft_obj),
        )
        cur.executemany(
            "INSERT INTO craft_ingredients (recipe_name, item_id, amount_num, amount_value, data) VALUES (?, ?, ?, ?, ?)",
            _iter_craft_ingredient_rows(craft_obj),
        )

        cur.executemany("INSERT INTO cooking (name, data) VALUES (?, ?)", _iter_item_list_rows(cooking_obj))
        cur.executemany(
            "INSERT INTO cooking_recipes (name, priority, weight, foodtype, hunger_json, health_json, sanity_json, perishtime_json, cooktime_json, tags, card_ingredients, data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            _iter_cooking_rows(cooking_obj),
        )
        cur.executemany(
            "INSERT INTO cooking_ingredients (item_id, tags, data) VALUES (?, ?, ?)",
            _iter_cooking_ingredient_rows(cooking_ingredients_obj),
        )

        cur.executemany(
            "INSERT INTO catalog_index (id, name, icon, image, has_icon, icon_only, kind, categories, behaviors, sources, tags, components, slots) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            _iter_catalog_index_rows(index_doc.get("items") or []),
        )

        conn.commit()
    finally:
        conn.close()

    tmp_path.replace(out_path)


def main() -> int:
    p = argparse.ArgumentParser(description="Build SQLite catalog from wagstaff_catalog_v2.json")
    p.add_argument("--catalog", default="data/index/wagstaff_catalog_v2.json", help="Catalog JSON path")
    p.add_argument("--icon-index", default="data/index/wagstaff_icon_index_v1.json", help="Icon index JSON path")
    p.add_argument("--out", default="data/index/wagstaff_catalog_v2.sqlite", help="Output SQLite path")
    p.add_argument("--force", action="store_true", help="Force rebuild even if cache matches")
    args = p.parse_args()

    catalog_path = (PROJECT_ROOT / args.catalog).resolve()
    if not catalog_path.exists():
        raise SystemExit(f"Catalog not found: {catalog_path}")

    icon_index_path = (PROJECT_ROOT / args.icon_index).resolve() if args.icon_index else None
    if icon_index_path and not icon_index_path.exists():
        icon_index_path = None

    out_path = (PROJECT_ROOT / args.out).resolve()

    inputs_sig = {
        "catalog": file_sig(catalog_path),
        "icon_index": file_sig(icon_index_path) if icon_index_path else {"path": "", "exists": False},
    }
    outputs_sig = {"out": file_sig(out_path)}
    cache = load_cache()
    cache_key = "catalog_sqlite"
    if not args.force:
        entry = cache.get(cache_key) or {}
        if entry.get("signature") == inputs_sig and entry.get("outputs") == outputs_sig:
            print("✅ Catalog SQLite up-to-date; skip rebuild")
            return 0

    _build_sqlite(catalog_path, out_path, icon_index_path)
    outputs_sig = {"out": file_sig(out_path)}
    cache[cache_key] = {"signature": inputs_sig, "outputs": outputs_sig}
    save_cache(cache)
    print(f"OK: Catalog SQLite written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _dedup_preserve_order(items: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in items:
        if not x:
            continue
        if x in seen:
            continue
        out.append(x)
        seen.add(x)
    return out


_SQLITE_SUFFIXES = (".sqlite", ".sqlite3", ".db")


def _is_sqlite_path(path: Path) -> bool:
    return path.suffix.lower() in _SQLITE_SUFFIXES


def _find_sqlite_peer(path: Path) -> Optional[Path]:
    if path.suffix.lower() != ".json":
        return None
    for ext in _SQLITE_SUFFIXES:
        candidate = path.with_suffix(ext)
        if candidate.exists():
            return candidate
    return None


@dataclass
class CraftRecipe:
    name: str
    product: Optional[str]
    tab: str
    tech: str
    filters: List[str]
    builder_tags: List[str]
    builder_skill: Optional[str]
    station_tag: Optional[str]
    ingredients: List[Dict[str, Any]]
    ingredients_unresolved: List[str]
    raw: Dict[str, Any]


@dataclass
class CookingRecipe:
    """Cookpot cooking recipe (preparedfoods).

    Notes
    - Currently backed by catalog['cooking'] entries.
    - `card_ingredients` may be missing for many recipes (legacy limitation).
    """

    name: str
    priority: float
    weight: float
    foodtype: Optional[str]
    hunger: Any
    health: Any
    sanity: Any
    perishtime: Any
    cooktime: Any
    tags: List[str]
    card_ingredients: List[Tuple[str, float]]
    raw: Dict[str, Any]


class CatalogError(RuntimeError):
    pass


COOKING_TAG_KEYS = {
    "meat",
    "monster",
    "fish",
    "egg",
    "dairy",
    "sweetener",
    "fruit",
    "veggie",
    "vegetable",
    "inedible",
    "fungus",
    "mushroom",
    "frozen",
    "seed",
    "fat",
    "magic",
}

COOKING_TAG_HINTS = {
    "meat": ["meat", "leafymeat"],
    "monster": ["monstermeat", "durian"],
    "fish": ["fish", "eel", "salmon", "tuna", "perch", "trout", "barnacle"],
    "egg": ["bird_egg", "tallbirdegg", "egg"],
    "dairy": ["goatmilk", "milk", "butter", "cheese"],
    "sweetener": ["honey", "sugar", "nectar", "syrup", "maplesyrup"],
    "fruit": ["berries", "berry", "banana", "pomegranate", "watermelon", "dragonfruit", "durian", "fig", "cave_banana"],
    "veggie": ["carrot", "corn", "pumpkin", "eggplant", "pepper", "potato", "tomato", "onion", "garlic", "asparagus", "cactus", "kelp"],
    "fungus": ["mushroom", "cap"],
    "inedible": ["twigs", "ice"],
    "frozen": ["ice"],
    "seed": ["seed"],
    "fat": ["butter", "goatmilk", "milk", "cheese"],
    "magic": ["mandrake", "nightmarefuel", "glommerfuel"],
}

COOKING_SMALL_MEAT = ["morsel", "smallmeat", "drumstick", "froglegs", "batwing"]


def normalize_cooking_tags(raw: Any) -> Dict[str, float]:
    out: Dict[str, float] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            key = str(k or "").strip().lower()
            if not key:
                continue
            if key not in COOKING_TAG_KEYS:
                continue
            try:
                out[key] = float(v)
            except Exception:
                continue
        return out
    if isinstance(raw, (list, tuple, set)):
        for k in raw:
            key = str(k or "").strip().lower()
            if not key or key not in COOKING_TAG_KEYS:
                continue
            out[key] = 1.0
    return out


def guess_cooking_tags(item_id: str, item: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    iid = str(item_id or "").strip().lower()
    if not iid:
        return {}
    tags = normalize_cooking_tags((item or {}).get("tags") if item else None)

    if "eggplant" in iid:
        tags.setdefault("veggie", 1.0)
    for key in COOKING_SMALL_MEAT:
        if key in iid:
            tags["meat"] = min(tags.get("meat", 1.0), 0.5)
            break

    for tag, hints in COOKING_TAG_HINTS.items():
        if tag == "egg" and "eggplant" in iid:
            continue
        if any(h in iid for h in hints):
            tags.setdefault(tag, 1.0)

    return tags


class CatalogStore:
    """Load + index wagstaff catalog for fast queries (thread-safe).

    Data source:
      - data/index/wagstaff_catalog_v2.json
      - data/index/wagstaff_catalog_v2.sqlite

    This layer is intentionally independent from wiki/cli layers. It should be safe
    to reuse from:
      - CLI (wiki)
      - Web (webcraft)
      - future GUI (desktop)
    """

    def __init__(self, catalog_path: Path):
        resolved = self._resolve_catalog_path(Path(catalog_path))
        self._path = resolved
        self._use_sqlite = _is_sqlite_path(self._path)
        self._lock = threading.RLock()
        self._mtime: float = -1.0
        self._icon_index_mtime: float = -1.0
        self._icon_index: Dict[str, str] = {}
        self._icon_index_path: Path = self._path.parent / "wagstaff_icon_index_v1.json"
        self._catalog_index_path: Path = self._path.parent / "wagstaff_catalog_index_v1.json"
        self._catalog_index_mtime: float = -1.0
        self._catalog_index_items: List[Dict[str, Any]] = []
        self._catalog_index_total: int = 0

        self._doc: Dict[str, Any] = {}
        self._meta: Dict[str, Any] = {}

        # presentation mapping (id -> {name, atlas, image, ...})
        self._assets: Dict[str, Any] = {}
        self._items: Dict[str, Dict[str, Any]] = {}
        self._item_ids: List[str] = []
        self._by_kind: Dict[str, List[str]] = {}
        self._by_category: Dict[str, List[str]] = {}
        self._by_behavior: Dict[str, List[str]] = {}
        self._by_source: Dict[str, List[str]] = {}
        self._by_component: Dict[str, List[str]] = {}
        self._by_tag_item: Dict[str, List[str]] = {}
        self._by_slot: Dict[str, List[str]] = {}

        # craft
        self._recipes: Dict[str, CraftRecipe] = {}
        self._aliases: Dict[str, str] = {}
        self._filter_defs: List[Dict[str, Any]] = []
        self._filter_order: List[str] = []

        # indexes (craft)
        self._by_filter: Dict[str, List[str]] = {}
        self._by_tab: Dict[str, List[str]] = {}
        self._by_tag: Dict[str, List[str]] = {}
        self._by_ingredient: Dict[str, List[str]] = {}
        self._by_product: Dict[str, List[str]] = {}

        # cooking
        self._cooking: Dict[str, CookingRecipe] = {}
        self._cook_by_tag: Dict[str, List[str]] = {}
        self._cook_by_foodtype: Dict[str, List[str]] = {}
        self._cook_by_ingredient: Dict[str, List[str]] = {}
        self._cooking_ingredients: Dict[str, Dict[str, Any]] = {}

        self.load(force=True)

    @staticmethod
    def _resolve_catalog_path(catalog_path: Path) -> Path:
        if _is_sqlite_path(catalog_path):
            return catalog_path
        peer = _find_sqlite_peer(catalog_path)
        return peer if peer else catalog_path

    @property
    def path(self) -> Path:
        return self._path

    def meta(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._meta)

    def schema_version(self) -> int:
        with self._lock:
            return int(self._doc.get("schema_version") or (self._meta or {}).get("schema") or 0)

    def mtime(self) -> float:
        with self._lock:
            return float(self._mtime or 0)

    def item_ids(self, include_icon_only: bool = False) -> List[str]:
        """Return known item ids (optionally including icon-only ids)."""
        with self._lock:
            ids = list(self._item_ids)
            if include_icon_only:
                self._ensure_icon_index()
                ids = _dedup_preserve_order(ids + list((self._icon_index or {}).keys()))
            return ids

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        if not item_id:
            return None
        with self._lock:
            v = (self._items or {}).get(str(item_id))
            return dict(v) if isinstance(v, dict) else None

    # ----------------- presentation assets -----------------

    def assets(self, include_icon_only: bool = False) -> Dict[str, Any]:
        """Return presentation assets mapping (shallow copy).

        If include_icon_only=True, merge in icon-index-only entries (name=id) so the
        catalog page can list/search more ids even when catalog assets are sparse.
        """
        with self._lock:
            base = dict(self._assets or {})
            if include_icon_only:
                self._ensure_icon_index()
                for k, png in (self._icon_index or {}).items():
                    if k in base:
                        if png and isinstance(base.get(k), dict):
                            base[k].setdefault("icon", png)
                            base[k].setdefault("image", png)
                        continue
                    base[k] = {"name": k, "icon": png, "image": png, "icon_only": True}
            return base

    def get_asset(self, item_id: str) -> Optional[Dict[str, Any]]:
        if not item_id:
            return None
        with self._lock:
            v = (self._assets or {}).get(str(item_id))
            if not v:
                v = (self._items or {}).get(str(item_id), {}).get("assets")
            return dict(v) if isinstance(v, dict) else None

    # ----------------- load / reload -----------------

    def load(self, force: bool = False) -> bool:
        """Load catalog if changed.

        Returns True if reload occurred.
        """
        with self._lock:
            try:
                mtime = self._path.stat().st_mtime
            except FileNotFoundError as e:
                raise CatalogError(f"Catalog file not found: {self._path}") from e

            if (not force) and self._doc and self._mtime == mtime:
                return False

            doc = self._load_doc()
            self._validate(doc)

            self._doc = doc
            self._meta = doc.get("meta") or {}
            self._mtime = mtime

            self._build_indexes(doc)
            self._load_icon_index_if_stale(force=force)
            self._load_catalog_index_if_stale(force=force)
            return True

    def _load_doc(self) -> Dict[str, Any]:
        if self._use_sqlite:
            return self._load_doc_from_sqlite(self._path)
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _load_doc_from_sqlite(self, path: Path) -> Dict[str, Any]:
        try:
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
        except Exception as exc:
            raise CatalogError(f"Failed to open SQLite catalog: {path}") from exc
        try:
            cur = conn.cursor()
            meta_rows = {row["key"]: row["value"] for row in cur.execute("SELECT key, value FROM meta")}
            items_rows = cur.execute("SELECT id, data FROM items").fetchall()
            assets_rows = cur.execute("SELECT id, data FROM assets").fetchall()
            craft_rows = cur.execute("SELECT key, data FROM craft").fetchall()
            cooking_rows = cur.execute("SELECT name, data FROM cooking").fetchall()
            tables = {row["name"] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "cooking_ingredients" in tables:
                cooking_ingredient_rows = cur.execute("SELECT item_id, data FROM cooking_ingredients").fetchall()
            else:
                cooking_ingredient_rows = []
        except Exception as exc:
            raise CatalogError(f"SQLite catalog missing tables: {path}") from exc
        finally:
            conn.close()

        def _load_json(value: Any) -> Any:
            if value is None:
                return None
            try:
                return json.loads(value)
            except Exception:
                return value

        meta_obj = _load_json(meta_rows.get("meta")) or {}
        stats_obj = _load_json(meta_rows.get("stats")) or {}
        schema_version = _load_json(meta_rows.get("schema_version"))
        if schema_version is None:
            schema_version = (meta_obj or {}).get("schema") or 0

        items = {str(row["id"]): _load_json(row["data"]) for row in items_rows}
        assets = {str(row["id"]): _load_json(row["data"]) for row in assets_rows}
        craft = {str(row["key"]): _load_json(row["data"]) for row in craft_rows}
        cooking = {str(row["name"]): _load_json(row["data"]) for row in cooking_rows}
        cooking_ingredients = {str(row["item_id"]): _load_json(row["data"]) for row in cooking_ingredient_rows}

        return {
            "schema_version": schema_version,
            "meta": meta_obj,
            "items": items,
            "assets": assets,
            "craft": craft,
            "cooking": cooking,
            "cooking_ingredients": cooking_ingredients,
            "stats": stats_obj,
        }

    def _validate(self, doc: Dict[str, Any]) -> None:
        if not isinstance(doc, dict):
            raise CatalogError("Catalog root must be a JSON object")
        if "meta" not in doc:
            raise CatalogError("Catalog missing key: meta")

        if "assets" in doc and not isinstance(doc.get("assets"), dict):
            raise CatalogError("Catalog assets must be an object")

        schema = int(doc.get("schema_version") or (doc.get("meta") or {}).get("schema") or 0)
        if schema < 2:
            raise CatalogError("Catalog schema must be >=2")
        if "items" not in doc or not isinstance(doc.get("items"), dict):
            raise CatalogError("Catalog items must be an object")

        if "craft" not in doc:
            raise CatalogError("Catalog missing key: craft")
        craft = doc.get("craft") or {}
        if "recipes" not in craft or not isinstance(craft.get("recipes"), dict):
            raise CatalogError("Catalog craft.recipes must be an object")

        # cooking is optional, but if present it must be an object.
        if "cooking" in doc and not isinstance(doc.get("cooking"), dict):
            raise CatalogError("Catalog cooking must be an object")
        if "cooking_ingredients" in doc and not isinstance(doc.get("cooking_ingredients"), dict):
            raise CatalogError("Catalog cooking_ingredients must be an object")

    def _build_indexes(self, doc: Dict[str, Any]) -> None:
        assets_obj = doc.get("assets") or {}
        items_obj = doc.get("items") or {}

        items_out: Dict[str, Dict[str, Any]] = {}
        assets_out: Dict[str, Dict[str, Any]] = {}

        if isinstance(items_obj, dict) and items_obj:
            for iid, raw in items_obj.items():
                if not iid:
                    continue
                if isinstance(raw, dict):
                    item = dict(raw)
                else:
                    item = {"id": iid}
                item_id = str(item.get("id") or iid).strip()
                if not item_id:
                    continue
                item["id"] = item_id
                items_out[item_id] = item

        if isinstance(assets_obj, dict):
            for iid, raw in assets_obj.items():
                if not iid or not isinstance(raw, dict):
                    continue
                assets_out[str(iid)] = dict(raw)

        # merge per-item assets into assets_out
        for iid, item in items_out.items():
            a = item.get("assets")
            if not isinstance(a, dict):
                continue
            merged = dict(assets_out.get(iid) or {})
            for k, v in a.items():
                if k not in merged or merged.get(k) in (None, "", []):
                    merged[k] = v
            if merged:
                assets_out[iid] = merged

        self._items = items_out
        self._assets = assets_out

        # ---- item indexes ----
        by_kind: Dict[str, List[str]] = {}
        by_category: Dict[str, List[str]] = {}
        by_behavior: Dict[str, List[str]] = {}
        by_source: Dict[str, List[str]] = {}
        by_component: Dict[str, List[str]] = {}
        by_tag: Dict[str, List[str]] = {}
        by_slot: Dict[str, List[str]] = {}

        def _as_list(val: Any) -> List[str]:
            if isinstance(val, str):
                return [val]
            if isinstance(val, (list, tuple, set)):
                return [str(x) for x in val if x]
            return []

        def _push(bucket: Dict[str, List[str]], key: Optional[str], iid: str) -> None:
            if not key:
                return
            bucket.setdefault(str(key), []).append(iid)

        for iid, item in items_out.items():
            kind = item.get("kind")
            if kind:
                _push(by_kind, str(kind), iid)
            for cat in _as_list(item.get("categories")):
                _push(by_category, cat, iid)
            for beh in _as_list(item.get("behaviors")):
                _push(by_behavior, beh, iid)
            for src in _as_list(item.get("sources")):
                _push(by_source, src, iid)
            for comp in _as_list(item.get("components")):
                _push(by_component, comp, iid)
            for tag in _as_list(item.get("tags")):
                _push(by_tag, tag, iid)
            for slot in _as_list(item.get("slots")):
                _push(by_slot, slot, iid)

        for bucket in (by_kind, by_category, by_behavior, by_source, by_component, by_tag, by_slot):
            for k in list(bucket.keys()):
                bucket[k] = sorted(_dedup_preserve_order(bucket[k]))

        self._item_ids = sorted(items_out.keys())
        self._by_kind = by_kind
        self._by_category = by_category
        self._by_behavior = by_behavior
        self._by_source = by_source
        self._by_component = by_component
        self._by_tag_item = by_tag
        self._by_slot = by_slot

        # ---- craft ----
        craft = doc.get("craft") or {}
        recipes_obj: Dict[str, Any] = craft.get("recipes") or {}
        aliases: Dict[str, str] = craft.get("aliases") or {}
        filter_defs: List[Dict[str, Any]] = craft.get("filter_defs") or []
        filter_order: List[str] = craft.get("filter_order") or []

        recipes: Dict[str, CraftRecipe] = {}
        for name, raw in recipes_obj.items():
            if not isinstance(raw, dict):
                continue

            btags = raw.get("builder_tags") or []
            if isinstance(btags, str):
                btags = [btags]
            btags = [str(x) for x in btags if x]

            rec = CraftRecipe(
                name=str(raw.get("name") or name),
                product=(raw.get("product") or None),
                tab=str(raw.get("tab") or "UNKNOWN"),
                tech=str(raw.get("tech") or "UNKNOWN"),
                filters=[str(x) for x in (raw.get("filters") or []) if x],
                builder_tags=btags,
                builder_skill=(raw.get("builder_skill") or None),
                station_tag=(raw.get("station_tag") or None),
                ingredients=list(raw.get("ingredients") or []),
                ingredients_unresolved=list(raw.get("ingredients_unresolved") or []),
                raw=raw,
            )
            recipes[rec.name] = rec

        # indexes
        by_filter: Dict[str, List[str]] = {}
        by_tab: Dict[str, List[str]] = {}
        by_tag: Dict[str, List[str]] = {}
        by_ing: Dict[str, List[str]] = {}
        by_product: Dict[str, List[str]] = {}

        for rec in recipes.values():
            if rec.product:
                by_product.setdefault(str(rec.product), []).append(rec.name)

            for f in rec.filters:
                by_filter.setdefault(f, []).append(rec.name)

            if rec.tab:
                by_tab.setdefault(rec.tab, []).append(rec.name)

            for t in rec.builder_tags:
                by_tag.setdefault(t, []).append(rec.name)

            for ing in rec.ingredients:
                item = str(ing.get("item") or "").strip()
                if not item:
                    continue
                by_ing.setdefault(item, []).append(rec.name)

        for bucket in (by_filter, by_tab, by_tag, by_ing, by_product):
            for k in list(bucket.keys()):
                bucket[k] = sorted(_dedup_preserve_order(bucket[k]))

        self._recipes = recipes
        self._aliases = {str(k): str(v) for k, v in aliases.items() if k and v}
        self._filter_defs = list(filter_defs)
        self._filter_order = list(filter_order)

        self._by_filter = by_filter
        self._by_tab = by_tab
        self._by_tag = by_tag
        self._by_ingredient = by_ing
        self._by_product = by_product

        # ---- cooking ----
        self._build_cooking_indexes(doc.get("cooking") or {})
        self._build_cooking_ingredient_indexes(doc.get("cooking_ingredients") or {})

    def _build_cooking_indexes(self, cooking_obj: Dict[str, Any]) -> None:
        recipes: Dict[str, CookingRecipe] = {}
        by_tag: Dict[str, List[str]] = {}
        by_ft: Dict[str, List[str]] = {}
        by_ing: Dict[str, List[str]] = {}

        if not isinstance(cooking_obj, dict):
            cooking_obj = {}

        for name, raw in cooking_obj.items():
            if not isinstance(raw, dict):
                continue

            tags = raw.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            tags = [str(x) for x in tags if x]

            ci_raw = raw.get("card_ingredients") or []
            card_ings: List[Tuple[str, float]] = []
            if isinstance(ci_raw, list):
                for row in ci_raw:
                    if not isinstance(row, (list, tuple)) or len(row) < 2:
                        continue
                    item = str(row[0]).strip()
                    if not item:
                        continue
                    try:
                        cnt = float(row[1])
                    except Exception:
                        continue
                    if cnt <= 0:
                        continue
                    card_ings.append((item, cnt))

            try:
                priority = float(raw.get("priority", 0))
            except Exception:
                priority = 0.0
            try:
                weight = float(raw.get("weight", 1))
            except Exception:
                weight = 1.0

            ft = raw.get("foodtype")
            foodtype = str(ft).strip() if ft else None

            rec = CookingRecipe(
                name=str(name),
                priority=priority,
                weight=weight,
                foodtype=foodtype,
                hunger=raw.get("hunger"),
                health=raw.get("health"),
                sanity=raw.get("sanity"),
                perishtime=raw.get("perishtime"),
                cooktime=raw.get("cooktime"),
                tags=tags,
                card_ingredients=card_ings,
                raw=raw,
            )
            recipes[rec.name] = rec

            if rec.foodtype:
                by_ft.setdefault(rec.foodtype, []).append(rec.name)

            for t in rec.tags:
                by_tag.setdefault(t, []).append(rec.name)

            for item, _ in rec.card_ingredients:
                by_ing.setdefault(item, []).append(rec.name)

        for bucket in (by_tag, by_ft, by_ing):
            for k in list(bucket.keys()):
                bucket[k] = sorted(_dedup_preserve_order(bucket[k]))

        self._cooking = recipes
        self._cook_by_tag = by_tag
        self._cook_by_foodtype = by_ft
        self._cook_by_ingredient = by_ing

    def _build_cooking_ingredient_indexes(self, cooking_obj: Dict[str, Any]) -> None:
        items: Dict[str, Dict[str, Any]] = {}
        if not isinstance(cooking_obj, dict):
            cooking_obj = {}
        for item_id, raw in cooking_obj.items():
            if not item_id or not isinstance(raw, dict):
                continue
            iid = str(item_id).strip()
            if not iid:
                continue
            item = dict(raw)
            item.setdefault("id", iid)
            items[iid] = item
        self._cooking_ingredients = items

    # ----------------- helpers -----------------

    def _load_icon_index_if_stale(self, force: bool = False) -> None:
        path = self._icon_index_path
        try:
            mtime = path.stat().st_mtime
        except Exception:
            return
        if (not force) and self._icon_index and self._icon_index_mtime == mtime:
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            icons = data.get("icons") or {}
            mp: Dict[str, str] = {}
            for k, v in icons.items():
                if not k or not isinstance(k, str):
                    continue
                if isinstance(v, dict) and v.get("png"):
                    mp[k] = str(v.get("png"))
            self._icon_index = mp
            self._icon_index_mtime = mtime
        except Exception:
            return

    def _load_catalog_index_if_stale(self, force: bool = False) -> None:
        if self._use_sqlite:
            self._load_catalog_index_from_sqlite(force=force)
            return

        path = self._catalog_index_path
        try:
            mtime = path.stat().st_mtime
        except Exception:
            self._catalog_index_items = []
            self._catalog_index_total = 0
            self._catalog_index_mtime = -1.0
            return
        if (not force) and self._catalog_index_items and self._catalog_index_mtime == mtime:
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items = data.get("items") if isinstance(data, dict) else None
            if isinstance(items, list):
                out: List[Dict[str, Any]] = []
                for row in items:
                    if not isinstance(row, dict):
                        continue
                    iid = str(row.get("id") or "").strip()
                    if not iid:
                        continue
                    out.append(dict(row))
                out.sort(key=lambda x: x.get("id") or "")
                self._catalog_index_items = out
                self._catalog_index_total = len(out)
            else:
                self._catalog_index_items = []
                self._catalog_index_total = 0
            self._catalog_index_mtime = mtime
        except Exception:
            return

    def _load_catalog_index_from_sqlite(self, force: bool = False) -> None:
        try:
            mtime = self._path.stat().st_mtime
        except Exception:
            self._catalog_index_items = []
            self._catalog_index_total = 0
            self._catalog_index_mtime = -1.0
            return
        if (not force) and self._catalog_index_items and self._catalog_index_mtime == mtime:
            return
        try:
            conn = sqlite3.connect(str(self._path))
            conn.row_factory = sqlite3.Row
        except Exception:
            return
        try:
            cur = conn.cursor()
            rows = cur.execute(
                """
                SELECT id, name, icon, image, has_icon, icon_only, kind, categories, behaviors, sources, tags, components, slots
                FROM catalog_index
                ORDER BY id
                """
            ).fetchall()
        except Exception:
            self._catalog_index_items = []
            self._catalog_index_total = 0
            self._catalog_index_mtime = mtime
            conn.close()
            return
        finally:
            conn.close()

        def _load_list(value: Any) -> List[str]:
            if value is None:
                return []
            if isinstance(value, list):
                return [str(x) for x in value if x]
            try:
                out = json.loads(value)
                if isinstance(out, list):
                    return [str(x) for x in out if x]
            except Exception:
                pass
            return []

        out: List[Dict[str, Any]] = []
        for row in rows:
            iid = str(row["id"] or "").strip()
            if not iid:
                continue
            out.append(
                {
                    "id": iid,
                    "name": row["name"],
                    "icon": row["icon"],
                    "image": row["image"],
                    "has_icon": bool(row["has_icon"]),
                    "icon_only": bool(row["icon_only"]),
                    "kind": row["kind"],
                    "categories": _load_list(row["categories"]),
                    "behaviors": _load_list(row["behaviors"]),
                    "sources": _load_list(row["sources"]),
                    "tags": _load_list(row["tags"]),
                    "components": _load_list(row["components"]),
                    "slots": _load_list(row["slots"]),
                }
            )
        self._catalog_index_items = out
        self._catalog_index_total = len(out)
        self._catalog_index_mtime = mtime

    def _ensure_icon_index(self) -> None:
        self._load_icon_index_if_stale()

    def catalog_index(self) -> List[Dict[str, Any]]:
        """Compact catalog index for search/listing."""
        items: List[Dict[str, Any]] = []
        with self._lock:
            self._load_catalog_index_if_stale()
            if self._catalog_index_items:
                return list(self._catalog_index_items)
            self._ensure_icon_index()
            ids = list(self._item_ids)
            if not ids and self._assets:
                ids = list(self._assets.keys())
            if self._icon_index:
                ids = _dedup_preserve_order(ids + list(self._icon_index.keys()))

            for iid in ids:
                if not iid:
                    continue
                item = self._items.get(iid) or {}
                asset = (self._assets or {}).get(iid) or item.get("assets") or {}
                name = asset.get("name") or item.get("name") or iid
                icon = asset.get("icon") or asset.get("image") or (self._icon_index or {}).get(iid)
                items.append(
                    {
                        "id": iid,
                        "name": name,
                        "image": asset.get("image") or icon,
                        "icon": icon,
                        "has_icon": bool(icon),
                        "icon_only": bool(iid not in self._items),
                        "kind": item.get("kind"),
                        "categories": item.get("categories") or [],
                        "behaviors": item.get("behaviors") or [],
                        "sources": item.get("sources") or [],
                        "tags": item.get("tags") or [],
                        "components": item.get("components") or [],
                        "slots": item.get("slots") or [],
                    }
                )
        items.sort(key=lambda x: x["id"])
        with self._lock:
            self._catalog_index_items = items
            self._catalog_index_total = len(items)
        return list(items)

    def catalog_index_page(self, *, offset: int = 0, limit: int = 200) -> Tuple[List[Dict[str, Any]], int]:
        """Return a page of catalog index entries and total count."""
        off = max(0, int(offset or 0))
        lim = max(1, min(int(limit or 200), 2000))
        with self._lock:
            self._load_catalog_index_if_stale()
            items = list(self._catalog_index_items) if self._catalog_index_items else self.catalog_index()
            total = self._catalog_index_total or len(items)
        return items[off : off + lim], total

    def catalog_search(
        self,
        q: str,
        *,
        offset: int = 0,
        limit: int = 200,
        name_lookup: Optional[Dict[str, str]] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Search catalog index entries (id/name/tags/etc).

        name_lookup:
          Optional external name mapping (id -> name) used for extra matching.
        """
        query = str(q or "").strip().lower()
        if not query:
            return [], 0

        def _split_query(text: str) -> Tuple[List[Tuple[str, str]], List[str]]:
            tokens = [t for t in text.split() if t]
            filters: List[Tuple[str, str]] = []
            words: List[str] = []
            for tok in tokens:
                if ":" in tok:
                    k, v = tok.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    if k and v:
                        filters.append((k, v))
                        continue
                words.append(tok)
            return filters, words

        filters, words = _split_query(query)

        def _as_list(val: Any) -> List[str]:
            if isinstance(val, str):
                return [val]
            if isinstance(val, (list, tuple, set)):
                return [str(x) for x in val if x]
            return []

        def _match_filters(item: Dict[str, Any]) -> bool:
            if not filters:
                return True
            kind = str(item.get("kind") or "").lower()
            cats = [v.lower() for v in _as_list(item.get("categories"))]
            behs = [v.lower() for v in _as_list(item.get("behaviors"))]
            srcs = [v.lower() for v in _as_list(item.get("sources"))]
            tags = [v.lower() for v in _as_list(item.get("tags"))]
            comps = [v.lower() for v in _as_list(item.get("components"))]
            slots = [v.lower() for v in _as_list(item.get("slots"))]

            def _hit(arr: List[str], vals: List[str]) -> bool:
                return any(v in arr for v in vals)

            for key_raw, val_raw in filters:
                key = key_raw.lower()
                vals = [v.strip().lower() for v in val_raw.split(",") if v.strip()]
                if not vals:
                    continue
                if key in ("kind", "type"):
                    if kind not in vals:
                        return False
                elif key in ("cat", "category"):
                    if not _hit(cats, vals):
                        return False
                elif key in ("beh", "behavior"):
                    if not _hit(behs, vals):
                        return False
                elif key in ("src", "source"):
                    if not _hit(srcs, vals):
                        return False
                elif key == "tag":
                    if not _hit(tags, vals):
                        return False
                elif key in ("comp", "component"):
                    if not _hit(comps, vals):
                        return False
                elif key == "slot":
                    if not _hit(slots, vals):
                        return False
            return True

        with self._lock:
            self._load_catalog_index_if_stale()
            items = list(self._catalog_index_items) if self._catalog_index_items else self.catalog_index()

        extra_names: Dict[str, str] = {}
        if name_lookup:
            extra_names = {
                str(k).lower(): str(v).lower()
                for k, v in name_lookup.items()
                if k and v
            }

        scored: List[Tuple[int, str, Dict[str, Any]]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if not _match_filters(item):
                continue
            iid_raw = str(item.get("id") or "")
            iid = iid_raw.lower()
            name = str(item.get("name") or "").lower()
            alt = extra_names.get(iid) or extra_names.get(iid_raw.lower(), "")
            score = 0
            if not words:
                score = 1
            else:
                for w in words:
                    if not w:
                        continue
                    if iid == w:
                        score += 1000
                    if iid.startswith(w):
                        score += 200
                    if w in iid:
                        score += 80
                    if w in name:
                        score += 40
                    if alt and w in alt:
                        score += 60
            if score > 0:
                scored.append((score, iid, item))

        scored.sort(key=lambda x: (-x[0], x[1]))
        total = len(scored)
        off = max(0, int(offset or 0))
        lim = max(1, min(int(limit or 200), 2000))
        sliced = [row[2] for row in scored[off : off + lim]]
        return sliced, total

    # ----------------- craft queries -----------------

    def resolve_recipe_name(self, q: str) -> Optional[str]:
        """Resolve query -> canonical recipe name via aliases & exact match (case-insensitive)."""
        if not q:
            return None
        q0 = str(q).strip()
        if not q0:
            return None

        with self._lock:
            if q0 in self._recipes:
                return q0

            if q0 in self._aliases:
                return self._aliases[q0]

            ql = q0.lower()
            for nm in self._recipes.keys():
                if nm.lower() == ql:
                    return nm
            for a, nm in self._aliases.items():
                if a.lower() == ql:
                    return nm

        return None

    def get_recipe(self, q: str) -> Optional[CraftRecipe]:
        name = self.resolve_recipe_name(q)
        if not name:
            return None
        with self._lock:
            return self._recipes.get(name)

    def iter_recipes(self) -> List[CraftRecipe]:
        """Return a snapshot list of all recipes."""
        with self._lock:
            return list(self._recipes.values())

    def list_filters(self) -> Tuple[List[str], List[Dict[str, Any]]]:
        with self._lock:
            return list(self._filter_order), list(self._filter_defs)

    def list_tabs(self) -> List[Dict[str, Any]]:
        """Return ordered tabs with counts.

        Order heuristic:
          - follow filter_order for any matching tab name
          - then append remaining tabs alphabetically
        """
        with self._lock:
            tab_names = set(self._by_tab.keys())
            ordered: List[str] = []
            for f in self._filter_order:
                if f in tab_names and f not in ordered:
                    ordered.append(f)
            ordered += sorted([t for t in tab_names if t not in ordered])
            return [{"name": t, "count": len(self._by_tab.get(t, []))} for t in ordered]

    def list_tags(self) -> List[Dict[str, Any]]:
        with self._lock:
            tags = [{"name": t, "count": len(v)} for t, v in self._by_tag.items()]
        tags.sort(key=lambda x: (-x["count"], x["name"]))
        return tags

    def list_by_filter(self, filter_name: str) -> List[str]:
        with self._lock:
            return list(self._by_filter.get(filter_name, []))

    def list_by_tab(self, tab: str) -> List[str]:
        with self._lock:
            return list(self._by_tab.get(tab, []))

    def list_by_tag(self, tag: str) -> List[str]:
        with self._lock:
            return list(self._by_tag.get(tag, []))

    def list_by_ingredient(self, item: str) -> List[str]:
        with self._lock:
            return list(self._by_ingredient.get(item, []))

    def list_by_product(self, item: str) -> List[str]:
        """List craft recipes whose product equals `item`."""
        key = (item or "").strip()
        if not key:
            return []
        with self._lock:
            return list(self._by_product.get(key, []))

    def search(
        self,
        q: str,
        limit: int = 50,
        name_lookup: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search craft recipes.

        Supported prefixes:
          - ing:<item>
          - tag:<builder_tag>
          - filter:<FILTER>
          - tab:<TAB>

        Otherwise:
          - substring match on recipe name or product
        """
        q = (q or "").strip()
        if not q:
            return []

        limit = max(1, min(int(limit or 50), 500))
        ql = q.lower()

        extra_names: Dict[str, str] = {}
        if name_lookup:
            extra_names = {
                str(k).lower(): str(v).lower()
                for k, v in name_lookup.items()
                if k and v
            }

        with self._lock:
            for prefix in ("ing:", "tag:", "filter:", "tab:"):
                if ql.startswith(prefix):
                    val = q[len(prefix) :].strip()
                    if not val:
                        return []
                    if prefix == "ing:":
                        names = self._by_ingredient.get(val, [])
                    elif prefix == "tag:":
                        names = self._by_tag.get(val, [])
                    elif prefix == "filter:":
                        names = self._by_filter.get(val, [])
                    else:
                        names = self._by_tab.get(val, [])
                    return [self._recipe_brief(nm) for nm in names[:limit]]

            nm = self.resolve_recipe_name(q)
            if nm:
                return [self._recipe_brief(nm)]

            if not extra_names:
                hits: List[str] = []
                for nm2, rec in self._recipes.items():
                    if ql in nm2.lower() or (rec.product and ql in str(rec.product).lower()):
                        hits.append(nm2)
                        if len(hits) >= limit:
                            break
                return [self._recipe_brief(nm2) for nm2 in hits]

            scored: List[Tuple[int, str]] = []
            for nm2, rec in self._recipes.items():
                nm2l = nm2.lower()
                prod = str(rec.product or "").lower()
                alt_nm = extra_names.get(nm2l) or ""
                alt_prod = extra_names.get(prod) if prod else ""
                score = 0
                if nm2l == ql:
                    score += 400
                elif nm2l.startswith(ql):
                    score += 200
                elif ql in nm2l:
                    score += 80
                if prod:
                    if prod == ql:
                        score += 120
                    elif prod.startswith(ql):
                        score += 60
                    elif ql in prod:
                        score += 20
                if alt_nm:
                    idx = alt_nm.find(ql)
                    if idx >= 0:
                        score += 120
                        if idx == 0:
                            score += 60
                        if len(alt_nm) == len(ql):
                            score += 40
                if alt_prod:
                    idx = alt_prod.find(ql)
                    if idx >= 0:
                        score += 60
                        if idx == 0:
                            score += 30
                        if len(alt_prod) == len(ql):
                            score += 20
                if score > 0:
                    scored.append((score, nm2))

            scored.sort(key=lambda x: (-x[0], x[1]))
            return [self._recipe_brief(nm2) for _, nm2 in scored[:limit]]

    def _recipe_brief(self, name: str) -> Dict[str, Any]:
        rec = self._recipes.get(name)
        if not rec:
            return {"name": name}
        return {
            "name": rec.name,
            "product": rec.product,
            "tab": rec.tab,
            "tech": rec.tech,
            "filters": rec.filters,
            "builder_tags": rec.builder_tags,
            "builder_skill": rec.builder_skill,
            "station_tag": rec.station_tag,
        }

    # ----------------- cooking queries -----------------

    def resolve_cooking_name(self, q: str) -> Optional[str]:
        if not q:
            return None
        q0 = str(q).strip()
        if not q0:
            return None

        with self._lock:
            if q0 in self._cooking:
                return q0

            ql = q0.lower()
            for nm in self._cooking.keys():
                if nm.lower() == ql:
                    return nm

        return None

    def get_cooking_recipe(self, q: str) -> Optional[CookingRecipe]:
        nm = self.resolve_cooking_name(q)
        if not nm:
            return None
        with self._lock:
            return self._cooking.get(nm)

    def iter_cooking_recipes(self) -> List[CookingRecipe]:
        with self._lock:
            return list(self._cooking.values())

    def cooking_ingredients(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._cooking_ingredients)

    def cooking_ingredients_with_fallback(self) -> Tuple[Dict[str, Dict[str, Any]], str]:
        with self._lock:
            if self._cooking_ingredients:
                return dict(self._cooking_ingredients), "cooking_ingredients"

            items: Dict[str, Dict[str, Any]] = {}

            def _is_foodish(item: Dict[str, Any]) -> bool:
                comps = item.get("components") or []
                if isinstance(comps, (list, tuple, set)) and "edible" in comps:
                    return True
                beh = item.get("behaviors") or []
                if isinstance(beh, (list, tuple, set)) and "edible" in beh:
                    return True
                cats = item.get("categories") or []
                if isinstance(cats, (list, tuple, set)) and "food" in cats:
                    return True
                return False

            cooking_ids = set(self._cooking.keys())
            for iid, item in self._items.items():
                foodish = _is_foodish(item)
                tags = guess_cooking_tags(iid, item if foodish else None)
                if not tags:
                    continue
                kind = str(item.get("kind") or "").strip().lower()
                if not foodish and set(tags.keys()) <= {"magic"}:
                    continue
                if kind in ("creature", "structure", "character", "world") and not foodish:
                    continue
                if not foodish and iid in cooking_ids and iid not in self._cook_by_ingredient:
                    continue
                items[iid] = {"id": iid, "tags": tags, "foodtype": None}

            for iid in self._cook_by_ingredient.keys():
                if iid in items:
                    continue
                tags = guess_cooking_tags(iid, self._items.get(iid))
                items[iid] = {"id": iid, "tags": tags, "foodtype": None}

            source = "items_fallback" if items else "card_ingredients"
            return items, source

    def list_cooking_ingredients(self) -> List[str]:
        with self._lock:
            if self._cooking_ingredients:
                items = self._cooking_ingredients.keys()
            else:
                items = self._cook_by_ingredient.keys()
        return sorted(items)

    def list_cooking_foodtypes(self) -> List[Dict[str, Any]]:
        with self._lock:
            items = [{"name": ft, "count": len(v)} for ft, v in self._cook_by_foodtype.items()]
        items.sort(key=lambda x: (-x["count"], x["name"]))
        return items

    def list_cooking_tags(self) -> List[Dict[str, Any]]:
        with self._lock:
            items = [{"name": t, "count": len(v)} for t, v in self._cook_by_tag.items()]
        items.sort(key=lambda x: (-x["count"], x["name"]))
        return items

    def list_cooking_by_foodtype(self, foodtype: str) -> List[str]:
        with self._lock:
            return list(self._cook_by_foodtype.get(foodtype, []))

    def list_cooking_by_tag(self, tag: str) -> List[str]:
        with self._lock:
            return list(self._cook_by_tag.get(tag, []))

    def list_cooking_by_ingredient(self, item: str) -> List[str]:
        with self._lock:
            return list(self._cook_by_ingredient.get(item, []))

    def search_cooking(
        self,
        q: str,
        limit: int = 50,
        name_lookup: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search cooking recipes.

        Supported prefixes:
          - ing:<item>      (uses card_ingredients index; may be incomplete)
          - tag:<tag>      (food tags)
          - type:<FOODTYPE.*> or foodtype:<FOODTYPE.*>

        Otherwise: substring match on recipe name.
        """
        q = (q or "").strip()
        if not q:
            return []

        limit = max(1, min(int(limit or 50), 500))
        ql = q.lower()

        extra_names: Dict[str, str] = {}
        if name_lookup:
            extra_names = {
                str(k).lower(): str(v).lower()
                for k, v in name_lookup.items()
                if k and v
            }

        with self._lock:
            for prefix in ("ing:", "tag:", "type:", "foodtype:"):
                if ql.startswith(prefix):
                    val = q[len(prefix) :].strip()
                    if not val:
                        return []
                    if prefix == "ing:":
                        names = self._cook_by_ingredient.get(val, [])
                    elif prefix == "tag:":
                        names = self._cook_by_tag.get(val, [])
                    else:
                        names = self._cook_by_foodtype.get(val, [])
                    return [{"name": nm} for nm in names[:limit]]

            nm = self.resolve_cooking_name(q)
            if nm:
                return [{"name": nm}]

            if not extra_names:
                hits: List[str] = []
                for nm2 in self._cooking.keys():
                    if ql in nm2.lower():
                        hits.append(nm2)
                        if len(hits) >= limit:
                            break
                return [{"name": nm2} for nm2 in hits]

            scored: List[Tuple[int, str]] = []
            for nm2 in self._cooking.keys():
                nm2l = nm2.lower()
                alt = extra_names.get(nm2l) or ""
                score = 0
                if nm2l == ql:
                    score += 200
                elif nm2l.startswith(ql):
                    score += 120
                elif ql in nm2l:
                    score += 60
                if alt:
                    idx = alt.find(ql)
                    if idx >= 0:
                        score += 120
                        if idx == 0:
                            score += 60
                        if len(alt) == len(ql):
                            score += 40
                if score > 0:
                    scored.append((score, nm2))

            scored.sort(key=lambda x: (-x[0], x[1]))
            return [{"name": nm2} for _, nm2 in scored[:limit]]

# -*- coding: utf-8 -*-
from __future__ import annotations

import json
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


class CatalogStore:
    """Load + index wagstaff catalog for fast queries (thread-safe).

    Data source:
      - data/index/wagstaff_catalog_v2.json

    This layer is intentionally independent from wiki/cli layers. It should be safe
    to reuse from:
      - CLI (wiki)
      - Web (webcraft)
      - future GUI (desktop)
    """

    def __init__(self, catalog_path: Path):
        self._path = Path(catalog_path)
        self._lock = threading.RLock()
        self._mtime: float = -1.0
        self._icon_index_mtime: float = -1.0
        self._icon_index: Dict[str, str] = {}
        self._icon_index_path: Path = self._path.parent / "wagstaff_icon_index_v1.json"

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

        self.load(force=True)

    @property
    def path(self) -> Path:
        return self._path

    def meta(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._meta)

    def schema_version(self) -> int:
        with self._lock:
            return int(self._doc.get("schema_version") or (self._meta or {}).get("schema") or 0)

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

            doc = json.loads(self._path.read_text(encoding="utf-8"))
            self._validate(doc)

            self._doc = doc
            self._meta = doc.get("meta") or {}
            self._mtime = mtime

            self._build_indexes(doc)
            self._load_icon_index_if_stale(force=force)
            return True

    def _validate(self, doc: Dict[str, Any]) -> None:
        if not isinstance(doc, dict):
            raise CatalogError("Catalog root must be a JSON object")
        if "meta" not in doc:
            raise CatalogError("Catalog missing key: meta")

        if "assets" in doc and not isinstance(doc.get("assets"), dict):
            raise CatalogError("Catalog assets must be an object")

        schema = int(doc.get("schema_version") or (doc.get("meta") or {}).get("schema") or 0)
        if ("items" in doc) or schema >= 2:
            if "items" not in doc or not isinstance(doc.get("items"), dict):
                raise CatalogError("Catalog items must be an object")

        if "craft" not in doc:
            raise CatalogError("Catalog missing key: craft")
        craft = doc.get("craft") or {}
        if "recipes" not in craft or not isinstance(craft.get("recipes"), dict):
            raise CatalogError("Catalog craft.recipes must be an object")

        # cooking is optional in v1, but if present it must be an object.
        if "cooking" in doc and not isinstance(doc.get("cooking"), dict):
            raise CatalogError("Catalog cooking must be an object")

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
        elif isinstance(assets_obj, dict) and assets_obj:
            # v1 fallback: derive items from assets
            for iid in assets_obj.keys():
                if not iid:
                    continue
                items_out[str(iid)] = {"id": str(iid)}

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

    def _ensure_icon_index(self) -> None:
        self._load_icon_index_if_stale()

    def catalog_index(self) -> List[Dict[str, Any]]:
        """Compact catalog index for search/listing."""
        items: List[Dict[str, Any]] = []
        with self._lock:
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
        return items

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

    def search(self, q: str, limit: int = 50) -> List[Dict[str, Any]]:
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

            hits: List[str] = []
            for nm2, rec in self._recipes.items():
                if ql in nm2.lower() or (rec.product and ql in str(rec.product).lower()):
                    hits.append(nm2)
                    if len(hits) >= limit:
                        break

            return [self._recipe_brief(nm2) for nm2 in hits]

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

    def search_cooking(self, q: str, limit: int = 50) -> List[Dict[str, Any]]:
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

            hits: List[str] = []
            for nm2 in self._cooking.keys():
                if ql in nm2.lower():
                    hits.append(nm2)
                    if len(hits) >= limit:
                        break

            return [{"name": nm2} for nm2 in hits]

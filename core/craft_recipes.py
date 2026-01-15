# -*- coding: utf-8 -*-
"""core/craft_recipes.py

Crafting recipes (Recipe/Recipe2/AddRecipe2) + recipe filter organization.

Why this module exists
- `scripts/recipes*.lua` and `scripts/recipes_filter.lua` are data sources.
- UI layers (wiki/GUI/web) need a stable, query-friendly Python representation.

Design goals (M0)
- Reuse `core/analyzer.py` Lua parsing primitives (single source of truth).
- Keep outputs JSON-serializable for catalog/index (M2).

Public API (expected by existing CLI)
- CraftRecipeDB.get(name)
- CraftRecipeDB.list_by_tab(tab)
- CraftRecipeDB.list_by_filter(filter)
- CraftRecipeDB.list_by_builder_tag(tag)
- CraftRecipeDB.list_by_tech(tech)

New (M2)
- CraftRecipeDB.list_by_ingredient(item)
- CraftRecipeDB.craftable(inventory)
- CraftRecipeDB.missing_for(recipe, inventory)
- CraftRecipeDB.to_dict() / CraftRecipeDB.from_dict()
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from analyzer import (
    LuaCallExtractor,
    LuaRaw,
    LuaTableValue,
    find_matching,
    lua_to_python,
    parse_lua_expr,
    parse_lua_string,
    strip_lua_comments,
)

__all__ = [
    "CraftRecipeDB",
    "parse_filter_defs",
]


# =========================================================
# Regex helpers
# =========================================================

_TECH_TOKEN_RE = re.compile(r"\bTECH\.[A-Z0-9_]+\b")
_TAB_TOKEN_RE = re.compile(r"\bRECIPETABS\.[A-Z0-9_]+\b")
_FILTER_TOKEN_RE = re.compile(r"\bCRAFTING_FILTERS\.([A-Z0-9_]+)\b")
_FILTER_ASSIGN_RE = re.compile(r"\bCRAFTING_FILTERS\.([A-Z0-9_]+)\.recipes\s*=\s*\{", re.MULTILINE)

# string literals inside a table list; recipes_filter.lua uses plain quoted names
_QUOTED_STR_RE = re.compile(r"([\"'])([^\"']+)\1")

# If a "{ ... }" argument contains '=', it is most likely a config table not a filter list.
# This heuristic is intentionally conservative.


# =========================================================
# Data model helpers
# =========================================================

def _dedup_preserve(seq: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for x in seq:
        if not x:
            continue
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _looks_like_kv_table(expr_text: str) -> bool:
    s = (expr_text or "").strip()
    return s.startswith("{") and ("=" in s)


def _extract_first_token(rx: re.Pattern[str], text: str) -> Optional[str]:
    m = rx.search(text or "")
    return m.group(0) if m else None


_NUM_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\d*\.?\d+)(?:[eE][+-]?\d+)?$")


def _to_amount(expr_text: str) -> Tuple[Optional[float], str]:
    """Return (amount_num, amount_expr)."""
    raw = (expr_text or "").strip() or "1"

    # Fast path numeric
    if _NUM_RE.match(raw):
        try:
            return float(raw), raw
        except Exception:
            return None, raw

    v = parse_lua_expr(raw)
    if isinstance(v, (int, float)):
        return float(v), raw

    # LuaRaw with a numeric string
    if isinstance(v, LuaRaw) and _NUM_RE.match(v.text.strip()):
        try:
            return float(v.text.strip()), raw
        except Exception:
            pass

    return None, raw


def _parse_string_list(v: Any) -> List[str]:
    """Try to turn a Lua table value into a list[str]."""
    if isinstance(v, LuaTableValue):
        out: List[str] = []
        for x in v.array:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, LuaRaw):
                # keep raw symbol if it looks like a string constant
                out.append(x.text)
            else:
                py = lua_to_python(x)
                if isinstance(py, str):
                    out.append(py)
        return _dedup_preserve(out)

    py = lua_to_python(v)
    if isinstance(py, list):
        return _dedup_preserve([str(x) for x in py if x is not None])

    return []


def _parse_config_fields(tbl: LuaTableValue) -> Dict[str, Any]:
    """Extract commonly useful fields from a recipe config table."""
    out: Dict[str, Any] = {}

    for k, v in (tbl.map or {}).items():
        if not isinstance(k, str):
            continue

        if k in {
            "builder_tag",
            "builder_skill",
            "station_tag",
            "product",
            "placer",
            "image",
            "atlas",
            "nounlock",
            "numtogive",
            "min_spacing",
            "testfn",  # sometimes exists
        }:
            out[k] = lua_to_python(v)
        elif k in {"builder_tags"}:
            out[k] = _parse_string_list(v)
        # Keep unknown keys out for now (index bloat).

    # normalize: builder_tags may be an object/dict if table is keyed; accept only list
    if "builder_tags" in out and not isinstance(out["builder_tags"], list):
        out.pop("builder_tags", None)

    return out


def _parse_filters_from_text(expr_text: str) -> List[str]:
    if not expr_text:
        return []

    filters: List[str] = []

    # CRAFTING_FILTERS.NAME tokens
    filters += [m.group(1) for m in _FILTER_TOKEN_RE.finditer(expr_text)]

    # quoted uppercase strings (rare but exists in some mods)
    for q in re.findall(r"[\"']([A-Z0-9_]+)[\"']", expr_text):
        if q and q.upper() == q:
            filters.append(q)

    return _dedup_preserve([f.upper() for f in filters if f])


# =========================================================
# Parsing: recipes.lua / recipes2.lua
# =========================================================


def _parse_ingredients_from_expr(expr_text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Extract Ingredient("item", amount) calls.

    Returns (ingredients, unresolved_items).

    Ingredient amount is stored as:
    - amount: original expression string
    - amount_num: parsed float if possible (else None)
    """
    if not expr_text:
        return [], []

    out: List[Dict[str, Any]] = []
    unresolved: List[str] = []

    ex = LuaCallExtractor(expr_text)
    for call in ex.iter_calls(["Ingredient"], include_member_calls=False):
        if not call.arg_list:
            continue

        item_expr = call.arg_list[0].strip()
        item = parse_lua_string(item_expr) or item_expr

        if len(call.arg_list) >= 2:
            amount_expr = call.arg_list[1]
        else:
            amount_expr = "1"

        amount_num, amount_raw = _to_amount(amount_expr)

        rec = {
            "item": item,
            "amount": amount_raw,
            "amount_num": amount_num,
        }
        out.append(rec)

        if amount_num is None:
            unresolved.append(str(item))

    return out, _dedup_preserve(unresolved)


def _init_recipe_record(name: str) -> Dict[str, Any]:
    return {
        "name": name,
        "product": name,  # default: in most DST recipes, name == prefab product
        "ingredients": [],
        "ingredients_unresolved": [],
        "tech": "UNKNOWN",
        "tab": "UNKNOWN",  # assigned later from filter membership
        "filters": [],
        "builder_tag": None,
        "builder_tags": [],
        "builder_skill": None,
        "station_tag": None,
        "sources": [],
        # optional metadata (for GUI)
        "image": None,
        "atlas": None,
        "placer": None,
        "nounlock": None,
        "numtogive": None,
    }


def _parse_recipe_call(call_name: str, args: Sequence[str]) -> Optional[Dict[str, Any]]:
    """Parse a Recipe/Recipe2/AddRecipe2 call into a recipe record."""
    if not args:
        return None

    name = parse_lua_string(args[0])
    if not name:
        return None

    rec = _init_recipe_record(name)
    rec["sources"].append(call_name)

    # ingredients: usually arg[1]
    if len(args) >= 2:
        ing, unresolved = _parse_ingredients_from_expr(args[1])
        if ing:
            rec["ingredients"] = ing
        if unresolved:
            rec["ingredients_unresolved"] = unresolved

    # tech: usually arg[2], but also scan whole call for TECH.X
    tech = None
    if len(args) >= 3:
        tech = _extract_first_token(_TECH_TOKEN_RE, args[2])
    if tech is None:
        tech = _extract_first_token(_TECH_TOKEN_RE, " ".join(args))
    if tech:
        rec["tech"] = tech

    # explicit RECIPETABS (legacy) if present
    tab = _extract_first_token(_TAB_TOKEN_RE, " ".join(args))
    if tab:
        rec["tab"] = tab

    # parse remaining args: config tables and/or explicit filter lists
    for a in args[2:]:
        a = (a or "").strip()
        if not a.startswith("{"):
            # Sometimes filters are passed as plain symbols; token-scan anyway.
            fs = _parse_filters_from_text(a)
            if fs:
                rec["filters"] = _dedup_preserve(list(rec.get("filters", [])) + fs)
            continue

        v = parse_lua_expr(a)
        if isinstance(v, LuaTableValue) and _looks_like_kv_table(a):
            fields = _parse_config_fields(v)
            for k, val in fields.items():
                if k == "builder_tags":
                    rec["builder_tags"] = _dedup_preserve(list(rec.get("builder_tags") or []) + list(val or []))
                    continue
                if val is None:
                    continue
                if rec.get(k) in (None, "UNKNOWN", [], {}):
                    rec[k] = val
                else:
                    # avoid overwriting unless empty
                    pass

            # product override
            if fields.get("product"):
                rec["product"] = fields.get("product")

        else:
            fs = _parse_filters_from_text(a)
            if fs:
                rec["filters"] = _dedup_preserve(list(rec.get("filters", [])) + fs)

    # Normalize builder_tags
    if rec.get("builder_tag"):
        rec["builder_tags"] = _dedup_preserve(list(rec.get("builder_tags") or []) + [str(rec["builder_tag"])])

    return rec


def parse_craft_recipes(recipes_lua: str, recipes2_lua: str) -> Dict[str, Dict[str, Any]]:
    """Parse craft recipes from recipes.lua + recipes2.lua.

    - recipes.lua: Recipe/Recipe2
    - recipes2.lua: AddRecipe2

    Returns dict: name -> recipe_record
    """
    out: Dict[str, Dict[str, Any]] = {}

    for src, fnames in ((recipes_lua or "", ["Recipe", "Recipe2"]), (recipes2_lua or "", ["AddRecipe2"])):
        if not src:
            continue
        ex = LuaCallExtractor(src)
        for call in ex.iter_calls(fnames, include_member_calls=False):
            rec = _parse_recipe_call(call.name, call.arg_list)
            if not rec:
                continue
            name = rec["name"]
            if name not in out:
                out[name] = rec
            else:
                # Merge: later source wins for missing fields; union for lists.
                cur = out[name]
                cur["sources"] = _dedup_preserve(list(cur.get("sources", [])) + list(rec.get("sources", [])))

                # ingredients: keep first non-empty
                if (not cur.get("ingredients")) and rec.get("ingredients"):
                    cur["ingredients"] = rec["ingredients"]

                # union unresolved
                cur["ingredients_unresolved"] = _dedup_preserve(
                    list(cur.get("ingredients_unresolved") or []) + list(rec.get("ingredients_unresolved") or [])
                )

                # prefer concrete tech
                if cur.get("tech") in (None, "", "UNKNOWN") and rec.get("tech") not in (None, "", "UNKNOWN"):
                    cur["tech"] = rec["tech"]

                # union filters
                cur["filters"] = _dedup_preserve(list(cur.get("filters") or []) + list(rec.get("filters") or []))

                # fill other scalar fields if empty
                for k in (
                    "builder_tag",
                    "builder_skill",
                    "station_tag",
                    "product",
                    "tab",
                    "image",
                    "atlas",
                    "placer",
                    "nounlock",
                    "numtogive",
                ):
                    if cur.get(k) in (None, "", "UNKNOWN") and rec.get(k) not in (None, "", "UNKNOWN"):
                        cur[k] = rec[k]

                # builder_tags union
                cur["builder_tags"] = _dedup_preserve(list(cur.get("builder_tags") or []) + list(rec.get("builder_tags") or []))

    return out


# =========================================================
# Parsing: recipes_filter.lua
# =========================================================


def parse_filter_defs(src: str) -> List[Dict[str, Any]]:
    """Parse the CRAFTING_FILTER_DEFS table as an ordered list of dicts."""
    if not src:
        return []

    clean = strip_lua_comments(src)
    idx = clean.find("CRAFTING_FILTER_DEFS")
    if idx == -1:
        return []

    brace = clean.find("{", idx)
    if brace == -1:
        return []

    end = find_matching(clean, brace, "{", "}")
    if end is None:
        return []

    block = clean[brace : end + 1]
    tbl = parse_lua_expr(block)
    if not isinstance(tbl, LuaTableValue):
        return []

    defs: List[Dict[str, Any]] = []
    for entry in tbl.array:
        if not isinstance(entry, LuaTableValue):
            continue
        d: Dict[str, Any] = {}
        for k, v in entry.map.items():
            if isinstance(k, str):
                d[k] = lua_to_python(v)
        if d:
            defs.append(d)

    return defs


def _parse_filter_order(src: str) -> List[str]:
    defs = parse_filter_defs(src)
    order: List[str] = []
    for d in defs:
        nm = d.get("name")
        if isinstance(nm, str) and nm:
            order.append(nm.upper())
    return order


def _parse_filter_recipe_lists(src: str) -> Dict[str, List[str]]:
    """Parse `CRAFTING_FILTERS.X.recipes = { ... }` lists."""
    out: Dict[str, List[str]] = {}
    if not src:
        return out

    clean = strip_lua_comments(src)

    for m in _FILTER_ASSIGN_RE.finditer(clean):
        flt = m.group(1).upper()
        brace = m.end() - 1
        end = find_matching(clean, brace, "{", "}")
        if end is None:
            continue
        inner = clean[brace + 1 : end]
        names = [sm.group(2) for sm in _QUOTED_STR_RE.finditer(inner)]
        # recipes list is typically plain strings (prefab names)
        out[flt] = _dedup_preserve(names)

    return out


def _parse_filter_bindings_by_calls(src: str) -> Dict[str, List[str]]:
    """Parse AddRecipeToFilter(s) calls.

    Returns: recipe_name -> [filters...]
    """
    out: Dict[str, List[str]] = defaultdict(list)
    if not src:
        return out

    ex = LuaCallExtractor(src)
    for call in ex.iter_calls(["AddRecipeToFilter", "AddRecipeToFilters"], include_member_calls=False):
        args = call.arg_list
        if not args:
            continue

        # recipe name is usually the first non-UPPERCASE string literal
        recipe_name: Optional[str] = None
        for a in args:
            s = parse_lua_string(a)
            if s and not s.isupper():
                recipe_name = s
                break
        if recipe_name is None:
            for a in args:
                s = parse_lua_string(a)
                if s:
                    recipe_name = s
                    break
        if not recipe_name:
            continue

        filters: List[str] = []
        for a in args:
            filters += _parse_filters_from_text(a)

        if filters:
            out[recipe_name] = _dedup_preserve(list(out.get(recipe_name, [])) + filters)

    return out


# =========================================================
# CraftRecipeDB (public)
# =========================================================


class CraftRecipeDB:
    """Queryable craft recipe database.

    Build sources:
    - recipes.lua / recipes2.lua (Recipe/Recipe2/AddRecipe2)
    - recipes_filter.lua (filters order + filter membership)

    Notes
    - `tab` is derived from filter order: first non-special filter in membership.
    - `filters` holds all known filter memberships.
    """

    _SPECIAL_FILTERS = {"FAVORITES", "CRAFTING_STATION", "SPECIAL_EVENT", "MODS", "CHARACTER", "EVERYTHING"}

    def __init__(self, *args, **kwargs):
        """Supported initializers:

        - CraftRecipeDB(recipes_lua=..., recipes2_lua=..., recipes_filter_lua=...)
        - CraftRecipeDB(recipes_lua, recipes2_lua, recipes_filter_lua)
        - CraftRecipeDB(recipes_lua, recipes_filter_lua)  # legacy fallback
        """
        recipes_lua = kwargs.get("recipes_lua", "")
        recipes2_lua = kwargs.get("recipes2_lua", "")
        recipes_filter_lua = kwargs.get("recipes_filter_lua", "")

        if args:
            if len(args) == 1:
                recipes_lua = args[0]
            elif len(args) == 2:
                recipes_lua = args[0]
                recipes_filter_lua = args[1]
            else:
                recipes_lua = args[0]
                recipes2_lua = args[1]
                recipes_filter_lua = args[2]

        self.recipes: Dict[str, Dict[str, Any]] = {}
        self.aliases: Dict[str, str] = {}

        self.filter_defs: List[Dict[str, Any]] = []
        self.filter_order: List[str] = []
        self.tab_order: List[str] = []

        self.by_tab: Dict[str, List[str]] = defaultdict(list)
        self.by_filter: Dict[str, List[str]] = defaultdict(list)
        self.by_tech: Dict[str, List[str]] = defaultdict(list)
        self.by_builder_tag: Dict[str, List[str]] = defaultdict(list)
        self.by_ingredient: Dict[str, List[str]] = defaultdict(list)

        self._build(recipes_lua or "", recipes2_lua or "", recipes_filter_lua or "")

    # -----------------
    # build
    # -----------------

    def _build(self, recipes_lua: str, recipes2_lua: str, recipes_filter_lua: str) -> None:
        # 1) base recipes
        self.recipes = parse_craft_recipes(recipes_lua, recipes2_lua)

        # 2) aliases
        for name in self.recipes.keys():
            self.aliases[name.lower()] = name
            self.aliases[name.replace("_", "").lower()] = name

        # 3) filter defs + membership
        self.filter_defs = parse_filter_defs(recipes_filter_lua)
        self.filter_order = _parse_filter_order(recipes_filter_lua)
        filter_lists = _parse_filter_recipe_lists(recipes_filter_lua)
        call_bindings = _parse_filter_bindings_by_calls(recipes_filter_lua)

        # membership: recipe -> filters
        membership: Dict[str, Set[str]] = {name: set(map(str.upper, (self.recipes[name].get("filters") or []))) for name in self.recipes.keys()}

        # from `CRAFTING_FILTERS.X.recipes = {...}`
        for flt, rlist in filter_lists.items():
            for r in rlist:
                if r in membership:
                    membership[r].add(flt)

        # from AddRecipeToFilter(s)
        for r, fs in call_bindings.items():
            if r in membership:
                for f in fs:
                    membership[r].add(f.upper())

        # 4) finalize per recipe: filters, tab
        for name, rec in self.recipes.items():
            fset = membership.get(name, set())
            # include whatever was already present
            rec["filters"] = sorted(_dedup_preserve([f.upper() for f in fset if f]))

            # choose tab: first non-special in defs order
            chosen: Optional[str] = None
            for f in self.filter_order:
                if f in fset and f not in self._SPECIAL_FILTERS:
                    chosen = f
                    break
            if chosen is None:
                # fallback: any in order
                for f in self.filter_order:
                    if f in fset:
                        chosen = f
                        break
            rec["tab"] = chosen or rec.get("tab") or "UNKNOWN"

            # normalize builder_tags again (after merges)
            if rec.get("builder_tag"):
                rec["builder_tags"] = _dedup_preserve(list(rec.get("builder_tags") or []) + [str(rec["builder_tag"])])
            else:
                rec["builder_tags"] = _dedup_preserve(list(rec.get("builder_tags") or []))

        # 5) build indices
        # by_filter / by_tab
        for name, rec in self.recipes.items():
            for f in rec.get("filters", []) or []:
                self.by_filter[str(f).upper()].append(name)

            t = str(rec.get("tab") or "UNKNOWN").upper()
            self.by_tab[t].append(name)

            # by_tech
            tech = str(rec.get("tech") or "UNKNOWN")
            if tech.upper().startswith("TECH."):
                tech = tech.split(".", 1)[1]
            self.by_tech[tech.upper()].append(name)

            # by_builder_tag(s)
            for bt in rec.get("builder_tags") or []:
                if bt:
                    self.by_builder_tag[str(bt).lower()].append(name)

            # by_ingredient
            for ing in rec.get("ingredients") or []:
                it = ing.get("item")
                if it:
                    self.by_ingredient[str(it).lower()].append(name)

        # sort & unique
        for mp in (self.by_filter, self.by_tab, self.by_tech, self.by_builder_tag, self.by_ingredient):
            for k in list(mp.keys()):
                mp[k] = sorted(set(mp[k]))

        # tab order: filter_order excluding specials
        self.tab_order = [f for f in self.filter_order if f and f not in self._SPECIAL_FILTERS]

    # -----------------
    # Public query API
    # -----------------

    def __len__(self) -> int:
        return len(self.recipes)

    def get(self, query_name: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        if not query_name:
            return None, None
        q = query_name.strip().lower()
        canonical = self.aliases.get(q) or self.aliases.get(q.replace("_", ""))
        if not canonical:
            return None, None
        return canonical, self.recipes.get(canonical)

    def list_tabs(self) -> List[str]:
        return list(self.tab_order)

    def list_filters(self) -> List[str]:
        return list(self.filter_order)

    def list_by_tab(self, tab: str) -> List[str]:
        key = (tab or "").strip().upper()
        # allow TECH/RECIPETABS raw
        if key.startswith("RECIPETABS."):
            key = key.split(".", 1)[1]
        return list(self.by_tab.get(key, []))

    def list_by_filter(self, flt: str) -> List[str]:
        key = (flt or "").strip().upper()
        if key.startswith("CRAFTING_FILTERS."):
            key = key.split(".", 1)[1]
        return list(self.by_filter.get(key, []))

    def list_by_builder_tag(self, tag: str) -> List[str]:
        key = (tag or "").strip().lower()
        return list(self.by_builder_tag.get(key, []))

    def list_by_tech(self, tech: str) -> List[str]:
        t = (tech or "").strip()
        if t.upper().startswith("TECH."):
            t = t.split(".", 1)[1]
        return list(self.by_tech.get(t.upper(), []))

    def list_by_ingredient(self, item: str) -> List[str]:
        key = (item or "").strip().lower()
        return list(self.by_ingredient.get(key, []))

    # -----------------
    # Craft planner (M2)
    # -----------------

    def missing_for(self, recipe_name: str, inventory: Mapping[str, float]) -> List[Dict[str, Any]]:
        """Return missing ingredients for a recipe under a given inventory.

        Inventory is a mapping item->count (int/float).

        If an ingredient has non-numeric amount (amount_num is None), it is returned
        as missing with reason="unresolved_amount".
        """
        _, rec = self.get(recipe_name)
        if not rec:
            return []

        inv = {str(k).lower(): float(v) for k, v in (inventory or {}).items()}

        missing: List[Dict[str, Any]] = []
        for ing in rec.get("ingredients") or []:
            item = str(ing.get("item") or "").lower()
            if not item:
                continue
            need_num = ing.get("amount_num")
            need_expr = ing.get("amount")
            have = inv.get(item, 0.0)

            if need_num is None:
                missing.append({"item": item, "need": need_expr, "have": have, "reason": "unresolved_amount"})
                continue

            if have + 1e-9 < float(need_num):
                missing.append({"item": item, "need": need_num, "have": have, "reason": "insufficient"})

        return missing

    def craftable(
        self,
        inventory: Mapping[str, float],
        *,
        builder_tag: Optional[str] = None,
        strict: bool = True,
    ) -> List[str]:
        """List craftable recipes.

        - builder_tag: if set, only recipes that are not character-locked or match builder_tag.
        - strict: if True, recipes with unresolved ingredient amounts are excluded.
        """
        inv = {str(k).lower(): float(v) for k, v in (inventory or {}).items()}
        bt = builder_tag.strip().lower() if builder_tag else None

        out: List[str] = []
        for name, rec in self.recipes.items():
            # builder constraints
            if bt:
                tags = [str(x).lower() for x in (rec.get("builder_tags") or [])]
                if tags and bt not in tags:
                    continue

            miss = self.missing_for(name, inv)
            if not miss:
                out.append(name)
            else:
                if strict:
                    continue
                # if not strict, allow unresolved-only
                if all(m.get("reason") == "unresolved_amount" for m in miss):
                    out.append(name)

        return sorted(out)

    # -----------------
    # Serialization (M2)
    # -----------------

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable snapshot (do not include derived indices)."""
        return {
            "schema": 1,
            "recipes": self.recipes,
            "aliases": self.aliases,
            "filter_defs": self.filter_defs,
            "filter_order": self.filter_order,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CraftRecipeDB":
        """Load from `to_dict()` output."""
        obj = cls(recipes_lua="", recipes2_lua="", recipes_filter_lua="")

        obj.recipes = {str(k): v for k, v in (data.get("recipes") or {}).items()}
        obj.aliases = {str(k): str(v) for k, v in (data.get("aliases") or {}).items()}
        obj.filter_defs = list(data.get("filter_defs") or [])
        obj.filter_order = [str(x).upper() for x in (data.get("filter_order") or [])]
        obj.tab_order = [f for f in obj.filter_order if f and f not in obj._SPECIAL_FILTERS]

        # rebuild indices
        obj.by_tab = defaultdict(list)
        obj.by_filter = defaultdict(list)
        obj.by_tech = defaultdict(list)
        obj.by_builder_tag = defaultdict(list)
        obj.by_ingredient = defaultdict(list)

        for name, rec in obj.recipes.items():
            for f in rec.get("filters", []) or []:
                obj.by_filter[str(f).upper()].append(name)
            t = str(rec.get("tab") or "UNKNOWN").upper()
            obj.by_tab[t].append(name)

            tech = str(rec.get("tech") or "UNKNOWN")
            if tech.upper().startswith("TECH."):
                tech = tech.split(".", 1)[1]
            obj.by_tech[tech.upper()].append(name)

            for bt in rec.get("builder_tags") or []:
                if bt:
                    obj.by_builder_tag[str(bt).lower()].append(name)

            for ing in rec.get("ingredients") or []:
                it = ing.get("item")
                if it:
                    obj.by_ingredient[str(it).lower()].append(name)

        for mp in (obj.by_filter, obj.by_tab, obj.by_tech, obj.by_builder_tag, obj.by_ingredient):
            for k in list(mp.keys()):
                mp[k] = sorted(set(mp[k]))

        return obj

    def dumps(self, *, indent: int = 2, ensure_ascii: bool = False) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent)

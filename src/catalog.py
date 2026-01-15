# -*- coding: utf-8 -*-
"""src/catalog.py

Catalog = stable, UI-agnostic, versioned index for downstream apps.

Motivation (M2)
- Parsing Lua on every query is wasteful for GUI/Web.
- A persisted, versioned catalog becomes the contract between...

Contents (v1)
- Crafting recipes: derived from `CraftRecipeDB`.
- Cooking recipes: extracted by `CookingRecipeAnalyzer`.
- Presentation assets mapping (optional):
  - Display names from `STRINGS.NAMES` (scripts/strings.lua)
  - Icon references from `Asset("ATLAS", ...)` / `Asset("IMAGE", ...)` (scripts/prefabs/*.lua)

The `assets` section is a *presentation-layer mapping*:
- key: internal id (e.g. "armor_wood")
- value: { name?, atlas?, image? }

This module intentionally only depends on core modules.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set, Tuple

from analyzer import LuaCallExtractor, find_matching, parse_lua_string, parse_lua_table
from craft_recipes import CraftRecipeDB


SCHEMA_VERSION = 1


_ID_RE = re.compile(r"^[a-z0-9_]+$")
_PREFAB_PREFIX = "scripts/prefabs/"



def _sha256_12_file(path: Path, chunk_size: int = 1024 * 1024) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()[:12]
    except Exception:
        return None


def _is_simple_id(s: str) -> bool:
    return bool(s) and bool(_ID_RE.match(s))

def _alt_id(iid: str) -> Optional[str]:
    """Best-effort alternative id for mapping.

    Many game ids have both forms in the wild (with/without underscores).
    This helper enables "armor_wood" -> "armorwood" fallback.
    """
    if not iid:
        return None
    if "_" not in iid:
        return None
    alt = iid.replace("_", "")
    return alt if alt and alt != iid else None



def _iter_craft_ids(craft: CraftRecipeDB) -> Iterable[str]:
    # recipe id itself
    for name, rec in (getattr(craft, "recipes", {}) or {}).items():
        if isinstance(name, str) and _is_simple_id(name):
            yield name

        if not isinstance(rec, dict):
            continue

        prod = rec.get("product")
        if isinstance(prod, str) and _is_simple_id(prod):
            yield prod

        for ing in rec.get("ingredients", []) or []:
            if not isinstance(ing, dict):
                continue
            item = ing.get("item")
            if isinstance(item, str) and _is_simple_id(item):
                yield item


def _iter_cooking_ids(cooking: Dict[str, Any]) -> Iterable[str]:
    for name, raw in (cooking or {}).items():
        if isinstance(name, str) and _is_simple_id(name):
            yield name
        if not isinstance(raw, dict):
            continue

        ci = raw.get("card_ingredients") or []
        if isinstance(ci, list):
            for row in ci:
                if not isinstance(row, (list, tuple)) or not row:
                    continue
                item = row[0]
                if isinstance(item, str) and _is_simple_id(item):
                    yield item


def _extract_strings_names(engine: Any) -> Dict[str, str]:
    """Extract STRINGS.NAMES mapping from scripts/strings.lua.

    Notes
    - `scripts/strings.lua` contains a giant `STRINGS = {...}` table.
    - Parsing the entire STRINGS table is expensive and can hit edge-cases.
      We instead locate and parse the `NAMES = { ... }` subtable directly.

    Output keys are normalized to lowercase ids.
    """
    src = (
        engine.read_file("scripts/strings.lua")
        or engine.read_file("strings.lua")
        or ""
    )
    if not src:
        return {}

    # Locate STRINGS = { ... }
    m = re.search(r"\bSTRINGS\s*=\s*\{", src)
    if not m:
        return {}
    strings_open = src.find("{", m.end() - 1)
    if strings_open < 0:
        return {}
    strings_close = find_matching(src, strings_open, "{", "}")
    if strings_close is None:
        return {}

    # Inside STRINGS block, locate the first top-level `NAMES = { ... }`
    block = src[strings_open: strings_close + 1]
    m2 = re.search(r"(?<![A-Za-z0-9_])NAMES\s*=\s*\{", block)
    if not m2:
        return {}

    names_open = strings_open + m2.end() - 1
    names_close = find_matching(src, names_open, "{", "}")
    if names_close is None:
        return {}

    inner = src[names_open + 1 : names_close]
    try:
        names_tbl = parse_lua_table(inner)
    except Exception:
        return {}

    out: Dict[str, str] = {}
    for k, v in (names_tbl.map or {}).items():
        if not isinstance(k, str):
            continue
        if not isinstance(v, str):
            continue
        kid = k.strip().lower()
        if not _is_simple_id(kid):
            continue
        out[kid] = v
    return out


def _score_asset_path(path: str, *, kind: str) -> Tuple[int, int, int]:
    """Scoring heuristic for selecting the 'best' atlas/image path.

    Higher tuple is better.
    """
    p = (path or "").lower()
    inv = 1 if "inventory" in p else 0
    # Kind-specific extension preference
    if kind == "ATLAS":
        ext = 2 if p.endswith(".xml") else 0
    else:
        ext = 2 if p.endswith(".tex") else 0
    # Prefer shorter paths (less specific penalty)
    short = max(0, 300 - len(p))
    return (inv, ext, short)


def _select_best(paths: Iterable[str], *, kind: str) -> Optional[str]:
    cand = [str(x) for x in paths if x]
    if not cand:
        return None
    cand.sort(key=lambda p: _score_asset_path(p, kind=kind), reverse=True)
    return cand[0]


def _extract_prefab_assets(engine: Any) -> Dict[str, Dict[str, str]]:
    """Extract prefab -> (atlas/image) mapping from prefab lua files.

    Strategy
    - For each scripts/prefabs/*.lua:
      - collect all Prefab("name", ...) calls => prefab names in this file
      - collect Asset("ATLAS", path) / Asset("IMAGE", path) calls
      - assign selected atlas/image to each prefab name

    Output keys are prefab ids (as-is in Prefab call), typically lowercase.
    """
    out: Dict[str, Dict[str, str]] = {}

    files = getattr(engine, "file_list", []) or []
    for path in files:
        if not isinstance(path, str):
            continue
        if not path.startswith(_PREFAB_PREFIX) or not path.endswith(".lua"):
            continue

        content = engine.read_file(path) or ""
        if not content:
            continue

        # Fast prefilter
        if "Asset" not in content:
            continue

        extractor = LuaCallExtractor(content)

        prefab_names: Set[str] = set()
        for call in extractor.iter_calls("Prefab", include_member_calls=False):
            if not call.arg_list:
                continue
            nm = parse_lua_string(call.arg_list[0])
            if isinstance(nm, str) and nm:
                prefab_names.add(nm)

        atlas_paths = []
        image_paths = []
        for call in extractor.iter_calls("Asset", include_member_calls=False):
            if len(call.arg_list) < 2:
                continue
            t = parse_lua_string(call.arg_list[0])
            p = parse_lua_string(call.arg_list[1])
            if not isinstance(t, str) or not isinstance(p, str):
                continue
            if t == "ATLAS":
                atlas_paths.append(p)
            elif t == "IMAGE":
                image_paths.append(p)

        if not atlas_paths and not image_paths:
            continue

        atlas = _select_best(atlas_paths, kind="ATLAS")
        image = _select_best(image_paths, kind="IMAGE")
        if not atlas and not image:
            continue

        # If Prefab(...) is not present, fall back to basename as a best-effort key.
        if not prefab_names:
            base = path.split("/")[-1].rsplit(".lua", 1)[0]
            if base:
                prefab_names.add(base)

        for nm in prefab_names:
            entry: Dict[str, str] = {}
            if atlas:
                entry["atlas"] = atlas
            if image:
                entry["image"] = image
            # Keep a light provenance for debugging (not used by UI).
            entry["prefab_file"] = path

            out[nm] = entry

    return out


def build_presentation_assets(engine: Any, craft: CraftRecipeDB, cooking: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Build presentation mapping for ids referenced by catalog.

    The mapping is intentionally *lossy*:
    - It only includes ids that appear in craft/cooking sections.
    - It only stores a small set of display-oriented fields.
    """
    referenced: Set[str] = set()
    referenced.update(_iter_craft_ids(craft))
    referenced.update(_iter_cooking_ids(cooking))

    # Extract global name + prefab asset maps (these can be large).
    names = _extract_strings_names(engine)
    prefab_assets = _extract_prefab_assets(engine)

    out: Dict[str, Dict[str, str]] = {}

    for iid in sorted(referenced):
        entry: Dict[str, str] = {}

        nm = names.get(iid)
        if not nm:
            alt = _alt_id(iid)
            nm = names.get(alt) if alt else None
        if nm:
            entry["name"] = nm

        pa = prefab_assets.get(iid)
        if not pa:
            alt = _alt_id(iid)
            pa = prefab_assets.get(alt) if alt else None
        if pa:
            if pa.get("atlas"):
                entry["atlas"] = pa["atlas"]
            if pa.get("image"):
                entry["image"] = pa["image"]
            # (optional) keep provenance if present
            if pa.get("prefab_file"):
                entry["prefab_file"] = pa["prefab_file"]

        if entry:
            out[iid] = entry

    return out


@dataclass
class WagstaffCatalog:
    """A versioned catalog.

    Keep it JSON-first to make it easy to consume from:
    - CLI
    - Web API
    - GUI
    - Static wiki builders
    """

    schema_version: int
    meta: Dict[str, Any]
    craft: CraftRecipeDB
    cooking: Dict[str, Any]
    assets: Dict[str, Dict[str, str]]

    # ------------------------------
    # Build / Load / Save
    # ------------------------------

    @classmethod
    def build(cls, *, engine: Any) -> "WagstaffCatalog":
        """Build a catalog from a WagstaffEngine."""
        craft_db = engine.recipes
        if craft_db is None:
            raise ValueError("engine.recipes is None; initialize engine with load_db=True")

        meta: Dict[str, Any] = {
            "schema": SCHEMA_VERSION,
            "engine_mode": getattr(engine, "mode", ""),
            "scripts_file_count": len(getattr(engine, "file_list", []) or []),
        }

        # signature
        sig = None
        try:
            if getattr(engine, "mode", "") == "zip":
                zf = getattr(engine, "source", None)
                zpath = getattr(zf, "filename", None)
                if zpath:
                    sig = _sha256_12_file(Path(zpath))
                    meta["scripts_zip"] = str(zpath)
            elif getattr(engine, "mode", "") == "folder":
                meta["scripts_dir"] = str(getattr(engine, "source", ""))
        except Exception:
            pass
        if sig:
            meta["scripts_sha256_12"] = sig

        cooking = getattr(engine, "cooking_recipes", {}) or {}

        # Presentation assets mapping (optional / best-effort)
        try:
            assets = build_presentation_assets(engine, craft_db, cooking)
            meta["assets_count"] = len(assets)
        except Exception:
            assets = {}

        return cls(
            schema_version=SCHEMA_VERSION,
            meta=meta,
            craft=craft_db,
            cooking=cooking,
            assets=assets,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": int(self.schema_version),
            "meta": self.meta,
            "craft": self.craft.to_dict(),
            "cooking": self.cooking,
            "assets": self.assets or {},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WagstaffCatalog":
        schema = int(d.get("schema_version") or d.get("schema") or 0)
        if schema != SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema_version: {schema} (expected {SCHEMA_VERSION})")
        meta = d.get("meta") or {}
        craft = CraftRecipeDB.from_dict(d.get("craft") or {})
        cooking = d.get("cooking") or {}
        assets = d.get("assets") or {}
        if not isinstance(assets, dict):
            assets = {}
        # ensure {id: {..}} shape
        norm_assets: Dict[str, Dict[str, str]] = {}
        for k, v in assets.items():
            if not isinstance(k, str) or not k:
                continue
            if not isinstance(v, dict):
                continue
            vv: Dict[str, str] = {}
            for kk in ("name", "atlas", "image", "prefab_file"):
                if kk in v and isinstance(v.get(kk), str) and v.get(kk):
                    vv[kk] = str(v.get(kk))
            if vv:
                norm_assets[k] = vv

        return cls(schema_version=schema, meta=meta, craft=craft, cooking=cooking, assets=norm_assets)

    def save_json(self, path: str | Path, *, indent: int = 2) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=indent), encoding="utf-8")
        return p

    @classmethod
    def load_json(cls, path: str | Path) -> "WagstaffCatalog":
        p = Path(path)
        d = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            raise ValueError("Catalog JSON must be a dict")
        return cls.from_dict(d)

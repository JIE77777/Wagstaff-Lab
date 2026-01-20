#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WagstaffEngine (core)

This module is intentionally UI-agnostic.

Responsibilities
- Mount DST scripts source (zip or folder) with a consistent "scripts/..." namespace.
- Provide fast `read_file()` + `find_file()` primitives.
- Load small, stable databases:
  - TuningResolver (scripts/tuning.lua)
  - CraftRecipeDB (scripts/recipes.lua + scripts/recipes2.lua + scripts/recipes_filter.lua)
  - CookingRecipeAnalyzer (scripts/preparedfoods.lua + scripts/prefabs/preparedfoods.lua)
  - CookingIngredientAnalyzer (scripts/ingredients.lua + scripts/cooking.lua)

Design notes
- Engine must be usable by CLI, GUI, and Web layers.
- Avoid hard dependency on Rich (it is optional). Use `silent=True` to suppress logs.
"""

from __future__ import annotations

import logging
import os
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Optional project config (exists in repo under core/config/loader.py)
try:
    from core.config import wagstaff_config  # type: ignore
except Exception:  # pragma: no cover
    wagstaff_config = None  # type: ignore

from core.parsers import (
    CookingIngredientAnalyzer,
    CookingRecipeAnalyzer,
    LuaAnalyzer,
    TuningResolver,
    parse_oceanfish_ingredients,
)
from core.craft_recipes import CraftRecipeDB

logger = logging.getLogger(__name__)


def _expanduser(p: Optional[str]) -> Optional[str]:
    return os.path.expanduser(p) if p else None


def _merge_cooking_ingredients(base: Dict[str, Dict], extra: Dict[str, Dict]) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for iid, row in (base or {}).items():
        if not isinstance(row, dict):
            continue
        merged = dict(row)
        merged.setdefault("id", iid)
        out[str(iid)] = merged

    for iid, row in (extra or {}).items():
        if not isinstance(row, dict):
            continue
        key = str(iid)
        if key not in out:
            merged = dict(row)
            merged.setdefault("id", key)
            out[key] = merged
            continue

        cur = dict(out[key])
        cur.setdefault("id", key)

        sources: List[str] = []
        for src in cur.get("sources") or []:
            if src not in sources:
                sources.append(src)
        for src in row.get("sources") or []:
            if src not in sources:
                sources.append(src)
        if sources:
            cur["sources"] = sources

        tags = dict(cur.get("tags") or {})
        for tag, val in (row.get("tags") or {}).items():
            if tag not in tags or tags.get(tag) in (None, 0, 0.0):
                tags[tag] = val
        if tags:
            cur["tags"] = tags

        tags_expr = dict(cur.get("tags_expr") or {})
        for tag, val in (row.get("tags_expr") or {}).items():
            if tag not in tags_expr:
                tags_expr[tag] = val
        if tags_expr:
            cur["tags_expr"] = tags_expr

        for field in ("name", "atlas", "image", "prefab", "foodtype"):
            if field not in cur and field in row:
                cur[field] = row[field]

        out[key] = cur

    return out


class WagstaffEngine:
    """Main entry used by CLI / devtools / GUI / Web.

    Parameters
    - load_db: load tuning + recipe DBs (and cooking recipes).
    - silent: suppress all logs.
    - dst_root: optional DST root path (overrides config).
    - scripts_zip: optional scripts zip path (highest priority).
    - scripts_dir: optional scripts folder path (highest priority for folder mode).
    - prefer_local_bundles: search project-root bundle drops first.
    """

    def __init__(
        self,
        load_db: bool = True,
        silent: bool = False,
        *,
        dst_root: Optional[str] = None,
        scripts_zip: Optional[str] = None,
        scripts_dir: Optional[str] = None,
        prefer_local_bundles: bool = True,
        encoding: str = "utf-8",
    ):
        self.encoding = encoding
        self.silent = bool(silent)

        self.mode: str = ""  # 'zip' | 'folder'
        self.source: object = None  # ZipFile or folder path (str)
        self.file_list: List[str] = []

        # basename index for fast fuzzy find
        self._basename_index: Dict[str, List[str]] = {}

        self.tuning: Optional[TuningResolver] = None
        self.recipes: Optional[CraftRecipeDB] = None
        self.cooking_recipes: Dict[str, Dict] = {}
        self.cooking_ingredients: Dict[str, Dict] = {}

        self._init_source(
            dst_root=dst_root,
            scripts_zip=scripts_zip,
            scripts_dir=scripts_dir,
            prefer_local_bundles=prefer_local_bundles,
        )
        self._build_basename_index()

        if load_db:
            self._init_databases()

    # --------------------------------------------------------
    # Context manager
    # --------------------------------------------------------

    def __enter__(self) -> "WagstaffEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # --------------------------------------------------------
    # Source mounting
    # --------------------------------------------------------

    def _project_root(self) -> Path:
        """Best-effort repo root.

        - Prefer wagstaff_config.project_root when available.
        - Fallback to core/.. (engine.py is expected under core/).
        """
        if wagstaff_config is not None and hasattr(wagstaff_config, "project_root"):
            try:
                return Path(str(wagstaff_config.project_root)).resolve()
            except Exception:
                pass
        # engine.py is usually core/engine.py
        return Path(__file__).resolve().parent.parent

    def _detect_candidates(self, dst_root: Optional[str], prefer_local_bundles: bool) -> Tuple[List[str], List[str]]:
        """Return (zip_candidates, dir_candidates)."""
        pr = self._project_root()

        dst_root = _expanduser(dst_root)
        if dst_root is None and wagstaff_config is not None:
            try:
                dst_root = _expanduser(wagstaff_config.get("PATHS", "DST_ROOT"))
            except Exception:
                dst_root = None

        zip_candidates: List[str] = []
        dir_candidates: List[str] = []

        # Prefer local bundle drops for faster iteration
        if prefer_local_bundles:
            zip_candidates += [
                str(pr / "scripts-no-language-pac.zip"),
                str(pr / "scripts_no_language.zip"),
                str(pr / "scripts.zip"),
                str(pr / "data" / "databundles" / "scripts.zip"),
            ]
            dir_candidates += [
                str(pr / "scripts"),
            ]

        if dst_root:
            zip_candidates += [
                os.path.join(dst_root, "data", "databundles", "scripts.zip"),
                os.path.join(dst_root, "data", "databundles", "scripts_no_language.zip"),
            ]
            dir_candidates += [
                os.path.join(dst_root, "data", "scripts"),
            ]

        return zip_candidates, dir_candidates

    def _log(self, msg: str) -> None:
        if not self.silent:
            logger.info(msg)

    def _init_source(
        self,
        *,
        dst_root: Optional[str],
        scripts_zip: Optional[str],
        scripts_dir: Optional[str],
        prefer_local_bundles: bool,
    ) -> None:
        # explicit overrides
        if scripts_zip:
            zp = _expanduser(scripts_zip)
            if zp and os.path.exists(zp):
                self.mode = "zip"
                self.source = zipfile.ZipFile(zp, "r")
                self.file_list = list(getattr(self.source, "namelist")())
                self._log(f"Mounted scripts zip: {zp}")
                return

        if scripts_dir:
            dp = _expanduser(scripts_dir)
            if dp and os.path.isdir(dp):
                self.mode = "folder"
                self.source = dp
                self.file_list = self._walk_folder(dp)
                self._log(f"Mounted scripts folder: {dp}")
                return

        zip_candidates, dir_candidates = self._detect_candidates(dst_root, prefer_local_bundles)

        for zp in zip_candidates:
            if zp and os.path.exists(zp):
                self.mode = "zip"
                self.source = zipfile.ZipFile(zp, "r")
                self.file_list = list(getattr(self.source, "namelist")())
                self._log(f"Mounted scripts zip: {zp}")
                return

        for dp in dir_candidates:
            if dp and os.path.isdir(dp):
                self.mode = "folder"
                self.source = dp
                self.file_list = self._walk_folder(dp)
                self._log(f"Mounted scripts folder: {dp}")
                return

        raise FileNotFoundError("Cannot find scripts source (zip or folder).")

    def _walk_folder(self, folder: str) -> List[str]:
        folder = os.path.abspath(folder)
        out: List[str] = []
        for root, _, files in os.walk(folder):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, folder).replace("\\", "/")
                out.append("scripts/" + rel)  # normalize namespace
        return out

    def _build_basename_index(self) -> None:
        mp: Dict[str, List[str]] = {}
        for p in self.file_list:
            if not p.endswith(".lua"):
                continue
            base = os.path.basename(p)
            key = base.replace(".lua", "").replace("_", "").lower()
            mp.setdefault(key, []).append(p)
        self._basename_index = mp

    # --------------------------------------------------------
    # IO
    # --------------------------------------------------------

    def _normalize_path_candidates(self, path: str) -> List[str]:
        p = (path or "").replace("\\", "/").lstrip("/")
        if not p:
            return []
        if p.startswith("scripts/"):
            return [p, p.replace("scripts/", "", 1)]
        return [p, "scripts/" + p]

    @lru_cache(maxsize=4096)
    def read_file(self, path: str) -> Optional[str]:
        """Read a UTF-8 text file from the mounted source.

        Accepts paths with or without the "scripts/" prefix.
        Returns None if not found.
        """
        candidates = self._normalize_path_candidates(path)
        if not candidates:
            return None

        try:
            if self.mode == "zip":
                zf: zipfile.ZipFile = self.source  # type: ignore[assignment]
                for p in candidates:
                    if p in self.file_list:
                        return zf.read(p).decode(self.encoding, errors="replace")
                return None

            # folder
            base: str = self.source  # type: ignore[assignment]
            for p in candidates:
                real = os.path.join(base, p.replace("scripts/", "", 1))
                if os.path.exists(real):
                    with open(real, "r", encoding=self.encoding, errors="replace") as f:
                        return f.read()
        except Exception:
            return None

        return None

    def find_file(self, name: str, fuzzy: bool = True) -> Optional[str]:
        """Find a file by short name.

        Examples
        - armorwood -> scripts/prefabs/armorwood.lua (or armor_wood.lua)
        - prefabs/armorwood.lua -> scripts/prefabs/armorwood.lua

        Returns a path in the normalized namespace (usually "scripts/...").
        """
        if not name:
            return None
        q = name.replace("\\", "/").strip()
        if not q:
            return None

        # direct hit if user passed a path
        for cand in self._normalize_path_candidates(q):
            if cand in self.file_list:
                return cand

        base = q.replace(".lua", "")
        candidates = [
            f"scripts/prefabs/{base}.lua",
            f"scripts/{base}.lua",
            f"scripts/{base}",
        ]
        for c in candidates:
            if c in self.file_list:
                return c

        if not fuzzy:
            return None

        key = os.path.basename(base).replace("_", "").lower()
        hits = self._basename_index.get(key)
        if hits:
            # prefer prefabs if ambiguous
            if len(hits) == 1:
                return hits[0]
            pref = [h for h in hits if h.startswith("scripts/prefabs/")]
            if len(pref) == 1:
                return pref[0]
            return hits[0]

        # final fallback: scan
        target = key
        for fname in self.file_list:
            if not fname.endswith(".lua"):
                continue
            b = os.path.basename(fname).replace(".lua", "").replace("_", "").lower()
            if b == target:
                return fname

        return None

    def close(self) -> None:
        if self.mode == "zip" and self.source is not None:
            try:
                self.source.close()  # type: ignore[attr-defined]
            except Exception:
                pass

    # --------------------------------------------------------
    # DB initialization
    # --------------------------------------------------------

    def _init_databases(self) -> None:
        self._log("Loading tuning / crafting / cooking databases...")

        t_content = self.read_file("scripts/tuning.lua") or self.read_file("tuning.lua") or ""
        self.tuning = TuningResolver(t_content)

        r1 = self.read_file("scripts/recipes.lua") or self.read_file("recipes.lua") or ""
        r2 = self.read_file("scripts/recipes2.lua") or self.read_file("recipes2.lua") or ""
        rf = self.read_file("scripts/recipes_filter.lua") or self.read_file("recipes_filter.lua") or ""
        self.recipes = CraftRecipeDB(recipes_lua=r1, recipes2_lua=r2, recipes_filter_lua=rf)

        # cooking recipes (optional)
        food_src = self.read_file("scripts/preparedfoods.lua") or ""
        if food_src:
            self.cooking_recipes.update(CookingRecipeAnalyzer(food_src).recipes)

        food_prefab_src = self.read_file("scripts/prefabs/preparedfoods.lua") or ""
        if food_prefab_src:
            # prefab file often contains the same table; merge (prefab wins)
            self.cooking_recipes.update(CookingRecipeAnalyzer(food_prefab_src).recipes)

        ing_path = "scripts/ingredients.lua"
        ing_src = self.read_file(ing_path)
        if not ing_src:
            ing_path = "ingredients.lua"
            ing_src = self.read_file(ing_path)
        if ing_src:
            self.cooking_ingredients = CookingIngredientAnalyzer(ing_src, source=ing_path).ingredients

        cook_path = "scripts/cooking.lua"
        cook_src = self.read_file(cook_path)
        if not cook_src:
            cook_path = "cooking.lua"
            cook_src = self.read_file(cook_path)
        if cook_src:
            extra = CookingIngredientAnalyzer(cook_src, source=cook_path).ingredients
            if extra:
                self.cooking_ingredients = _merge_cooking_ingredients(self.cooking_ingredients, extra)

        fish_path = "scripts/prefabs/oceanfishdef.lua"
        fish_src = self.read_file(fish_path)
        if not fish_src:
            fish_path = "prefabs/oceanfishdef.lua"
            fish_src = self.read_file(fish_path)
        if fish_src:
            fish_extra = parse_oceanfish_ingredients(fish_src, source=fish_path)
            if fish_extra:
                self.cooking_ingredients = _merge_cooking_ingredients(self.cooking_ingredients, fish_extra)

    # --------------------------------------------------------
    # High-level helpers
    # --------------------------------------------------------

    def analyze_prefab(self, item_name: str) -> Optional[Dict]:
        """High-level prefab analysis (LuaAnalyzer + tuning enrichment)."""
        path = self.find_file(item_name, fuzzy=True)
        if not path:
            return None

        content = self.read_file(path)
        if not content:
            return None

        data = LuaAnalyzer(content, path=path).get_report()

        if self.tuning:
            for comp in data.get("components", []) or []:
                comp["properties"] = [self.tuning.enrich(p) for p in comp.get("properties", [])]
                comp["methods"] = [self.tuning.enrich(m) for m in comp.get("methods", [])]

        return data

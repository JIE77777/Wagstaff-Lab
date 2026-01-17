#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DST raw data coverage scan.

Outputs:
- data/reports/dst_raw_coverage.md
- data/reports/dst_raw_coverage.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.analyzer import LuaCallExtractor, parse_lua_string, strip_lua_comments  # type: ignore
from core.indexers.shared import _extract_strings_names  # type: ignore
from core.engine import WagstaffEngine  # type: ignore

try:
    from core.utils import wagstaff_config  # type: ignore
except Exception:
    wagstaff_config = None  # type: ignore

REPORT_DIR = PROJECT_ROOT / "data" / "reports"
_ID_RE = re.compile(r"^[a-z0-9_]+$")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _norm_id(val: str) -> str:
    return str(val or "").replace("_", "").lower()


def _scan_inventory_icons(dst_root: Path) -> Tuple[Set[str], List[str]]:
    icons: Set[str] = set()
    xmls: List[str] = []
    data_dir = dst_root / "data"
    img_dir = data_dir / "images"
    bundle_zip = data_dir / "databundles" / "images.zip"

    def _parse_xml_bytes(label: str, data: bytes) -> None:
        try:
            root = ET.fromstring(data)
        except Exception:
            return
        for el in root.findall(".//Element"):
            name = el.attrib.get("name")
            if name:
                n = name.strip().lower()
                if n.endswith(".tex"):
                    n = n[:-4]
                if _ID_RE.match(n):
                    icons.add(n)
        if label and label not in xmls:
            xmls.append(label)

    if bundle_zip.exists():
        try:
            import zipfile

            with zipfile.ZipFile(bundle_zip, "r") as zf:
                for name in zf.namelist():
                    base = os.path.basename(name)
                    if not base.startswith("inventoryimages") or not base.endswith(".xml"):
                        continue
                    try:
                        _parse_xml_bytes(
                            (bundle_zip.relative_to(dst_root).as_posix() + ":" + name),
                            zf.read(name),
                        )
                    except Exception:
                        continue
        except Exception:
            pass

    if img_dir.is_dir():
        for p in sorted(img_dir.glob("inventoryimages*.xml")):
            try:
                _parse_xml_bytes(p.relative_to(dst_root).as_posix(), p.read_bytes())
            except Exception:
                continue
    return icons, xmls


def _scan_data_dir(
    dst_root: Path,
    *,
    top_n_ext: int = 20,
    top_n_files: int = 30,
    include_files: bool = False,
    max_files: int = 0,
) -> Dict[str, Any]:
    data_dir = dst_root / "data"
    if not data_dir.is_dir():
        return {}

    top_dirs: Dict[str, Dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})
    ext_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})
    largest: List[Tuple[int, str]] = []
    file_list: List[Dict[str, Any]] = []
    total_files = 0
    total_bytes = 0

    def _push_largest(size: int, rel: str) -> None:
        nonlocal largest
        largest.append((size, rel))
        largest.sort(key=lambda x: x[0], reverse=True)
        if len(largest) > top_n_files:
            largest = largest[:top_n_files]

    for root, _, files in os.walk(data_dir):
        for name in files:
            full = Path(root) / name
            try:
                st = full.stat()
            except Exception:
                continue
            size = int(st.st_size)
            rel = full.relative_to(data_dir).as_posix()
            total_files += 1
            total_bytes += size

            parts = rel.split("/")
            top = parts[0] if parts else "[root]"
            top_dirs[top]["files"] += 1
            top_dirs[top]["bytes"] += size

            ext = Path(name).suffix.lower() or "<no_ext>"
            ext_counts[ext]["files"] += 1
            ext_counts[ext]["bytes"] += size

            if include_files:
                file_list.append(
                    {
                        "path": rel,
                        "bytes": size,
                        "ext": ext,
                        "dir": top,
                    }
                )

            _push_largest(size, rel)

    top_dirs_list = [{"dir": k, "files": v["files"], "bytes": v["bytes"]} for k, v in top_dirs.items()]
    top_dirs_list.sort(key=lambda x: x["files"], reverse=True)

    ext_list = [{"ext": k, "files": v["files"], "bytes": v["bytes"]} for k, v in ext_counts.items()]
    ext_list.sort(key=lambda x: x["files"], reverse=True)

    if include_files:
        file_list.sort(key=lambda x: x["path"])
        if max_files and len(file_list) > max_files:
            file_list = file_list[:max_files]

    return {
        "total_files": total_files,
        "total_bytes": total_bytes,
        "top_dirs": top_dirs_list,
        "top_exts": ext_list[:top_n_ext],
        "largest_files": [{"bytes": b, "path": p} for b, p in largest],
        "files": file_list if include_files else None,
    }


def _scan_data_bundles(
    dst_root: Path,
    *,
    include_entries: bool = False,
    max_entries: int = 0,
) -> List[Dict[str, Any]]:
    bundles_dir = dst_root / "data" / "databundles"
    if not bundles_dir.is_dir():
        return []

    out: List[Dict[str, Any]] = []
    for zp in sorted(bundles_dir.glob("*.zip")):
        try:
            with zipfile.ZipFile(zp, "r") as zf:
                infos = zf.infolist()
                total_bytes = sum(i.file_size for i in infos)
                entries = None
                if include_entries:
                    entries = []
                    for info in infos:
                        entries.append(
                            {
                                "path": info.filename,
                                "bytes": int(info.file_size),
                            }
                        )
                    if max_entries and len(entries) > max_entries:
                        entries = entries[:max_entries]
                out.append(
                    {
                        "file": zp.name,
                        "entries": len(infos),
                        "bytes": total_bytes,
                        "files": entries,
                    }
                )
        except Exception:
            out.append(
                {
                    "file": zp.name,
                    "entries": -1,
                    "bytes": -1,
                    "files": None,
                }
            )
    return out


def _scan_scripts_overview(engine: WagstaffEngine) -> Dict[str, Any]:
    files = list(engine.file_list)
    lua_files = [f for f in files if f.endswith(".lua")]

    top_dir = Counter()
    second_dir = Counter()
    for f in lua_files:
        clean = f[8:] if f.startswith("scripts/") else f
        parts = clean.split("/")
        if len(parts) == 1:
            top_dir["[root]"] += 1
        else:
            top_dir[parts[0]] += 1
            if len(parts) >= 2:
                second_dir[f"{parts[0]}/{parts[1]}"] += 1

    categories = {
        "prefabs": [f for f in lua_files if f.startswith("scripts/prefabs/")],
        "components": [f for f in lua_files if f.startswith("scripts/components/")],
        "stategraphs": [f for f in lua_files if f.startswith("scripts/stategraphs/")],
        "brains": [f for f in lua_files if f.startswith("scripts/brains/")],
        "behaviours": [f for f in lua_files if f.startswith("scripts/behaviours/")],
        "widgets": [f for f in lua_files if f.startswith("scripts/widgets/")],
        "screens": [f for f in lua_files if f.startswith("scripts/screens/")],
        "strings": [f for f in lua_files if f.startswith("scripts/strings")],
        "recipes": [
            f
            for f in lua_files
            if f.endswith("recipes.lua") or f.endswith("recipes2.lua") or f.endswith("recipes_filter.lua")
        ],
        "tuning": [f for f in lua_files if f.endswith("tuning.lua")],
        "prefabs_postinit": [f for f in lua_files if f.startswith("scripts/prefabs_postinit/")],
    }
    cat_counts = {k: len(v) for k, v in categories.items()}

    top_dirs = [{"dir": d, "count": c} for d, c in top_dir.most_common(40)]
    top_second = [{"dir": d, "count": c} for d, c in second_dir.most_common(60)]

    return {
        "total_files": len(files),
        "lua_files": len(lua_files),
        "categories": cat_counts,
        "top_dirs": top_dirs,
        "top_second_level": top_second,
    }


def _collect_prefab_data(engine: WagstaffEngine) -> Dict[str, Any]:
    prefab_files = [
        f for f in engine.file_list if f.startswith("scripts/prefabs/") and f.endswith(".lua")
    ]

    prefabs_declared: Set[str] = set()
    prefabs_fallback: Set[str] = set()
    file_prefabs: Dict[str, Set[str]] = {}
    file_components: Dict[str, Set[str]] = {}
    file_tags: Dict[str, Set[str]] = {}
    file_assets: Dict[str, int] = {}

    for path in prefab_files:
        content = engine.read_file(path) or ""
        if not content:
            continue
        clean = strip_lua_comments(content)
        extractor = LuaCallExtractor(clean)

        prefabs: Set[str] = set()
        for call in extractor.iter_calls("Prefab", include_member_calls=False):
            if not call.arg_list:
                continue
            nm = parse_lua_string(call.arg_list[0])
            if isinstance(nm, str) and nm:
                n = nm.strip().lower()
                if _ID_RE.match(n):
                    prefabs.add(n)

        if not prefabs:
            base = path.split("/")[-1].rsplit(".lua", 1)[0]
            if base:
                b = base.strip().lower()
                if _ID_RE.match(b):
                    prefabs_fallback.add(b)
                    prefabs = {b}
        else:
            prefabs_declared.update(prefabs)

        file_prefabs[path] = prefabs

        comps: Set[str] = set()
        for call in extractor.iter_calls("AddComponent"):
            if call.arg_list:
                cn = parse_lua_string(call.arg_list[0])
                if isinstance(cn, str) and cn:
                    comps.add(cn.strip().lower())
        file_components[path] = comps

        tags: Set[str] = set()
        for call in extractor.iter_calls("AddTag"):
            if call.arg_list:
                tg = parse_lua_string(call.arg_list[0])
                if isinstance(tg, str) and tg:
                    tags.add(tg.strip().lower())
        file_tags[path] = tags

        assets = 0
        for call in extractor.iter_calls("Asset"):
            if len(call.arg_list) >= 2:
                assets += 1
        file_assets[path] = assets

    # Prefab-level aggregates (file-level heuristic)
    prefab_components: Dict[str, Set[str]] = defaultdict(set)
    prefab_tags: Dict[str, Set[str]] = defaultdict(set)
    prefab_assets: Dict[str, int] = defaultdict(int)

    for path, prefabs in file_prefabs.items():
        comps = file_components.get(path, set())
        tags = file_tags.get(path, set())
        assets = file_assets.get(path, 0)
        for pf in prefabs:
            prefab_components[pf].update(comps)
            prefab_tags[pf].update(tags)
            prefab_assets[pf] += assets

    all_prefabs = set(prefab_components.keys()) | set(prefab_tags.keys()) | prefabs_declared | prefabs_fallback

    return {
        "prefab_files": prefab_files,
        "prefabs_declared": prefabs_declared,
        "prefabs_fallback": prefabs_fallback,
        "prefab_components": prefab_components,
        "prefab_tags": prefab_tags,
        "prefab_assets": prefab_assets,
        "all_prefabs": all_prefabs,
        "file_prefabs": file_prefabs,
        "file_components": file_components,
        "file_tags": file_tags,
    }


def _coverage_counts(base: Set[str], target: Set[str]) -> Dict[str, Any]:
    direct = len(base & target)
    norm_base = {_norm_id(x) for x in base}
    norm_target = {_norm_id(x) for x in target}
    normalized = len(norm_base & norm_target)
    return {
        "base": len(base),
        "target": len(target),
        "direct": direct,
        "normalized": normalized,
    }


def _sample_missing(base: Set[str], target: Set[str], limit: int = 40) -> Dict[str, Any]:
    missing = sorted([x for x in base if x not in target])
    return {
        "count": len(missing),
        "sample": missing[:limit],
    }


def _safe_str(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    return str(val)


def _craft_sets(engine: WagstaffEngine) -> Dict[str, Set[str]]:
    craft = engine.recipes
    recipes = getattr(craft, "recipes", {}) if craft is not None else {}

    recipe_ids: Set[str] = set()
    product_ids: Set[str] = set()
    ingredient_ids: Set[str] = set()

    for name, rec in (recipes or {}).items():
        if isinstance(name, str) and name:
            recipe_ids.add(name.strip().lower())
        if not isinstance(rec, dict):
            continue
        prod = rec.get("product")
        if isinstance(prod, str) and prod:
            product_ids.add(prod.strip().lower())
        for ing in rec.get("ingredients", []) or []:
            if not isinstance(ing, dict):
                continue
            item = ing.get("item")
            if isinstance(item, str) and item:
                ingredient_ids.add(item.strip().lower())

    return {
        "recipe_ids": recipe_ids,
        "product_ids": product_ids,
        "ingredient_ids": ingredient_ids,
    }


def _cooking_sets(engine: WagstaffEngine) -> Dict[str, Any]:
    cooking = engine.cooking_recipes or {}
    recipe_ids: Set[str] = set()
    ingredient_ids: Set[str] = set()
    tuning_expr_count = 0

    for name, rec in cooking.items():
        if isinstance(name, str) and name:
            recipe_ids.add(name.strip().lower())
        if not isinstance(rec, dict):
            continue

        for key in ("hunger", "health", "sanity", "perishtime", "cooktime"):
            v = rec.get(key)
            if isinstance(v, str) and "TUNING." in v:
                tuning_expr_count += 1

        ci = rec.get("card_ingredients") or []
        if isinstance(ci, list):
            for row in ci:
                if not isinstance(row, (list, tuple)) or not row:
                    continue
                item = row[0]
                if isinstance(item, str) and item:
                    ingredient_ids.add(item.strip().lower())

    return {
        "recipe_ids": recipe_ids,
        "ingredient_ids": ingredient_ids,
        "tuning_expr_fields": tuning_expr_count,
    }


def build_report(
    engine: WagstaffEngine,
    *,
    dst_root: Path,
    top_n: int = 25,
    data_full: bool = False,
    data_max_files: int = 0,
    bundle_full: bool = False,
    bundle_max_files: int = 0,
) -> Dict[str, Any]:
    pref = _collect_prefab_data(engine)
    prefabs = pref["all_prefabs"]
    prefab_components = pref["prefab_components"]
    prefab_tags = pref["prefab_tags"]

    # Strings
    names_map = _extract_strings_names(engine)
    names = {k.strip().lower() for k in names_map.keys() if isinstance(k, str)}

    # Icons
    icon_names, icon_xmls = _scan_inventory_icons(dst_root)
    data_scan = _scan_data_dir(dst_root, include_files=data_full, max_files=data_max_files)
    bundle_scan = _scan_data_bundles(dst_root, include_entries=bundle_full, max_entries=bundle_max_files)
    scripts_scan = _scan_scripts_overview(engine)

    # Item prefabs (heuristic)
    item_prefabs = {p for p, comps in prefab_components.items() if "inventoryitem" in comps}

    # Craft/Cooking
    craft_sets = _craft_sets(engine)
    cooking_sets = _cooking_sets(engine)

    # Tuning
    tuning_keys = set()
    if engine.tuning is not None:
        tuning_keys = set(getattr(engine.tuning, "raw_map", {}).keys())

    # Component/tag histograms
    comp_counts = Counter()
    for comps in prefab_components.values():
        for c in comps:
            comp_counts[c] += 1
    tag_counts = Counter()
    for tags in prefab_tags.values():
        for t in tags:
            tag_counts[t] += 1

    top_components = [{"component": k, "prefabs": v} for k, v in comp_counts.most_common(top_n)]
    top_tags = [{"tag": k, "prefabs": v} for k, v in tag_counts.most_common(top_n)]

    # Coverage stats
    coverage = {
        "prefab_names": _coverage_counts(prefabs, names),
        "item_prefab_names": _coverage_counts(item_prefabs, names),
        "item_prefab_icons": _coverage_counts(item_prefabs, icon_names),
        "icons_vs_prefabs": _coverage_counts(icon_names, prefabs),
        "craft_products_vs_items": _coverage_counts(craft_sets["product_ids"], item_prefabs),
        "craft_ingredients_vs_items": _coverage_counts(craft_sets["ingredient_ids"], item_prefabs),
        "cooking_ingredients_vs_items": _coverage_counts(cooking_sets["ingredient_ids"], item_prefabs),
    }

    samples = {
        "item_prefabs_missing_icons": _sample_missing(item_prefabs, icon_names),
        "item_prefabs_missing_names": _sample_missing(item_prefabs, names),
        "prefabs_missing_names": _sample_missing(prefabs, names),
        "icons_without_prefabs": _sample_missing(icon_names, prefabs),
    }

    total_files = len(engine.file_list)
    lua_files = len([f for f in engine.file_list if f.endswith(".lua")])

    return {
        "generated": _now_iso(),
        "dst_root": str(dst_root),
        "engine": {
            "mode": engine.mode,
            "scripts_zip": _safe_str(getattr(getattr(engine, "source", None), "filename", None)),
            "scripts_dir": _safe_str(getattr(engine, "source", None) if engine.mode == "folder" else None),
            "scripts_file_count": len(engine.file_list),
        },
        "counts": {
            "total_files": total_files,
            "lua_files": lua_files,
            "prefab_files": len(pref["prefab_files"]),
            "prefabs_total": len(prefabs),
            "prefabs_declared": len(pref["prefabs_declared"]),
            "prefabs_fallback": len(pref["prefabs_fallback"]),
            "item_prefabs": len(item_prefabs),
            "strings_names": len(names),
            "icons": len(icon_names),
            "craft_recipes": len(craft_sets["recipe_ids"]),
            "craft_products": len(craft_sets["product_ids"]),
            "craft_ingredients": len(craft_sets["ingredient_ids"]),
            "cooking_recipes": len(cooking_sets["recipe_ids"]),
            "cooking_ingredients": len(cooking_sets["ingredient_ids"]),
            "tuning_keys": len(tuning_keys),
            "tuning_expr_in_cooking_fields": int(cooking_sets["tuning_expr_fields"]),
        },
        "icon_sources": icon_xmls,
        "data_scan": data_scan,
        "bundle_scan": bundle_scan,
        "scripts_scan": scripts_scan,
        "coverage": coverage,
        "top_components": top_components,
        "top_tags": top_tags,
        "samples": samples,
        "notes": [
            "Components/tags are file-level heuristics; prefab-specific attribution may overestimate.",
            "Normalized coverage removes underscores and lowercases ids.",
        ],
    }


def render_md(doc: Dict[str, Any]) -> str:
    lines: List[str] = []
    counts = doc.get("counts") or {}
    engine = doc.get("engine") or {}
    coverage = doc.get("coverage") or {}

    lines.append("# DST Raw Coverage Report")
    lines.append("")
    lines.append("## Meta")
    lines.append("```yaml")
    lines.append(f"generated: {doc.get('generated')}")
    lines.append(f"dst_root: {doc.get('dst_root')}")
    lines.append(f"engine_mode: {engine.get('mode')}")
    if engine.get("scripts_zip"):
        lines.append(f"scripts_zip: {engine.get('scripts_zip')}")
    if engine.get("scripts_dir"):
        lines.append(f"scripts_dir: {engine.get('scripts_dir')}")
    lines.append(f"scripts_file_count: {engine.get('scripts_file_count')}")
    lines.append("```")

    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---:|")
    for key in (
        "total_files",
        "lua_files",
        "prefab_files",
        "prefabs_total",
        "prefabs_declared",
        "prefabs_fallback",
        "item_prefabs",
        "strings_names",
        "icons",
        "craft_recipes",
        "craft_products",
        "craft_ingredients",
        "cooking_recipes",
        "cooking_ingredients",
        "tuning_keys",
        "tuning_expr_in_cooking_fields",
    ):
        if key in counts:
            lines.append(f"| {key} | {counts.get(key)} |")

    lines.append("")
    lines.append("## Icon Sources")
    lines.append("")
    for x in doc.get("icon_sources") or []:
        lines.append(f"- `{x}`")

    scripts_scan = doc.get("scripts_scan") or {}
    if scripts_scan:
        lines.append("")
        lines.append("## Scripts Overview")
        lines.append("")
        lines.append("```yaml")
        lines.append(f"total_files: {scripts_scan.get('total_files')}")
        lines.append(f"lua_files: {scripts_scan.get('lua_files')}")
        lines.append("```")

        lines.append("")
        lines.append("### Categories")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|---|---:|")
        for k, v in sorted((scripts_scan.get("categories") or {}).items(), key=lambda x: x[0]):
            lines.append(f"| {k} | {v} |")

        lines.append("")
        lines.append("### Top Directories (scripts)")
        lines.append("")
        lines.append("| Dir | Files |")
        lines.append("|---|---:|")
        for row in (scripts_scan.get("top_dirs") or []):
            lines.append(f"| {row.get('dir')} | {row.get('count')} |")

        lines.append("")
        lines.append("### Top 2nd-level Directories")
        lines.append("")
        lines.append("| Dir | Files |")
        lines.append("|---|---:|")
        for row in (scripts_scan.get("top_second_level") or []):
            lines.append(f"| {row.get('dir')} | {row.get('count')} |")

    data_scan = doc.get("data_scan") or {}
    if data_scan:
        lines.append("")
        lines.append("## Data Directory Summary")
        lines.append("")
        lines.append("```yaml")
        lines.append(f"total_files: {data_scan.get('total_files')}")
        lines.append(f"total_bytes: {data_scan.get('total_bytes')}")
        lines.append("```")

        lines.append("")
        lines.append("### Top Directories (by file count)")
        lines.append("")
        lines.append("| Dir | Files | Bytes |")
        lines.append("|---|---:|---:|")
        for row in (data_scan.get("top_dirs") or [])[:20]:
            lines.append(f"| {row.get('dir')} | {row.get('files')} | {row.get('bytes')} |")

        lines.append("")
        lines.append("### Top Extensions (by file count)")
        lines.append("")
        lines.append("| Ext | Files | Bytes |")
        lines.append("|---|---:|---:|")
        for row in (data_scan.get("top_exts") or []):
            lines.append(f"| {row.get('ext')} | {row.get('files')} | {row.get('bytes')} |")

        lines.append("")
        lines.append("### Largest Files")
        lines.append("")
        lines.append("| Bytes | Path |")
        lines.append("|---:|---|")
        for row in (data_scan.get("largest_files") or []):
            lines.append(f"| {row.get('bytes')} | `{row.get('path')}` |")
        if data_scan.get("files") is not None:
            lines.append("")
            lines.append(f"- data_files_listed: {len(data_scan.get('files') or [])} (see JSON)")

    bundle_scan = doc.get("bundle_scan") or []
    if bundle_scan:
        lines.append("")
        lines.append("## Data Bundles (databundles/*.zip)")
        lines.append("")
        lines.append("| Bundle | Entries | Bytes |")
        lines.append("|---|---:|---:|")
        for row in bundle_scan:
            lines.append(f"| {row.get('file')} | {row.get('entries')} | {row.get('bytes')} |")

    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append("| Metric | Base | Target | Direct | Normalized |")
    lines.append("|---|---:|---:|---:|---:|")
    for name, data in coverage.items():
        lines.append(
            f"| {name} | {data.get('base')} | {data.get('target')} | {data.get('direct')} | {data.get('normalized')} |"
        )

    lines.append("")
    lines.append("## Top Components (by prefab count)")
    lines.append("")
    lines.append("| Component | Prefabs |")
    lines.append("|---|---:|")
    for row in doc.get("top_components") or []:
        lines.append(f"| {row.get('component')} | {row.get('prefabs')} |")

    lines.append("")
    lines.append("## Top Tags (by prefab count)")
    lines.append("")
    lines.append("| Tag | Prefabs |")
    lines.append("|---|---:|")
    for row in doc.get("top_tags") or []:
        lines.append(f"| {row.get('tag')} | {row.get('prefabs')} |")

    samples = doc.get("samples") or {}
    lines.append("")
    lines.append("## Samples (missing)")
    for k, v in samples.items():
        lines.append(f"\n### {k}")
        lines.append(f"- missing_count: {v.get('count')}")
        for s in v.get("sample") or []:
            lines.append(f"- {s}")

    lines.append("")
    lines.append("## Notes")
    for n in doc.get("notes") or []:
        lines.append(f"- {n}")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan DST raw data and produce coverage report.")
    parser.add_argument("--out-md", default=str(REPORT_DIR / "dst_raw_coverage.md"))
    parser.add_argument("--out-json", default=str(REPORT_DIR / "dst_raw_coverage.json"))
    parser.add_argument("--top", type=int, default=25, help="Top N components/tags to include")
    parser.add_argument("--data-full", action="store_true", help="Include full data/ file list in JSON output")
    parser.add_argument("--data-max-files", type=int, default=0, help="Limit data file list length (0 = no limit)")
    parser.add_argument("--bundle-full", action="store_true", help="Include full databundles/*.zip entry lists in JSON output")
    parser.add_argument("--bundle-max-files", type=int, default=0, help="Limit bundle entry list length (0 = no limit)")
    parser.add_argument("--scripts-zip", default=None, help="Override scripts zip path")
    parser.add_argument("--scripts-dir", default=None, help="Override scripts folder path")
    parser.add_argument("--dst-root", default=None, help="Override DST root (default from config)")

    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    config_dst_root = None
    if args.dst_root:
        config_dst_root = args.dst_root
    elif wagstaff_config is not None:
        try:
            config_dst_root = wagstaff_config.get("PATHS", "DST_ROOT")
        except Exception:
            config_dst_root = None

    engine = WagstaffEngine(
        load_db=True,
        silent=True,
        scripts_zip=args.scripts_zip,
        scripts_dir=args.scripts_dir,
        dst_root=config_dst_root,
    )

    # Resolve dst_root for icons (fallback to engine-detected root)
    dst_root = Path(config_dst_root).expanduser().resolve() if config_dst_root else None
    if dst_root is None:
        # try project config via engine config lookup path
        # engine._project_root and config are private; use inferred from scripts_zip path
        if engine.mode == "zip" and getattr(engine.source, "filename", None):
            zpath = Path(str(engine.source.filename)).expanduser().resolve()
            # scripts.zip usually lives under DST_ROOT/data/databundles
            dst_root = zpath.parent.parent.parent if zpath.parent.parent.parent.exists() else zpath.parent.parent
        elif engine.mode == "folder":
            # scripts folder under DST_ROOT/data/scripts
            spath = Path(str(engine.source)).expanduser().resolve()
            dst_root = spath.parent.parent if spath.parent.parent.exists() else spath.parent
    if dst_root is None:
        raise SystemExit("Unable to infer dst_root; pass --dst-root explicitly.")

    doc = build_report(
        engine,
        dst_root=dst_root,
        top_n=int(args.top),
        data_full=bool(args.data_full),
        data_max_files=int(args.data_max_files or 0),
        bundle_full=bool(args.bundle_full),
        bundle_max_files=int(args.bundle_max_files or 0),
    )

    md_path = Path(args.out_md)
    json_path = Path(args.out_json)
    md_path.write_text(render_md(doc), encoding="utf-8")
    json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ Coverage report written: {md_path}")
    print(f"✅ JSON written: {json_path}")


if __name__ == "__main__":
    main()

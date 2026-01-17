#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resource index builder (core).

Collects a structured inventory of DST scripts and data resources.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import os
import re
import xml.etree.ElementTree as ET
import zipfile

from core.analyzer import LuaCallExtractor, parse_lua_string, strip_lua_comments
from core.schemas.meta import build_meta


SCHEMA_VERSION = 1
_ID_RE = re.compile(r"^[a-z0-9_]+$")

SCRIPT_KINDS = [
    ("prefab", "scripts/prefabs/"),
    ("prefab_postinit", "scripts/prefabs_postinit/"),
    ("component", "scripts/components/"),
    ("stategraph", "scripts/stategraphs/"),
    ("brain", "scripts/brains/"),
    ("behaviour", "scripts/behaviours/"),
    ("widget", "scripts/widgets/"),
    ("screen", "scripts/screens/"),
    ("map", "scripts/map/"),
    ("scenario", "scripts/scenarios/"),
    ("string", "scripts/strings"),
    ("language", "scripts/languages/"),
    ("tuning", "scripts/tuning.lua"),
    ("recipe", "scripts/recipes"),
    ("tool", "scripts/tools/"),
    ("util", "scripts/util/"),
]


def _classify_script(path: str) -> str:
    p = (path or "").replace("\\", "/")
    for kind, prefix in SCRIPT_KINDS:
        if prefix.endswith(".lua"):
            if p.endswith(prefix):
                return kind
        elif p.startswith(prefix):
            return kind
    return "other"


def _scan_scripts(file_list: Iterable[str]) -> Dict[str, Any]:
    files = [str(f) for f in file_list]
    lua_files = [f for f in files if f.endswith(".lua")]

    by_kind: Dict[str, List[str]] = defaultdict(list)
    items: List[Dict[str, str]] = []
    top_dir = Counter()
    second_dir = Counter()

    for f in lua_files:
        kind = _classify_script(f)
        items.append({"path": f, "kind": kind})
        by_kind[kind].append(f)

        clean = f[8:] if f.startswith("scripts/") else f
        parts = clean.split("/")
        if len(parts) == 1:
            top_dir["[root]"] += 1
        else:
            top_dir[parts[0]] += 1
            if len(parts) >= 2:
                second_dir[f"{parts[0]}/{parts[1]}"] += 1

    categories = {k: len(v) for k, v in by_kind.items()}

    top_dirs = [{"dir": d, "count": c} for d, c in top_dir.most_common(40)]
    top_second = [{"dir": d, "count": c} for d, c in second_dir.most_common(60)]

    return {
        "total_files": len(files),
        "lua_files": len(lua_files),
        "categories": categories,
        "top_dirs": top_dirs,
        "top_second_level": top_second,
        "files": items,
        "by_kind": dict(by_kind),
    }


def _parse_prefab_file(content: str) -> Dict[str, Any]:
    clean = strip_lua_comments(content or "")
    extractor = LuaCallExtractor(clean)

    prefabs: Set[str] = set()
    skipped = 0
    for call in extractor.iter_calls("Prefab", include_member_calls=False):
        if not call.arg_list:
            continue
        nm = parse_lua_string(call.arg_list[0])
        if isinstance(nm, str) and nm:
            n = nm.strip().lower()
            if _ID_RE.match(n):
                prefabs.add(n)
            else:
                skipped += 1

    assets: List[Dict[str, str]] = []
    for call in extractor.iter_calls("Asset", include_member_calls=False):
        if len(call.arg_list) < 2:
            continue
        t = parse_lua_string(call.arg_list[0])
        p = parse_lua_string(call.arg_list[1])
        if isinstance(t, str) and isinstance(p, str):
            assets.append({"type": t, "path": p})

    tags: Set[str] = set()
    for call in extractor.iter_calls("AddTag"):
        if call.arg_list:
            tg = parse_lua_string(call.arg_list[0])
            if isinstance(tg, str) and tg:
                tags.add(tg.strip().lower())

    components: Set[str] = set()
    for call in extractor.iter_calls("AddComponent"):
        if call.arg_list:
            cn = parse_lua_string(call.arg_list[0])
            if isinstance(cn, str) and cn:
                components.add(cn.strip().lower())

    brain = None
    m = re.search(r"SetBrain\s*\(\s*require\s*\(\s*['\"](.*?)['\"]\s*\)\s*\)", clean)
    if m:
        brain = m.group(1)

    stategraph = None
    m = re.search(r"SetStateGraph\s*\(\s*['\"](.*?)['\"]\s*\)", clean)
    if m:
        stategraph = m.group(1)

    helpers = sorted(set(re.findall(r"^\s*(Make[A-Za-z0-9_]+)\s*\(", content or "", flags=re.MULTILINE)))

    return {
        "prefabs": prefabs,
        "prefabs_skipped": skipped,
        "assets": assets,
        "tags": tags,
        "components": components,
        "brain": brain,
        "stategraph": stategraph,
        "helpers": helpers,
    }


def _scan_prefabs(engine: Any) -> Dict[str, Any]:
    prefab_files = [
        f for f in getattr(engine, "file_list", []) if str(f).startswith("scripts/prefabs/") and str(f).endswith(".lua")
    ]

    prefab_items: Dict[str, Dict[str, Any]] = {}
    file_entries: List[Dict[str, Any]] = []
    skipped_total = 0

    for path in prefab_files:
        content = engine.read_file(path) or ""
        if not content:
            continue

        parsed = _parse_prefab_file(content)
        prefabs = set(parsed["prefabs"])

        if not prefabs:
            base = str(path).split("/")[-1].rsplit(".lua", 1)[0].strip().lower()
            if _ID_RE.match(base):
                prefabs.add(base)

        file_entries.append(
            {
                "path": path,
                "prefabs": sorted(prefabs),
                "components": sorted(parsed["components"]),
                "tags": sorted(parsed["tags"]),
                "assets_count": len(parsed["assets"]),
            }
        )

        skipped_total += int(parsed.get("prefabs_skipped", 0) or 0)

        for pf in prefabs:
            entry = prefab_items.setdefault(
                pf,
                {
                    "files": [],
                    "components": set(),
                    "tags": set(),
                    "assets": [],
                    "brains": set(),
                    "stategraphs": set(),
                    "helpers": set(),
                },
            )
            if path not in entry["files"]:
                entry["files"].append(path)
            entry["components"].update(parsed["components"])
            entry["tags"].update(parsed["tags"])
            entry["helpers"].update(parsed["helpers"])
            if parsed.get("brain"):
                entry["brains"].add(parsed["brain"])
            if parsed.get("stategraph"):
                entry["stategraphs"].add(parsed["stategraph"])

            asset_keys = {f"{a.get('type')}:{a.get('path')}" for a in entry["assets"]}
            for a in parsed["assets"]:
                key = f"{a.get('type')}:{a.get('path')}"
                if key not in asset_keys:
                    entry["assets"].append(a)
                    asset_keys.add(key)

    # normalize sets -> lists
    for pf, entry in prefab_items.items():
        entry["components"] = sorted(entry["components"])
        entry["tags"] = sorted(entry["tags"])
        entry["brains"] = sorted(entry["brains"])
        entry["stategraphs"] = sorted(entry["stategraphs"])
        entry["helpers"] = sorted(entry["helpers"])

    return {
        "total_files": len(prefab_files),
        "total_prefabs": len(prefab_items),
        "prefabs_skipped": skipped_total,
        "items": prefab_items,
        "files": file_entries,
    }


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
    include_files: bool = False,
    max_files: int = 0,
) -> Dict[str, Any]:
    data_dir = dst_root / "data"
    if not data_dir.is_dir():
        return {}

    top_dirs: Dict[str, Dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})
    ext_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})
    file_list: List[Dict[str, Any]] = []
    total_files = 0
    total_bytes = 0

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
        "top_exts": ext_list,
        "files": file_list if include_files else None,
    }


def _scan_bundles(
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
                    entries = [{"path": i.filename, "bytes": int(i.file_size)} for i in infos]
                    if max_entries and len(entries) > max_entries:
                        entries = entries[:max_entries]
                out.append({"file": zp.name, "entries": len(infos), "bytes": total_bytes, "files": entries})
        except Exception:
            out.append({"file": zp.name, "entries": -1, "bytes": -1, "files": None})
    return out


def build_resource_index(
    *,
    engine: Any,
    dst_root: Path,
    include_data_files: bool = False,
    max_data_files: int = 0,
    include_bundle_files: bool = False,
    max_bundle_files: int = 0,
) -> Dict[str, Any]:
    files = list(getattr(engine, "file_list", []) or [])
    scripts = _scan_scripts(files)
    prefabs = _scan_prefabs(engine)
    icons, icon_sources = _scan_inventory_icons(dst_root)
    data_scan = _scan_data_dir(dst_root, include_files=include_data_files, max_files=max_data_files)
    bundle_scan = _scan_bundles(dst_root, include_entries=include_bundle_files, max_entries=max_bundle_files)

    meta = build_meta(
        schema=SCHEMA_VERSION,
        tool="build_resource_index",
        sources={
            "dst_root": str(dst_root),
            "scripts_zip": getattr(getattr(engine, "source", None), "filename", None),
            "scripts_dir": getattr(engine, "source", None) if getattr(engine, "mode", "") == "folder" else None,
        },
        extra={
            "engine_mode": getattr(engine, "mode", ""),
            "scripts_file_count": len(files),
            "dst_root": str(dst_root),
            "scripts_zip": getattr(getattr(engine, "source", None), "filename", None),
            "scripts_dir": getattr(engine, "source", None) if getattr(engine, "mode", "") == "folder" else None,
        },
    )

    if data_scan:
        meta["data_file_count"] = data_scan.get("total_files")
        meta["data_total_bytes"] = data_scan.get("total_bytes")

    return {
        "schema_version": SCHEMA_VERSION,
        "meta": meta,
        "scripts": scripts,
        "prefabs": prefabs,
        "assets": {
            "inventory_icons": sorted(icons),
            "inventory_atlases": icon_sources,
        },
        "data": data_scan,
        "bundles": bundle_scan,
    }


def render_resource_index_summary(index: Dict[str, Any]) -> str:
    meta = index.get("meta") or {}
    scripts = index.get("scripts") or {}
    prefabs = index.get("prefabs") or {}
    assets = index.get("assets") or {}
    data = index.get("data") or {}
    bundles = index.get("bundles") or []

    lines: List[str] = []
    lines.append("# Wagstaff Resource Index Summary")
    lines.append("")
    lines.append("## Meta")
    lines.append("```yaml")
    lines.append(f"generated: {meta.get('generated')}")
    lines.append(f"dst_root: {meta.get('dst_root')}")
    lines.append(f"engine_mode: {meta.get('engine_mode')}")
    if meta.get("scripts_zip"):
        lines.append(f"scripts_zip: {meta.get('scripts_zip')}")
    if meta.get("scripts_dir"):
        lines.append(f"scripts_dir: {meta.get('scripts_dir')}")
    lines.append(f"scripts_file_count: {meta.get('scripts_file_count')}")
    if meta.get("data_file_count") is not None:
        lines.append(f"data_file_count: {meta.get('data_file_count')}")
    if meta.get("data_total_bytes") is not None:
        lines.append(f"data_total_bytes: {meta.get('data_total_bytes')}")
    lines.append("```")

    lines.append("")
    lines.append("## Scripts")
    lines.append("")
    lines.append("```yaml")
    lines.append(f"total_files: {scripts.get('total_files')}")
    lines.append(f"lua_files: {scripts.get('lua_files')}")
    lines.append("```")

    lines.append("")
    lines.append("### Script Categories")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|---|---:|")
    for k, v in sorted((scripts.get("categories") or {}).items(), key=lambda x: x[0]):
        lines.append(f"| {k} | {v} |")

    lines.append("")
    lines.append("## Prefabs")
    lines.append("")
    lines.append("```yaml")
    lines.append(f"prefab_files: {prefabs.get('total_files')}")
    lines.append(f"prefabs_total: {prefabs.get('total_prefabs')}")
    lines.append(f"prefabs_skipped: {prefabs.get('prefabs_skipped')}")
    lines.append("```")

    lines.append("")
    lines.append("## Assets")
    lines.append("")
    lines.append("```yaml")
    lines.append(f"inventory_icons: {len(assets.get('inventory_icons') or [])}")
    lines.append(f"inventory_atlases: {len(assets.get('inventory_atlases') or [])}")
    lines.append("```")

    if data:
        lines.append("")
        lines.append("## Data Summary")
        lines.append("")
        lines.append("```yaml")
        lines.append(f"total_files: {data.get('total_files')}")
        lines.append(f"total_bytes: {data.get('total_bytes')}")
        lines.append("```")

    if bundles:
        lines.append("")
        lines.append("## Bundles")
        lines.append("")
        lines.append("| Bundle | Entries | Bytes |")
        lines.append("|---|---:|---:|")
        for row in bundles:
            lines.append(f"| {row.get('file')} | {row.get('entries')} | {row.get('bytes')} |")

    return "\n".join(lines) + "\n"

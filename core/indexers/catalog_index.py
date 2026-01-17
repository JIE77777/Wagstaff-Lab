#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catalog index builder (core).

Build a compact, search-friendly index from wagstaff_catalog_v2.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.schemas.meta import build_meta

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


def load_icon_index(path: Optional[Path]) -> Dict[str, str]:
    if path is None:
        return {}
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    icons = doc.get("icons") if isinstance(doc, dict) else None
    if not isinstance(icons, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in icons.items():
        if not k or not isinstance(k, str):
            continue
        if isinstance(v, dict) and v.get("png"):
            out[k] = str(v.get("png"))
    return out


def _build_item_list(
    catalog: Dict[str, Any],
    *,
    icon_index: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    items_obj = catalog.get("items") or {}
    assets_obj = catalog.get("assets") or {}

    if not isinstance(items_obj, dict):
        items_obj = {}
    if not isinstance(assets_obj, dict):
        assets_obj = {}

    icon_index = icon_index or {}

    ids: List[str] = []
    ids.extend([str(k) for k in items_obj.keys() if k])
    ids.extend([str(k) for k in assets_obj.keys() if k])
    ids.extend([str(k) for k in icon_index.keys() if k])
    ids = _dedup_preserve_order(ids)

    out: List[Dict[str, Any]] = []

    for iid in ids:
        if not iid:
            continue
        item = items_obj.get(iid) if isinstance(items_obj.get(iid), dict) else {}
        asset = assets_obj.get(iid) if isinstance(assets_obj.get(iid), dict) else {}
        asset = asset or (item.get("assets") if isinstance(item, dict) else {}) or {}
        name = asset.get("name") or item.get("name") or iid
        icon = asset.get("icon") or asset.get("image") or icon_index.get(iid)
        entry = {
            "id": iid,
            "name": name,
            "image": asset.get("image") or icon,
            "icon": icon,
            "has_icon": bool(icon),
            "icon_only": bool(iid not in items_obj),
            "kind": item.get("kind"),
            "categories": item.get("categories") or [],
            "behaviors": item.get("behaviors") or [],
            "sources": item.get("sources") or [],
            "tags": item.get("tags") or [],
            "components": item.get("components") or [],
            "slots": item.get("slots") or [],
        }
        out.append(entry)

    out.sort(key=lambda x: x.get("id") or "")
    return out


def _build_indexes(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[str]]]:
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

    for item in items:
        iid = str(item.get("id") or "").strip()
        if not iid:
            continue
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

    return {
        "by_kind": by_kind,
        "by_category": by_category,
        "by_behavior": by_behavior,
        "by_source": by_source,
        "by_component": by_component,
        "by_tag": by_tag,
        "by_slot": by_slot,
    }


def build_catalog_index(
    catalog: Dict[str, Any],
    *,
    icon_index: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    items = _build_item_list(catalog, icon_index=icon_index)
    indexes = _build_indexes(items)

    items_total = len(items)
    icon_only = len([i for i in items if i.get("icon_only")])
    icons_total = len([i for i in items if i.get("has_icon")])

    meta_src = catalog.get("meta") if isinstance(catalog, dict) else {}
    meta_src = meta_src if isinstance(meta_src, dict) else {}

    meta = build_meta(
        schema=1,
        tool="build_catalog_index",
        sources={
            "catalog": "wagstaff_catalog_v2.json",
            "scripts_zip": meta_src.get("scripts_zip"),
            "scripts_dir": meta_src.get("scripts_dir"),
        },
        extra={
            "catalog_schema": int(catalog.get("schema_version") or meta_src.get("schema") or 0),
            "scripts_sha256_12": meta_src.get("scripts_sha256_12"),
            "scripts_zip": meta_src.get("scripts_zip"),
            "scripts_dir": meta_src.get("scripts_dir"),
        },
    )

    return {
        "schema_version": 1,
        "meta": meta,
        "counts": {
            "items_total": items_total,
            "items_with_icon": icons_total,
            "icon_only": icon_only,
        },
        "items": items,
        "indexes": indexes,
    }


def render_index_summary(index_doc: Dict[str, Any]) -> str:
    meta = index_doc.get("meta") or {}
    counts = index_doc.get("counts") or {}
    lines = []
    lines.append("# Wagstaff Catalog Index Summary")
    lines.append("")
    lines.append("## Meta")
    lines.append("```yaml")
    lines.append(f"schema_version: {index_doc.get('schema_version')}")
    lines.append(f"catalog_schema: {meta.get('catalog_schema')}")
    lines.append(f"scripts_sha256_12: {meta.get('scripts_sha256_12')}")
    lines.append("```")
    lines.append("")
    lines.append("## Counts")
    lines.append("```yaml")
    for k, v in counts.items():
        lines.append(f"{k}: {v}")
    lines.append("```")
    return "\n".join(lines) + "\n"

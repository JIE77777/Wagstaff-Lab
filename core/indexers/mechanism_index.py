# -*- coding: utf-8 -*-
"""Mechanism index builder (core).

Focus: component definitions + prefab/component linkage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from core.indexers.shared import _sha256_12_file
from core.parsers import ComponentParser
from core.schemas.meta import build_meta


SCHEMA_VERSION = 1


def _scan_components(engine: Any) -> Dict[str, Any]:
    files = [
        f
        for f in getattr(engine, "file_list", []) or []
        if str(f).startswith("scripts/components/") and str(f).endswith(".lua")
    ]

    items: Dict[str, Dict[str, Any]] = {}
    for path in files:
        content = engine.read_file(path) or ""
        if not content:
            continue
        parsed = ComponentParser(content, path=path).parse()
        cid = str(parsed.get("id") or "").strip().lower()
        if not cid:
            continue
        items[cid] = parsed

    return {
        "total_files": len(files),
        "items": items,
    }


def _build_prefab_links(resource_index: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    prefabs = (resource_index or {}).get("prefabs") or {}
    items = prefabs.get("items") or {}
    if not isinstance(items, dict):
        items = {}

    out: Dict[str, Dict[str, Any]] = {}
    for iid, row in items.items():
        if not iid or not isinstance(row, dict):
            continue
        out[str(iid)] = {
            "components": sorted({str(x) for x in (row.get("components") or []) if x}),
            "tags": sorted({str(x) for x in (row.get("tags") or []) if x}),
            "brains": sorted({str(x) for x in (row.get("brains") or []) if x}),
            "stategraphs": sorted({str(x) for x in (row.get("stategraphs") or []) if x}),
            "helpers": sorted({str(x) for x in (row.get("helpers") or []) if x}),
            "files": sorted({str(x) for x in (row.get("files") or []) if x}),
        }
    return out


def _build_component_usage(prefab_links: Dict[str, Any]) -> Dict[str, List[str]]:
    usage: Dict[str, Set[str]] = {}
    for pid, row in (prefab_links or {}).items():
        comps = row.get("components") if isinstance(row, dict) else None
        if not isinstance(comps, list):
            continue
        for c in comps:
            if not c:
                continue
            usage.setdefault(str(c), set()).add(str(pid))
    return {k: sorted(v) for k, v in usage.items()}


def render_mechanism_index_summary(index: Dict[str, Any]) -> str:
    meta = index.get("meta") or {}
    counts = index.get("counts") or {}
    usage = index.get("component_usage") or {}

    rows: List[Dict[str, Any]] = []
    for cid, prefabs in (usage or {}).items():
        if not cid:
            continue
        n = len(prefabs) if isinstance(prefabs, list) else 0
        rows.append({"component": cid, "prefabs": n})

    rows.sort(key=lambda x: (-int(x.get("prefabs") or 0), str(x.get("component") or "")))
    top_rows = rows[:20]

    lines: List[str] = []
    lines.append("# Wagstaff Mechanism Index Summary")
    lines.append("")
    lines.append("## Meta")
    lines.append("```yaml")
    lines.append(f"schema_version: {index.get('schema_version')}")
    lines.append(f"generated: {meta.get('generated')}")
    lines.append(f"scripts_sha256_12: {meta.get('scripts_sha256_12')}")
    if meta.get("scripts_zip"):
        lines.append(f"scripts_zip: {meta.get('scripts_zip')}")
    if meta.get("scripts_dir"):
        lines.append(f"scripts_dir: {meta.get('scripts_dir')}")
    lines.append("```")
    lines.append("")
    lines.append("## Counts")
    lines.append("```yaml")
    for k, v in counts.items():
        lines.append(f"{k}: {v}")
    lines.append("```")
    lines.append("")
    lines.append("## Top Components by Prefab Usage")
    lines.append("")
    lines.append("| Component | Prefabs |")
    lines.append("| --- | --- |")
    for row in top_rows:
        lines.append(f"| {row.get('component')} | {row.get('prefabs')} |")
    return "\n".join(lines) + "\n"


def build_mechanism_index(
    *,
    engine: Any,
    resource_index: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    components = _scan_components(engine)
    prefab_links = _build_prefab_links(resource_index)
    component_usage = _build_component_usage(prefab_links)
    mapping = {
        "prefab_component": [
            {"source": "prefab", "source_id": pid, "target": "component", "target_id": cid}
            for cid, pids in component_usage.items()
            for pid in pids
        ]
    }

    scripts_zip = getattr(getattr(engine, "source", None), "filename", None)
    scripts_sha = _sha256_12_file(Path(scripts_zip)) if scripts_zip else None
    scripts_dir = getattr(engine, "source", None) if getattr(engine, "mode", "") == "folder" else None

    meta = build_meta(
        schema=SCHEMA_VERSION,
        tool="build_mechanism_index",
        sources={
            "resource_index": "wagstaff_resource_index_v1.json",
            "scripts_zip": scripts_zip,
            "scripts_dir": scripts_dir,
        },
        extra={
            "scripts_sha256_12": scripts_sha,
            "scripts_zip": scripts_zip,
            "scripts_dir": scripts_dir,
        },
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "meta": meta,
        "counts": {
            "components_total": len(components.get("items") or {}),
            "prefabs_total": len(prefab_links),
            "components_used": len(component_usage),
            "prefab_component_edges": len(mapping.get("prefab_component") or []),
        },
        "components": components,
        "prefabs": {"items": prefab_links},
        "component_usage": component_usage,
        "links": mapping,
    }

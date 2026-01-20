# -*- coding: utf-8 -*-
"""Mechanism index builder (core).

Focus: component definitions + prefab/component linkage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from core.indexers.shared import _sha256_12_file
from core.parsers import ComponentParser, PrefabParser
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


def _normalize_prefab_assets(assets: Any) -> List[Dict[str, str]]:
    if not isinstance(assets, list):
        return []
    out: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for row in assets:
        if not isinstance(row, dict):
            continue
        asset_type = str(row.get("type") or "").strip()
        path = str(row.get("path") or "").strip()
        if not asset_type or not path:
            continue
        key = f"{asset_type}:{path}"
        if key in seen:
            continue
        out.append({"type": asset_type, "path": path})
        seen.add(key)
    return out


def _component_calls_to_map(calls: Any) -> Dict[str, Dict[str, Set[str]]]:
    out: Dict[str, Dict[str, Set[str]]] = {}
    if not isinstance(calls, list):
        return out
    for row in calls:
        if not isinstance(row, dict):
            continue
        comp = row.get("component") or row.get("name")
        comp = str(comp or "").strip().lower()
        if not comp:
            continue
        entry = out.setdefault(comp, {"methods": set(), "properties": set()})
        for method in row.get("methods") or []:
            if method:
                entry["methods"].add(str(method))
        for prop in row.get("properties") or []:
            if prop:
                entry["properties"].add(str(prop))
    return out


def _component_calls_from_map(calls_map: Dict[str, Dict[str, Set[str]]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for comp in sorted(calls_map.keys()):
        entry = calls_map.get(comp) or {}
        out.append(
            {
                "component": comp,
                "methods": sorted(entry.get("methods") or []),
                "properties": sorted(entry.get("properties") or []),
            }
        )
    return out


def _scan_prefab_details(engine: Any, resource_index: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    prefab_files = [
        f for f in getattr(engine, "file_list", []) if str(f).startswith("scripts/prefabs/") and str(f).endswith(".lua")
    ]

    file_prefabs: Dict[str, List[str]] = {}
    prefabs_meta = (resource_index or {}).get("prefabs") or {}
    files_meta = prefabs_meta.get("files") if isinstance(prefabs_meta, dict) else None
    if isinstance(files_meta, list):
        for row in files_meta:
            if not isinstance(row, dict):
                continue
            path = row.get("path")
            prefabs = row.get("prefabs") or []
            if not path or not isinstance(prefabs, list):
                continue
            file_prefabs[str(path)] = [str(p).strip().lower() for p in prefabs if p]

    store: Dict[str, Dict[str, Any]] = {}
    for path in prefab_files:
        content = engine.read_file(path) or ""
        if not content:
            continue
        parsed = PrefabParser(content, path=path).parse()
        events = [str(e).strip() for e in (parsed.get("events") or []) if str(e).strip()]
        assets = _normalize_prefab_assets(parsed.get("assets"))
        comp_calls = _component_calls_from_map(_component_calls_to_map(parsed.get("components")))
        if not events and not assets and not comp_calls:
            continue

        prefabs = file_prefabs.get(str(path)) or []
        if not prefabs:
            fallback = parsed.get("prefab_name") or Path(str(path)).stem
            if fallback:
                prefabs = [str(fallback).strip().lower()]

        for pid in prefabs:
            if not pid:
                continue
            bucket = store.setdefault(pid, {"events": set(), "assets": {}, "component_calls": {}})
            bucket["events"].update(events)
            for asset in assets:
                key = f"{asset.get('type')}:{asset.get('path')}"
                bucket["assets"][key] = asset
            comp_map = bucket["component_calls"]
            incoming = _component_calls_to_map(comp_calls)
            for comp, data in incoming.items():
                entry = comp_map.setdefault(comp, {"methods": set(), "properties": set()})
                entry["methods"].update(data.get("methods") or set())
                entry["properties"].update(data.get("properties") or set())

    out: Dict[str, Dict[str, Any]] = {}
    for pid, bucket in store.items():
        row: Dict[str, Any] = {}
        events = sorted(bucket.get("events") or [])
        if events:
            row["events"] = events
        assets_map = bucket.get("assets") or {}
        if assets_map:
            row["assets"] = [assets_map[k] for k in sorted(assets_map.keys())]
        calls_map = bucket.get("component_calls") or {}
        if calls_map:
            row["component_calls"] = _component_calls_from_map(calls_map)
        out[pid] = row

    return out


def _merge_list(base: Any, extra: Any) -> List[str]:
    base_list = [str(x) for x in (base or []) if x]
    extra_list = [str(x) for x in (extra or []) if x]
    return sorted(set(base_list) | set(extra_list))


def _merge_component_calls(base: Any, extra: Any) -> List[Dict[str, Any]]:
    base_map = _component_calls_to_map(base)
    extra_map = _component_calls_to_map(extra)
    for comp, data in extra_map.items():
        entry = base_map.setdefault(comp, {"methods": set(), "properties": set()})
        entry["methods"].update(data.get("methods") or set())
        entry["properties"].update(data.get("properties") or set())
    return _component_calls_from_map(base_map)


def _merge_assets(base: Any, extra: Any) -> List[Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {}
    for row in _normalize_prefab_assets(base) + _normalize_prefab_assets(extra):
        key = f"{row.get('type')}:{row.get('path')}"
        merged[key] = row
    return [merged[k] for k in sorted(merged.keys())]


def _build_prefab_links(
    resource_index: Optional[Dict[str, Any]],
    prefab_details: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    prefabs = (resource_index or {}).get("prefabs") or {}
    items = prefabs.get("items") or {}
    if not isinstance(items, dict):
        items = {}

    out: Dict[str, Dict[str, Any]] = {}
    for iid, row in items.items():
        if not iid or not isinstance(row, dict):
            continue
        entry = {
            "components": sorted({str(x) for x in (row.get("components") or []) if x}),
            "tags": sorted({str(x) for x in (row.get("tags") or []) if x}),
            "brains": sorted({str(x) for x in (row.get("brains") or []) if x}),
            "stategraphs": sorted({str(x) for x in (row.get("stategraphs") or []) if x}),
            "helpers": sorted({str(x) for x in (row.get("helpers") or []) if x}),
            "files": sorted({str(x) for x in (row.get("files") or []) if x}),
        }
        assets = _normalize_prefab_assets(row.get("assets"))
        if assets:
            entry["assets"] = assets
        out[str(iid)] = entry

    if prefab_details:
        for pid, extra in prefab_details.items():
            if not pid or not isinstance(extra, dict):
                continue
            entry = out.setdefault(
                str(pid),
                {
                    "components": [],
                    "tags": [],
                    "brains": [],
                    "stategraphs": [],
                    "helpers": [],
                    "files": [],
                },
            )
            events = _merge_list(entry.get("events"), extra.get("events"))
            if events:
                entry["events"] = events
            assets = _merge_assets(entry.get("assets"), extra.get("assets"))
            if assets:
                entry["assets"] = assets
            component_calls = _merge_component_calls(entry.get("component_calls"), extra.get("component_calls"))
            if component_calls:
                entry["component_calls"] = component_calls
                entry["components"] = _merge_list(
                    entry.get("components"),
                    [row.get("component") for row in component_calls if isinstance(row, dict)],
                )
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


def render_mechanism_crosscheck_report(
    resource_index: Optional[Dict[str, Any]],
    mechanism_index: Dict[str, Any],
) -> str:
    lines: List[str] = []
    lines.append("# Wagstaff Mechanism Crosscheck Report")
    lines.append("")

    if not resource_index or not isinstance(resource_index, dict):
        lines.append("Resource index not available; crosscheck skipped.")
        return "\n".join(lines) + "\n"

    res_prefabs = (resource_index.get("prefabs") or {}).get("items") or {}
    mech_prefabs = (mechanism_index.get("prefabs") or {}).get("items") or {}

    if not isinstance(res_prefabs, dict):
        res_prefabs = {}
    if not isinstance(mech_prefabs, dict):
        mech_prefabs = {}

    res_prefab_ids = {str(k) for k in res_prefabs.keys() if k}
    mech_prefab_ids = {str(k) for k in mech_prefabs.keys() if k}

    missing_prefabs = sorted(res_prefab_ids - mech_prefab_ids)
    extra_prefabs = sorted(mech_prefab_ids - res_prefab_ids)

    res_components_used: Set[str] = set()
    prefabs_without_components: List[str] = []
    for pid, row in res_prefabs.items():
        comps = row.get("components") if isinstance(row, dict) else None
        if not isinstance(comps, list) or not comps:
            prefabs_without_components.append(str(pid))
            continue
        for c in comps:
            if c:
                res_components_used.add(str(c))

    mech_components = (mechanism_index.get("components") or {}).get("items") or {}
    if not isinstance(mech_components, dict):
        mech_components = {}
    mech_component_ids = {str(k) for k in mech_components.keys() if k}
    mech_component_usage = mechanism_index.get("component_usage") or {}
    mech_component_used = {str(k) for k in mech_component_usage.keys() if k}

    missing_component_defs = sorted(res_components_used - mech_component_ids)
    unused_component_defs = sorted(mech_component_ids - mech_component_used)

    lines.append("## Counts")
    lines.append("```yaml")
    lines.append(f"resource_prefabs: {len(res_prefab_ids)}")
    lines.append(f"mechanism_prefabs: {len(mech_prefab_ids)}")
    lines.append(f"missing_prefabs: {len(missing_prefabs)}")
    lines.append(f"extra_prefabs: {len(extra_prefabs)}")
    lines.append(f"resource_components_used: {len(res_components_used)}")
    lines.append(f"mechanism_components_defined: {len(mech_component_ids)}")
    lines.append(f"missing_component_defs: {len(missing_component_defs)}")
    lines.append(f"unused_component_defs: {len(unused_component_defs)}")
    lines.append(f"prefabs_without_components: {len(prefabs_without_components)}")
    lines.append("```")
    lines.append("")

    def _section(title: str, items: List[str], limit: int = 40) -> None:
        lines.append(f"## {title}")
        if not items:
            lines.append("")
            lines.append("(none)")
            lines.append("")
            return
        lines.append("")
        lines.append("```text")
        for x in items[:limit]:
            lines.append(str(x))
        if len(items) > limit:
            lines.append(f"... ({len(items) - limit} more)")
        lines.append("```")
        lines.append("")

    _section("Missing Prefabs in Mechanism Index", missing_prefabs)
    _section("Extra Prefabs in Mechanism Index", extra_prefabs)
    _section("Missing Component Definitions", missing_component_defs)
    _section("Unused Component Definitions", unused_component_defs)
    _section("Prefabs Without Components (Resource Index)", prefabs_without_components)

    return "\n".join(lines) + "\n"


def build_mechanism_index(
    *,
    engine: Any,
    resource_index: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    components = _scan_components(engine)
    prefab_details = _scan_prefab_details(engine, resource_index)
    prefab_links = _build_prefab_links(resource_index, prefab_details)
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static mechanics coverage baseline + component capability map."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.indexers.catalog_v2 import _STAT_METHODS, _STAT_PROPERTIES  # noqa: E402
from core.schemas.meta import now_iso  # noqa: E402
from core.version import versions  # noqa: E402


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _stat_map() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for comp, mapping in _STAT_METHODS.items():
        entry = out.setdefault(comp, {"setters": {}, "properties": {}, "stat_keys": set()})
        for method, specs in mapping.items():
            keys = [k for k, _ in specs]
            entry["setters"][method] = keys
            entry["stat_keys"].update(keys)
    for comp, mapping in _STAT_PROPERTIES.items():
        entry = out.setdefault(comp, {"setters": {}, "properties": {}, "stat_keys": set()})
        entry["properties"].update(mapping)
        entry["stat_keys"].update(mapping.values())
    # normalize stat_keys to sorted list
    for comp, entry in out.items():
        entry["stat_keys"] = sorted(set(entry.get("stat_keys") or []))
    return out


def _value_present(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    value = entry.get("value")
    if value is not None:
        return True
    return False


def build_report(
    *,
    catalog_doc: Dict[str, Any],
    mechanism_doc: Dict[str, Any],
) -> Dict[str, Any]:
    stat_map = _stat_map()
    items = catalog_doc.get("items") if isinstance(catalog_doc, dict) else None
    items = items if isinstance(items, dict) else {}

    component_usage = mechanism_doc.get("component_usage") if isinstance(mechanism_doc, dict) else {}
    component_usage = component_usage if isinstance(component_usage, dict) else {}

    comp_items: Dict[str, Set[str]] = {comp: set() for comp in stat_map.keys()}
    comp_stats_items: Dict[str, int] = {comp: 0 for comp in stat_map.keys()}
    comp_field_hits: Dict[str, Counter] = {comp: Counter() for comp in stat_map.keys()}
    comp_value_hits: Dict[str, Counter] = {comp: Counter() for comp in stat_map.keys()}

    for iid, item in items.items():
        if not isinstance(item, dict):
            continue
        comps = [str(c) for c in (item.get("components") or []) if c]
        stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
        for comp in comps:
            if comp not in stat_map:
                continue
            comp_items[comp].add(str(iid))
            keys = stat_map[comp]["stat_keys"]
            hit_any = False
            for key in keys:
                if key in stats:
                    hit_any = True
                    comp_field_hits[comp][key] += 1
                    if _value_present(stats.get(key)):
                        comp_value_hits[comp][key] += 1
            if hit_any:
                comp_stats_items[comp] += 1

    components_out: Dict[str, Any] = {}
    total_component_items = 0
    total_component_stats = 0
    total_field_slots = 0
    total_field_hits = 0
    total_value_hits = 0

    for comp, entry in stat_map.items():
        items_total = len(comp_items.get(comp, set()))
        stats_items = comp_stats_items.get(comp, 0)
        fields = entry.get("stat_keys") or []
        field_total = len(fields)

        total_component_items += items_total
        total_component_stats += stats_items
        total_field_slots += items_total * field_total
        total_field_hits += sum(comp_field_hits.get(comp, Counter()).values())
        total_value_hits += sum(comp_value_hits.get(comp, Counter()).values())

        c0 = (stats_items / items_total) if items_total else 0.0
        c1 = (sum(comp_field_hits.get(comp, Counter()).values()) / (items_total * field_total)) if items_total and field_total else 0.0
        c2 = (sum(comp_value_hits.get(comp, Counter()).values()) / (items_total * field_total)) if items_total and field_total else 0.0

        field_cov = []
        value_cov = []
        for key in fields:
            hits = comp_field_hits.get(comp, Counter()).get(key, 0)
            val_hits = comp_value_hits.get(comp, Counter()).get(key, 0)
            ratio = (hits / items_total) if items_total else 0.0
            val_ratio = (val_hits / items_total) if items_total else 0.0
            field_cov.append({"key": key, "items": items_total, "with_stats": hits, "coverage": ratio})
            value_cov.append({"key": key, "items": items_total, "with_value": val_hits, "coverage": val_ratio})

        prefabs = component_usage.get(comp) if isinstance(component_usage.get(comp), list) else []
        components_out[comp] = {
            "prefabs_total": len(prefabs or []),
            "items_total": items_total,
            "items_with_stats": stats_items,
            "coverage_c0": c0,
            "coverage_c1": c1,
            "coverage_c2": c2,
            "fields_total": field_total,
            "fields": field_cov,
            "values": value_cov,
            "setters": entry.get("setters") or {},
            "properties": entry.get("properties") or {},
            "stat_keys": fields,
        }

    overall_c0 = (total_component_stats / total_component_items) if total_component_items else 0.0
    overall_c1 = (total_field_hits / total_field_slots) if total_field_slots else 0.0
    overall_c2 = (total_value_hits / total_field_slots) if total_field_slots else 0.0

    return {
        "meta": {
            "tool": "static_mechanics_coverage",
            "generated": now_iso(),
            **versions(),
        },
        "summary": {
            "components_total": len(stat_map),
            "items_total": len(items),
            "component_items_total": total_component_items,
            "component_items_with_stats": total_component_stats,
            "coverage_c0": overall_c0,
            "coverage_c1": overall_c1,
            "coverage_c2": overall_c2,
        },
        "components": components_out,
    }


def render_report_md(doc: Dict[str, Any]) -> str:
    summary = doc.get("summary") or {}
    components = doc.get("components") or {}

    rows = sorted(
        components.items(),
        key=lambda kv: (kv[1].get("coverage_c1", 0.0), kv[1].get("items_total", 0)),
    )

    lines: List[str] = []
    lines.append("# Static Mechanics Coverage Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("```yaml")
    for key in (
        "components_total",
        "items_total",
        "component_items_total",
        "component_items_with_stats",
        "coverage_c0",
        "coverage_c1",
        "coverage_c2",
    ):
        val = summary.get(key)
        if isinstance(val, float):
            lines.append(f"{key}: {val:.4f}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("```")
    lines.append("")

    lines.append("## Lowest Coverage Components (C1)")
    lines.append("```yaml")
    for comp, data in rows[:12]:
        items_total = data.get("items_total", 0)
        c0 = data.get("coverage_c0", 0.0)
        c1 = data.get("coverage_c1", 0.0)
        c2 = data.get("coverage_c2", 0.0)
        lines.append(f"{comp}: items={items_total} c0={c0:.2%} c1={c1:.2%} c2={c2:.2%}")
    lines.append("```")
    lines.append("")

    lines.append("## Coverage by Component")
    lines.append("```yaml")
    for comp, data in rows:
        items_total = data.get("items_total", 0)
        stats_items = data.get("items_with_stats", 0)
        c0 = data.get("coverage_c0", 0.0)
        c1 = data.get("coverage_c1", 0.0)
        c2 = data.get("coverage_c2", 0.0)
        lines.append(
            f"{comp}: items={items_total} with_stats={stats_items} "
            f"c0={c0:.2%} c1={c1:.2%} c2={c2:.2%}"
        )
    lines.append("```")
    lines.append("")
    lines.append("## Capability Map")
    lines.append("See JSON report for setters/properties/stat_keys detail.")

    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Static mechanics coverage baseline")
    p.add_argument("--catalog", default="data/index/wagstaff_catalog_v2.json", help="Catalog v2 JSON path")
    p.add_argument("--mechanism", default="data/index/wagstaff_mechanism_index_v1.json", help="Mechanism index path")
    p.add_argument("--out-json", default="data/reports/static_mechanics_coverage_report.json", help="Output JSON path")
    p.add_argument("--out-md", default="data/reports/static_mechanics_coverage_report.md", help="Output Markdown path")
    args = p.parse_args()

    catalog_doc = _load_json((PROJECT_ROOT / args.catalog).resolve())
    mechanism_doc = _load_json((PROJECT_ROOT / args.mechanism).resolve())

    report = build_report(catalog_doc=catalog_doc, mechanism_doc=mechanism_doc)

    out_json = (PROJECT_ROOT / args.out_json).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    out_md = (PROJECT_ROOT / args.out_md).resolve()
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_report_md(report), encoding="utf-8")

    print(f"OK: Static mechanics coverage report written: {out_md}")
    print(f"OK: JSON written: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

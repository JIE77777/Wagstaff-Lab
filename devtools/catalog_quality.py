#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catalog quality/coverage report.

Metrics
- stats coverage by component
- i18n coverage by language
- tuning trace coverage (items + cooking)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.indexers.catalog_v2 import TUNING_FIELDS, _STAT_METHODS, _STAT_PROPERTIES  # noqa: E402
from core.indexers.catalog_index import load_icon_index  # noqa: E402


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _collect_component_keys() -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for comp, mapping in _STAT_METHODS.items():
        for items in mapping.values():
            for key, _ in items:
                out.setdefault(comp, set()).add(key)
    for comp, mapping in _STAT_PROPERTIES.items():
        for key in mapping.values():
            out.setdefault(comp, set()).add(key)
    return out


def _norm_id(x: str) -> str:
    return str(x or "").strip().lower()


def _trace_keys(trace_doc: Dict[str, Any]) -> Set[str]:
    if not isinstance(trace_doc, dict):
        return set()
    return {str(k) for k in trace_doc.keys() if k}


def _stat_trace_key(item_id: str, stat_key: str, entry: Dict[str, Any]) -> str:
    if isinstance(entry, dict) and entry.get("trace_key"):
        return str(entry.get("trace_key"))
    return f"item:{item_id}:stat:{stat_key}"


def _sample(items: Set[str], limit: int = 20) -> List[str]:
    return sorted(items)[:limit]


def build_report(
    *,
    catalog_doc: Dict[str, Any],
    icon_index: Dict[str, str],
    i18n_doc: Dict[str, Any],
    trace_doc: Dict[str, Any],
) -> Dict[str, Any]:
    items = catalog_doc.get("items") if isinstance(catalog_doc, dict) else None
    items = items if isinstance(items, dict) else {}
    cooking = catalog_doc.get("cooking") if isinstance(catalog_doc, dict) else None
    cooking = cooking if isinstance(cooking, dict) else {}
    assets = catalog_doc.get("assets") if isinstance(catalog_doc, dict) else None
    assets = assets if isinstance(assets, dict) else {}

    item_ids = {str(k) for k in items.keys() if k}
    asset_ids = {str(k) for k in assets.keys() if k}
    icon_ids = {str(k) for k in (icon_index or {}).keys() if k}
    all_ids = sorted(item_ids | asset_ids | icon_ids)

    # stats coverage by component
    comp_keys = _collect_component_keys()
    comp_counts: Dict[str, Dict[str, Any]] = {}
    comp_item_counts: Dict[str, int] = {}
    comp_key_hits: Dict[str, Counter] = {}
    comp_missing_items: Dict[str, List[str]] = {}
    stat_counts = Counter()

    items_with_stats = 0
    stats_total = 0
    tuning_stats_total = 0
    tuning_stats_traced = 0

    trace_keys = _trace_keys(trace_doc)

    for iid, item in items.items():
        if not isinstance(item, dict):
            continue
        comps = [str(c) for c in (item.get("components") or []) if c]
        stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
        if stats:
            items_with_stats += 1
        stats_total += len(stats or {})

        for k in stats.keys():
            stat_counts[str(k)] += 1

        for comp in comps:
            if comp not in comp_keys:
                continue
            comp_counts.setdefault(comp, {"items": 0, "with_stats": 0})
            comp_counts[comp]["items"] += 1
            comp_item_counts[comp] = comp_item_counts.get(comp, 0) + 1
            keyset = comp_keys.get(comp) or set()
            hit = any(k in stats for k in keyset)
            if hit:
                comp_counts[comp]["with_stats"] += 1
            else:
                comp_missing_items.setdefault(comp, []).append(iid)
            if keyset:
                comp_key_hits.setdefault(comp, Counter())
                for k in stats.keys():
                    if k in keyset:
                        comp_key_hits[comp][k] += 1

        for sk, entry in (stats or {}).items():
            if not isinstance(entry, dict):
                continue
            expr = entry.get("expr")
            if isinstance(expr, str) and "TUNING." in expr:
                tuning_stats_total += 1
                tkey = _stat_trace_key(iid, sk, entry)
                if tkey in trace_keys:
                    tuning_stats_traced += 1

    # cooking tuning trace coverage
    cooking_tuning_total = 0
    cooking_tuning_traced = 0
    for name, rec in cooking.items():
        if not isinstance(rec, dict):
            continue
        for field in TUNING_FIELDS:
            val = rec.get(field)
            expr = None
            if isinstance(val, dict):
                expr = val.get("expr") if isinstance(val.get("expr"), str) else None
            elif isinstance(val, str):
                expr = val
            if expr and "TUNING." in expr:
                cooking_tuning_total += 1
                tkey = f"cooking:{name}:{field}"
                if tkey in trace_keys:
                    cooking_tuning_traced += 1

    if cooking_tuning_total == 0:
        cooking_trace_keys = {k for k in trace_keys if k.startswith("cooking:")}
        if cooking_trace_keys:
            cooking_tuning_total = len(cooking_trace_keys)
            cooking_tuning_traced = len(cooking_trace_keys)

    # i18n coverage
    i18n_names = i18n_doc.get("names") if isinstance(i18n_doc, dict) else None
    i18n_names = i18n_names if isinstance(i18n_names, dict) else {}
    i18n_langs = sorted([str(k) for k in i18n_names.keys() if k])

    i18n_cov: Dict[str, Any] = {}
    for lang in i18n_langs:
        mp = i18n_names.get(lang) if isinstance(i18n_names.get(lang), dict) else {}
        names = {str(k) for k in mp.keys() if k}
        covered_items = len(item_ids & names)
        covered_all = len(set(all_ids) & names)
        missing_items = item_ids - names
        i18n_cov[lang] = {
            "names": len(names),
            "coverage_items": {
                "total": len(item_ids),
                "covered": covered_items,
            },
            "coverage_all_ids": {
                "total": len(all_ids),
                "covered": covered_all,
            },
            "missing_items": len(missing_items),
            "missing_items_sample": _sample(missing_items, 20),
        }

    comp_out: Dict[str, Any] = {}
    comp_missing: Dict[str, List[str]] = {}
    comp_low_coverage: Dict[str, List[Dict[str, Any]]] = {}
    comp_missing_items_out: Dict[str, Any] = {}
    for comp, data in comp_counts.items():
        total = data.get("items") or 0
        with_stats = data.get("with_stats") or 0
        ratio = (with_stats / total) if total else 0.0
        comp_out[comp] = {"items": total, "with_stats": with_stats, "coverage": ratio}
        missing_items = sorted(set(comp_missing_items.get(comp, [])))
        comp_missing_items_out[comp] = {
            "missing": len(missing_items),
            "sample": missing_items[:30],
        }

    for comp, keys in comp_keys.items():
        total = comp_item_counts.get(comp, 0)
        hits = comp_key_hits.get(comp, Counter())
        missing = sorted([k for k in keys if hits.get(k, 0) == 0])
        comp_missing[comp] = missing
        if total:
            rows: List[Dict[str, Any]] = []
            for k in sorted(keys):
                with_stats = hits.get(k, 0)
                cov = with_stats / total
                rows.append({"key": k, "items": total, "with_stats": with_stats, "coverage": cov})
            rows.sort(key=lambda r: (r["coverage"], -r["items"]))
            comp_low_coverage[comp] = rows[:5]

    top_stats = stat_counts.most_common(40)

    # i18n UI coverage
    i18n_ui = i18n_doc.get("ui") if isinstance(i18n_doc, dict) else None
    i18n_ui = i18n_ui if isinstance(i18n_ui, dict) else {}
    ui_langs = sorted([str(k) for k in i18n_ui.keys() if k])
    base_lang = "en" if "en" in i18n_ui else (ui_langs[0] if ui_langs else "")
    base_keys = set()
    if base_lang:
        base_keys = {str(k) for k in (i18n_ui.get(base_lang) or {}).keys() if k}
    if not base_keys and i18n_ui:
        for mp in i18n_ui.values():
            if isinstance(mp, dict):
                base_keys.update([str(k) for k in mp.keys() if k])

    ui_cov: Dict[str, Any] = {}
    for lang in ui_langs:
        mp = i18n_ui.get(lang) if isinstance(i18n_ui.get(lang), dict) else {}
        keys = {str(k) for k in mp.keys() if k}
        missing = sorted(base_keys - keys) if base_keys else []
        ui_cov[lang] = {
            "keys": len(keys),
            "base": len(base_keys),
            "missing": len(missing),
            "missing_sample": missing[:20],
        }

    return {
        "counts": {
            "items_total": len(item_ids),
            "assets_total": len(asset_ids),
            "icons_total": len(icon_ids),
            "all_ids_total": len(all_ids),
            "items_with_stats": items_with_stats,
            "stats_total": stats_total,
        },
        "stats_coverage": {
            "by_component": comp_out,
            "top_stats": top_stats,
            "missing_keys": comp_missing,
            "low_coverage_keys": comp_low_coverage,
            "missing_items": comp_missing_items_out,
        },
        "tuning_trace": {
            "items": {
                "tuning_exprs": tuning_stats_total,
                "with_trace": tuning_stats_traced,
            },
            "cooking": {
                "tuning_exprs": cooking_tuning_total,
                "with_trace": cooking_tuning_traced,
            },
        },
        "i18n": {
            "langs": i18n_langs,
            "coverage": i18n_cov,
            "ui_langs": ui_langs,
            "ui_base_lang": base_lang,
            "ui_coverage": ui_cov,
        },
    }


def render_report_md(doc: Dict[str, Any]) -> str:
    counts = doc.get("counts") or {}
    stats_cov = doc.get("stats_coverage") or {}
    trace = doc.get("tuning_trace") or {}
    i18n = doc.get("i18n") or {}

    lines: List[str] = []
    lines.append("# Catalog Quality Report")
    lines.append("")
    lines.append("## Counts")
    lines.append("```yaml")
    for k, v in counts.items():
        lines.append(f"{k}: {v}")
    lines.append("```")
    lines.append("")

    lines.append("## Stats Coverage (by component)")
    lines.append("```yaml")
    comp = stats_cov.get("by_component") or {}
    # sort by coverage asc
    comp_rows = sorted(comp.items(), key=lambda kv: (kv[1].get("coverage", 0), -kv[1].get("items", 0)))
    for name, data in comp_rows:
        total = data.get("items", 0)
        with_stats = data.get("with_stats", 0)
        cov = data.get("coverage", 0.0)
        lines.append(f"{name}: {with_stats}/{total} ({cov:.2%})")
    lines.append("```")
    lines.append("")

    missing_items = stats_cov.get("missing_items") or {}
    if missing_items:
        lines.append("## Stats Missing Items (sample)")
        lines.append("```yaml")
        rows = sorted(
            missing_items.items(),
            key=lambda kv: (-(kv[1].get("missing", 0) or 0), kv[0]),
        )
        for comp, data in rows:
            missing = data.get("missing", 0)
            if not missing:
                continue
            sample = data.get("sample") or []
            sample_str = ", ".join(sample[:10])
            lines.append(f"{comp}: missing={missing} sample=[{sample_str}]")
        lines.append("```")
        lines.append("")

    lines.append("## Tuning Trace Coverage")
    lines.append("```yaml")
    items = trace.get("items") or {}
    cook = trace.get("cooking") or {}
    lines.append(f"items_tuning_exprs: {items.get('tuning_exprs', 0)}")
    lines.append(f"items_with_trace: {items.get('with_trace', 0)}")
    lines.append(f"cooking_tuning_exprs: {cook.get('tuning_exprs', 0)}")
    lines.append(f"cooking_with_trace: {cook.get('with_trace', 0)}")
    lines.append("```")
    lines.append("")

    lines.append("## i18n Coverage")
    lines.append("```yaml")
    for lang, data in (i18n.get("coverage") or {}).items():
        cov_items = data.get("coverage_items") or {}
        cov_all = data.get("coverage_all_ids") or {}
        lines.append(f"{lang}:")
        lines.append(f"  names: {data.get('names', 0)}")
        lines.append(f"  items: {cov_items.get('covered', 0)}/{cov_items.get('total', 0)}")
        lines.append(f"  all_ids: {cov_all.get('covered', 0)}/{cov_all.get('total', 0)}")
    lines.append("```")
    lines.append("")

    lines.append("## Top Stats (by frequency)")
    lines.append("```yaml")
    for stat, cnt in (stats_cov.get("top_stats") or [])[:30]:
        lines.append(f"{stat}: {cnt}")
    lines.append("```")

    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Catalog quality / coverage report")
    p.add_argument("--catalog", default="data/index/wagstaff_catalog_v2.json", help="Catalog v2 JSON path")
    p.add_argument("--icon-index", default="data/index/wagstaff_icon_index_v1.json", help="Icon index JSON path")
    p.add_argument("--i18n", default="data/index/wagstaff_i18n_v1.json", help="i18n index JSON path")
    p.add_argument("--trace", default="data/index/wagstaff_tuning_trace_v1.json", help="Tuning trace JSON path")
    p.add_argument("--out-json", default="data/reports/catalog_quality_report.json", help="Output JSON report")
    p.add_argument("--out-md", default="data/reports/catalog_quality_report.md", help="Output Markdown report")

    args = p.parse_args()

    catalog_path = (PROJECT_ROOT / args.catalog).resolve()
    icon_path = (PROJECT_ROOT / args.icon_index).resolve() if args.icon_index else None
    i18n_path = (PROJECT_ROOT / args.i18n).resolve() if args.i18n else None
    trace_path = (PROJECT_ROOT / args.trace).resolve() if args.trace else None

    catalog_doc = _load_json(catalog_path)
    icon_index = load_icon_index(icon_path) if icon_path else {}
    i18n_doc = _load_json(i18n_path) if i18n_path else {}
    trace_doc = _load_json(trace_path) if trace_path else {}

    report = build_report(
        catalog_doc=catalog_doc,
        icon_index=icon_index,
        i18n_doc=i18n_doc,
        trace_doc=trace_doc,
    )

    out_json = (PROJECT_ROOT / args.out_json).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    out_md = (PROJECT_ROOT / args.out_md).resolve()
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_report_md(report), encoding="utf-8")

    print(f"OK: Quality report written: {out_md}")
    print(f"OK: JSON written: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

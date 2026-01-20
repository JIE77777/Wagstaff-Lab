#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quality gate for Wagstaff artifacts (lightweight validation + report)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from devtools.validators import validate_mechanism_index, validate_sqlite_v4  # noqa: E402


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _as_dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _as_list(v: Any) -> List[Any]:
    return v if isinstance(v, list) else []


def _ratio(n: int, d: int) -> float:
    return (n / d) if d else 0.0


def _check_catalog(doc: Dict[str, Any], min_items: int) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    issues: List[Tuple[str, str]] = []
    meta = _as_dict(doc.get("meta"))
    schema = int(doc.get("schema_version") or meta.get("schema") or 0)
    items = _as_dict(doc.get("items"))
    assets = _as_dict(doc.get("assets"))

    if schema < 2:
        issues.append(("warn", f"catalog schema_version < 2 ({schema})"))

    items_total = len(items)
    assets_total = len(assets)
    if items_total < min_items:
        issues.append(("fail", f"catalog items_total too small ({items_total} < {min_items})"))

    items_with_stats = 0
    stats_total = 0
    for item in items.values():
        if not isinstance(item, dict):
            continue
        stats = item.get("stats")
        if isinstance(stats, dict) and stats:
            items_with_stats += 1
            stats_total += len(stats)

    return {
        "schema_version": schema,
        "items_total": items_total,
        "assets_total": assets_total,
        "items_with_stats": items_with_stats,
        "stats_total": stats_total,
        "stats_ratio": _ratio(items_with_stats, items_total),
    }, issues


def _check_catalog_index(doc: Dict[str, Any], items_total: int) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    issues: List[Tuple[str, str]] = []
    items = _as_list(doc.get("items"))
    indexes = _as_dict(doc.get("indexes"))
    counts = _as_dict(doc.get("counts"))

    if not items:
        issues.append(("fail", "catalog index has no items"))
    if not indexes:
        issues.append(("warn", "catalog index missing indexes section"))

    index_items = len(items)
    if items_total and index_items < items_total:
        issues.append(("warn", f"catalog index items < catalog items ({index_items} < {items_total})"))

    return {
        "items_total": index_items,
        "has_indexes": bool(indexes),
        "counts_items": counts.get("items_total"),
    }, issues


def _check_icon_index(doc: Dict[str, Any], min_icons: int) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    issues: List[Tuple[str, str]] = []
    icons = _as_dict(doc.get("icons"))
    icons_total = len(icons)
    if icons_total < min_icons:
        issues.append(("warn", f"icon index icons_total too small ({icons_total} < {min_icons})"))
    return {"icons_total": icons_total}, issues


def _check_i18n(doc: Dict[str, Any], items_total: int, min_ratio: float) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    issues: List[Tuple[str, str]] = []
    names = _as_dict(doc.get("names"))
    langs = [k for k in names.keys() if k]
    coverage: Dict[str, Any] = {}
    for lang in langs:
        mp = _as_dict(names.get(lang))
        ratio = _ratio(len(mp), items_total)
        coverage[lang] = {"names": len(mp), "ratio": ratio}
        if ratio < min_ratio:
            issues.append(("warn", f"i18n coverage low for {lang} ({ratio:.2%} < {min_ratio:.2%})"))
    return {"langs": langs, "coverage": coverage}, issues


def _check_tuning_trace(doc: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    issues: List[Tuple[str, str]] = []
    total = len(doc)
    cooking = len([k for k in doc.keys() if str(k).startswith("cooking:")])
    items = len([k for k in doc.keys() if str(k).startswith("item:")])
    if total == 0:
        issues.append(("warn", "tuning trace file is empty"))
    return {"total": total, "items": items, "cooking": cooking}, issues


def render_report(
    *,
    inputs: Dict[str, str],
    summary: Dict[str, Any],
    issues: List[Tuple[str, str]],
) -> str:
    lines: List[str] = []
    lines.append("# Quality Gate Report")
    lines.append("")
    lines.append("## Inputs")
    lines.append("```yaml")
    for k, v in inputs.items():
        lines.append(f"{k}: {v}")
    lines.append("```")
    lines.append("")
    lines.append("## Summary")
    lines.append("```yaml")
    for k, v in summary.items():
        lines.append(f"{k}: {v}")
    lines.append("```")
    lines.append("")
    lines.append("## Issues")
    if not issues:
        lines.append("- PASS: no issues detected")
    else:
        for level, msg in issues:
            lines.append(f"- {level.upper()}: {msg}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Quality gate for Wagstaff artifacts")
    p.add_argument("--catalog", default="data/index/wagstaff_catalog_v2.json", help="Catalog v2 JSON path")
    p.add_argument("--catalog-index", default="data/index/wagstaff_catalog_index_v1.json", help="Catalog index JSON path")
    p.add_argument("--icon-index", default="data/index/wagstaff_icon_index_v1.json", help="Icon index JSON path")
    p.add_argument("--i18n", default="data/index/wagstaff_i18n_v1.json", help="i18n index JSON path")
    p.add_argument("--tuning-trace", default="data/index/wagstaff_tuning_trace_v1.json", help="Tuning trace JSON path")
    p.add_argument(
        "--mechanism",
        default="data/index/wagstaff_mechanism_index_v1.json",
        help="Mechanism index JSON path",
    )
    p.add_argument("--catalog-sqlite", default="data/index/wagstaff_catalog_v2.sqlite", help="Catalog SQLite path")
    p.add_argument(
        "--mechanism-sqlite",
        default="data/index/wagstaff_mechanism_index_v1.sqlite",
        help="Mechanism SQLite path",
    )
    p.add_argument("--skip-sqlite", action="store_true", help="Skip SQLite v4 validation")
    p.add_argument("--skip-mechanism", action="store_true", help="Skip mechanism index validation")
    p.add_argument("--min-items", type=int, default=1000, help="Minimum catalog items to pass")
    p.add_argument("--min-icons", type=int, default=1000, help="Minimum icon entries to warn")
    p.add_argument("--min-i18n-ratio", type=float, default=0.30, help="Minimum i18n coverage ratio to warn")
    p.add_argument("--strict", action="store_true", help="Treat warnings as failures (only when --enforce)")
    p.add_argument("--enforce", action="store_true", help="Exit non-zero on failures (for CI/release)")
    p.add_argument("--out", default="data/reports/quality_gate_report.md", help="Output report path")
    p.add_argument("--out-json", default="data/reports/quality_gate_report.json", help="Output JSON report path")
    args = p.parse_args()

    inputs = {
        "catalog": args.catalog,
        "catalog_index": args.catalog_index,
        "icon_index": args.icon_index,
        "i18n": args.i18n,
        "tuning_trace": args.tuning_trace,
        "mechanism": args.mechanism,
        "catalog_sqlite": args.catalog_sqlite,
        "mechanism_sqlite": args.mechanism_sqlite,
    }

    issues: List[Tuple[str, str]] = []
    summary: Dict[str, Any] = {}

    # catalog
    catalog_path = (PROJECT_ROOT / args.catalog).resolve()
    catalog_doc = _load_json(catalog_path)
    if catalog_doc is None:
        issues.append(("fail", f"catalog missing or unreadable: {catalog_path}"))
        catalog_metrics = {"items_total": 0, "assets_total": 0, "items_with_stats": 0, "stats_total": 0}
    else:
        catalog_metrics, catalog_issues = _check_catalog(catalog_doc, min_items=int(args.min_items))
        issues.extend(catalog_issues)
    summary.update({f"catalog_{k}": v for k, v in catalog_metrics.items()})

    # catalog index
    idx_path = (PROJECT_ROOT / args.catalog_index).resolve()
    idx_doc = _load_json(idx_path)
    if idx_doc is None:
        issues.append(("fail", f"catalog index missing or unreadable: {idx_path}"))
    else:
        idx_metrics, idx_issues = _check_catalog_index(idx_doc, int(summary.get("catalog_items_total") or 0))
        issues.extend(idx_issues)
        summary.update({f"catalog_index_{k}": v for k, v in idx_metrics.items()})

    # icon index
    icon_path = (PROJECT_ROOT / args.icon_index).resolve()
    icon_doc = _load_json(icon_path)
    if icon_doc is None:
        issues.append(("warn", f"icon index missing or unreadable: {icon_path}"))
    else:
        icon_metrics, icon_issues = _check_icon_index(icon_doc, int(args.min_icons))
        issues.extend(icon_issues)
        summary.update({f"icon_{k}": v for k, v in icon_metrics.items()})

    # i18n
    i18n_path = (PROJECT_ROOT / args.i18n).resolve()
    i18n_doc = _load_json(i18n_path)
    if i18n_doc is None:
        issues.append(("warn", f"i18n index missing or unreadable: {i18n_path}"))
    else:
        i18n_metrics, i18n_issues = _check_i18n(
            i18n_doc,
            int(summary.get("catalog_items_total") or 0),
            float(args.min_i18n_ratio),
        )
        issues.extend(i18n_issues)
        summary.update({f"i18n_{k}": v for k, v in i18n_metrics.items()})

    # tuning trace
    trace_path = (PROJECT_ROOT / args.tuning_trace).resolve()
    trace_doc = _load_json(trace_path)
    if trace_doc is None:
        issues.append(("warn", f"tuning trace missing or unreadable: {trace_path}"))
    else:
        trace_metrics, trace_issues = _check_tuning_trace(trace_doc)
        issues.extend(trace_issues)
        summary.update({f"trace_{k}": v for k, v in trace_metrics.items()})

    # mechanism index (optional)
    if not args.skip_mechanism:
        mech_path = (PROJECT_ROOT / args.mechanism).resolve()
        mech_doc = _load_json(mech_path)
        if mech_doc is None:
            issues.append(("warn", f"mechanism index missing or unreadable: {mech_path}"))
        else:
            mech_counts = _as_dict(mech_doc.get("counts"))
            summary["mechanism_schema_version"] = int(
                mech_doc.get("schema_version") or (mech_doc.get("meta") or {}).get("schema") or 0
            )
            summary["mechanism_components_total"] = int(mech_counts.get("components_total") or 0)
            summary["mechanism_prefabs_total"] = int(mech_counts.get("prefabs_total") or 0)
            summary["mechanism_prefab_component_edges"] = int(mech_counts.get("prefab_component_edges") or 0)

            mech_result = validate_mechanism_index(mech_doc)
            mech_errors = mech_result.get("errors") or []
            mech_warnings = mech_result.get("warnings") or []
            summary["mechanism_validation_errors"] = len(mech_errors)
            summary["mechanism_validation_warnings"] = len(mech_warnings)
            for msg in mech_errors:
                issues.append(("fail", f"mechanism index: {msg}"))
            for msg in mech_warnings:
                issues.append(("warn", f"mechanism index: {msg}"))

    # sqlite v4
    if not args.skip_sqlite:
        catalog_sqlite = (PROJECT_ROOT / args.catalog_sqlite).resolve()
        catalog_summary, catalog_issues = validate_sqlite_v4(catalog_sqlite, kind="catalog")
        issues.extend(catalog_issues)
        summary.update({f"sqlite_catalog_{k}": v for k, v in catalog_summary.items()})

        mechanism_sqlite = (PROJECT_ROOT / args.mechanism_sqlite).resolve()
        mech_summary, mech_issues = validate_sqlite_v4(mechanism_sqlite, kind="mechanism")
        issues.extend(mech_issues)
        summary.update({f"sqlite_mechanism_{k}": v for k, v in mech_summary.items()})

    issue_counts = {"fail": 0, "warn": 0}
    for level, _ in issues:
        if level in issue_counts:
            issue_counts[level] += 1
    summary["issues_total"] = len(issues)
    summary["issues_fail"] = issue_counts["fail"]
    summary["issues_warn"] = issue_counts["warn"]

    out_path = (PROJECT_ROOT / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_report(inputs=inputs, summary=summary, issues=issues), encoding="utf-8")

    out_json_path = (PROJECT_ROOT / args.out_json).resolve()
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json = {
        "inputs": inputs,
        "summary": summary,
        "issues": [{"level": level, "message": msg} for level, msg in issues],
    }
    out_json_path.write_text(json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: Quality gate report written: {out_path}")
    print(f"OK: Quality gate JSON written: {out_json_path}")

    if not args.enforce:
        return 0
    fails = [i for i in issues if i[0] == "fail"]
    warns = [i for i in issues if i[0] == "warn"]
    if fails:
        return 2
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

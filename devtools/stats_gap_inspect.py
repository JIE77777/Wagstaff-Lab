#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stats gap inspection for prefab assignments (heuristic).

Focus: equippable / rechargeable / heater missing stats.
Outputs JSON + Markdown reports for manual review.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.lua import LuaCallExtractor, strip_lua_comments  # noqa: E402
from core.indexers.catalog_v2 import _STAT_METHODS, _STAT_PROPERTIES  # noqa: E402


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


def _read_zip(zip_obj: Optional[zipfile.ZipFile], name: str) -> str:
    if zip_obj is None:
        return ""
    try:
        return zip_obj.read(name).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _load_prefab_source(
    *,
    zip_obj: Optional[zipfile.ZipFile],
    zip_paths: Set[str],
    rel_path: str,
) -> str:
    rel = rel_path.lstrip("/")
    if rel in zip_paths:
        return _read_zip(zip_obj, rel)
    path = Path(rel_path)
    if path.exists():
        return _read_file(path)
    return ""


def _extract_aliases(clean: str, comp: str) -> Set[str]:
    aliases: Set[str] = set()
    for m in re.finditer(
        rf"\blocal\s+([A-Za-z0-9_]+)\s*=\s*(?:inst|self)[.:]AddComponent\(\s*['\"]{re.escape(comp)}['\"]",
        clean,
    ):
        aliases.add(m.group(1))
    for m in re.finditer(
        rf"\b([A-Za-z0-9_]+)\s*=\s*(?:inst|self)[.:]AddComponent\(\s*['\"]{re.escape(comp)}['\"]",
        clean,
    ):
        aliases.add(m.group(1))
    for m in re.finditer(
        rf"\blocal\s+([A-Za-z0-9_]+)\s*=\s*(?:inst|self)\.components\.{re.escape(comp)}\b",
        clean,
    ):
        aliases.add(m.group(1))
    for m in re.finditer(
        rf"\b([A-Za-z0-9_]+)\s*=\s*(?:inst|self)\.components\.{re.escape(comp)}\b",
        clean,
    ):
        aliases.add(m.group(1))
    return aliases


def _classify_expr(expr: str) -> Set[str]:
    flags: Set[str] = set()
    if not expr:
        return flags
    low = expr.lower()
    if "function" in low:
        flags.add("function")
    if re.search(r"\b(if|then|elseif)\b", low):
        flags.add("conditional")
    if re.search(r"\b(and|or)\b", low):
        flags.add("conditional")
    return flags


def _inspect_component(
    *,
    comp: str,
    content: str,
    raw_lines: List[str],
) -> List[Dict[str, Any]]:
    clean = strip_lua_comments(content or "")
    clean_lines = clean.splitlines()

    prop_map = _STAT_PROPERTIES.get(comp, {})
    method_names = set((_STAT_METHODS.get(comp) or {}).keys())

    bases = [f"components.{comp}"]
    aliases = sorted(_extract_aliases(clean, comp))
    alias_set = set(aliases)
    bases.extend(aliases)

    records: List[Dict[str, Any]] = []
    for idx, line in enumerate(clean_lines, start=1):
        for base in bases:
            if base not in line:
                continue
            # property assignment
            m = re.search(rf"\b{re.escape(base)}\.([A-Za-z0-9_]+)\s*=\s*(.+)$", line)
            if m:
                prop = m.group(1).strip().lower()
                if prop in prop_map:
                    expr = m.group(2).strip().rstrip(",")
                    flags = _classify_expr(expr)
                    if prop.endswith("fn"):
                        flags.add("function")
                    records.append(
                        {
                            "line": idx,
                            "kind": "prop",
                            "name": prop,
                            "expr": expr,
                            "flags": sorted(flags),
                            "text": (raw_lines[idx - 1].strip() if idx - 1 < len(raw_lines) else line.strip()),
                        }
                    )
                    continue
    if method_names:
        extractor = LuaCallExtractor(content)
        for call in extractor.iter_calls(method_names, include_member_calls=True):
            cname = None
            m = re.search(r"\bcomponents\.([A-Za-z0-9_]+)\b", call.full_name)
            if m:
                cname = m.group(1).lower()
            else:
                root = re.split(r"[.:]", call.full_name, 1)[0]
                if root in alias_set:
                    cname = comp
            if cname != comp:
                continue
            args = call.args.strip()
            flags = _classify_expr(args)
            if call.name.lower().endswith("fn"):
                flags.add("function")
            line_idx = call.line
            records.append(
                {
                    "line": line_idx,
                    "kind": "method",
                    "name": call.name,
                    "expr": args,
                    "flags": sorted(flags),
                    "text": (
                        raw_lines[line_idx - 1].strip() if line_idx - 1 < len(raw_lines) else call.full_name
                    ),
                }
            )
    return records


def _summarize_item(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    flags = {f for r in records for f in (r.get("flags") or [])}
    return {
        "records": records,
        "flags": sorted(flags),
        "has_function": "function" in flags,
        "has_conditional": "conditional" in flags,
    }


def _build_report(
    *,
    catalog_doc: Dict[str, Any],
    components: List[str],
    scripts_zip: Optional[Path],
    max_records: int,
) -> Dict[str, Any]:
    items = catalog_doc.get("items") if isinstance(catalog_doc.get("items"), dict) else {}
    comp_keys = _collect_component_keys()

    zip_obj: Optional[zipfile.ZipFile] = None
    zip_paths: Set[str] = set()
    if scripts_zip and scripts_zip.exists():
        zip_obj = zipfile.ZipFile(scripts_zip)
        zip_paths = set(zip_obj.namelist())

    out: Dict[str, Any] = {
        "meta": {
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scripts_zip": str(scripts_zip) if scripts_zip else None,
            "components": components,
        },
        "components": {},
    }

    for comp in components:
        keys = comp_keys.get(comp, set())
        missing_items: List[str] = []
        for iid, item in items.items():
            if not isinstance(item, dict):
                continue
            comps = [str(c) for c in (item.get("components") or []) if c]
            if comp not in comps:
                continue
            stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
            hit = any(k in stats for k in keys)
            if not hit:
                missing_items.append(str(iid))

        missing_items = sorted(set(missing_items))
        item_details: Dict[str, Any] = {}
        fn_count = 0
        cond_count = 0
        with_records = 0

        for iid in missing_items:
            item = items.get(iid) or {}
            prefab_files = [str(p) for p in (item.get("prefab_files") or []) if p]
            records: List[Dict[str, Any]] = []
            for pfile in prefab_files:
                content = _load_prefab_source(zip_obj=zip_obj, zip_paths=zip_paths, rel_path=pfile)
                if not content:
                    continue
                raw_lines = content.splitlines()
                records.extend(_inspect_component(comp=comp, content=content, raw_lines=raw_lines))
            if max_records and len(records) > max_records:
                records = records[:max_records]

            summary = _summarize_item(records)
            if summary["records"]:
                with_records += 1
            if summary["has_function"]:
                fn_count += 1
            if summary["has_conditional"]:
                cond_count += 1

            item_details[iid] = {
                "prefab_files": prefab_files,
                "records": summary["records"],
                "flags": summary["flags"],
                "has_function": summary["has_function"],
                "has_conditional": summary["has_conditional"],
            }

        out["components"][comp] = {
            "missing_items": missing_items,
            "summary": {
                "missing": len(missing_items),
                "with_records": with_records,
                "with_function": fn_count,
                "with_conditional": cond_count,
            },
            "items": item_details,
        }

    if zip_obj:
        zip_obj.close()

    return out


def _render_md(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    meta = report.get("meta") or {}
    lines.append("# Stats Gap Inspection")
    lines.append("")
    lines.append("## Meta")
    lines.append("```yaml")
    for k in ("generated", "scripts_zip", "components"):
        lines.append(f"{k}: {meta.get(k)}")
    lines.append("```")
    lines.append("")

    comps = report.get("components") or {}
    for comp, data in comps.items():
        summary = data.get("summary") or {}
        lines.append(f"## {comp}")
        lines.append("```yaml")
        lines.append(f"missing: {summary.get('missing', 0)}")
        lines.append(f"with_records: {summary.get('with_records', 0)}")
        lines.append(f"with_function: {summary.get('with_function', 0)}")
        lines.append(f"with_conditional: {summary.get('with_conditional', 0)}")
        lines.append("```")
        lines.append("")

        items = data.get("items") or {}
        flagged = []
        for iid, info in items.items():
            flags = info.get("flags") or []
            if "function" in flags or "conditional" in flags:
                flagged.append(iid)
        flagged = sorted(flagged)[:20]
        if flagged:
            lines.append("Sample flagged items:")
            lines.append("```text")
            for iid in flagged:
                flags = ", ".join(items[iid].get("flags") or [])
                lines.append(f"- {iid}: {flags}")
            lines.append("```")
            lines.append("")

        missing = data.get("missing_items") or []
        no_records = [iid for iid in missing if not (items.get(iid) or {}).get("records")]
        no_records = sorted(no_records)[:20]
        if no_records:
            lines.append("Sample items with no detected assignments:")
            lines.append("```text")
            for iid in no_records:
                lines.append(f"- {iid}")
            lines.append("```")
            lines.append("")

        # sample lines
        sample_lines = []
        for iid, info in items.items():
            recs = info.get("records") or []
            for rec in recs:
                text = rec.get("text") or ""
                sample_lines.append((iid, rec.get("line"), text))
            if len(sample_lines) >= 10:
                break
        if sample_lines:
            lines.append("Sample lines:")
            lines.append("```text")
            for iid, line, text in sample_lines[:10]:
                lines.append(f"{iid}:L{line} {text}")
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Inspect missing stats assignments (heuristic).")
    p.add_argument("--catalog", default="data/index/wagstaff_catalog_v2.json")
    p.add_argument("--scripts-zip", default=None)
    p.add_argument("--components", default="equippable,rechargeable,heater")
    p.add_argument("--max-records", type=int, default=10)
    p.add_argument("--out-json", default="data/reports/stats_gap_inspect.json")
    p.add_argument("--out-md", default="data/reports/stats_gap_inspect.md")
    args = p.parse_args()

    catalog_path = (PROJECT_ROOT / args.catalog).resolve()
    catalog_doc = _load_json(catalog_path)

    scripts_zip = args.scripts_zip
    if not scripts_zip:
        meta = catalog_doc.get("meta") if isinstance(catalog_doc.get("meta"), dict) else {}
        scripts_zip = meta.get("scripts_zip")
    scripts_zip_path = Path(scripts_zip) if scripts_zip else None

    components = [c.strip().lower() for c in str(args.components).split(",") if c.strip()]

    report = _build_report(
        catalog_doc=catalog_doc,
        components=components,
        scripts_zip=scripts_zip_path,
        max_records=args.max_records,
    )

    out_json = (PROJECT_ROOT / args.out_json).resolve()
    out_md = (PROJECT_ROOT / args.out_md).resolve()
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(_render_md(report), encoding="utf-8")

    print(f"OK: Report written: {out_md}")
    print(f"OK: JSON written: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

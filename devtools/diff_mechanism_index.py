#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diff two mechanism index JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def _load(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to read {path}: {exc}") from exc


def _as_set(obj: Any) -> Set[str]:
    if isinstance(obj, list):
        return {str(x) for x in obj if x}
    return set()


def _component_ids(doc: Dict[str, Any]) -> Set[str]:
    items = (doc.get("components") or {}).get("items") or {}
    if not isinstance(items, dict):
        return set()
    return {str(k) for k in items.keys() if k}


def _prefab_ids(doc: Dict[str, Any]) -> Set[str]:
    items = (doc.get("prefabs") or {}).get("items") or {}
    if not isinstance(items, dict):
        return set()
    return {str(k) for k in items.keys() if k}


def _link_pairs(doc: Dict[str, Any]) -> Set[Tuple[str, str]]:
    links = (doc.get("links") or {}).get("prefab_component") or []
    if not isinstance(links, list):
        return set()
    out: Set[Tuple[str, str]] = set()
    for row in links:
        if not isinstance(row, dict):
            continue
        if row.get("source") != "prefab" or row.get("target") != "component":
            continue
        src = row.get("source_id")
        tgt = row.get("target_id")
        if src and tgt:
            out.add((str(src), str(tgt)))
    return out


def _counts(doc: Dict[str, Any]) -> Dict[str, int]:
    counts = doc.get("counts") or {}
    if not isinstance(counts, dict):
        return {}
    out: Dict[str, int] = {}
    for k, v in counts.items():
        try:
            out[str(k)] = int(v)
        except Exception:
            continue
    return out


def _print_section(title: str, items: List[str], limit: int) -> None:
    print(f"## {title}")
    if not items:
        print("(none)")
        print("")
        return
    print("```text")
    for x in items[:limit]:
        print(x)
    if len(items) > limit:
        print(f"... ({len(items) - limit} more)")
    print("```")
    print("")


def main() -> int:
    p = argparse.ArgumentParser(description="Diff two mechanism index JSON files.")
    p.add_argument("--a", required=True, help="Path to baseline JSON")
    p.add_argument("--b", required=True, help="Path to target JSON")
    p.add_argument("--limit", type=int, default=40, help="Max items per section")
    args = p.parse_args()

    path_a = Path(args.a).expanduser().resolve()
    path_b = Path(args.b).expanduser().resolve()
    if not path_a.exists() or not path_b.exists():
        print("❌ Missing input file", file=sys.stderr)
        return 1

    doc_a = _load(path_a)
    doc_b = _load(path_b)

    counts_a = _counts(doc_a)
    counts_b = _counts(doc_b)
    keys = sorted(set(counts_a.keys()) | set(counts_b.keys()))

    print("# Wagstaff Mechanism Index Diff")
    print("")
    print("## Counts")
    print("```yaml")
    for k in keys:
        print(f"{k}: {counts_a.get(k)} -> {counts_b.get(k)}")
    print("```")
    print("")

    comps_a = _component_ids(doc_a)
    comps_b = _component_ids(doc_b)
    pref_a = _prefab_ids(doc_a)
    pref_b = _prefab_ids(doc_b)

    _print_section("Components Added", sorted(comps_b - comps_a), args.limit)
    _print_section("Components Removed", sorted(comps_a - comps_b), args.limit)
    _print_section("Prefabs Added", sorted(pref_b - pref_a), args.limit)
    _print_section("Prefabs Removed", sorted(pref_a - pref_b), args.limit)

    links_a = _link_pairs(doc_a)
    links_b = _link_pairs(doc_b)

    added_links = sorted([f"{a} -> {b}" for (a, b) in (links_b - links_a)])
    removed_links = sorted([f"{a} -> {b}" for (a, b) in (links_a - links_b)])

    _print_section("Links Added", added_links, args.limit)
    _print_section("Links Removed", removed_links, args.limit)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

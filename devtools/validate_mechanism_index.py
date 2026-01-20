#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate mechanism index JSON against the v1 spec."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def _fail(msg: str, errors: List[str]) -> None:
    errors.append(msg)


def _warn(msg: str, warnings: List[str]) -> None:
    warnings.append(msg)


def _is_dict(x: Any) -> bool:
    return isinstance(x, dict)


def _is_list(x: Any) -> bool:
    return isinstance(x, list)


def validate(doc: Dict[str, Any]) -> Dict[str, List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not _is_dict(doc):
        _fail("root is not a dict", errors)
        return {"errors": errors, "warnings": warnings}

    for key in ("schema_version", "meta", "counts", "components", "prefabs", "component_usage", "links"):
        if key not in doc:
            _fail(f"missing top-level key: {key}", errors)

    if "schema_version" in doc and not isinstance(doc.get("schema_version"), int):
        _fail("schema_version is not int", errors)

    if "meta" in doc and not _is_dict(doc.get("meta")):
        _fail("meta is not dict", errors)

    counts = doc.get("counts")
    if _is_dict(counts):
        for key in ("components_total", "prefabs_total", "components_used", "prefab_component_edges"):
            if key not in counts:
                _warn(f"counts missing: {key}", warnings)
    else:
        _fail("counts is not dict", errors)

    components = doc.get("components")
    if _is_dict(components):
        if not isinstance(components.get("total_files"), int):
            _warn("components.total_files missing or not int", warnings)
        items = components.get("items")
        if not _is_dict(items):
            _fail("components.items is not dict", errors)
        else:
            for cid, row in items.items():
                if not _is_dict(row):
                    _warn(f"component {cid} row not dict", warnings)
                    continue
                if row.get("id") and str(row.get("id")) != str(cid):
                    _warn(f"component id mismatch: key={cid} row.id={row.get('id')}", warnings)
    else:
        _fail("components is not dict", errors)

    prefabs = doc.get("prefabs")
    if _is_dict(prefabs):
        items = prefabs.get("items")
        if not _is_dict(items):
            _fail("prefabs.items is not dict", errors)
    else:
        _fail("prefabs is not dict", errors)

    usage = doc.get("component_usage")
    if _is_dict(usage):
        for cid, pids in usage.items():
            if not _is_list(pids):
                _warn(f"component_usage[{cid}] is not list", warnings)
    else:
        _fail("component_usage is not dict", errors)

    links = doc.get("links")
    if _is_dict(links):
        edges = links.get("prefab_component")
        if not _is_list(edges):
            _fail("links.prefab_component is not list", errors)
        else:
            for row in edges:
                if not _is_dict(row):
                    _warn("link row is not dict", warnings)
                    continue
                for key in ("source", "source_id", "target", "target_id"):
                    if key not in row:
                        _warn(f"link missing field: {key}", warnings)
                if row.get("source") not in (None, "prefab"):
                    _warn(f"link source not prefab: {row.get('source')}", warnings)
                if row.get("target") not in (None, "component"):
                    _warn(f"link target not component: {row.get('target')}", warnings)
    else:
        _fail("links is not dict", errors)

    return {"errors": errors, "warnings": warnings}


def main() -> int:
    p = argparse.ArgumentParser(description="Validate mechanism index JSON.")
    p.add_argument(
        "--in",
        dest="input_path",
        default="data/index/wagstaff_mechanism_index_v1.json",
        help="Input JSON path",
    )
    p.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = p.parse_args()

    path = Path(args.input_path).expanduser().resolve()
    if not path.exists():
        print(f"❌ Missing file: {path}", file=sys.stderr)
        return 1

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"❌ Failed to read JSON: {exc}", file=sys.stderr)
        return 1

    result = validate(doc)
    errors = result.get("errors") or []
    warnings = result.get("warnings") or []

    for msg in errors:
        print(f"❌ {msg}", file=sys.stderr)
    for msg in warnings:
        print(f"⚠️  {msg}", file=sys.stderr)

    if errors or (warnings and args.strict):
        print(f"❌ Validation failed. errors={len(errors)} warnings={len(warnings)}", file=sys.stderr)
        return 1

    print(f"✅ Validation passed. warnings={len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

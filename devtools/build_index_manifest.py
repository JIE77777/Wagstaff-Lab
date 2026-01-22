#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build an index manifest for generated artifacts."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.schemas.meta import now_iso  # noqa: E402
from core.version import versions  # noqa: E402
from devtools.build_cache import file_sig  # noqa: E402


INDEX_ARTIFACTS = [
    {"id": "resource_index", "kind": "resource", "format": "json", "path": "data/index/wagstaff_resource_index_v1.json"},
    {"id": "catalog", "kind": "catalog", "format": "json", "path": "data/index/wagstaff_catalog_v2.json"},
    {"id": "catalog_sqlite", "kind": "catalog", "format": "sqlite", "path": "data/index/wagstaff_catalog_v2.sqlite"},
    {"id": "catalog_index", "kind": "catalog_index", "format": "json", "path": "data/index/wagstaff_catalog_index_v1.json"},
    {"id": "i18n", "kind": "i18n", "format": "json", "path": "data/index/wagstaff_i18n_v1.json"},
    {"id": "farming_defs", "kind": "farming_defs", "format": "json", "path": "data/index/wagstaff_farming_defs_v1.json"},
    {"id": "farming_fixed", "kind": "farming_fixed", "format": "json", "path": "data/index/wagstaff_farming_fixed_v1.json"},
    {"id": "icon_index", "kind": "icon_index", "format": "json", "path": "data/index/wagstaff_icon_index_v1.json"},
    {"id": "tuning_trace", "kind": "tuning_trace", "format": "json", "path": "data/index/wagstaff_tuning_trace_v1.json"},
    {"id": "mechanism_index", "kind": "mechanism", "format": "json", "path": "data/index/wagstaff_mechanism_index_v1.json"},
    {"id": "mechanism_sqlite", "kind": "mechanism", "format": "sqlite", "path": "data/index/wagstaff_mechanism_index_v1.sqlite"},
    {"id": "behavior_graph", "kind": "behavior", "format": "json", "path": "data/index/wagstaff_behavior_graph_v1.json"},
    {"id": "tag_overrides", "kind": "tag_overrides", "format": "json", "path": "data/index/tag_overrides_v1.json"},
]

META_KEYS = ("schema", "project_version", "index_version", "generated", "tool", "db_schema_version")


def _parse_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text


def _extract_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key in META_KEYS:
        if key in meta:
            out[key] = meta.get(key)
    return out


def _load_json_meta(path: Path) -> Dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    meta = doc.get("meta") if isinstance(doc, dict) else {}
    return {
        "schema_version": doc.get("schema_version") if isinstance(doc, dict) else None,
        "meta": meta if isinstance(meta, dict) else {},
    }


def _load_sqlite_meta(path: Path) -> Dict[str, Any]:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        rows = {row["key"]: row["value"] for row in cur.execute("SELECT key, value FROM meta")}
    finally:
        conn.close()
    meta = _parse_value(rows.get("meta")) or {}
    return {
        "schema_version": _parse_value(rows.get("schema_version")),
        "db_schema_version": _parse_value(rows.get("db_schema_version")),
        "meta": meta if isinstance(meta, dict) else {},
    }


def _build_manifest(*, include_missing: bool) -> Dict[str, Any]:
    artifacts: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for artifact in INDEX_ARTIFACTS:
        rel_path = Path(artifact["path"])
        path = (PROJECT_ROOT / rel_path).resolve()
        if not path.exists():
            if include_missing:
                artifacts.append(
                    {
                        **artifact,
                        "path": str(rel_path),
                        "status": "missing",
                        "file": file_sig(path),
                    }
                )
            else:
                warnings.append(f"missing:{rel_path}")
            continue
        try:
            if artifact["format"] == "sqlite":
                info = _load_sqlite_meta(path)
            else:
                info = _load_json_meta(path)
        except Exception as exc:
            warnings.append(f"unreadable:{rel_path}:{exc}")
            info = {"schema_version": None, "meta": {}}

        record: Dict[str, Any] = {
            **artifact,
            "path": str(rel_path),
            "schema_version": info.get("schema_version"),
            "meta": _extract_meta(info.get("meta") or {}),
            "file": file_sig(path),
        }
        if info.get("db_schema_version") is not None:
            record["db_schema_version"] = info.get("db_schema_version")
        artifacts.append(record)

    return {
        "meta": {
            "tool": "build_index_manifest",
            "generated": now_iso(),
            **versions(),
        },
        "counts": {"artifacts": len(artifacts)},
        "artifacts": artifacts,
        "warnings": warnings,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Build index manifest for data/index artifacts")
    p.add_argument("--out", default="data/index/wagstaff_index_manifest.json", help="Manifest output path")
    p.add_argument("--include-missing", action="store_true", help="Include missing artifacts in manifest")
    args = p.parse_args()

    manifest = _build_manifest(include_missing=bool(args.include_missing))
    out_path = (PROJECT_ROOT / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Index manifest written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

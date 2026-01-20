#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build mechanism index (components + prefab links)."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.engine import WagstaffEngine  # noqa: E402
from core.indexers.mechanism_index import (
    build_mechanism_index,
    render_mechanism_crosscheck_report,
    render_mechanism_index_summary,
)  # noqa: E402
from devtools.build_cache import file_sig, files_sig, load_cache, save_cache  # noqa: E402
from devtools.validate_mechanism_index import validate as validate_schema  # noqa: E402

try:
    from core.utils import wagstaff_config  # type: ignore
except Exception:
    wagstaff_config = None  # type: ignore


def _resolve_dst_root(arg: str | None) -> str | None:
    if arg:
        return str(arg)
    if wagstaff_config is None:
        return None
    try:
        return wagstaff_config.get("PATHS", "DST_ROOT")
    except Exception:
        return None


def _write_sqlite(doc: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);

            CREATE TABLE components (
                id TEXT PRIMARY KEY,
                class_name TEXT,
                path TEXT,
                aliases_json TEXT,
                methods_json TEXT,
                fields_json TEXT,
                events_json TEXT,
                requires_json TEXT,
                raw_json TEXT
            );
            CREATE TABLE component_fields (
                component_id TEXT,
                field TEXT,
                PRIMARY KEY (component_id, field)
            );
            CREATE TABLE component_methods (
                component_id TEXT,
                method TEXT,
                PRIMARY KEY (component_id, method)
            );
            CREATE TABLE component_events (
                component_id TEXT,
                event TEXT,
                PRIMARY KEY (component_id, event)
            );

            CREATE TABLE prefabs (
                id TEXT PRIMARY KEY,
                components_json TEXT,
                tags_json TEXT,
                brains_json TEXT,
                stategraphs_json TEXT,
                helpers_json TEXT,
                files_json TEXT,
                raw_json TEXT
            );
            CREATE TABLE prefab_components (
                prefab_id TEXT,
                component_id TEXT,
                PRIMARY KEY (prefab_id, component_id)
            );

            CREATE TABLE links (
                source TEXT,
                source_id TEXT,
                target TEXT,
                target_id TEXT
            );

            CREATE TABLE stategraphs (id TEXT PRIMARY KEY, raw_json TEXT);
            CREATE TABLE stategraph_states (stategraph_id TEXT, state_name TEXT, raw_json TEXT);
            CREATE TABLE stategraph_events (stategraph_id TEXT, event TEXT, raw_json TEXT);
            CREATE TABLE stategraph_edges (stategraph_id TEXT, src TEXT, dst TEXT, event TEXT);

            CREATE TABLE brains (id TEXT PRIMARY KEY, raw_json TEXT);
            CREATE TABLE brain_nodes (brain_id TEXT, node_id TEXT, raw_json TEXT);
            CREATE TABLE brain_edges (brain_id TEXT, src TEXT, dst TEXT, raw_json TEXT);
            """
        )

        meta = doc.get("meta") or {}
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("schema_version", str(doc.get("schema_version") or "")))
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("meta", json.dumps(meta, ensure_ascii=False)))

        components = (doc.get("components") or {}).get("items") or {}
        for cid, row in components.items():
            if not isinstance(row, dict):
                continue
            cur.execute(
                """
                INSERT OR REPLACE INTO components
                (id, class_name, path, aliases_json, methods_json, fields_json, events_json, requires_json, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    row.get("class_name"),
                    row.get("path"),
                    json.dumps(row.get("aliases") or [], ensure_ascii=False),
                    json.dumps(row.get("methods") or [], ensure_ascii=False),
                    json.dumps(row.get("fields") or [], ensure_ascii=False),
                    json.dumps(row.get("events") or [], ensure_ascii=False),
                    json.dumps(row.get("requires") or [], ensure_ascii=False),
                    json.dumps(row, ensure_ascii=False),
                ),
            )
            for field in row.get("fields") or []:
                cur.execute(
                    "INSERT OR REPLACE INTO component_fields (component_id, field) VALUES (?, ?)",
                    (cid, field),
                )
            for method in row.get("methods") or []:
                cur.execute(
                    "INSERT OR REPLACE INTO component_methods (component_id, method) VALUES (?, ?)",
                    (cid, method),
                )
            for event in row.get("events") or []:
                cur.execute(
                    "INSERT OR REPLACE INTO component_events (component_id, event) VALUES (?, ?)",
                    (cid, event),
                )

        prefabs = (doc.get("prefabs") or {}).get("items") or {}
        for pid, row in prefabs.items():
            if not isinstance(row, dict):
                continue
            cur.execute(
                """
                INSERT OR REPLACE INTO prefabs
                (id, components_json, tags_json, brains_json, stategraphs_json, helpers_json, files_json, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pid,
                    json.dumps(row.get("components") or [], ensure_ascii=False),
                    json.dumps(row.get("tags") or [], ensure_ascii=False),
                    json.dumps(row.get("brains") or [], ensure_ascii=False),
                    json.dumps(row.get("stategraphs") or [], ensure_ascii=False),
                    json.dumps(row.get("helpers") or [], ensure_ascii=False),
                    json.dumps(row.get("files") or [], ensure_ascii=False),
                    json.dumps(row, ensure_ascii=False),
                ),
            )
            for comp in row.get("components") or []:
                cur.execute(
                    "INSERT OR REPLACE INTO prefab_components (prefab_id, component_id) VALUES (?, ?)",
                    (pid, comp),
                )

        for link in (doc.get("links") or {}).get("prefab_component") or []:
            if not isinstance(link, dict):
                continue
            cur.execute(
                "INSERT INTO links (source, source_id, target, target_id) VALUES (?, ?, ?, ?)",
                (
                    link.get("source"),
                    link.get("source_id"),
                    link.get("target"),
                    link.get("target_id"),
                ),
            )

        conn.commit()
    finally:
        conn.close()


def _validate_index(doc: dict) -> List[str]:
    warnings: List[str] = []
    components = (doc.get("components") or {}).get("items") or {}
    prefabs = (doc.get("prefabs") or {}).get("items") or {}
    links = (doc.get("links") or {}).get("prefab_component") or []
    usage = doc.get("component_usage") or {}

    if not isinstance(components, dict):
        warnings.append("components.items is not a dict")
        components = {}
    if not isinstance(prefabs, dict):
        warnings.append("prefabs.items is not a dict")
        prefabs = {}
    if not isinstance(links, list):
        warnings.append("links.prefab_component is not a list")
        links = []
    if not isinstance(usage, dict):
        warnings.append("component_usage is not a dict")
        usage = {}

    link_pairs = set()
    for row in links:
        if not isinstance(row, dict):
            continue
        src = row.get("source")
        src_id = row.get("source_id")
        tgt = row.get("target")
        tgt_id = row.get("target_id")
        if src != "prefab" or tgt != "component":
            warnings.append(f"link kind mismatch: {src}->{tgt}")
            continue
        if src_id not in prefabs:
            warnings.append(f"link missing prefab: {src_id}")
        if tgt_id not in components:
            warnings.append(f"link missing component: {tgt_id}")
        link_pairs.add((str(src_id), str(tgt_id)))

    for pid, row in prefabs.items():
        comps = row.get("components") if isinstance(row, dict) else None
        if not isinstance(comps, list):
            continue
        for cid in comps:
            if cid not in components:
                warnings.append(f"prefab references unknown component: {pid} -> {cid}")
            if (str(pid), str(cid)) not in link_pairs:
                warnings.append(f"missing link entry: {pid} -> {cid}")

    for cid, pids in usage.items():
        if not isinstance(pids, list):
            continue
        for pid in pids:
            if (str(pid), str(cid)) not in link_pairs:
                warnings.append(f"component_usage missing link: {cid} -> {pid}")

    counts = doc.get("counts") or {}
    if counts.get("prefab_component_edges") is not None:
        if int(counts.get("prefab_component_edges") or 0) != len(link_pairs):
            warnings.append("counts.prefab_component_edges does not match links size")

    return warnings


def main() -> int:
    p = argparse.ArgumentParser(description="Build Wagstaff mechanism index (components + prefab links).")
    p.add_argument("--out", default="data/index/wagstaff_mechanism_index_v1.json", help="Output JSON path")
    p.add_argument("--sqlite", default="data/index/wagstaff_mechanism_index_v1.sqlite", help="Output SQLite path")
    p.add_argument("--summary", default="data/reports/mechanism_index_summary.md", help="Output summary Markdown")
    p.add_argument(
        "--crosscheck",
        default="data/reports/mechanism_crosscheck_report.md",
        help="Output crosscheck Markdown",
    )
    p.add_argument("--resource-index", default="data/index/wagstaff_resource_index_v1.json", help="Input resource index")
    p.add_argument("--scripts-zip", default=None, help="Override scripts zip path")
    p.add_argument("--scripts-dir", default=None, help="Override scripts folder path")
    p.add_argument("--dst-root", default=None, help="Override DST root (default from config)")
    p.add_argument("--no-sqlite", action="store_true", help="Skip SQLite output")
    p.add_argument("--force", action="store_true", help="Force rebuild even if cache matches")
    p.add_argument("--silent", action="store_true", help="Suppress engine logs")
    p.add_argument("--strict", action="store_true", help="Fail build on any validation warning")

    args = p.parse_args()

    dst_root = _resolve_dst_root(args.dst_root)
    if not dst_root:
        raise SystemExit("DST_ROOT missing. Set conf/settings.ini or pass --dst-root.")

    engine = WagstaffEngine(
        load_db=False,
        silent=bool(args.silent),
        dst_root=dst_root,
        scripts_zip=args.scripts_zip,
        scripts_dir=args.scripts_dir,
    )

    out_path = (PROJECT_ROOT / args.out).resolve()
    sqlite_path = (PROJECT_ROOT / args.sqlite).resolve()
    summary_path = (PROJECT_ROOT / args.summary).resolve()
    crosscheck_path = (PROJECT_ROOT / args.crosscheck).resolve()
    resource_path = (PROJECT_ROOT / args.resource_index).resolve()

    scripts_sig = {}
    if engine.mode == "zip" and hasattr(engine.source, "filename"):
        scripts_sig = {"mode": "zip", "source": file_sig(Path(engine.source.filename))}
    elif engine.mode == "folder" and engine.source:
        base = Path(str(engine.source))
        files = [base / p for p in (engine.file_list or [])]
        scripts_sig = {"mode": "folder", "source": files_sig(files, label=str(base))}

    inputs_sig = {
        "scripts": scripts_sig,
        "resource_index": file_sig(resource_path),
        "sqlite": not bool(args.no_sqlite),
    }

    outputs_sig = {
        "out": file_sig(out_path),
        "sqlite": file_sig(sqlite_path) if not args.no_sqlite else {"path": str(sqlite_path), "exists": False},
        "summary": file_sig(summary_path),
        "crosscheck": file_sig(crosscheck_path),
    }

    cache = load_cache()
    cache_key = "mechanism_index"
    if not args.force:
        entry = cache.get(cache_key) or {}
        if entry.get("signature") == inputs_sig and entry.get("outputs") == outputs_sig:
            print("✅ Mechanism index up-to-date; skip rebuild")
            return 0

    resource_index = None
    if resource_path.exists():
        try:
            resource_index = json.loads(resource_path.read_text(encoding="utf-8"))
        except Exception:
            resource_index = None

    index = build_mechanism_index(engine=engine, resource_index=resource_index)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.no_sqlite:
        _write_sqlite(index, sqlite_path)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(render_mechanism_index_summary(index), encoding="utf-8")

    crosscheck_path.parent.mkdir(parents=True, exist_ok=True)
    crosscheck_path.write_text(render_mechanism_crosscheck_report(resource_index, index), encoding="utf-8")

    schema_result = validate_schema(index)
    schema_errors = schema_result.get("errors") or []
    schema_warnings = schema_result.get("warnings") or []
    consistency_warnings = _validate_index(index)

    for msg in schema_errors:
        print(f"❌ {msg}", file=sys.stderr)
    for msg in schema_warnings:
        print(f"⚠️  {msg}", file=sys.stderr)
    for msg in consistency_warnings:
        print(f"⚠️  {msg}", file=sys.stderr)

    has_errors = bool(schema_errors)
    has_warnings = bool(schema_warnings or consistency_warnings)

    outputs_sig = {
        "out": file_sig(out_path),
        "sqlite": file_sig(sqlite_path) if not args.no_sqlite else {"path": str(sqlite_path), "exists": False},
        "summary": file_sig(summary_path),
        "crosscheck": file_sig(crosscheck_path),
    }

    print(f"✅ Mechanism index written: {out_path}")
    if not args.no_sqlite:
        print(f"✅ Mechanism sqlite written: {sqlite_path}")
    print(f"✅ Summary written: {summary_path}")
    print(f"✅ Crosscheck written: {crosscheck_path}")
    if has_errors or (args.strict and has_warnings):
        print(
            f"❌ Validation failed. errors={len(schema_errors)} warnings={len(schema_warnings) + len(consistency_warnings)}",
            file=sys.stderr,
        )
        return 2

    if has_warnings:
        print(f"⚠️  Warnings: {len(schema_warnings) + len(consistency_warnings)}", file=sys.stderr)

    cache[cache_key] = {"signature": inputs_sig, "outputs": outputs_sig}
    save_cache(cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

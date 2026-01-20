#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validation helpers for Wagstaff artifacts (library-only)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

DB_SCHEMA_VERSION = 4

CATALOG_REQUIRED_TABLES: Set[str] = {
    "meta",
    "items",
    "item_stats",
    "item_categories",
    "item_behaviors",
    "item_sources",
    "item_tags",
    "item_components",
    "item_slots",
    "assets",
    "craft_meta",
    "craft_recipes",
    "craft_ingredients",
    "cooking_recipes",
    "cooking_ingredients",
    "catalog_index",
}

CATALOG_OPTIONAL_TABLES: Set[str] = {
    "catalog_index_fts",
    "tuning_trace",
}

CATALOG_REQUIRED_COLUMNS: Dict[str, Set[str]] = {
    "meta": {"key", "value"},
    "items": {
        "id",
        "kind",
        "name",
        "categories_json",
        "behaviors_json",
        "sources_json",
        "tags_json",
        "components_json",
        "slots_json",
        "assets_json",
        "prefab_files_json",
        "raw_json",
    },
    "item_stats": {"item_id", "stat_key", "expr", "expr_resolved", "trace_key", "value_json", "raw_json"},
    "item_categories": {"item_id", "category"},
    "item_behaviors": {"item_id", "behavior"},
    "item_sources": {"item_id", "source"},
    "item_tags": {"item_id", "tag"},
    "item_components": {"item_id", "component"},
    "item_slots": {"item_id", "slot"},
    "assets": {"id", "name", "icon", "image", "atlas", "build", "bank", "raw_json"},
    "craft_meta": {"key", "value_json"},
    "craft_recipes": {
        "name",
        "product",
        "tab",
        "tech",
        "builder_skill",
        "station_tag",
        "filters_json",
        "builder_tags_json",
        "raw_json",
    },
    "craft_ingredients": {"recipe_name", "item_id", "amount_num", "amount_value", "raw_json"},
    "cooking_recipes": {
        "name",
        "priority",
        "weight",
        "foodtype",
        "hunger_json",
        "health_json",
        "sanity_json",
        "perishtime_json",
        "cooktime_json",
        "tags_json",
        "card_ingredients_json",
        "raw_json",
    },
    "cooking_ingredients": {"item_id", "tags_json", "tags_expr", "sources_json", "raw_json"},
    "catalog_index": {
        "id",
        "name",
        "icon",
        "image",
        "has_icon",
        "icon_only",
        "kind",
        "categories_json",
        "behaviors_json",
        "sources_json",
        "tags_json",
        "components_json",
        "slots_json",
    },
}

CATALOG_OPTIONAL_COLUMNS: Dict[str, Set[str]] = {
    "tuning_trace": {"trace_key", "raw_json"},
}

MECHANISM_REQUIRED_TABLES: Set[str] = {
    "meta",
    "components",
    "component_fields",
    "component_methods",
    "component_events",
    "prefabs",
    "prefab_components",
    "links",
}

MECHANISM_OPTIONAL_TABLES: Set[str] = {
    "stategraphs",
    "stategraph_states",
    "stategraph_events",
    "stategraph_edges",
    "brains",
    "brain_nodes",
    "brain_edges",
}

MECHANISM_REQUIRED_COLUMNS: Dict[str, Set[str]] = {
    "meta": {"key", "value"},
    "components": {
        "id",
        "class_name",
        "path",
        "aliases_json",
        "methods_json",
        "fields_json",
        "events_json",
        "requires_json",
        "raw_json",
    },
    "component_fields": {"component_id", "field"},
    "component_methods": {"component_id", "method"},
    "component_events": {"component_id", "event"},
    "prefabs": {
        "id",
        "components_json",
        "tags_json",
        "brains_json",
        "stategraphs_json",
        "helpers_json",
        "files_json",
        "raw_json",
    },
    "prefab_components": {"prefab_id", "component_id"},
    "links": {"source", "source_id", "target", "target_id"},
}

MECHANISM_OPTIONAL_COLUMNS: Dict[str, Set[str]] = {
    "prefabs": {"events_json", "assets_json", "component_calls_json"},
    "links": {"relation"},
}


def _parse_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _fetch_tables(conn: sqlite3.Connection) -> Set[str]:
    cur = conn.cursor()
    return {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _table_columns(conn: sqlite3.Connection, table: str) -> Set[str]:
    cur = conn.cursor()
    try:
        rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.Error:
        return set()
    return {row[1] for row in rows}


def _load_meta(conn: sqlite3.Connection) -> Dict[str, Any]:
    cur = conn.cursor()
    try:
        rows = cur.execute("SELECT key, value FROM meta").fetchall()
    except sqlite3.Error:
        return {}
    return {str(k): v for k, v in rows}


def _validate_meta(meta: Dict[str, Any], label: str) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    issues: List[Tuple[str, str]] = []
    summary: Dict[str, Any] = {}

    db_schema = _parse_int(meta.get("db_schema_version"))
    summary["db_schema_version"] = db_schema
    if db_schema is None:
        issues.append(("fail", f"{label} sqlite missing meta.db_schema_version"))
    elif db_schema != DB_SCHEMA_VERSION:
        issues.append(("fail", f"{label} sqlite db_schema_version != {DB_SCHEMA_VERSION} ({db_schema})"))

    schema_version = _parse_int(meta.get("schema_version"))
    summary["schema_version"] = schema_version
    if schema_version is None:
        issues.append(("warn", f"{label} sqlite missing meta.schema_version"))

    if "meta" not in meta:
        issues.append(("warn", f"{label} sqlite missing meta.meta json"))

    return summary, issues


def _validate_columns(
    *,
    label: str,
    tables: Set[str],
    conn: sqlite3.Connection,
    required: Dict[str, Set[str]],
    optional: Dict[str, Set[str]],
) -> List[Tuple[str, str]]:
    issues: List[Tuple[str, str]] = []
    for table, cols in required.items():
        if table not in tables:
            continue
        actual = _table_columns(conn, table)
        missing = sorted(set(cols) - actual)
        if missing:
            issues.append(("fail", f"{label} sqlite missing columns in {table}: {', '.join(missing)}"))

    for table, cols in optional.items():
        if table not in tables:
            continue
        actual = _table_columns(conn, table)
        missing = sorted(set(cols) - actual)
        if missing:
            issues.append(("warn", f"{label} sqlite missing optional columns in {table}: {', '.join(missing)}"))
    return issues


def validate_sqlite_v4(path: Path, *, kind: str) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    issues: List[Tuple[str, str]] = []
    summary: Dict[str, Any] = {"exists": path.exists()}
    if not path.exists():
        issues.append(("fail", f"{kind} sqlite missing: {path}"))
        return summary, issues

    try:
        conn = sqlite3.connect(str(path))
    except sqlite3.Error as exc:
        issues.append(("fail", f"{kind} sqlite open failed: {exc}"))
        return summary, issues

    try:
        tables = _fetch_tables(conn)
        summary["tables_total"] = len(tables)
        if "meta" not in tables:
            issues.append(("fail", f"{kind} sqlite missing table: meta"))
            return summary, issues

        meta = _load_meta(conn)
        meta_summary, meta_issues = _validate_meta(meta, kind)
        summary.update(meta_summary)
        issues.extend(meta_issues)

        if kind == "catalog":
            missing = sorted(CATALOG_REQUIRED_TABLES - tables)
            if missing:
                issues.append(("fail", f"{kind} sqlite missing tables: {', '.join(missing)}"))
            optional_missing = sorted(CATALOG_OPTIONAL_TABLES - tables)
            if optional_missing:
                issues.append(("warn", f"{kind} sqlite missing optional tables: {', '.join(optional_missing)}"))
            issues.extend(
                _validate_columns(
                    label=kind,
                    tables=tables,
                    conn=conn,
                    required=CATALOG_REQUIRED_COLUMNS,
                    optional=CATALOG_OPTIONAL_COLUMNS,
                )
            )
            summary["has_fts"] = "catalog_index_fts" in tables
            summary["has_tuning_trace"] = "tuning_trace" in tables
        elif kind == "mechanism":
            missing = sorted(MECHANISM_REQUIRED_TABLES - tables)
            if missing:
                issues.append(("fail", f"{kind} sqlite missing tables: {', '.join(missing)}"))
            optional_missing = sorted(MECHANISM_OPTIONAL_TABLES - tables)
            if optional_missing:
                issues.append(("warn", f"{kind} sqlite missing optional tables: {', '.join(optional_missing)}"))
            issues.extend(
                _validate_columns(
                    label=kind,
                    tables=tables,
                    conn=conn,
                    required=MECHANISM_REQUIRED_COLUMNS,
                    optional=MECHANISM_OPTIONAL_COLUMNS,
                )
            )
            summary["has_links_relation"] = "relation" in _table_columns(conn, "links")
        else:
            issues.append(("warn", f"unknown sqlite kind: {kind}"))
    finally:
        conn.close()

    return summary, issues


def validate_mechanism_index(doc: Dict[str, Any]) -> Dict[str, List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(doc, dict):
        errors.append("root is not a dict")
        return {"errors": errors, "warnings": warnings}

    for key in ("schema_version", "meta", "counts", "components", "prefabs", "component_usage", "links"):
        if key not in doc:
            errors.append(f"missing top-level key: {key}")

    if "schema_version" in doc and not isinstance(doc.get("schema_version"), int):
        errors.append("schema_version is not int")

    if "meta" in doc and not isinstance(doc.get("meta"), dict):
        errors.append("meta is not dict")

    counts = doc.get("counts")
    if isinstance(counts, dict):
        for key in ("components_total", "prefabs_total", "components_used", "prefab_component_edges"):
            if key not in counts:
                warnings.append(f"counts missing: {key}")
    else:
        errors.append("counts is not dict")

    components = doc.get("components")
    if isinstance(components, dict):
        if not isinstance(components.get("total_files"), int):
            warnings.append("components.total_files missing or not int")
        items = components.get("items")
        if not isinstance(items, dict):
            errors.append("components.items is not dict")
        else:
            for cid, row in items.items():
                if not isinstance(row, dict):
                    warnings.append(f"component {cid} row not dict")
                    continue
                if row.get("id") and str(row.get("id")) != str(cid):
                    warnings.append(f"component id mismatch: key={cid} row.id={row.get('id')}")
    else:
        errors.append("components is not dict")

    prefabs = doc.get("prefabs")
    if isinstance(prefabs, dict):
        items = prefabs.get("items")
        if not isinstance(items, dict):
            errors.append("prefabs.items is not dict")
    else:
        errors.append("prefabs is not dict")

    usage = doc.get("component_usage")
    if isinstance(usage, dict):
        for cid, pids in usage.items():
            if not isinstance(pids, list):
                warnings.append(f"component_usage[{cid}] is not list")
    else:
        errors.append("component_usage is not dict")

    links = doc.get("links")
    if isinstance(links, dict):
        edges = links.get("prefab_component")
        if not isinstance(edges, list):
            errors.append("links.prefab_component is not list")
        else:
            for row in edges:
                if not isinstance(row, dict):
                    warnings.append("link row is not dict")
                    continue
                for key in ("source", "source_id", "target", "target_id"):
                    if key not in row:
                        warnings.append(f"link missing field: {key}")
                if row.get("source") not in (None, "prefab"):
                    warnings.append(f"link source not prefab: {row.get('source')}")
                if row.get("target") not in (None, "component"):
                    warnings.append(f"link target not component: {row.get('target')}")
    else:
        errors.append("links is not dict")

    return {"errors": errors, "warnings": warnings}

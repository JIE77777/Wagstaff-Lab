# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

_SQLITE_SUFFIXES = (".sqlite", ".sqlite3", ".db")


def _is_sqlite_path(path: Path) -> bool:
    return path.suffix.lower() in _SQLITE_SUFFIXES


def _find_sqlite_peer(path: Path) -> Optional[Path]:
    if path.suffix.lower() != ".json":
        return None
    for ext in _SQLITE_SUFFIXES:
        candidate = path.with_suffix(ext)
        if candidate.exists():
            return candidate
    return None


def _load_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


class MechanismError(RuntimeError):
    pass


class MechanismStore:
    """Load + query mechanism index (thread-safe)."""

    def __init__(self, path: Path):
        resolved = self.resolve_path(Path(path))
        self._path = resolved
        self._use_sqlite = _is_sqlite_path(self._path)
        self._lock = threading.RLock()
        self._mtime: float = -1.0

        self._doc: Dict[str, Any] = {}
        self._meta: Dict[str, Any] = {}
        self._counts: Dict[str, Any] = {}

        self._components: Dict[str, Dict[str, Any]] = {}
        self._component_ids: List[str] = []
        self._prefabs: Dict[str, Dict[str, Any]] = {}
        self._prefab_ids: List[str] = []
        self._component_usage: Dict[str, List[str]] = {}
        self._links: List[Dict[str, Any]] = []

        self.load(force=True)

    @staticmethod
    def resolve_path(path: Path) -> Path:
        if _is_sqlite_path(path):
            return path
        peer = _find_sqlite_peer(path)
        return peer if peer else path

    @property
    def path(self) -> Path:
        return self._path

    def mtime(self) -> float:
        with self._lock:
            return float(self._mtime or 0)

    def meta(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._meta)

    def counts(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._counts)

    def schema_version(self) -> int:
        with self._lock:
            return int(self._doc.get("schema_version") or (self._meta or {}).get("schema") or 0)

    def component_ids(self) -> List[str]:
        with self._lock:
            return list(self._component_ids)

    def prefab_ids(self) -> List[str]:
        with self._lock:
            return list(self._prefab_ids)

    def get_component(self, component_id: str) -> Optional[Dict[str, Any]]:
        cid = str(component_id or "").strip()
        if not cid:
            return None
        with self._lock:
            row = self._components.get(cid)
            if row is None and cid.lower() != cid:
                row = self._components.get(cid.lower())
            return dict(row) if isinstance(row, dict) else None

    def get_prefab(self, prefab_id: str) -> Optional[Dict[str, Any]]:
        pid = str(prefab_id or "").strip()
        if not pid:
            return None
        with self._lock:
            row = self._prefabs.get(pid)
            if row is None and pid.lower() != pid:
                row = self._prefabs.get(pid.lower())
            return dict(row) if isinstance(row, dict) else None

    def component_usage(self, component_id: str) -> List[str]:
        cid = str(component_id or "").strip()
        if not cid:
            return []
        with self._lock:
            if cid in self._component_usage:
                return list(self._component_usage.get(cid) or [])
            if cid.lower() in self._component_usage:
                return list(self._component_usage.get(cid.lower()) or [])
            return []

    def prefabs_for_component(self, component_id: str) -> List[str]:
        return self.component_usage(component_id)

    def search_components(self, query: str) -> List[str]:
        q = str(query or "").strip().lower()
        if not q:
            return self.component_ids()
        out: List[str] = []
        with self._lock:
            for cid in self._component_ids:
                row = self._components.get(cid) or {}
                hay = [cid, row.get("class_name")] + list(row.get("aliases") or [])
                if any(q in str(v).lower() for v in hay if v):
                    out.append(cid)
        return out

    def search_prefabs(self, query: str) -> List[str]:
        q = str(query or "").strip().lower()
        if not q:
            return self.prefab_ids()
        out: List[str] = []
        with self._lock:
            for pid in self._prefab_ids:
                if q in pid.lower():
                    out.append(pid)
        return out

    def links(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(row) for row in self._links]

    def load(self, force: bool = False) -> bool:
        """Load index if changed. Returns True if reload occurred."""
        with self._lock:
            try:
                mtime = self._path.stat().st_mtime
            except FileNotFoundError as exc:
                raise MechanismError(f"Mechanism index not found: {self._path}") from exc

            if (not force) and self._doc and self._mtime == mtime:
                return False

            doc = self._load_doc()
            self._validate(doc)

            self._doc = doc
            self._meta = doc.get("meta") or {}
            self._mtime = mtime

            self._build_indexes(doc)
            return True

    def _load_doc(self) -> Dict[str, Any]:
        if self._use_sqlite:
            return self._load_doc_from_sqlite(self._path)
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _load_doc_from_sqlite(self, path: Path) -> Dict[str, Any]:
        try:
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
        except Exception as exc:
            raise MechanismError(f"Failed to open SQLite mechanism index: {path}") from exc
        try:
            cur = conn.cursor()
            tables = {row["name"] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"meta", "components", "prefabs", "prefab_components", "links"}
            missing = sorted(required - tables)
            if missing:
                raise MechanismError(f"SQLite mechanism index missing tables: {', '.join(missing)}")

            meta_rows = {row["key"]: row["value"] for row in cur.execute("SELECT key, value FROM meta")}
            comp_rows = cur.execute(
                """
                SELECT id, class_name, path, aliases_json, methods_json, fields_json, events_json, requires_json, raw_json
                FROM components
                """
            ).fetchall()
            prefab_cols = {row["name"] for row in cur.execute("PRAGMA table_info(prefabs)")}
            prefab_select = [
                "id",
                "components_json",
                "tags_json",
                "brains_json",
                "stategraphs_json",
                "helpers_json",
                "files_json",
                "raw_json",
            ]
            for col in ("events_json", "assets_json", "component_calls_json"):
                if col in prefab_cols:
                    prefab_select.append(col)
            prefab_rows = cur.execute(f"SELECT {', '.join(prefab_select)} FROM prefabs").fetchall()
            prefab_component_rows = cur.execute(
                "SELECT prefab_id, component_id FROM prefab_components"
            ).fetchall()
            link_cols = {row["name"] for row in cur.execute("PRAGMA table_info(links)")}
            link_select = "source, source_id, target, target_id"
            if "relation" in link_cols:
                link_select = f"{link_select}, relation"
            link_rows = cur.execute(f"SELECT {link_select} FROM links").fetchall()
        except Exception as exc:
            raise MechanismError(f"SQLite mechanism index query failed: {path}") from exc
        finally:
            conn.close()

        meta_obj = _load_json(meta_rows.get("meta")) or {}
        schema_version = _load_json(meta_rows.get("schema_version"))
        if schema_version is None:
            schema_version = (meta_obj or {}).get("schema") or 0

        components: Dict[str, Dict[str, Any]] = {}
        for row in comp_rows:
            cid = str(row["id"] or "").strip()
            if not cid:
                continue
            raw = _load_json(row["raw_json"])
            if isinstance(raw, dict):
                data = dict(raw)
            else:
                data = {
                    "type": "component",
                    "id": cid,
                    "class_name": row["class_name"],
                    "path": row["path"],
                    "aliases": _load_json(row["aliases_json"]) or [],
                    "methods": _load_json(row["methods_json"]) or [],
                    "fields": _load_json(row["fields_json"]) or [],
                    "events": _load_json(row["events_json"]) or [],
                    "requires": _load_json(row["requires_json"]) or [],
                }
            components[cid] = data

        prefabs: Dict[str, Dict[str, Any]] = {}
        for row in prefab_rows:
            pid = str(row["id"] or "").strip()
            if not pid:
                continue
            raw = _load_json(row["raw_json"])
            if isinstance(raw, dict):
                data = dict(raw)
            else:
                data = {
                    "components": _load_json(row["components_json"]) or [],
                    "tags": _load_json(row["tags_json"]) or [],
                    "brains": _load_json(row["brains_json"]) or [],
                    "stategraphs": _load_json(row["stategraphs_json"]) or [],
                    "helpers": _load_json(row["helpers_json"]) or [],
                    "files": _load_json(row["files_json"]) or [],
                }
                if "events_json" in row.keys():
                    data["events"] = _load_json(row["events_json"]) or []
                if "assets_json" in row.keys():
                    data["assets"] = _load_json(row["assets_json"]) or []
                if "component_calls_json" in row.keys():
                    data["component_calls"] = _load_json(row["component_calls_json"]) or []
            prefabs[pid] = data

        component_usage: Dict[str, List[str]] = {}
        for row in prefab_component_rows:
            pid = str(row["prefab_id"] or "").strip()
            cid = str(row["component_id"] or "").strip()
            if not pid or not cid:
                continue
            component_usage.setdefault(cid, []).append(pid)
        component_usage = {k: sorted(set(v)) for k, v in component_usage.items()}

        links: List[Dict[str, Any]] = []
        for row in link_rows:
            src = row["source"]
            tgt = row["target"]
            if not src or not tgt:
                continue
            link = {
                "source": src,
                "source_id": row["source_id"],
                "target": tgt,
                "target_id": row["target_id"],
            }
            if "relation" in row.keys():
                link["relation"] = row["relation"]
            links.append(link)

        counts = {
            "components_total": len(components),
            "prefabs_total": len(prefabs),
            "components_used": len(component_usage),
            "prefab_component_edges": len({(row["prefab_id"], row["component_id"]) for row in prefab_component_rows}),
        }

        return {
            "schema_version": schema_version,
            "meta": meta_obj,
            "counts": counts,
            "components": {"total_files": len(components), "items": components},
            "prefabs": {"items": prefabs},
            "component_usage": component_usage,
            "links": {"prefab_component": links},
        }

    def _validate(self, doc: Dict[str, Any]) -> None:
        if not isinstance(doc, dict):
            raise MechanismError("Mechanism index root must be a JSON object")
        if "meta" not in doc:
            raise MechanismError("Mechanism index missing key: meta")

    def _build_indexes(self, doc: Dict[str, Any]) -> None:
        comp_items = (doc.get("components") or {}).get("items") or {}
        prefab_items = (doc.get("prefabs") or {}).get("items") or {}
        usage = doc.get("component_usage") or {}
        links = (doc.get("links") or {}).get("prefab_component") or []

        components: Dict[str, Dict[str, Any]] = {}
        for cid, row in comp_items.items():
            if not cid or not isinstance(row, dict):
                continue
            data = dict(row)
            data.setdefault("id", str(cid))
            data.setdefault("type", "component")
            components[str(cid)] = data

        prefabs: Dict[str, Dict[str, Any]] = {}
        for pid, row in prefab_items.items():
            if not pid or not isinstance(row, dict):
                continue
            data = dict(row)
            data.setdefault("id", str(pid))
            prefabs[str(pid)] = data

        usage_map: Dict[str, List[str]] = {}
        if isinstance(usage, dict):
            for cid, pids in usage.items():
                if not cid or not isinstance(pids, list):
                    continue
                usage_map[str(cid)] = sorted({str(pid) for pid in pids if pid})

        links_list: List[Dict[str, Any]] = []
        if isinstance(links, list):
            for row in links:
                if not isinstance(row, dict):
                    continue
                links_list.append(dict(row))

        if not usage_map and links_list:
            usage_map = {}
            for row in links_list:
                cid = row.get("target_id")
                pid = row.get("source_id")
                if row.get("source") != "prefab" or row.get("target") != "component":
                    continue
                if not cid or not pid:
                    continue
                usage_map.setdefault(str(cid), set()).add(str(pid))
            usage_map = {k: sorted(v) for k, v in usage_map.items()}

        if not links_list and usage_map:
            links_list = [
                {"source": "prefab", "source_id": pid, "target": "component", "target_id": cid}
                for cid, pids in usage_map.items()
                for pid in pids
            ]

        counts = dict(doc.get("counts") or {})
        counts.setdefault("components_total", len(components))
        counts.setdefault("prefabs_total", len(prefabs))
        counts.setdefault("components_used", len(usage_map))
        counts.setdefault(
            "prefab_component_edges",
            len({(row.get("source_id"), row.get("target_id")) for row in links_list if row.get("source") == "prefab"}),
        )

        self._components = components
        self._component_ids = sorted(components.keys())
        self._prefabs = prefabs
        self._prefab_ids = sorted(prefabs.keys())
        self._component_usage = usage_map
        self._links = links_list
        self._counts = counts

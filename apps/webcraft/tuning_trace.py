# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import bisect


_SQLITE_SUFFIXES = (".sqlite", ".sqlite3", ".db")


def _is_sqlite_path(path: Path) -> bool:
    return path.suffix.lower() in _SQLITE_SUFFIXES


class TuningTraceStore:
    """Load + index tuning trace JSON for on-demand queries (thread-safe)."""

    def __init__(self, path: Path):
        self._path = Path(path)
        self._use_sqlite = _is_sqlite_path(self._path)
        self._lock = threading.RLock()
        self._mtime: float = -1.0
        self._doc: Dict[str, Any] = {}
        self._keys: List[str] = []
        self.load(force=True)

    @property
    def path(self) -> Path:
        return self._path

    def mtime(self) -> float:
        with self._lock:
            return float(self._mtime or 0)

    def load(self, force: bool = False) -> bool:
        """Load trace file if changed. Returns True if reload occurred."""
        with self._lock:
            if not self._path.exists():
                self._doc = {}
                self._keys = []
                self._mtime = -1.0
                return False
            try:
                mtime = self._path.stat().st_mtime
            except Exception:
                return False
            if (not force) and self._doc and self._mtime == mtime:
                return False
            if self._use_sqlite:
                doc = self._load_sqlite(self._path)
            else:
                try:
                    doc = json.loads(self._path.read_text(encoding="utf-8"))
                except Exception:
                    doc = {}
            self._doc = doc if isinstance(doc, dict) else {}
            self._keys = sorted(k for k in self._doc.keys() if isinstance(k, str))
            self._mtime = mtime
            return True

    @staticmethod
    def _load_sqlite(path: Path) -> Dict[str, Any]:
        try:
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
        except Exception:
            return {}
        try:
            cur = conn.cursor()
            tables = {row["name"] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "tuning_trace" not in tables:
                return {}
            rows = cur.execute("SELECT trace_key, raw_json FROM tuning_trace").fetchall()
        except Exception:
            return {}
        finally:
            conn.close()

        out: Dict[str, Any] = {}
        for row in rows:
            key = str(row["trace_key"] or "").strip()
            if not key:
                continue
            raw = row["raw_json"]
            if raw is None:
                out[key] = None
                continue
            try:
                out[key] = json.loads(raw)
            except Exception:
                out[key] = raw
        return out

    def count(self) -> int:
        with self._lock:
            return len(self._doc)

    def get(self, key: str) -> Optional[Any]:
        if not key:
            return None
        with self._lock:
            v = self._doc.get(str(key))
            if isinstance(v, dict):
                return dict(v)
            return v

    def get_prefix(self, prefix: str, *, limit: int = 2000) -> Dict[str, Any]:
        p = str(prefix or "")
        if not p:
            return {}
        out: Dict[str, Any] = {}
        with self._lock:
            keys = self._keys
            start = bisect.bisect_left(keys, p)
            end = bisect.bisect_right(keys, p + "\uffff")
            for k in keys[start:end]:
                v = self._doc.get(k)
                out[k] = dict(v) if isinstance(v, dict) else v
                if len(out) >= limit:
                    break
        return out

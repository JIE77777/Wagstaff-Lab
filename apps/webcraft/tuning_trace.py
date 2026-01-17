# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import bisect


class TuningTraceStore:
    """Load + index tuning trace JSON for on-demand queries (thread-safe)."""

    def __init__(self, path: Path):
        self._path = Path(path)
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
            try:
                doc = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                doc = {}
            self._doc = doc if isinstance(doc, dict) else {}
            self._keys = sorted(k for k in self._doc.keys() if isinstance(k, str))
            self._mtime = mtime
            return True

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

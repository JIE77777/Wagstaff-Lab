# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional


class TuningTraceStore:
    """Load + index tuning trace JSON for on-demand queries (thread-safe)."""

    def __init__(self, path: Path):
        self._path = Path(path)
        self._lock = threading.RLock()
        self._mtime: float = -1.0
        self._doc: Dict[str, Any] = {}
        self.load(force=True)

    @property
    def path(self) -> Path:
        return self._path

    def load(self, force: bool = False) -> bool:
        """Load trace file if changed. Returns True if reload occurred."""
        with self._lock:
            if not self._path.exists():
                self._doc = {}
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
            for k, v in self._doc.items():
                if not isinstance(k, str) or not k.startswith(p):
                    continue
                out[k] = dict(v) if isinstance(v, dict) else v
                if len(out) >= limit:
                    break
        return out

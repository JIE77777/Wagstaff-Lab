# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


class I18nIndexStore:
    """Load + query i18n index JSON (thread-safe)."""

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
        """Load index file if changed. Returns True if reload occurred."""
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

    def meta(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._doc.get("meta") or {})

    def langs(self) -> List[str]:
        with self._lock:
            langs = self._doc.get("langs")
            if isinstance(langs, list) and langs:
                return sorted({str(x) for x in langs if x})
            names = self._doc.get("names") or {}
            if isinstance(names, dict):
                return sorted({str(k) for k, v in names.items() if k and isinstance(v, dict) and v})
            return []

    def ui_langs(self) -> List[str]:
        with self._lock:
            ui = self._doc.get("ui") or {}
            if isinstance(ui, dict):
                return sorted({str(k) for k, v in ui.items() if k and isinstance(v, dict) and v})
            return []

    def names(self, lang: str) -> Dict[str, str]:
        l = str(lang or "").strip().lower()
        if not l:
            return {}
        with self._lock:
            names = (self._doc.get("names") or {}).get(l) if isinstance(self._doc.get("names"), dict) else None
            if not isinstance(names, dict):
                return {}
            return {str(k): str(v) for k, v in names.items() if k and v}

    def ui_strings(self, lang: str) -> Dict[str, str]:
        l = str(lang or "").strip().lower()
        if not l:
            return {}
        with self._lock:
            ui = (self._doc.get("ui") or {}).get(l) if isinstance(self._doc.get("ui"), dict) else None
            if not isinstance(ui, dict):
                return {}
            return {str(k): str(v) for k, v in ui.items() if k and v}

    def public_meta(self) -> Dict[str, Any]:
        name_langs = self.langs()
        return {
            "enabled": bool(name_langs),
            "langs": name_langs,
            "ui_langs": self.ui_langs(),
            "modes": ["en", "zh", "id"],
            "default_mode": "en",
        }

    def count_names(self, lang: str) -> int:
        return len(self.names(lang))

    def count_ui(self, lang: str) -> int:
        return len(self.ui_strings(lang))

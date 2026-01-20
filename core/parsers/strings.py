# -*- coding: utf-8 -*-
"""Strings parser."""

from __future__ import annotations

import re
from typing import Any, Dict

from core.parsers.base import BaseParser

__all__ = ["StringParser"]


class StringParser(BaseParser):
    def parse(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"type": "strings", "roots": [], "includes": self._extract_requires()}
        roots = set()
        roots.update(re.findall(r"STRINGS\.([A-Z0-9_]+)\s*=\s*\{", self.clean))
        roots.update(re.findall(r"STRINGS\.([A-Z0-9_]+)\s*=\s*['\"]", self.clean))
        data["roots"] = sorted(roots)
        return data

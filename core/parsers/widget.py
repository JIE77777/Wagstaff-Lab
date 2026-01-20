# -*- coding: utf-8 -*-
"""Widget parser."""

from __future__ import annotations

import re
from typing import Any, Dict

from core.parsers.base import BaseParser

__all__ = ["WidgetParser"]


class WidgetParser(BaseParser):
    def parse(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"type": "widget", "classes": [], "dependencies": self._extract_requires()}
        for name, parent in re.findall(r"local\s+([A-Za-z0-9_]+)\s*=\s*Class\s*\(\s*([A-Za-z0-9_]+)", self.clean):
            data["classes"].append({"name": name, "parent": parent})
        return data

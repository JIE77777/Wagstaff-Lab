# -*- coding: utf-8 -*-
"""LuaAnalyzer facade for selecting domain parsers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.parsers.base import BaseParser
from core.parsers.loot import LootParser
from core.parsers.prefab import PrefabParser
from core.parsers.strings import StringParser
from core.parsers.widget import WidgetParser

__all__ = ["LuaAnalyzer"]


class LuaAnalyzer:
    """Facade: choose best strategy based on content + optional path."""

    def __init__(self, content: str, path: Optional[str] = None):
        self.content = content or ""
        self.path = path
        self.parser = self._select_strategy()

    def _select_strategy(self) -> BaseParser:
        p = (self.path or "").replace("\\", "/")
        c = self.content

        if p.startswith("scripts/widgets/") or p.startswith("scripts/screens/"):
            return WidgetParser(c, p)
        if p.startswith("scripts/strings"):
            return StringParser(c, p)
        if p.startswith("scripts/prefabs/"):
            return PrefabParser(c, p)

        if "Class(Widget" in c or "Class(Screen" in c or 'require "widgets/' in c or "require('widgets/" in c:
            return WidgetParser(c, p)
        if "return Prefab" in c or "Prefab(" in c:
            return PrefabParser(c, p)
        if "STRINGS." in c and "STRINGS.CHARACTERS" in c:
            return StringParser(c, p)
        if "SetSharedLootTable" in c or "AddChanceLoot" in c:
            return LootParser(c, p)
        return PrefabParser(c, p)

    def get_report(self) -> Dict[str, Any]:
        return self.parser.parse()

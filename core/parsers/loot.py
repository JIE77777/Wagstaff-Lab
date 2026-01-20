# -*- coding: utf-8 -*-
"""Loot table parser."""

from __future__ import annotations

from typing import Any, Dict

from core.lua import LuaCallExtractor, LuaTableValue, parse_lua_expr, parse_lua_string
from core.parsers.base import BaseParser

__all__ = ["LootParser"]


class LootParser(BaseParser):
    """Parse shared loot tables + simple loot helpers."""

    def parse(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"type": "loot", "table_name": None, "entries": []}
        extractor = LuaCallExtractor(self.content)

        for call in extractor.iter_calls("SetSharedLootTable"):
            if not call.arg_list:
                continue
            name = parse_lua_string(call.arg_list[0]) or None
            if name:
                data["table_name"] = name
            if len(call.arg_list) >= 2:
                tbl = parse_lua_expr(call.arg_list[1])
                if isinstance(tbl, LuaTableValue):
                    for row in tbl.array:
                        if isinstance(row, LuaTableValue) and len(row.array) >= 2:
                            item = row.array[0]
                            chance = row.array[1]
                            if isinstance(item, str) and isinstance(chance, (int, float)):
                                data["entries"].append({"item": item, "chance": float(chance), "method": "TableData"})

        for call in extractor.iter_calls(["AddRandomLoot", "AddRandomLootTable"]):
            if len(call.arg_list) >= 2:
                item = parse_lua_string(call.arg_list[0])
                w = parse_lua_expr(call.arg_list[1])
                if isinstance(item, str) and isinstance(w, (int, float)):
                    data["entries"].append({"item": item, "weight": float(w), "method": "Random"})

        for call in extractor.iter_calls("AddChanceLoot"):
            if len(call.arg_list) >= 2:
                item = parse_lua_string(call.arg_list[0])
                c = parse_lua_expr(call.arg_list[1])
                if isinstance(item, str) and isinstance(c, (int, float)):
                    data["entries"].append({"item": item, "chance": float(c), "method": "Chance"})

        return data

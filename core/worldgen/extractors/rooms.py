# -*- coding: utf-8 -*-
"""Extract rooms from map/rooms*.lua."""

from __future__ import annotations

from typing import Any, Dict

from core.lua.call_extractor import LuaCallExtractor
from core.worldgen.extractors.common import (
    coerce_list,
    coerce_map,
    extract_local_tables,
    parse_string,
    resolve_table,
)


def _build_room(rid: str, data: Dict[str, Any], raw: str) -> Dict[str, Any]:
    return {
        "type": "room",
        "id": rid,
        "value": data.get("value"),
        "tags": coerce_list(data.get("tags")),
        "contents": coerce_map(data.get("contents")),
        "raw": {"table": data, "expr": raw},
    }


def extract_rooms(engine: Any) -> Dict[str, Dict[str, Any]]:
    rooms: Dict[str, Dict[str, Any]] = {}
    for path in getattr(engine, "file_list", []) or []:
        if not str(path).startswith("scripts/map/rooms"):
            continue
        if not str(path).endswith(".lua"):
            continue
        content = engine.read_file(path) or ""
        if "AddRoom" not in content:
            continue
        locals_map = extract_local_tables(content)
        extractor = LuaCallExtractor(content)
        for call in extractor.iter_calls("AddRoom"):
            if len(call.arg_list) < 2:
                continue
            rid = parse_string(call.arg_list[0]) or ""
            rid = str(rid).strip()
            if not rid:
                continue
            data, raw = resolve_table(call.arg_list[1], locals_map)
            rooms[rid] = _build_room(rid, data, raw)
    return rooms

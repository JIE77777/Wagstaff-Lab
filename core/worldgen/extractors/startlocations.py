# -*- coding: utf-8 -*-
"""Extract start locations from map/startlocations.lua."""

from __future__ import annotations

from typing import Any, Dict

from core.lua.call_extractor import LuaCallExtractor
from core.worldgen.extractors.common import extract_local_tables, parse_string, resolve_table


def _build_start_location(sid: str, data: Dict[str, Any], raw: str) -> Dict[str, Any]:
    return {
        "type": "start_location",
        "id": sid,
        "name": data.get("name"),
        "location": data.get("location"),
        "start_setpeice": data.get("start_setpeice"),
        "start_node": data.get("start_node"),
        "raw": {"table": data, "expr": raw},
    }


def extract_startlocations(engine: Any) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for path in getattr(engine, "file_list", []) or []:
        if str(path) != "scripts/map/startlocations.lua":
            continue
        content = engine.read_file(path) or ""
        if "AddStartLocation" not in content:
            continue
        locals_map = extract_local_tables(content)
        extractor = LuaCallExtractor(content)
        for call in extractor.iter_calls("AddStartLocation"):
            if len(call.arg_list) < 2:
                continue
            sid = parse_string(call.arg_list[0]) or ""
            sid = str(sid).strip()
            if not sid:
                continue
            data, raw = resolve_table(call.arg_list[1], locals_map)
            out[sid] = _build_start_location(sid, data, raw)
    return out

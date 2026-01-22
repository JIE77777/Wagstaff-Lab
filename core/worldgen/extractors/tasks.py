# -*- coding: utf-8 -*-
"""Extract tasks from map/tasks*.lua."""

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


def _build_task(tid: str, data: Dict[str, Any], raw: str) -> Dict[str, Any]:
    return {
        "type": "task",
        "id": tid,
        "locks": coerce_list(data.get("locks")),
        "keys_given": coerce_list(data.get("keys_given")),
        "room_choices": coerce_map(data.get("room_choices")),
        "room_bg": data.get("room_bg"),
        "background_room": data.get("background_room"),
        "colour": coerce_map(data.get("colour")),
        "raw": {"table": data, "expr": raw},
    }


def extract_tasks(engine: Any) -> Dict[str, Dict[str, Any]]:
    tasks: Dict[str, Dict[str, Any]] = {}
    for path in getattr(engine, "file_list", []) or []:
        if not str(path).startswith("scripts/map/tasks"):
            continue
        if not str(path).endswith(".lua"):
            continue
        content = engine.read_file(path) or ""
        if "AddTask" not in content:
            continue
        locals_map = extract_local_tables(content)
        extractor = LuaCallExtractor(content)
        for call in extractor.iter_calls("AddTask"):
            if len(call.arg_list) < 2:
                continue
            tid = parse_string(call.arg_list[0]) or ""
            tid = str(tid).strip()
            if not tid:
                continue
            data, raw = resolve_table(call.arg_list[1], locals_map)
            tasks[tid] = _build_task(tid, data, raw)
    return tasks

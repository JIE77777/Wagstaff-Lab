# -*- coding: utf-8 -*-
"""Extract task sets from map/tasksets*.lua."""

from __future__ import annotations

from typing import Any, Dict

from core.lua.call_extractor import LuaCallExtractor
from core.worldgen.extractors.common import coerce_list, coerce_map, parse_string, resolve_table


def _build_taskset(tid: str, data: Dict[str, Any], raw: str) -> Dict[str, Any]:
    return {
        "type": "taskset",
        "id": tid,
        "name": data.get("name"),
        "location": data.get("location"),
        "tasks": coerce_list(data.get("tasks")),
        "optionaltasks": coerce_list(data.get("optionaltasks")),
        "numoptionaltasks": data.get("numoptionaltasks"),
        "valid_start_tasks": coerce_list(data.get("valid_start_tasks")),
        "required_prefabs": coerce_list(data.get("required_prefabs")),
        "set_pieces": coerce_map(data.get("set_pieces")),
        "ocean_population": coerce_list(data.get("ocean_population")),
        "raw": {"table": data, "expr": raw},
    }


def extract_tasksets(engine: Any) -> Dict[str, Dict[str, Any]]:
    tasksets: Dict[str, Dict[str, Any]] = {}
    for path in getattr(engine, "file_list", []) or []:
        if not str(path).startswith("scripts/map/tasksets"):
            continue
        if not str(path).endswith(".lua"):
            continue
        content = engine.read_file(path) or ""
        if "AddTaskSet" not in content:
            continue
        extractor = LuaCallExtractor(content)
        for call in extractor.iter_calls("AddTaskSet"):
            if len(call.arg_list) < 2:
                continue
            tid = parse_string(call.arg_list[0]) or ""
            tid = str(tid).strip()
            if not tid:
                continue
            data, raw = resolve_table(call.arg_list[1], {})
            tasksets[tid] = _build_taskset(tid, data, raw)
    return tasksets

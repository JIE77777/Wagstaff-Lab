# -*- coding: utf-8 -*-
"""Extract worldgen/settings presets from map/levels*.lua."""

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


def _build_worldgen_preset(pid: str, data: Dict[str, Any], raw: str, level_type: str) -> Dict[str, Any]:
    overrides = coerce_map(data.get("overrides"))
    required_setpieces = coerce_list(data.get("required_setpieces"))
    random_set_pieces = coerce_list(data.get("random_set_pieces"))
    numrandom_set_pieces = data.get("numrandom_set_pieces")

    task_set = overrides.get("task_set") if overrides else None
    start_location = overrides.get("start_location") if overrides else None

    return {
        "type": "worldgen_preset",
        "id": pid,
        "name": data.get("name"),
        "desc": data.get("desc"),
        "location": data.get("location"),
        "version": data.get("version"),
        "task_set": task_set,
        "start_location": start_location,
        "required_setpieces": required_setpieces,
        "random_set_pieces": random_set_pieces,
        "numrandom_set_pieces": numrandom_set_pieces,
        "overrides": overrides,
        "level_type": level_type,
        "raw": {"table": data, "expr": raw},
    }


def _build_settings_preset(pid: str, data: Dict[str, Any], raw: str, level_type: str) -> Dict[str, Any]:
    overrides = coerce_map(data.get("overrides"))
    return {
        "type": "settings_preset",
        "id": pid,
        "name": data.get("name"),
        "desc": data.get("desc"),
        "location": data.get("location"),
        "version": data.get("version"),
        "overrides": overrides,
        "playstyle": data.get("playstyle"),
        "level_type": level_type,
        "raw": {"table": data, "expr": raw},
    }


def extract_presets(engine: Any) -> Dict[str, Dict[str, Dict[str, Any]]]:
    settings: Dict[str, Dict[str, Any]] = {}
    worldgen: Dict[str, Dict[str, Any]] = {}

    for path in getattr(engine, "file_list", []) or []:
        if not str(path).startswith("scripts/map/levels"):
            continue
        if not str(path).endswith(".lua"):
            continue
        content = engine.read_file(path) or ""
        if "AddLevel" not in content and "AddWorldGenLevel" not in content and "AddSettingsPreset" not in content:
            continue

        locals_map = extract_local_tables(content)
        extractor = LuaCallExtractor(content)
        for call in extractor.iter_calls(["AddLevel", "AddWorldGenLevel", "AddSettingsPreset"]):
            if len(call.arg_list) < 2:
                continue
            level_type = parse_string(call.arg_list[0]) or ""
            table_expr = call.arg_list[1]
            data, raw = resolve_table(table_expr, locals_map)
            pid = data.get("id") or parse_string(table_expr) or ""
            pid = str(pid).strip()
            if not pid:
                continue

            if call.name == "AddSettingsPreset":
                settings[pid] = _build_settings_preset(pid, data, raw, level_type)
            else:
                worldgen[pid] = _build_worldgen_preset(pid, data, raw, level_type)

    return {
        "settings": settings,
        "worldgen": worldgen,
    }

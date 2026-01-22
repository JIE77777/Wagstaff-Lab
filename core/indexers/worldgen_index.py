# -*- coding: utf-8 -*-
"""Worldgen index builder (core)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from core.indexers.shared import _sha256_12_file
from core.schemas.meta import build_meta
from core.worldgen.extractors import (
    extract_layouts,
    extract_presets,
    extract_rooms,
    extract_startlocations,
    extract_tasks,
    extract_tasksets,
)


SCHEMA_VERSION = 1


def _scripts_sha(engine: Any) -> str | None:
    if getattr(engine, "mode", None) == "zip":
        zf = getattr(engine, "source", None)
        if zf is not None and hasattr(zf, "filename"):
            path = Path(str(zf.filename))
            return _sha256_12_file(path)
    return None


def _build_links(doc: Dict[str, Any]) -> Dict[str, list]:
    links: Dict[str, list] = {
        "preset_taskset": [],
        "taskset_task": [],
        "task_room": [],
        "room_layout": [],
        "preset_set_piece": [],
        "taskset_set_piece": [],
        "start_location": [],
    }

    tasksets = doc.get("tasksets") or {}
    tasks = doc.get("tasks") or {}
    rooms = doc.get("rooms") or {}
    presets = (doc.get("presets") or {}).get("worldgen") or {}
    start_locations = doc.get("start_locations") or {}

    for pid, row in presets.items():
        task_set = row.get("task_set")
        if task_set:
            links["preset_taskset"].append(
                {"source": "preset", "source_id": pid, "target": "taskset", "target_id": task_set, "relation": "task_set"}
            )
        for sp_id in row.get("required_setpieces") or []:
            links["preset_set_piece"].append(
                {"source": "preset", "source_id": pid, "target": "set_piece", "target_id": sp_id, "relation": "required"}
            )
        for sp_id in row.get("random_set_pieces") or []:
            links["preset_set_piece"].append(
                {"source": "preset", "source_id": pid, "target": "set_piece", "target_id": sp_id, "relation": "random"}
            )

    for tid, row in tasksets.items():
        for task_id in row.get("tasks") or []:
            links["taskset_task"].append(
                {"source": "taskset", "source_id": tid, "target": "task", "target_id": task_id, "relation": "main"}
            )
        for task_id in row.get("optionaltasks") or []:
            links["taskset_task"].append(
                {"source": "taskset", "source_id": tid, "target": "task", "target_id": task_id, "relation": "optional"}
            )
        for task_id in row.get("valid_start_tasks") or []:
            links["taskset_task"].append(
                {"source": "taskset", "source_id": tid, "target": "task", "target_id": task_id, "relation": "valid_start"}
            )
        for sp_id in (row.get("set_pieces") or {}).keys():
            links["taskset_set_piece"].append(
                {"source": "taskset", "source_id": tid, "target": "set_piece", "target_id": sp_id, "relation": "taskset"}
            )

    for task_id, row in tasks.items():
        for room_id, weight in (row.get("room_choices") or {}).items():
            links["task_room"].append(
                {
                    "source": "task",
                    "source_id": task_id,
                    "target": "room",
                    "target_id": room_id,
                    "relation": "room_choice",
                    "weight": weight,
                }
            )
        bg_room = row.get("background_room")
        if bg_room:
            links["task_room"].append(
                {
                    "source": "task",
                    "source_id": task_id,
                    "target": "room",
                    "target_id": bg_room,
                    "relation": "background_room",
                }
            )

    for rid, row in rooms.items():
        contents = row.get("contents") or {}
        static_layouts = contents.get("static_layouts") or []
        for layout_id in static_layouts if isinstance(static_layouts, list) else []:
            links["room_layout"].append(
                {
                    "source": "room",
                    "source_id": rid,
                    "target": "layout",
                    "target_id": layout_id,
                    "relation": "static_layout",
                }
            )

    for sid, row in start_locations.items():
        start_node = row.get("start_node")
        if isinstance(start_node, list):
            for rn in start_node:
                links["start_location"].append(
                    {"source": "start_location", "source_id": sid, "target": "room", "target_id": rn, "relation": "start_node"}
                )
        elif start_node:
            links["start_location"].append(
                {"source": "start_location", "source_id": sid, "target": "room", "target_id": start_node, "relation": "start_node"}
            )

    return links


def build_worldgen_index(engine: Any) -> Dict[str, Any]:
    presets = extract_presets(engine)
    tasksets = extract_tasksets(engine)
    tasks = extract_tasks(engine)
    rooms = extract_rooms(engine)
    layouts, set_pieces = extract_layouts(engine)
    start_locations = extract_startlocations(engine)

    counts = {
        "settings_presets_total": len((presets.get("settings") or {})),
        "worldgen_presets_total": len((presets.get("worldgen") or {})),
        "tasksets_total": len(tasksets),
        "tasks_total": len(tasks),
        "rooms_total": len(rooms),
        "layouts_total": len(layouts),
        "set_pieces_total": len(set_pieces),
        "start_locations_total": len(start_locations),
    }

    sources = {"scripts_mode": getattr(engine, "mode", None)}
    scripts_sha = _scripts_sha(engine)
    if scripts_sha:
        sources["scripts_sha256_12"] = scripts_sha

    meta = build_meta(schema=SCHEMA_VERSION, tool="worldgen-index", sources=sources)

    doc = {
        "schema_version": SCHEMA_VERSION,
        "meta": meta,
        "counts": counts,
        "presets": presets,
        "tasksets": tasksets,
        "tasks": tasks,
        "rooms": rooms,
        "layouts": {"static": layouts, "dynamic": {}},
        "set_pieces": set_pieces,
        "start_locations": start_locations,
    }
    doc["links"] = _build_links(doc)
    return doc

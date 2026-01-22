# -*- coding: utf-8 -*-
"""Build a lightweight topology skeleton from worldgen structures."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.worldgen.topology.graph_metrics import compute_graph_metrics


def _node_id(kind: str, raw_id: str) -> str:
    return f"{kind}:{raw_id}"


def _add_node(nodes: Dict[str, Dict[str, Any]], kind: str, raw_id: str, **extra: Any) -> str:
    nid = _node_id(kind, raw_id)
    if nid not in nodes:
        nodes[nid] = {"id": nid, "kind": kind, "raw_id": raw_id, **extra}
    return nid


def build_topology_graph(data: Dict[str, Any]) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    tasksets = data.get("tasksets") or {}
    tasks = data.get("tasks") or {}
    rooms = data.get("rooms") or {}
    presets = (data.get("presets") or {}).get("worldgen") or {}
    start_locations = data.get("start_locations") or {}
    set_pieces = data.get("set_pieces") or {}

    # Taskset -> task links
    for tid, row in tasksets.items():
        ts_node = _add_node(nodes, "taskset", tid, label=row.get("name"))
        for task_id in row.get("tasks") or []:
            tnode = _add_node(nodes, "task", str(task_id))
            edges.append({"source": ts_node, "target": tnode, "relation": "main"})
        for task_id in row.get("optionaltasks") or []:
            tnode = _add_node(nodes, "task", str(task_id))
            edges.append({"source": ts_node, "target": tnode, "relation": "optional"})
        for task_id in row.get("valid_start_tasks") or []:
            tnode = _add_node(nodes, "task", str(task_id))
            edges.append({"source": ts_node, "target": tnode, "relation": "valid_start"})

        for sp_id in (row.get("set_pieces") or {}).keys():
            sp_node = _add_node(nodes, "set_piece", str(sp_id))
            edges.append({"source": ts_node, "target": sp_node, "relation": "taskset_set_piece"})

    # Task -> room links
    for task_id, row in tasks.items():
        tnode = _add_node(nodes, "task", task_id)
        room_choices = row.get("room_choices") or {}
        for room_id, weight in room_choices.items():
            rnode = _add_node(nodes, "room", str(room_id))
            edges.append({"source": tnode, "target": rnode, "relation": "room_choice", "weight": weight})

        bg_room = row.get("background_room")
        if bg_room:
            rnode = _add_node(nodes, "room", str(bg_room))
            edges.append({"source": tnode, "target": rnode, "relation": "background_room"})

    # Preset -> taskset / set pieces
    for pid, row in presets.items():
        pnode = _add_node(nodes, "preset", pid, label=row.get("name"))
        task_set = row.get("task_set")
        if task_set:
            ts_node = _add_node(nodes, "taskset", str(task_set))
            edges.append({"source": pnode, "target": ts_node, "relation": "task_set"})
        for sp_id in row.get("required_setpieces") or []:
            sp_node = _add_node(nodes, "set_piece", str(sp_id))
            edges.append({"source": pnode, "target": sp_node, "relation": "required"})
        for sp_id in row.get("random_set_pieces") or []:
            sp_node = _add_node(nodes, "set_piece", str(sp_id))
            edges.append({"source": pnode, "target": sp_node, "relation": "random"})

    # Start locations
    for sid, row in start_locations.items():
        snode = _add_node(nodes, "start_location", sid, label=row.get("name"))
        start_node = row.get("start_node")
        if isinstance(start_node, list):
            for rn in start_node:
                rnode = _add_node(nodes, "room", str(rn))
                edges.append({"source": snode, "target": rnode, "relation": "start_node"})
        elif start_node:
            rnode = _add_node(nodes, "room", str(start_node))
            edges.append({"source": snode, "target": rnode, "relation": "start_node"})

        sp = row.get("start_setpeice")
        if sp:
            sp_node = _add_node(nodes, "set_piece", str(sp))
            edges.append({"source": snode, "target": sp_node, "relation": "start_setpiece"})

    # Set piece nodes (from layouts)
    for sp_id in set_pieces.keys():
        _add_node(nodes, "set_piece", str(sp_id))

    metrics = compute_graph_metrics(list(nodes.values()), edges)
    metrics["nodes"] = len(nodes)
    metrics["edges"] = len(edges)

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "metrics": metrics,
        "meta": {"topology_kind": "static_skeleton"},
    }

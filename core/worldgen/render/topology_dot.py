# -*- coding: utf-8 -*-
"""Render topology graph as DOT."""

from __future__ import annotations

from typing import Dict, List


_KIND_SHAPE = {
    "preset": "box",
    "taskset": "box",
    "task": "ellipse",
    "room": "diamond",
    "set_piece": "note",
    "start_location": "octagon",
}


def render_topology_dot(graph: Dict[str, List[dict]]) -> str:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    lines = ["digraph worldgen_topology {"]
    lines.append("  rankdir=LR;")
    lines.append("  node [fontsize=10];")

    for node in nodes:
        nid = node.get("id")
        if not nid:
            continue
        kind = node.get("kind") or "node"
        shape = _KIND_SHAPE.get(kind, "ellipse")
        label = node.get("raw_id") or nid
        lines.append(f'  "{nid}" [label="{label}" shape="{shape}"];')

    for edge in edges:
        src = edge.get("source")
        dst = edge.get("target")
        if not src or not dst:
            continue
        rel = edge.get("relation") or ""
        lines.append(f'  "{src}" -> "{dst}" [label="{rel}"];')

    lines.append("}")
    return "\n".join(lines)

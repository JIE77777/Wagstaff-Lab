# -*- coding: utf-8 -*-
"""Graph metrics for worldgen topology."""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Set


def _build_undirected_adj(nodes: List[dict], edges: List[dict]) -> Dict[str, Set[str]]:
    adj: Dict[str, Set[str]] = {str(n.get("id")): set() for n in nodes if n.get("id") is not None}
    for e in edges:
        src = str(e.get("source"))
        dst = str(e.get("target"))
        if src not in adj or dst not in adj:
            continue
        adj[src].add(dst)
        adj[dst].add(src)
    return adj


def compute_graph_metrics(nodes: List[dict], edges: List[dict]) -> dict:
    if not nodes:
        return {"components": 0, "avg_degree": 0.0, "cycle_count": 0}

    adj = _build_undirected_adj(nodes, edges)
    visited: Set[str] = set()
    components = 0
    for node_id in adj:
        if node_id in visited:
            continue
        components += 1
        q = deque([node_id])
        visited.add(node_id)
        while q:
            cur = q.popleft()
            for nxt in adj.get(cur, []):
                if nxt in visited:
                    continue
                visited.add(nxt)
                q.append(nxt)

    degree_sum = sum(len(v) for v in adj.values())
    avg_degree = degree_sum / max(len(adj), 1)

    # Undirected cycle count (independent cycles)
    edge_count = len(edges)
    cycle_count = edge_count - len(adj) + components
    if cycle_count < 0:
        cycle_count = 0

    return {
        "components": components,
        "avg_degree": round(avg_degree, 4),
        "cycle_count": cycle_count,
    }

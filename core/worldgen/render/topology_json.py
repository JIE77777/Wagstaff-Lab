# -*- coding: utf-8 -*-
"""Render topology graph as JSON-ready dict."""

from __future__ import annotations

from typing import Any, Dict


def render_topology_json(graph: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "nodes": graph.get("nodes") or [],
        "edges": graph.get("edges") or [],
        "metrics": graph.get("metrics") or {},
        "meta": meta or {},
    }
    return out

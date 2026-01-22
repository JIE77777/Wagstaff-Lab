# -*- coding: utf-8 -*-
"""Behavior graph index builder (core).

Scope: stategraph + brain structural extraction (MVP).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

from core.indexers.shared import _sha256_12_file
from core.lua import LuaCallExtractor, strip_lua_comments
from core.lua.match import _find_matching
from core.lua.split import _split_top_level
from core.schemas.meta import build_meta


SCHEMA_VERSION = 1


def _scan_stategraph_files(engine: Any) -> List[str]:
    return [
        f
        for f in getattr(engine, "file_list", []) or []
        if str(f).startswith("scripts/stategraphs/") and str(f).endswith(".lua")
    ]


def _scan_brain_files(engine: Any) -> List[str]:
    return [
        f
        for f in getattr(engine, "file_list", []) or []
        if str(f).startswith("scripts/brains/") and str(f).endswith(".lua")
    ]


def _iter_state_blocks(clean: str) -> List[Tuple[str, str]]:
    blocks: List[Tuple[str, str]] = []
    for m in re.finditer(r"State\s*\{", clean):
        open_brace = clean.find("{", m.start())
        if open_brace < 0:
            continue
        close = _find_matching(clean, open_brace, "{", "}")
        if close is None:
            continue
        block = clean[m.start() : close + 1]
        name_m = re.search(r"name\s*=\s*['\"]([A-Za-z0-9_]+)['\"]", block)
        name = name_m.group(1) if name_m else ""
        blocks.append((name, block))
    return blocks


def _extract_state_edges(state: str, block: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    edges: List[Dict[str, Any]] = []
    timers: List[str] = []
    edge_seen = set()

    event_edge_pat = re.compile(
        r"EventHandler\s*\(\s*['\"]([A-Za-z0-9_]+)['\"]\s*,\s*function.*?GoToState\s*\(\s*['\"]([A-Za-z0-9_]+)['\"]",
        re.DOTALL,
    )
    for m in event_edge_pat.finditer(block):
        trigger = m.group(1)
        target = m.group(2)
        key = f"{state}:{trigger}:{target}"
        if key in edge_seen:
            continue
        edge_seen.add(key)
        edges.append(
            {
                "from": state,
                "to": target,
                "trigger": trigger,
                "condition": None,
                "tags": ["event"],
            }
        )

    goto_pat = re.compile(r"GoToState\s*\(\s*['\"]([A-Za-z0-9_]+)['\"]")
    for m in goto_pat.finditer(block):
        target = m.group(1)
        key = f"{state}:goto:{target}"
        if key in edge_seen:
            continue
        edge_seen.add(key)
        edges.append(
            {
                "from": state,
                "to": target,
                "trigger": "goto",
                "condition": None,
                "tags": ["state"],
            }
        )

    time_pat = re.compile(r"TimeEvent\s*\(\s*([^,]+)\s*,")
    for m in time_pat.finditer(block):
        expr = m.group(1).strip()
        if expr:
            timers.append(f"{state}:{expr}")

    return edges, timers


def _parse_stategraph(content: str) -> Dict[str, Any]:
    clean = strip_lua_comments(content or "")
    states = sorted(set(re.findall(r"State\s*\{\s*name\s*=\s*['\"]([A-Za-z0-9_]+)['\"]", clean)))
    events = sorted(set(re.findall(r"EventHandler\s*\(\s*['\"]([A-Za-z0-9_]+)['\"]", clean)))

    edges: List[Dict[str, Any]] = []
    edge_seen = set()
    edge_pat = re.compile(
        r"EventHandler\s*\(\s*['\"]([A-Za-z0-9_]+)['\"]\s*,\s*function.*?GoToState\s*\(\s*['\"]([A-Za-z0-9_]+)['\"]",
        re.DOTALL,
    )
    for m in edge_pat.finditer(clean):
        trigger = m.group(1)
        target = m.group(2)
        key = f"*:{trigger}:{target}"
        if key in edge_seen:
            continue
        edge_seen.add(key)
        edges.append(
            {
                "from": "*",
                "to": target,
                "trigger": trigger,
                "condition": None,
                "tags": ["event"],
            }
        )

    timers: List[str] = []
    for state, block in _iter_state_blocks(clean):
        if not state:
            continue
        block_edges, block_timers = _extract_state_edges(state, block)
        for edge in block_edges:
            key = f"{edge.get('from')}:{edge.get('trigger')}:{edge.get('to')}"
            if key in edge_seen:
                continue
            edge_seen.add(key)
            edges.append(edge)
        timers.extend(block_timers)

    return {
        "states": states,
        "edges": edges,
        "events": events,
        "timers": sorted(set(timers)),
    }


def _scan_assignment_expr(text: str, start: int) -> str:
    n = len(text)
    i = start
    depth = 0
    started = False
    while i < n:
        ch = text[i]
        if not started and ch.isspace():
            i += 1
            continue
        started = True
        if ch == "\n" and depth == 0:
            break
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        i += 1
    return text[start:i].strip().rstrip(",")


def _collect_local_assignments(clean: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in re.finditer(r"\blocal\s+([A-Za-z0-9_]+)\s*=", clean):
        var = m.group(1)
        expr = _scan_assignment_expr(clean, m.end())
        if expr:
            out[var] = expr
    return out


def _compact_args(args: List[str]) -> Dict[str, Any]:
    preview = []
    for arg in args[:4]:
        s = arg.strip()
        if len(s) > 120:
            s = s[:117] + "..."
        preview.append(s)
    return {"args_total": len(args), "args_preview": preview}


def _parse_node_expr(expr: str, *, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], graph_id: str, depth: int = 0) -> Optional[str]:
    if not expr or depth > 24:
        return None
    expr = expr.strip()
    m = re.match(r"([A-Za-z0-9_]+(?:Node|Decorator))\s*\(", expr)
    if not m:
        return None
    kind = m.group(1)
    open_paren = expr.find("(", m.end() - 1)
    close = _find_matching(expr, open_paren, "(", ")")
    if close is None:
        return None
    args_str = expr[open_paren + 1 : close]
    args = [a for a in _split_top_level(args_str, ",") if a]

    node_id = f"{graph_id}:{len(nodes) + 1}"
    nodes.append(
        {
            "id": node_id,
            "kind": kind,
            "condition": None,
            "params": _compact_args(args),
        }
    )

    child_exprs: List[str] = []
    if args:
        first = args[0].strip()
        if first.startswith("{") and first.endswith("}"):
            inner = first[1:-1].strip()
            if inner:
                child_exprs.extend([c for c in _split_top_level(inner, ",") if c])

    if not child_exprs:
        for arg in args:
            if re.match(r"\s*[A-Za-z0-9_]+(?:Node|Decorator)\s*\(", arg):
                child_exprs.append(arg)

    for child in child_exprs:
        child_id = _parse_node_expr(child, nodes=nodes, edges=edges, graph_id=graph_id, depth=depth + 1)
        if child_id:
            edges.append({"from": node_id, "to": child_id, "rule": None})

    return node_id


def _parse_brain(content: str, graph_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    clean = strip_lua_comments(content or "")
    local_assignments = _collect_local_assignments(clean)

    extractor = LuaCallExtractor(clean)
    bt_calls = list(extractor.iter_calls("BT", include_member_calls=False))
    if not bt_calls:
        return [], [], None

    root_expr = None
    for call in bt_calls:
        if len(call.arg_list) >= 2:
            root_expr = call.arg_list[1]
            break

    if not root_expr:
        return [], [], None

    root_expr = root_expr.strip()
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", root_expr):
        root_expr = local_assignments.get(root_expr, root_expr)

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    _parse_node_expr(root_expr, nodes=nodes, edges=edges, graph_id=graph_id)
    return nodes, edges, None


def build_behavior_graph(*, engine: Any, resource_index: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    stategraph_files = _scan_stategraph_files(engine)
    brain_files = _scan_brain_files(engine)

    stategraphs: Dict[str, Any] = {}
    for path in stategraph_files:
        content = engine.read_file(path) or ""
        gid = Path(str(path)).stem
        parsed = _parse_stategraph(content)
        stategraphs[gid] = {
            "id": gid,
            "source": path,
            **parsed,
            "notes": "mvp+: state block edges + event handler transitions",
        }

    brains: Dict[str, Any] = {}
    for path in brain_files:
        content = engine.read_file(path) or ""
        gid = Path(str(path)).stem
        nodes, edges, priority = _parse_brain(content, gid)
        brains[gid] = {
            "id": gid,
            "source": path,
            "nodes": nodes,
            "edges": edges,
            "priority": priority,
            "notes": "mvp+: bt root parse with heuristic node edges",
        }

    prefab_links: Dict[str, Any] = {}
    prefabs = (resource_index or {}).get("prefabs") or {}
    items = prefabs.get("items") if isinstance(prefabs, dict) else None
    items = items if isinstance(items, dict) else {}
    for pid, row in items.items():
        if not isinstance(row, dict):
            continue
        stategraphs_list = row.get("stategraphs") or []
        brains_list = row.get("brains") or []
        sg = stategraphs_list[0] if isinstance(stategraphs_list, list) and stategraphs_list else None
        brain = brains_list[0] if isinstance(brains_list, list) and brains_list else None
        prefab_links[str(pid)] = {"stategraph": sg, "brain": brain}

    scripts_zip = getattr(getattr(engine, "source", None), "filename", None)
    scripts_sha = _sha256_12_file(Path(scripts_zip)) if scripts_zip else None
    scripts_dir = getattr(engine, "source", None) if getattr(engine, "mode", "") == "folder" else None

    meta = build_meta(
        schema=SCHEMA_VERSION,
        tool="build_behavior_graph",
        sources={
            "resource_index": "wagstaff_resource_index_v1.json",
            "scripts_zip": scripts_zip,
            "scripts_dir": scripts_dir,
        },
        extra={
            "scripts_sha256_12": scripts_sha,
            "scripts_zip": scripts_zip,
            "scripts_dir": scripts_dir,
        },
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "meta": meta,
        "counts": {
            "stategraphs_total": len(stategraphs),
            "brains_total": len(brains),
            "prefabs_total": len(prefab_links),
        },
        "stategraphs": stategraphs,
        "brains": brains,
        "prefab_links": prefab_links,
    }

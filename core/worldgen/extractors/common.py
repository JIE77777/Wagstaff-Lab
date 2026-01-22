# -*- coding: utf-8 -*-
"""Shared helpers for worldgen extractors."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from core.lua.expr import LuaTableValue, lua_to_python, parse_lua_expr
from core.lua.match import _find_matching
from core.lua.scan import strip_lua_comments


def parse_expr(expr: str) -> Any:
    return lua_to_python(parse_lua_expr(expr))


def parse_table_expr(expr: str) -> Optional[Dict[str, Any]]:
    parsed = parse_lua_expr(expr)
    if isinstance(parsed, LuaTableValue):
        val = lua_to_python(parsed)
        if isinstance(val, dict):
            return val
    return None


def parse_string(expr: str) -> Optional[str]:
    val = parse_expr(expr)
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return str(val)


def coerce_list(val: Any) -> list:
    if val is None:
        return []
    if isinstance(val, dict) and "__array__" in val:
        arr = val.get("__array__") or []
        return [coerce_scalar(v) for v in arr if v is not None]
    if isinstance(val, list):
        return [coerce_scalar(v) for v in val if v is not None]
    return [coerce_scalar(val)]


def coerce_map(val: Any) -> Dict[str, Any]:
    if isinstance(val, dict):
        if "__array__" in val:
            out = dict(val)
            out.pop("__array__", None)
            return {str(k): v for k, v in out.items()}
        return {str(k): v for k, v in val.items()}
    return {}


def coerce_scalar(val: Any) -> Any:
    if isinstance(val, dict) and "__array__" in val:
        return val.get("__array__") or []
    return val


def extract_local_tables(content: str) -> Dict[str, str]:
    text = strip_lua_comments(content or "")
    out: Dict[str, str] = {}
    i = 0
    pattern = re.compile(r"(?<![A-Za-z0-9_])(?:local\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{")
    while True:
        m = pattern.search(text, i)
        if not m:
            break
        name = m.group(1)
        brace_start = text.find("{", m.end() - 1)
        if brace_start == -1:
            i = m.end()
            continue
        brace_end = _find_matching(text, brace_start, "{", "}")
        if brace_end is None:
            i = m.end()
            continue
        out[name] = text[brace_start: brace_end + 1]
        i = brace_end + 1
    return out


def resolve_table(expr: str, local_tables: Dict[str, str]) -> Tuple[Dict[str, Any], str]:
    expr = (expr or "").strip()
    if expr in local_tables:
        raw = local_tables[expr]
        parsed = parse_table_expr(raw) or {}
        return parsed, raw
    parsed = parse_table_expr(expr) or {}
    return parsed, expr

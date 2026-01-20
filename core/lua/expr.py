# -*- coding: utf-8 -*-
"""Lua expression parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional

from core.lua.match import _find_matching
from core.lua.scan import _long_bracket_level, strip_lua_comments
from core.lua.split import _split_top_level

__all__ = [
    "LuaRaw",
    "LuaTableValue",
    "lua_to_python",
    "parse_lua_string",
    "parse_lua_expr",
    "parse_lua_table",
    "_NUM_RE",
]


@dataclass
class LuaRaw:
    """Opaque expression (kept as raw text)."""

    text: str


@dataclass
class LuaTableValue:
    """Lua table constructor parsed into (array, map)."""

    array: List[Any]
    map: Dict[Any, Any]


def lua_to_python(v: Any) -> Any:
    """Recursively convert LuaTableValue/LuaRaw into plain Python types."""
    if isinstance(v, LuaRaw):
        return v.text
    if isinstance(v, LuaTableValue):
        arr = [lua_to_python(x) for x in v.array]
        mp = {lua_to_python(k): lua_to_python(val) for k, val in v.map.items()}
        if mp and arr:
            return {"__array__": arr, **mp}
        if mp:
            return mp
        return arr
    if isinstance(v, list):
        return [lua_to_python(x) for x in v]
    if isinstance(v, dict):
        return {lua_to_python(k): lua_to_python(val) for k, val in v.items()}
    return v


_NUM_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?$")


def _parse_lua_string(expr: str) -> Optional[str]:
    expr = (expr or "").strip()
    if len(expr) >= 2 and expr[0] == expr[-1] and expr[0] in ("'", '"'):
        body = expr[1:-1]
        body = body.replace(r"\\", "\\").replace(r"\'", "'").replace(r"\"", '"')
        return body
    if expr.startswith("["):
        level = _long_bracket_level(expr, 0)
        if level is not None:
            opener_len = 2 + level
            close_pat = "]" + ("=" * level) + "]"
            end = expr.find(close_pat, opener_len)
            if end != -1:
                return expr[opener_len:end]
    return None


def parse_lua_string(expr: str) -> Optional[str]:
    """Public wrapper: parse a Lua string literal (short or long bracket)."""
    return _parse_lua_string(expr)


def parse_lua_expr(expr: str) -> Any:
    """
    Parse a subset of Lua expressions into Python types:
    - string/long-string -> str
    - number -> int/float
    - true/false/nil -> bool/None
    - table constructor -> LuaTableValue
    - function (...) ... end -> LuaRaw("<function>")
    - identifier/dotted path / everything else -> LuaRaw(expr)
    """
    expr = (expr or "").strip()
    if not expr:
        return LuaRaw("")

    if expr.startswith("function"):
        sig_end = expr.find(")")
        if sig_end != -1 and sig_end < 160:
            return LuaRaw(expr[: sig_end + 1] + " ... end")
        return LuaRaw("<function>")

    if expr == "nil":
        return None
    if expr in ("true", "false"):
        return expr == "true"

    s = _parse_lua_string(expr)
    if s is not None:
        return s

    if _NUM_RE.match(expr):
        try:
            f = float(expr)
            return int(f) if f.is_integer() else f
        except Exception:
            return LuaRaw(expr)

    if expr.startswith("{"):
        close = _find_matching(expr, 0, "{", "}")
        if close is None:
            return LuaRaw(expr)
        inner = expr[1:close]
        return parse_lua_table(inner)

    if re.match(r"^[A-Za-z_][A-Za-z0-9_\.]*$", expr):
        return LuaRaw(expr)

    return LuaRaw(expr)


def parse_lua_table(inner: str) -> LuaTableValue:
    """
    Parse the inside of { ... } (without outer braces).
    Returns LuaTableValue(array, map).
    """
    inner = strip_lua_comments(inner)

    array: List[Any] = []
    mp: Dict[Any, Any] = {}

    for item in _split_top_level(inner, ","):
        item = (item or "").strip()
        if not item:
            continue

        # key = value
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", item, flags=re.DOTALL)
        if m:
            key = m.group(1)
            mp[key] = parse_lua_expr(m.group(2))
            continue

        # ["key"] = value (also long bracket keys)
        m = re.match(r'^\[\s*([\'"].*?[\'"]|\[=*\[.*?\]=*\])\s*\]\s*=\s*(.+)$', item, flags=re.DOTALL)
        if m:
            key_raw = m.group(1)
            key = _parse_lua_string(key_raw) or LuaRaw(key_raw)
            mp[key] = parse_lua_expr(m.group(2))
            continue

        # [expr] = value
        m = re.match(r"^\[\s*(.+?)\s*\]\s*=\s*(.+)$", item, flags=re.DOTALL)
        if m:
            mp[LuaRaw(m.group(1).strip())] = parse_lua_expr(m.group(2))
            continue

        # array entry
        array.append(parse_lua_expr(item))

    return LuaTableValue(array=array, map=mp)

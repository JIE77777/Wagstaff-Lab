#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lua parsing primitives + domain analyzers for Wagstaff-Lab.

Core goals
- Robust scanning: skip comments/strings/long-brackets.
- Balanced parsing: brackets + Lua block keywords (function/if/for/while/repeat/do/end/until).
- Practical AST-lite: parse Lua table constructors into (array, map) for data-driven extraction.
- Extract function calls with balanced parentheses (supports member calls obj:Method()).

Public API (intended stable)
- strip_lua_comments(text) -> str
- split_top_level(text, sep=',') -> List[str]
- find_matching(text, open_idx, open_ch, close_ch) -> Optional[int]
- parse_lua_string(expr) -> Optional[str]
- parse_lua_expr(expr) -> Any
- parse_lua_table(inner) -> LuaTableValue
- LuaCallExtractor(content).iter_calls(...)
- TuningResolver(content)
- LuaAnalyzer(content, path=None).get_report()
- CookingRecipeAnalyzer(content).recipes
- CookingIngredientAnalyzer(content).ingredients
"""

from __future__ import annotations

import bisect
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union

__all__ = [
    # scanning helpers
    "strip_lua_comments",
    "split_top_level",
    "find_matching",
    # expr parsing
    "parse_lua_string",
    "parse_lua_expr",
    "parse_lua_table",
    "LuaRaw",
    "LuaTableValue",
    "lua_to_python",
    # call extraction
    "LuaCall",
    "LuaCallExtractor",
    # tuning
    "TuningResolver",
    # domain parsers
    "LootParser",
    "WidgetParser",
    "StringParser",
    "PrefabParser",
    "LuaAnalyzer",
    # cooking
    "CookingRecipeAnalyzer",
    "CookingIngredientAnalyzer",
]


# ============================================================
# 0) Low-level Lua scanning helpers
# ============================================================

_LUA_KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for", "function", "goto",
    "if", "in", "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while",
}


def _is_ident_start(ch: str) -> bool:
    return ch == "_" or ("A" <= ch <= "Z") or ("a" <= ch <= "z")


def _is_ident_char(ch: str) -> bool:
    return _is_ident_start(ch) or ("0" <= ch <= "9")


def _long_bracket_level(text: str, i: int) -> Optional[int]:
    """
    If text[i:] starts a Lua long-bracket opener: [=*[ , return '=' count; else None.
    Examples: [[ -> 0, [=[ -> 1, [==[ -> 2
    """
    n = len(text)
    if i >= n or text[i] != "[":
        return None
    j = i + 1
    while j < n and text[j] == "=":
        j += 1
    if j < n and text[j] == "[":
        return j - i - 1
    return None


def _skip_long_bracket(text: str, i: int, level: int) -> int:
    """Skip Lua long-bracket string/comment starting at i. Return next index."""
    n = len(text)
    opener_len = 2 + level
    start = i + opener_len
    close_pat = "]" + ("=" * level) + "]"
    end = text.find(close_pat, start)
    if end == -1:
        return n
    return end + len(close_pat)


def _skip_short_string(text: str, i: int, quote: str) -> int:
    """Skip '...' or "...", supporting backslash escapes. Return next index."""
    n = len(text)
    i += 1
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == quote:
            return i + 1
        i += 1
    return n


def _skip_comment(text: str, i: int) -> int:
    """i points at '-' and text[i:i+2]=='--'. Skip a line or block comment. Return next index."""
    n = len(text)
    if not text.startswith("--", i):
        return i

    # Block comment: --[=*[ ... ]=*]
    if i + 2 < n and text[i + 2] == "[":
        level = _long_bracket_level(text, i + 2)
        if level is not None:
            return _skip_long_bracket(text, i + 2, level)

    # Line comment
    nl = text.find("\n", i + 2)
    return n if nl == -1 else nl + 1


def _skip_string_or_long_string(text: str, i: int) -> Optional[int]:
    """If position i starts a string/long-string, return next index; else None."""
    if i >= len(text):
        return None
    ch = text[i]
    if ch in ("'", '"'):
        return _skip_short_string(text, i, ch)
    if ch == "[":
        level = _long_bracket_level(text, i)
        if level is not None:
            return _skip_long_bracket(text, i, level)
    return None


def strip_lua_comments(text: str) -> str:
    """
    Remove Lua comments while preserving line breaks (keeps line numbers stable).
    Strings/long-strings are preserved.
    """
    if not text:
        return ""
    n = len(text)
    out: List[str] = []
    i = 0
    while i < n:
        if text.startswith("--", i):
            j = _skip_comment(text, i)
            out.append("\n" * text[i:j].count("\n"))
            i = j
            continue
        nxt = _skip_string_or_long_string(text, i)
        if nxt is not None:
            out.append(text[i:nxt])
            i = nxt
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


# ============================================================
# 1) Balanced splitting (commas at top-level), with Lua block awareness
# ============================================================

def _split_top_level(text: str, sep: str = ",") -> List[str]:
    """
    Split by sep at top level.

    Top level means:
    - not in (), {}, []
    - not in strings/comments/long-strings
    - not inside Lua blocks (function/if/for/while/repeat/do ... end/until)

    This is critical for safely splitting function call arguments in DST scripts.
    """
    if not text:
        return []

    n = len(text)
    parts: List[str] = []
    start = 0
    i = 0

    bracket_stack: List[str] = []
    block_stack: List[Tuple[str, bool]] = []  # (kind, awaiting_do)

    def _push_block(kind: str) -> None:
        block_stack.append((kind, False))

    def _push_loop(kind: str) -> None:
        block_stack.append((kind, True))

    def _on_do() -> None:
        if block_stack and block_stack[-1][0] in ("for", "while") and block_stack[-1][1]:
            kind, _ = block_stack[-1]
            block_stack[-1] = (kind, False)
        else:
            _push_block("do")

    def _on_end() -> None:
        if block_stack:
            block_stack.pop()

    def _on_until() -> None:
        # close the nearest repeat
        for idx in range(len(block_stack) - 1, -1, -1):
            if block_stack[idx][0] == "repeat":
                del block_stack[idx:]
                return

    while i < n:
        if text.startswith("--", i):
            i = _skip_comment(text, i)
            continue

        nxt = _skip_string_or_long_string(text, i)
        if nxt is not None:
            i = nxt
            continue

        ch = text[i]

        if ch in "({[":
            if ch == "[":
                level = _long_bracket_level(text, i)
                if level is not None:
                    i = _skip_long_bracket(text, i, level)
                    continue
            bracket_stack.append(ch)
            i += 1
            continue

        if ch in ")}]":
            want = {")": "(", "}": "{", "]": "["}[ch]
            if bracket_stack and bracket_stack[-1] == want:
                bracket_stack.pop()
            i += 1
            continue

        # block keywords
        if _is_ident_start(ch):
            j = i + 1
            while j < n and _is_ident_char(text[j]):
                j += 1
            word = text[i:j]
            if word == "function":
                _push_block("function")
            elif word == "if":
                _push_block("if")
            elif word == "for":
                _push_loop("for")
            elif word == "while":
                _push_loop("while")
            elif word == "repeat":
                _push_block("repeat")
            elif word == "do":
                _on_do()
            elif word == "end":
                _on_end()
            elif word == "until":
                _on_until()
            i = j
            continue

        if ch == sep and not bracket_stack and not block_stack:
            parts.append(text[start:i].strip())
            start = i + 1
            i += 1
            continue

        i += 1

    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def split_top_level(text: str, sep: str = ",") -> List[str]:
    """Public wrapper for _split_top_level."""
    return _split_top_level(text, sep)


def _find_matching(text: str, open_idx: int, open_ch: str, close_ch: str) -> Optional[int]:
    """Find the matching closing bracket for open_ch at open_idx. Skip strings/comments/long brackets."""
    n = len(text)
    if open_idx >= n or text[open_idx] != open_ch:
        return None

    stack: List[str] = [open_ch]
    i = open_idx + 1
    while i < n and stack:
        if text.startswith("--", i):
            i = _skip_comment(text, i)
            continue
        nxt = _skip_string_or_long_string(text, i)
        if nxt is not None:
            i = nxt
            continue

        ch = text[i]
        if ch in "({[":
            if ch == "[":
                level = _long_bracket_level(text, i)
                if level is not None:
                    i = _skip_long_bracket(text, i, level)
                    continue
            stack.append(ch)
            i += 1
            continue

        if ch in ")}]":
            want = {")": "(", "}": "{", "]": "["}[ch]
            if stack and stack[-1] == want:
                stack.pop()
            i += 1
            continue

        i += 1

    if stack:
        return None
    return i - 1


def find_matching(text: str, open_idx: int, open_ch: str, close_ch: str) -> Optional[int]:
    """Public wrapper for _find_matching."""
    return _find_matching(text, open_idx, open_ch, close_ch)


# ============================================================
# 2) Expression parser (subset; practical for DST data tables)
# ============================================================

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


# ============================================================
# 3) Lua call extractor (NAME(...) and obj:Method(...))
# ============================================================

@dataclass(frozen=True)
class LuaCall:
    name: str
    full_name: str
    start: int
    end: int
    open_paren: int
    close_paren: int
    args: str
    arg_list: List[str]
    line: int
    col: int


class LuaCallExtractor:
    """
    Extract Lua function calls with balanced parentheses, skipping comments/strings/long strings.

    Supports:
    - NAME(...)
    - obj.NAME(...)
    - obj:NAME(...)
    """

    def __init__(self, content: str):
        self.content = content or ""
        self._line_starts: Optional[List[int]] = None

    def iter_calls(
        self,
        names: Union[str, Sequence[str]],
        *,
        include_member_calls: bool = True,
        match_full_name: bool = False,
    ) -> Iterator[LuaCall]:
        if isinstance(names, str):
            targets = {names}
        else:
            targets = set(names)

        text = self.content
        n = len(text)
        i = 0

        while i < n:
            if text.startswith("--", i):
                i = _skip_comment(text, i)
                continue

            nxt = _skip_string_or_long_string(text, i)
            if nxt is not None:
                i = nxt
                continue

            ch = text[i]
            if _is_ident_start(ch):
                # first ident
                j = i + 1
                while j < n and _is_ident_char(text[j]):
                    j += 1
                first = text[i:j]
                if first in _LUA_KEYWORDS:
                    i = j
                    continue

                full = first
                last = first
                k = j

                if include_member_calls:
                    # ".ident" / ":ident" chain
                    while True:
                        kk = k
                        while kk < n and text[kk].isspace():
                            kk += 1
                        if kk < n and text[kk] in ".:":
                            sep = text[kk]
                            kk += 1
                            while kk < n and text[kk].isspace():
                                kk += 1
                            if kk < n and _is_ident_start(text[kk]):
                                jj = kk + 1
                                while jj < n and _is_ident_char(text[jj]):
                                    jj += 1
                                seg = text[kk:jj]
                                full = full + sep + seg
                                last = seg
                                k = jj
                                continue
                        break

                hit = (full in targets) if match_full_name else (last in targets)
                if hit:
                    kk = k
                    while kk < n and text[kk].isspace():
                        kk += 1
                    if kk < n and text[kk] == "(":
                        close = _find_matching(text, kk, "(", ")")
                        if close is not None:
                            args = text[kk + 1: close]
                            arg_list = self.split_args(args)
                            line, col = self._line_col(i)
                            yield LuaCall(
                                name=last,
                                full_name=full,
                                start=i,
                                end=close + 1,
                                open_paren=kk,
                                close_paren=close,
                                args=args,
                                arg_list=arg_list,
                                line=line,
                                col=col,
                            )
                            i = close + 1
                            continue

                i = k
                continue

            i += 1

    def extract_calls(self, names: Union[str, Sequence[str]], **kwargs: Any) -> List[LuaCall]:
        return list(self.iter_calls(names, **kwargs))

    def split_args(self, args: str) -> List[str]:
        return [p for p in _split_top_level(args, ",") if p]

    def _ensure_line_starts(self) -> None:
        if self._line_starts is not None:
            return
        self._line_starts = [0]
        for m in re.finditer("\n", self.content):
            self._line_starts.append(m.end())

    def _line_col(self, pos: int) -> Tuple[int, int]:
        self._ensure_line_starts()
        assert self._line_starts is not None
        idx = bisect.bisect_right(self._line_starts, pos) - 1
        line_start = self._line_starts[idx]
        return idx + 1, (pos - line_start) + 1


# ============================================================
# 4) TuningResolver (chain + simple arithmetic evaluation)
# ============================================================

_ARITH_TOKEN_RE = re.compile(r"\s*(\d+\.\d+|\d+|[A-Za-z_][A-Za-z0-9_\.]*|\*\*|\^|[+\-*/()])\s*")


class TuningResolver:
    """
    Lightweight resolver for DST `scripts/tuning.lua`.

    Goals
    - Parse common constant assignments:
        - `local NAME = <rhs>`  (UPPER_CASE only)
        - `TUNING.NAME = <rhs>`
    - Resolve numeric chains and simple arithmetic expressions.
    - Provide *traceable* resolution (for UI/wiki), not only final numbers.

    Notes
    - This is intentionally conservative: if an expression can't be proven safe and numeric,
      resolution returns None rather than guessing.
    """

    _REF_PAT = re.compile(
        r"TUNING\.([A-Za-z0-9_]+)|TUNING\[\s*([\'\"])([A-Za-z0-9_]+)\2\s*\]"
    )

    def __init__(self, content: str):
        self.raw_map: Dict[str, Any] = {}
        self.local_map: Dict[str, Any] = {}
        if content:
            self._parse_tuning(content)

    # --------------------------
    # Parsing
    # --------------------------

    def _parse_tuning(self, content: str) -> None:
        clean = strip_lua_comments(content)

        # locals (allow lowercase; many tuning constants depend on lower vars like calories_per_day)
        for m in re.finditer(r"^\s*local\s+([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$", clean, flags=re.MULTILINE):
            name, rhs = m.group(1), m.group(2)
            rhs = rhs.strip().rstrip(",")
            val = self._parse_rhs(rhs)
            if val is not None:
                self.local_map[name] = val

        # TUNING.KEY = rhs
        for m in re.finditer(r"^\s*TUNING\.([A-Z0-9_]+)\s*=\s*(.+?)\s*$", clean, flags=re.MULTILINE):
            key, rhs = m.group(1), m.group(2)
            rhs = rhs.strip().rstrip(",")
            val = self._parse_rhs(rhs)
            self.raw_map[key] = val if val is not None else rhs

        # TUNING = { KEY = rhs, ... }
        for m_table in re.finditer(r"\bTUNING\s*=\s*\{", clean):
            open_idx = clean.find("{", m_table.start())
            close_idx = find_matching(clean, open_idx, "{", "}")
            if close_idx is None:
                continue
            inner = clean[open_idx + 1 : close_idx]
            for m in re.finditer(r"^\s*([A-Z0-9_]+)\s*=\s*(.+?)\s*(?:,|$)", inner, flags=re.MULTILINE):
                key, rhs = m.group(1), m.group(2)
                rhs = rhs.strip().rstrip(",")
                val = self._parse_rhs(rhs)
                if key not in self.raw_map:
                    self.raw_map[key] = val if val is not None else rhs

    def _parse_rhs(self, rhs: str) -> Optional[Any]:
        rhs = (rhs or "").strip().rstrip(",")
        if not rhs:
            return None
        if rhs in ("true", "false"):
            return rhs == "true"
        if rhs == "nil":
            return None

        s = _parse_lua_string(rhs)
        if s is not None:
            return s

        if _NUM_RE.match(rhs):
            try:
                f = float(rhs)
                return int(f) if f.is_integer() else f
            except Exception:
                return None

        # keep as raw string expression / symbol
        return rhs

    # --------------------------
    # Resolution (internal)
    # --------------------------

    @staticmethod
    def _norm_key(ref: str) -> str:
        ref = (ref or "").strip()
        return ref[7:] if ref.startswith("TUNING.") else ref

    def _resolve_ref(self, ref: str, depth: int = 8) -> Optional[Union[int, float]]:
        """Resolve a ref/expression to a number (or None)."""
        if depth <= 0:
            return None
        ref = (ref or "").strip()
        if not ref:
            return None

        # numeric literal
        if _NUM_RE.match(ref):
            try:
                f = float(ref)
                return int(f) if f.is_integer() else f
            except Exception:
                return None

        # math.* function calls (limited whitelist)
        m_call = re.match(r"^math\.([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$", ref)
        if m_call:
            fn = m_call.group(1).lower()
            args_raw = m_call.group(2)
            args: List[Optional[Union[int, float]]] = []
            for part in _split_top_level(args_raw, sep=","):
                part = part.strip()
                if not part:
                    continue
                args.append(self._resolve_ref(part, depth - 1))
            # only proceed if all args resolved
            if any(a is None for a in args):
                return None
            vals = [float(a) for a in args if a is not None]
            try:
                if fn == "abs" and len(vals) == 1:
                    return abs(vals[0])
                if fn == "floor" and len(vals) == 1:
                    return math.floor(vals[0])
                if fn == "ceil" and len(vals) == 1:
                    return math.ceil(vals[0])
                if fn == "sqrt" and len(vals) == 1:
                    return math.sqrt(vals[0])
                if fn == "max" and vals:
                    return max(vals)
                if fn == "min" and vals:
                    return min(vals)
                if fn in ("pow",) and len(vals) == 2:
                    return math.pow(vals[0], vals[1])
            except Exception:
                return None
            return None

        # direct symbol (TUNING.X / local X)
        if re.match(r"^[A-Za-z_][A-Za-z0-9_\.]*$", ref):
            key = self._norm_key(ref)
            v = self.raw_map.get(key, self.local_map.get(key))
            if isinstance(v, (int, float)):
                return v
            if isinstance(v, str) and v and v != ref:
                # symbol chain (A -> B) or expression
                if re.match(r"^[A-Za-z_][A-Za-z0-9_\.]*$", v):
                    return self._resolve_ref(v, depth - 1)
                return self._resolve_ref(v, depth - 1)
            return None

        # arithmetic expression (conservative tokenizer)
        py_parts: List[str] = []
        for tok in _ARITH_TOKEN_RE.findall(ref):
            tok = tok.strip()
            if not tok:
                continue

            # Lua exponent
            if tok == "^":
                py_parts.append("**")
                continue
            if tok in {"+", "-", "*", "/", "(", ")", "**"}:
                py_parts.append(tok)
                continue
            if _NUM_RE.match(tok):
                py_parts.append(tok)
                continue

            val = self._resolve_ref(tok, depth - 1)
            if val is None:
                return None
            py_parts.append(str(val))

        expr_py = "".join(py_parts)
        # Safety: only numbers + operators
        if re.search(r"[^0-9\.\+\-\*\/\(\)eE]", expr_py):
            return None
        try:
            out = eval(expr_py, {"__builtins__": {}}, {})
            if isinstance(out, (int, float)):
                if isinstance(out, float) and out.is_integer():
                    return int(out)
                return out
        except Exception:
            return None
        return None

    # --------------------------
    # Public APIs
    # --------------------------

    def explain(self, key: str, max_hops: int = 10) -> Tuple[str, Optional[Union[int, float]]]:
        """Return (chain_text, resolved_value)."""
        key = self._norm_key(key)
        if not key:
            return "", None

        chain: List[str] = []
        visited = set()
        cur = key

        for _ in range(max_hops):
            if cur in visited:
                chain.append(f"{cur} (loop)")
                break
            visited.add(cur)

            v = self.raw_map.get(cur, self.local_map.get(cur))
            if v is None:
                chain.append(cur)
                break

            chain.append(cur)

            if isinstance(v, (int, float)):
                chain.append(str(v))
                return " -> ".join(chain), v

            if isinstance(v, str):
                chain.append(v)
                if re.match(r"^[A-Za-z_][A-Za-z0-9_\.]*$", v):
                    cur = self._norm_key(v)
                    continue
                val = self._resolve_ref(v)
                if val is not None:
                    chain.append(str(val))
                    return " -> ".join(chain), val
                break

            chain.append(str(v))
            break

        # fallback try resolve the symbol itself (handles local->expr cases)
        val = self._resolve_ref(key)
        return " -> ".join(chain) if chain else key, val

    def trace_key(self, key: str, max_hops: int = 16) -> Dict[str, Any]:
        """Structured trace for a single TUNING key."""
        key0 = key
        key = self._norm_key(key)
        steps: List[Dict[str, Any]] = []
        visited = set()
        cur = key

        for _ in range(max_hops):
            if not cur:
                break
            if cur in visited:
                steps.append({"key": cur, "raw": None, "note": "loop"})
                break
            visited.add(cur)

            v = self.raw_map.get(cur, self.local_map.get(cur))
            steps.append({"key": cur, "raw": v})

            if isinstance(v, (int, float)):
                chain = " -> ".join([str(s.get("key") or "") for s in steps] + [str(v)])
                return {"key": key0, "normalized": key, "value": v, "steps": steps, "chain": chain}

            if isinstance(v, str) and re.match(r"^[A-Za-z_][A-Za-z0-9_\.]*$", v):
                cur = self._norm_key(v)
                continue

            # expression or unknown
            if isinstance(v, str):
                val = self._resolve_ref(v)
                return {
                    "key": key0,
                    "normalized": key,
                    "value": val,
                    "steps": steps + [{"key": "<expr>", "raw": v, "value": val}],
                    "chain": " -> ".join([str(s.get("key") or s.get("raw") or "") for s in steps] + [v, str(val)]),
                }
            break

        # fallback
        val = self._resolve_ref(key)
        return {
            "key": key0,
            "normalized": key,
            "value": val,
            "steps": steps,
            "chain": " -> ".join([str(s.get("key") or s.get("raw") or "") for s in steps if s.get("key")] + ([str(val)] if val is not None else [])),
        }

    def trace_expr(self, expr: str) -> Dict[str, Any]:
        """Trace an arbitrary expression containing TUNING refs."""
        expr = (expr or "").strip()
        refs = []
        for m in self._REF_PAT.finditer(expr):
            k = m.group(1) or m.group(3)
            if k and k not in refs:
                refs.append(k)

        ref_traces: Dict[str, Any] = {}
        for k in refs:
            ref_traces[k] = self.trace_key(k)

        value = self._resolve_ref(expr)

        # best-effort normalized expression (TUNING.X -> number)
        expr_resolved = expr
        for k in refs:
            v = ref_traces.get(k, {}).get("value")
            if isinstance(v, (int, float)):
                expr_resolved = re.sub(
                    rf"\bTUNING\.{re.escape(k)}\b",
                    str(v),
                    expr_resolved,
                )
                expr_resolved = re.sub(
                    rf"TUNING\[\s*([\'\"])\s*{re.escape(k)}\s*\1\s*\]",
                    str(v),
                    expr_resolved,
                )

        return {
            "expr": expr,
            "value": value,
            "expr_resolved": expr_resolved,
            "refs": ref_traces,
            "expr_chain": " ; ".join(sorted([rt.get("chain") or "" for rt in ref_traces.values() if rt])),
        }

    def enrich(self, text: str) -> str:
        """Inline enrichment: replace `TUNING.X` in text with `TUNING.X (chain)` when resolvable."""
        if not text or "TUNING" not in text:
            return text

        def repl(m: re.Match) -> str:
            key = m.group(1) or m.group(3)
            if not key:
                return m.group(0)
            chain, val = self.explain(key)
            if val is None:
                return f"TUNING.{key}"
            return f"TUNING.{key} ({chain})"

        return self._REF_PAT.sub(repl, text)


# ============================================================
# 5) Domain parsers (Prefab / Loot / Widgets / Strings)
# ============================================================

class BaseParser:
    def __init__(self, content: str, path: Optional[str] = None):
        self.path = path
        self.content = content or ""
        self.clean = strip_lua_comments(self.content)

    def _extract_requires(self) -> List[str]:
        return re.findall(r'require\s*\(?\s*["\'](.*?)["\']\s*\)?', self.clean)


class LootParser(BaseParser):
    """Parse shared loot tables + simple loot helpers."""
    def parse(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"type": "loot", "table_name": None, "entries": []}
        extractor = LuaCallExtractor(self.content)

        for call in extractor.iter_calls("SetSharedLootTable"):
            if not call.arg_list:
                continue
            name = parse_lua_string(call.arg_list[0]) or None
            if name:
                data["table_name"] = name
            if len(call.arg_list) >= 2:
                tbl = parse_lua_expr(call.arg_list[1])
                if isinstance(tbl, LuaTableValue):
                    for row in tbl.array:
                        if isinstance(row, LuaTableValue) and len(row.array) >= 2:
                            item = row.array[0]
                            chance = row.array[1]
                            if isinstance(item, str) and isinstance(chance, (int, float)):
                                data["entries"].append({"item": item, "chance": float(chance), "method": "TableData"})

        for call in extractor.iter_calls(["AddRandomLoot", "AddRandomLootTable"]):
            if len(call.arg_list) >= 2:
                item = parse_lua_string(call.arg_list[0])
                w = parse_lua_expr(call.arg_list[1])
                if isinstance(item, str) and isinstance(w, (int, float)):
                    data["entries"].append({"item": item, "weight": float(w), "method": "Random"})

        for call in extractor.iter_calls("AddChanceLoot"):
            if len(call.arg_list) >= 2:
                item = parse_lua_string(call.arg_list[0])
                c = parse_lua_expr(call.arg_list[1])
                if isinstance(item, str) and isinstance(c, (int, float)):
                    data["entries"].append({"item": item, "chance": float(c), "method": "Chance"})

        return data


class WidgetParser(BaseParser):
    def parse(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"type": "widget", "classes": [], "dependencies": self._extract_requires()}
        for name, parent in re.findall(r"local\s+([A-Za-z0-9_]+)\s*=\s*Class\s*\(\s*([A-Za-z0-9_]+)", self.clean):
            data["classes"].append({"name": name, "parent": parent})
        return data


class StringParser(BaseParser):
    def parse(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"type": "strings", "roots": [], "includes": self._extract_requires()}
        roots = set()
        roots.update(re.findall(r"STRINGS\.([A-Z0-9_]+)\s*=\s*\{", self.clean))
        roots.update(re.findall(r"STRINGS\.([A-Z0-9_]+)\s*=\s*['\"]", self.clean))
        data["roots"] = sorted(roots)
        return data


class PrefabParser(BaseParser):
    def parse(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "type": "prefab",
            "assets": [],
            "components": [],
            "helpers": [],
            "stategraph": None,
            "brain": None,
            "events": [],
            "tags": [],
            "prefab_name": None,
        }

        extractor = LuaCallExtractor(self.content)

        for call in extractor.iter_calls("Prefab"):
            if call.arg_list:
                nm = parse_lua_string(call.arg_list[0])
                if nm:
                    data["prefab_name"] = nm
                    break

        for call in extractor.iter_calls("Asset"):
            if len(call.arg_list) >= 2:
                t = parse_lua_string(call.arg_list[0])
                p = parse_lua_string(call.arg_list[1])
                if isinstance(t, str) and isinstance(p, str):
                    data["assets"].append({"type": t, "path": p})

        m = re.search(r"SetBrain\s*\(\s*require\s*\(\s*['\"](.*?)['\"]\s*\)\s*\)", self.clean)
        if m:
            data["brain"] = m.group(1)
        m = re.search(r"SetStateGraph\s*\(\s*['\"](.*?)['\"]\s*\)", self.clean)
        if m:
            data["stategraph"] = m.group(1)

        data["events"] = re.findall(r'EventHandler\s*\(\s*["\']([^"\']+)["\']\s*,', self.clean)
        data["helpers"] = sorted(set(re.findall(r"^\s*(Make[A-Za-z0-9_]+)\s*\(", self.content, flags=re.MULTILINE)))

        tags: List[str] = []
        for call in extractor.iter_calls("AddTag"):
            if call.arg_list:
                tg = parse_lua_string(call.arg_list[0])
                if tg:
                    tags.append(tg)
        data["tags"] = sorted(set(tags))

        comps = set()
        for call in extractor.iter_calls("AddComponent"):
            if call.arg_list:
                cn = parse_lua_string(call.arg_list[0])
                if cn:
                    comps.add(cn)

        for comp_name in sorted(comps):
            comp_data = {"name": comp_name, "methods": [], "properties": []}

            method_pat = re.compile(r"components\." + re.escape(comp_name) + r"[:\.]([A-Za-z0-9_]+)\s*\((.*?)\)", re.DOTALL)
            for m_name, m_args in method_pat.findall(self.clean):
                clean_args = re.sub(r"\s+", " ", m_args).strip()
                if len(clean_args) > 60:
                    clean_args = clean_args[:57] + "..."
                comp_data["methods"].append(f"{m_name}({clean_args})")

            prop_pat = re.compile(r"components\." + re.escape(comp_name) + r"\.([A-Za-z0-9_]+)\s*=\s*([^=\n]+)")
            for p_name, p_val in prop_pat.findall(self.clean):
                comp_data["properties"].append(f"{p_name} = {p_val.strip()}")

            data["components"].append(comp_data)

        return data


class LuaAnalyzer:
    """Facade: choose best strategy based on content + optional path."""
    def __init__(self, content: str, path: Optional[str] = None):
        self.content = content or ""
        self.path = path
        self.parser = self._select_strategy()

    def _select_strategy(self) -> BaseParser:
        p = (self.path or "").replace("\\", "/")
        c = self.content

        if p.startswith("scripts/widgets/") or p.startswith("scripts/screens/"):
            return WidgetParser(c, p)
        if p.startswith("scripts/strings"):
            return StringParser(c, p)
        if p.startswith("scripts/prefabs/"):
            return PrefabParser(c, p)

        if "Class(Widget" in c or "Class(Screen" in c or 'require "widgets/' in c or "require('widgets/" in c:
            return WidgetParser(c, p)
        if "return Prefab" in c or "Prefab(" in c:
            return PrefabParser(c, p)
        if "STRINGS." in c and "STRINGS.CHARACTERS" in c:
            return StringParser(c, p)
        if "SetSharedLootTable" in c or "AddChanceLoot" in c:
            return LootParser(c, p)
        return PrefabParser(c, p)

    def get_report(self) -> Dict[str, Any]:
        return self.parser.parse()


# ============================================================
# 6) Cooking recipe analyzer (preparedfoods*.lua)
# ============================================================

# ============================================================
# 6) Cooking recipe analyzer (preparedfoods*.lua)
# ============================================================

def _iter_named_table_blocks(parent_table_body: str) -> Iterable[Tuple[str, str]]:
    """
    Iterate top-level `name = { ... }` blocks inside a parent table body (WITHOUT outer braces).

    This is stricter than a regex: it skips strings/comments and respects nested braces.
    """
    text = parent_table_body or ""
    n = len(text)
    i = 0
    depth = 0

    while i < n:
        if text.startswith("--", i):
            i = _skip_comment(text, i)
            continue

        nxt = _skip_string_or_long_string(text, i)
        if nxt is not None:
            i = nxt
            continue

        ch = text[i]

        if ch == "{":
            depth += 1
            i += 1
            continue
        if ch == "}":
            depth = max(0, depth - 1)
            i += 1
            continue

        if depth == 0:
            # skip whitespace/commas between entries
            if ch.isspace() or ch == ",":
                i += 1
                continue

            if _is_ident_start(ch):
                j = i + 1
                while j < n and _is_ident_char(text[j]):
                    j += 1
                name = text[i:j]

                k = j
                while k < n and text[k].isspace():
                    k += 1
                if k < n and text[k] == "=":
                    k += 1
                    while k < n and text[k].isspace():
                        k += 1
                    if k < n and text[k] == "{":
                        open_idx = k
                        close_idx = _find_matching(text, open_idx, "{", "}")
                        if close_idx is None:
                            i = j
                            continue
                        body = text[open_idx + 1: close_idx]
                        yield name, body
                        i = close_idx + 1
                        continue

                i = j
                continue

        i += 1


def _find_lua_function_end(text: str, fn_start: int) -> Optional[int]:
    """Return index right after the `end` that closes the function started at fn_start."""
    if fn_start < 0 or fn_start >= len(text):
        return None
    if not text.startswith("function", fn_start):
        return None

    n = len(text)
    i = fn_start

    bracket_stack: List[str] = []
    block_stack: List[Tuple[str, bool]] = []  # (kind, awaiting_do)

    def _push_block(kind: str) -> None:
        block_stack.append((kind, False))

    def _push_loop(kind: str) -> None:
        block_stack.append((kind, True))

    def _on_do() -> None:
        if block_stack and block_stack[-1][0] in ("for", "while") and block_stack[-1][1]:
            kind, _ = block_stack[-1]
            block_stack[-1] = (kind, False)
        else:
            _push_block("do")

    def _on_end() -> None:
        if block_stack:
            block_stack.pop()

    def _on_until() -> None:
        # close the nearest repeat
        for idx in range(len(block_stack) - 1, -1, -1):
            if block_stack[idx][0] == "repeat":
                del block_stack[idx:]
                return

    # consume the initial 'function'
    _push_block("function")
    i += len("function")

    while i < n and block_stack:
        if text.startswith("--", i):
            i = _skip_comment(text, i)
            continue
        nxt = _skip_string_or_long_string(text, i)
        if nxt is not None:
            i = nxt
            continue

        ch = text[i]

        # bracket stack (keep keywords inside parentheses from confusing us less; still scan keywords)
        if ch in "({[":
            if ch == "[":
                level = _long_bracket_level(text, i)
                if level is not None:
                    i = _skip_long_bracket(text, i, level)
                    continue
            bracket_stack.append(ch)
            i += 1
            continue

        if ch in ")}]":
            want = {")": "(", "}": "{", "]": "["}[ch]
            if bracket_stack and bracket_stack[-1] == want:
                bracket_stack.pop()
            i += 1
            continue

        if _is_ident_start(ch):
            j = i + 1
            while j < n and _is_ident_char(text[j]):
                j += 1
            word = text[i:j]

            if word == "function":
                _push_block("function")
            elif word == "if":
                _push_block("if")
            elif word == "for":
                _push_loop("for")
            elif word == "while":
                _push_loop("while")
            elif word == "repeat":
                _push_block("repeat")
            elif word == "do":
                _on_do()
            elif word == "end":
                _on_end()
                if not block_stack:
                    return j
            elif word == "until":
                _on_until()
                if not block_stack:
                    return j

            i = j
            continue

        i += 1

    return None


def _extract_test_return_expr(entry_body: str) -> Optional[str]:
    """Extract the boolean return expression from `test = function(...) return <expr> end`."""
    if not entry_body:
        return None

    m = re.search(r"\btest\s*=\s*function\b", entry_body)
    if not m:
        return None

    fn_start = m.end() - len("function")
    fn_end = _find_lua_function_end(entry_body, fn_start)
    if fn_end is None:
        return None

    fn_src = entry_body[fn_start:fn_end]
    clean = strip_lua_comments(fn_src)

    mret = re.search(r"\breturn\b\s*([\s\S]*?)\bend\b", clean)
    if not mret:
        return None

    expr = mret.group(1).strip()
    expr = re.sub(r"\s+", " ", expr)
    return expr or None


def _parse_rule_constraints(expr: str) -> Dict[str, Any]:
    """Best-effort extraction of common `names.*` / `tags.*` constraints from test-return expr."""
    expr = (expr or "").strip()
    out: Dict[str, Any] = {"raw": expr, "tags": [], "names": [], "unparsed": []}
    if not expr:
        return out

    # Normalize spaces to reduce corner cases
    e = re.sub(r"\s+", " ", expr)

    seen = set()

    # comparisons: tags.X <op> (number|nil|identifier)
    cmp_pat = re.compile(
        r"\b(?P<scope>tags|names)\.(?P<key>[A-Za-z0-9_]+)\s*(?P<op>==|~=|<=|>=|<|>)\s*(?P<rhs>[^\s\)\]]+)"
    )
    for m in cmp_pat.finditer(e):
        scope = m.group("scope")
        key = m.group("key")
        op = m.group("op")
        rhs = m.group("rhs").rstrip(",")
        rhs_norm: Any
        if rhs == "nil":
            rhs_norm = None
        elif _NUM_RE.match(rhs):
            try:
                rhs_norm = float(rhs)
                if isinstance(rhs_norm, float) and rhs_norm.is_integer():
                    rhs_norm = int(rhs_norm)
            except Exception:
                rhs_norm = rhs
        else:
            rhs_norm = rhs

        rec = (scope, key, op, str(rhs_norm))
        if rec in seen:
            continue
        seen.add(rec)
        out[scope].append({"key": key, "op": op, "value": rhs_norm, "text": m.group(0)})

    # presence (truthy): tags.X / names.X
    pres_pat = re.compile(r"\b(?P<scope>tags|names)\.(?P<key>[A-Za-z0-9_]+)\b(?!\s*(==|~=|<=|>=|<|>))")
    for m in pres_pat.finditer(e):
        scope = m.group("scope")
        key = m.group("key")
        rec = (scope, key, ">", 0)
        if rec in seen:
            continue
        seen.add(rec)
        out[scope].append({"key": key, "op": ">", "value": 0, "text": m.group(0)})

    # negated presence: not tags.X / not names.X
    neg_pat = re.compile(r"\bnot\s+(?P<scope>tags|names)\.(?P<key>[A-Za-z0-9_]+)\b")
    for m in neg_pat.finditer(e):
        scope = m.group("scope")
        key = m.group("key")
        rec = (scope, key, "==", 0)
        if rec in seen:
            continue
        seen.add(rec)
        out[scope].append({"key": key, "op": "==", "value": 0, "text": m.group(0)})

    return out


class CookingRecipeAnalyzer:
    """
    Parse preparedfoods*.lua (data-driven part).

    Extract stable fields for wiki/web:
    - priority/weight/foodtype/hunger/health/sanity/perishtime/cooktime/tags
    - card_def.ingredients -> card_ingredients: list[[item, count], ...]
    - rule constraints (best-effort): `test = function(...) return ... end`
    """

    STABLE_KEYS = (
        "priority",
        "weight",
        "foodtype",
        "hunger",
        "health",
        "sanity",
        "perishtime",
        "cooktime",
        "tags",
    )

    def __init__(self, content: str):
        self.content = content or ""
        self.recipes: Dict[str, Dict[str, Any]] = {}
        if content:
            self._parse()

    def _parse(self) -> None:
        # most files: local foods = { ... }
        m = re.search(r"local\s+foods\s*=\s*\{", self.content)
        if not m:
            return
        open_idx = m.end() - 1
        close_idx = _find_matching(self.content, open_idx, "{", "}")
        if close_idx is None:
            return

        inner = self.content[open_idx + 1: close_idx]

        for name, body in _iter_named_table_blocks(inner):
            tbl = parse_lua_table(body)
            if not isinstance(tbl, LuaTableValue):
                continue

            mp = tbl.map
            out: Dict[str, Any] = {}

            for key in self.STABLE_KEYS:
                if key in mp:
                    out[key] = lua_to_python(mp[key])

            # card_def.ingredients -> card_ingredients
            card = mp.get("card_def")
            if isinstance(card, LuaTableValue):
                ing = card.map.get("ingredients")
                if isinstance(ing, LuaTableValue):
                    rows: List[List[Any]] = []
                    for r in ing.array:
                        if isinstance(r, LuaTableValue) and len(r.array) >= 2:
                            rows.append([lua_to_python(r.array[0]), lua_to_python(r.array[1])])
                    if rows:
                        out["card_ingredients"] = rows

            # rule constraints (test-return expr)
            test_expr = _extract_test_return_expr(body)
            if test_expr:
                out["rule"] = {
                    "kind": "test_return",
                    "expr": test_expr,
                    "constraints": _parse_rule_constraints(test_expr),
                }

            if out:
                self.recipes[name] = out


# ============================================================
# 7) Cooking ingredient analyzer (ingredients.lua / cooking.lua)
# ============================================================

_ING_ID_RE = re.compile(r"^[a-z0-9_]+$")


def _clean_ingredient_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw = raw.lower()
    if not _ING_ID_RE.match(raw):
        return None
    return raw


def _coerce_tag_value(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and _NUM_RE.match(value):
        try:
            return float(value)
        except Exception:
            return None
    return None


def _parse_tag_table(tags: Any) -> Tuple[Dict[str, float], Dict[str, str]]:
    if not isinstance(tags, LuaTableValue):
        return {}, {}
    out: Dict[str, float] = {}
    expr: Dict[str, str] = {}

    for key, value in tags.map.items():
        k = lua_to_python(key)
        if not isinstance(k, str):
            continue
        k = k.strip().lower()
        if not k:
            continue
        v = lua_to_python(value)
        num = _coerce_tag_value(v)
        if num is None:
            expr[k] = str(v)
        else:
            out[k] = num

    for entry in tags.array:
        k = lua_to_python(entry)
        if not isinstance(k, str):
            continue
        k = k.strip().lower()
        if not k or k in out or k in expr:
            continue
        out[k] = 1.0

    return out, expr


def _extract_table_by_pattern(content: str, pattern: str) -> Optional[LuaTableValue]:
    m = re.search(pattern, content)
    if not m:
        return None
    open_idx = content.find("{", m.end() - 1)
    if open_idx < 0:
        return None
    close_idx = _find_matching(content, open_idx, "{", "}")
    if close_idx is None:
        return None
    inner = content[open_idx + 1 : close_idx]
    try:
        return parse_lua_table(inner)
    except Exception:
        return None


def _find_ingredients_table(content: str) -> Optional[LuaTableValue]:
    patterns = [
        r"(?:^|\b)local\s+ingredients\s*=\s*\{",
        r"(?:^|\b)ingredients\s*=\s*\{",
        r"(?:^|\b)INGREDIENTS\s*=\s*\{",
        r"\bcooking\.ingredients\s*=\s*\{",
    ]
    for pat in patterns:
        tbl = _extract_table_by_pattern(content, pat)
        if isinstance(tbl, LuaTableValue):
            return tbl

    cooking_tbl = _extract_table_by_pattern(content, r"(?:^|\b)local\s+cooking\s*=\s*\{")
    if not isinstance(cooking_tbl, LuaTableValue):
        cooking_tbl = _extract_table_by_pattern(content, r"(?:^|\b)cooking\s*=\s*\{")
    if isinstance(cooking_tbl, LuaTableValue):
        ing = cooking_tbl.map.get("ingredients")
        if isinstance(ing, LuaTableValue):
            return ing

    return None


def _find_named_table(content: str, name: str) -> Optional[LuaTableValue]:
    if not name:
        return None
    pat_name = re.escape(name)
    patterns = [
        rf"(?:^|\b)local\s+{pat_name}\s*=\s*\{{",
        rf"(?:^|\b){pat_name}\s*=\s*\{{",
    ]
    for pat in patterns:
        tbl = _extract_table_by_pattern(content, pat)
        if isinstance(tbl, LuaTableValue):
            return tbl
    return None


def _coerce_lua_bool(expr: str, default: bool = False) -> bool:
    val = parse_lua_expr(expr)
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, LuaRaw):
        raw = val.text.strip().lower()
        if raw == "true":
            return True
        if raw == "false":
            return False
    return default


class CookingIngredientAnalyzer:
    """Parse cooking ingredient definitions and extract tag contributions."""

    def __init__(self, content: str, *, source: str = ""):
        self.content = content or ""
        self.source = source or ""
        self.ingredients: Dict[str, Dict[str, Any]] = {}
        if content:
            self._parse()

    def _parse(self) -> None:
        tbl = _find_ingredients_table(self.content)
        if not isinstance(tbl, LuaTableValue):
            self._parse_add_ingredient_values()
            self._apply_aliases()
            return
        if not (tbl.map or tbl.array):
            self._parse_add_ingredient_values()
            self._apply_aliases()
            return

        for key, value in (tbl.map or {}).items():
            ing_id = _clean_ingredient_id(lua_to_python(key))
            if not ing_id:
                continue

            out: Dict[str, Any] = {"id": ing_id}

            if isinstance(value, LuaTableValue):
                tags, tag_expr = _parse_tag_table(value.map.get("tags"))
                if tags:
                    out["tags"] = tags
                if tag_expr:
                    out["tags_expr"] = tag_expr

                for field in ("name", "atlas", "image", "prefab", "foodtype"):
                    if field in value.map:
                        out[field] = lua_to_python(value.map[field])

            if self.source:
                out["sources"] = [self.source]

            if len(out) > 1:
                self.ingredients[ing_id] = out

        self._apply_aliases()

    def _apply_aliases(self) -> None:
        aliases_tbl = _find_named_table(self.content, "aliases")
        if not isinstance(aliases_tbl, LuaTableValue):
            return
        for alias_key, alias_val in (aliases_tbl.map or {}).items():
            alias = _clean_ingredient_id(lua_to_python(alias_key))
            target = _clean_ingredient_id(lua_to_python(alias_val))
            if not alias or not target:
                continue
            if alias in self.ingredients:
                continue
            src = self.ingredients.get(target)
            if not isinstance(src, dict):
                continue
            out: Dict[str, Any] = {"id": alias}
            if "tags" in src:
                out["tags"] = dict(src["tags"])
            if "tags_expr" in src:
                out["tags_expr"] = dict(src["tags_expr"])
            if "foodtype" in src:
                out["foodtype"] = src["foodtype"]
            if "sources" in src:
                out["sources"] = list(src["sources"])
            if len(out) > 1:
                self.ingredients[alias] = out

    def _parse_add_ingredient_values(self) -> None:
        extractor = LuaCallExtractor(self.content)
        calls = extractor.extract_calls("AddIngredientValues", include_member_calls=False)
        if not calls:
            return

        table_cache: Dict[str, Optional[LuaTableValue]] = {}

        def _resolve_names(expr: str) -> List[str]:
            val = parse_lua_expr(expr)
            if isinstance(val, LuaTableValue):
                names = [lua_to_python(x) for x in val.array]
                return [x for x in names if isinstance(x, str)]
            if isinstance(val, str):
                return [val]
            if isinstance(val, LuaRaw):
                key = val.text.strip()
                if not key:
                    return []
                if key not in table_cache:
                    table_cache[key] = _find_named_table(self.content, key)
                tbl = table_cache.get(key)
                if isinstance(tbl, LuaTableValue):
                    names = [lua_to_python(x) for x in tbl.array]
                    return [x for x in names if isinstance(x, str)]
            return []

        def _set_entry(ing_id: str, tags: Dict[str, float], tag_expr: Dict[str, str]) -> None:
            out: Dict[str, Any] = {"id": ing_id}
            if tags:
                out["tags"] = tags
            if tag_expr:
                out["tags_expr"] = tag_expr
            if self.source:
                out["sources"] = [self.source]
            if len(out) > 1:
                self.ingredients[ing_id] = out

        for call in calls:
            args = [str(a).strip() for a in (call.arg_list or [])]
            if len(args) < 2:
                continue
            names_expr = args[0]
            tags_expr = args[1]
            cancook = _coerce_lua_bool(args[2]) if len(args) >= 3 else False
            candry = _coerce_lua_bool(args[3]) if len(args) >= 4 else False

            names = _resolve_names(names_expr)
            if not names:
                continue
            tags_val = parse_lua_expr(tags_expr)
            tags, tag_expr = _parse_tag_table(tags_val if isinstance(tags_val, LuaTableValue) else None)

            for name in names:
                ing_id = _clean_ingredient_id(name)
                if not ing_id:
                    continue
                _set_entry(ing_id, dict(tags), dict(tag_expr))

                if cancook:
                    cooked_tags = dict(tags)
                    cooked_tags["precook"] = 1.0
                    _set_entry(f"{ing_id}_cooked", cooked_tags, dict(tag_expr))
                if candry:
                    dried_tags = dict(tags)
                    dried_tags["dried"] = 1.0
                    _set_entry(f"{ing_id}_dried", dried_tags, dict(tag_expr))

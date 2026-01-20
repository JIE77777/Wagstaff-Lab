# -*- coding: utf-8 -*-
"""Low-level Lua scanning helpers."""

from __future__ import annotations

from typing import List, Optional

__all__ = [
    "_is_ident_start",
    "_is_ident_char",
    "_long_bracket_level",
    "_skip_long_bracket",
    "_skip_short_string",
    "_skip_comment",
    "_skip_string_or_long_string",
    "strip_lua_comments",
]


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

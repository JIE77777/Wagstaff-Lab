# -*- coding: utf-8 -*-
"""Bracket matching helpers for Lua."""

from __future__ import annotations

from typing import List, Optional

from core.lua.scan import (
    _long_bracket_level,
    _skip_comment,
    _skip_long_bracket,
    _skip_string_or_long_string,
)

__all__ = [
    "_find_matching",
    "find_matching",
]


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

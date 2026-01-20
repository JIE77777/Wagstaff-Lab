# -*- coding: utf-8 -*-
"""Balanced splitting helpers for Lua."""

from __future__ import annotations

from typing import List, Tuple

from core.lua.scan import (
    _is_ident_char,
    _is_ident_start,
    _long_bracket_level,
    _skip_comment,
    _skip_long_bracket,
    _skip_string_or_long_string,
)

__all__ = [
    "_split_top_level",
    "split_top_level",
]


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

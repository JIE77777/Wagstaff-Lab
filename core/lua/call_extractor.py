# -*- coding: utf-8 -*-
"""Lua function call extraction helpers."""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from typing import Iterator, List, Optional, Sequence, Tuple, Union

from core.lua.match import _find_matching
from core.lua.scan import (
    _is_ident_char,
    _is_ident_start,
    _skip_comment,
    _skip_string_or_long_string,
)
from core.lua.split import _split_top_level

__all__ = [
    "LuaCall",
    "LuaCallExtractor",
]


_LUA_KEYWORDS = {
    "and",
    "break",
    "do",
    "else",
    "elseif",
    "end",
    "false",
    "for",
    "function",
    "goto",
    "if",
    "in",
    "local",
    "nil",
    "not",
    "or",
    "repeat",
    "return",
    "then",
    "true",
    "until",
    "while",
}


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
                            args = text[kk + 1 : close]
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

    def extract_calls(self, names: Union[str, Sequence[str]], **kwargs: object) -> List[LuaCall]:
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

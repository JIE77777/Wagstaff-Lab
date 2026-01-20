# -*- coding: utf-8 -*-
"""Component parser (scripts/components/*.lua)."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Set

from core.lua import LuaCallExtractor, parse_lua_string
from core.parsers.base import BaseParser

__all__ = ["ComponentParser"]


def _basename_id(path: Optional[str]) -> str:
    if not path:
        return ""
    base = os.path.basename(path)
    if base.endswith(".lua"):
        base = base[:-4]
    return base.strip().lower()


def _guess_class_name(component_id: str) -> str:
    if not component_id:
        return ""
    parts = [p for p in component_id.split("_") if p]
    if parts:
        return "".join([p[:1].upper() + p[1:] for p in parts])
    return component_id[:1].upper() + component_id[1:]


class ComponentParser(BaseParser):
    """Parse component API surface (methods/fields/events)."""

    def parse(self) -> Dict[str, Any]:
        comp_id = _basename_id(self.path)
        data: Dict[str, Any] = {
            "type": "component",
            "id": comp_id,
            "class_name": None,
            "aliases": [],
            "methods": [],
            "fields": [],
            "events": [],
            "requires": self._extract_requires(),
            "path": self.path,
        }

        aliases: Set[str] = set()
        for m in re.finditer(r"(?m)^\s*(?:local\s+)?([A-Za-z0-9_]+)\s*=\s*Class\b", self.clean):
            aliases.add(m.group(1))

        # prefer an explicit return alias as class name
        class_name = None
        mret = re.search(r"\breturn\s+([A-Za-z0-9_]+)\b", self.clean)
        if mret:
            cand = mret.group(1)
            if cand in aliases:
                class_name = cand

        if class_name is None and aliases:
            class_name = sorted(aliases)[0]

        if not aliases and comp_id:
            guess = _guess_class_name(comp_id)
            aliases.add(guess)
            class_name = guess

        # methods: function Alias:Method(...) / Alias.Method(...)
        methods: Set[str] = set()
        for m in re.finditer(r"\bfunction\s+([A-Za-z0-9_]+)[:\.]([A-Za-z0-9_]+)\s*\(", self.clean):
            obj = m.group(1)
            name = m.group(2)
            if aliases and obj not in aliases:
                continue
            methods.add(name)

        # fields: self.field = ...
        fields = set(re.findall(r"\bself\.([A-Za-z0-9_]+)\s*=", self.clean))

        # events: ListenForEvent("event", ...)
        events: Set[str] = set()
        extractor = LuaCallExtractor(self.content)
        for call in extractor.iter_calls("ListenForEvent"):
            if not call.arg_list:
                continue
            ev = parse_lua_string(call.arg_list[0])
            if isinstance(ev, str) and ev:
                events.add(ev)

        data["class_name"] = class_name
        data["aliases"] = sorted(aliases)
        data["methods"] = sorted(methods)
        data["fields"] = sorted(fields)
        data["events"] = sorted(events)
        return data

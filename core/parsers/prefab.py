# -*- coding: utf-8 -*-
"""Prefab parser."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from core.lua import LuaCallExtractor, parse_lua_string
from core.parsers.base import BaseParser

__all__ = ["PrefabParser"]


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

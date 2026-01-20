# -*- coding: utf-8 -*-
"""Cooking recipe and ingredient analyzers."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from core.lua import (
    LuaCallExtractor,
    LuaRaw,
    LuaTableValue,
    _NUM_RE,
    _find_matching,
    _is_ident_char,
    _is_ident_start,
    _long_bracket_level,
    _skip_comment,
    _skip_long_bracket,
    _skip_string_or_long_string,
    lua_to_python,
    parse_lua_expr,
    parse_lua_table,
    parse_lua_string,
    strip_lua_comments,
)

__all__ = [
    "CookingRecipeAnalyzer",
    "CookingIngredientAnalyzer",
    "parse_oceanfish_ingredients",
]


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
                        body = text[open_idx + 1 : close_idx]
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
    out: Dict[str, Any] = {"raw": expr, "tags": [], "names": [], "names_any": [], "names_sum": [], "unparsed": []}
    if not expr:
        return out

    # Normalize spaces to reduce corner cases
    e = re.sub(r"\s+", " ", expr)

    seen = set()
    sum_seen: Set[Tuple[str, str, int]] = set()
    or_names: Set[str] = set()
    or_spans: List[Tuple[int, int]] = []

    def _add_name_constraint(key: str, op: str, value: Any, text: str) -> None:
        rec = ("names", key, op, str(value))
        if rec in seen:
            return
        seen.add(rec)
        out["names"].append({"key": key, "op": op, "value": value, "text": text})

    def _add_names_sum(keys: List[str], min_val: int, text: str) -> None:
        if len(keys) != 2:
            return
        a = str(keys[0]).strip()
        b = str(keys[1]).strip()
        if not a or not b or a == b:
            return
        key = tuple(sorted((a, b))) + (int(min_val),)
        if key in sum_seen:
            return
        sum_seen.add(key)
        out["names_sum"].append({"keys": [a, b], "min": int(min_val), "text": text})

    # detect parenthesized OR groups: (names.a or names.b)
    paren_pat = re.compile(r"\(([^()]+)\)")
    for m in paren_pat.finditer(e):
        body = m.group(1)
        if not re.match(r"^\s*names\.[A-Za-z0-9_]+(?:\s+or\s+names\.[A-Za-z0-9_]+)+\s*$", body):
            continue
        keys = re.findall(r"\bnames\.([A-Za-z0-9_]+)\b", body)
        if len(keys) < 2:
            continue
        prefix = e[: m.start()].rstrip()
        negated = bool(re.search(r"\bnot$", prefix))
        if negated:
            for key in keys:
                _add_name_constraint(key, "==", 0, f"not names.{key}")
            or_names.update(keys)
            or_spans.append(m.span())
            continue
        out["names_any"].append({"keys": keys, "text": body.strip()})
        or_names.update(keys)
        or_spans.append(m.span())

    # detect inline OR groups: names.a or names.b
    or_pat = re.compile(r"\bnames\.[A-Za-z0-9_]+\b(?:\s+or\s+names\.[A-Za-z0-9_]+\b)+")
    for m in or_pat.finditer(e):
        span = m.span()
        if any(span[0] >= s[0] and span[1] <= s[1] for s in or_spans):
            continue
        body = m.group(0)
        if re.search(r"\bnot\s+names\.", body):
            continue
        prefix = e[: m.start()].rstrip()
        if re.search(r"\bnot$", prefix):
            continue
        keys = re.findall(r"\bnames\.([A-Za-z0-9_]+)\b", body)
        if len(keys) < 2:
            continue
        out["names_any"].append({"keys": keys, "text": body.strip()})
        or_names.update(keys)
        or_spans.append(span)

    # detect OR sum groups: ((names.a and names.a > 1) or (names.b and names.b > 1) or (names.a and names.b))
    sum_pat = re.compile(
        r"\(+\s*names\.(?P<a>[A-Za-z0-9_]+)\s+and\s+names\.(?P=a)\s*(?:>=|>)\s*(?P<n1>[0-9]+)\s*\)+\s+or\s+"
        r"\(+\s*names\.(?P<b>[A-Za-z0-9_]+)\s+and\s+names\.(?P=b)\s*(?:>=|>)\s*(?P<n2>[0-9]+)\s*\)+\s+or\s+"
        r"\(+\s*names\.(?P<x>[A-Za-z0-9_]+)\s+and\s+names\.(?P<y>[A-Za-z0-9_]+)\s*\)+"
    )
    for m in sum_pat.finditer(e):
        a = m.group("a")
        b = m.group("b")
        x = m.group("x")
        y = m.group("y")
        if not a or not b or {x, y} != {a, b}:
            continue
        _add_names_sum([a, b], 2, m.group(0).strip())

    # detect plus sum groups: (names.a + names.b >= N)
    plus_pat = re.compile(
        r"\(?\s*\(?\s*names\.(?P<a>[A-Za-z0-9_]+)\s*(?:or\s*0)?\s*\)?\s*\+\s*"
        r"\(?\s*names\.(?P<b>[A-Za-z0-9_]+)\s*(?:or\s*0)?\s*\)?\s*\)?\s*(?P<op>>=|>)\s*(?P<n>[0-9]+)"
    )
    for m in plus_pat.finditer(e):
        a = m.group("a")
        b = m.group("b")
        op = m.group("op") or ">="
        n = m.group("n") or "0"
        try:
            min_val = int(n)
        except Exception:
            continue
        if op == ">":
            min_val += 1
        _add_names_sum([a, b], min_val, m.group(0).strip())

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

    sum_keys: Set[str] = set()
    for g in out.get("names_sum") or []:
        keys_raw = g.get("keys") if isinstance(g, dict) else None
        if not isinstance(keys_raw, list):
            continue
        for k in keys_raw:
            key = str(k).strip()
            if key:
                sum_keys.add(key)

    if or_names:
        filtered: List[Dict[str, Any]] = []
        for c in out["names"]:
            key = str(c.get("key") or "").strip()
            op = str(c.get("op") or "").strip()
            value = c.get("value")
            if key in or_names and op in (">", ">=") and (value is None or float(value) <= 0):
                continue
            filtered.append(c)
        out["names"] = filtered

    if sum_keys and out.get("names"):
        filtered = []
        for c in out["names"]:
            key = str(c.get("key") or "").strip()
            op = str(c.get("op") or "").strip()
            value = c.get("value")
            try:
                rhs = float(value)
            except Exception:
                rhs = None
            positive = op in (">", ">=") and (rhs is None or rhs >= 0)
            if op == "==" and rhs is not None and rhs > 0:
                positive = True
            if key in sum_keys and positive:
                continue
            filtered.append(c)
        out["names"] = filtered

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

        inner = self.content[open_idx + 1 : close_idx]

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


def parse_oceanfish_ingredients(content: str, *, source: str = "") -> Dict[str, Dict[str, Any]]:
    fish_tbl = _find_named_table(content or "", "FISH_DEFS")
    if not isinstance(fish_tbl, LuaTableValue):
        return {}

    out: Dict[str, Dict[str, Any]] = {}

    def _resolve_tags(value: Any) -> Tuple[Dict[str, float], Dict[str, str]]:
        if isinstance(value, LuaTableValue):
            return _parse_tag_table(value)
        if isinstance(value, LuaRaw):
            key = value.text.strip()
            if key:
                tbl = _find_named_table(content, key)
                if isinstance(tbl, LuaTableValue):
                    return _parse_tag_table(tbl)
            return {}, {}
        if isinstance(value, str):
            val = parse_lua_expr(value)
            if isinstance(val, LuaTableValue):
                return _parse_tag_table(val)
            if isinstance(val, LuaRaw):
                key = val.text.strip()
                if key:
                    tbl = _find_named_table(content, key)
                    if isinstance(tbl, LuaTableValue):
                        return _parse_tag_table(tbl)
        return {}, {}

    for _, entry in (fish_tbl.map or {}).items():
        if not isinstance(entry, LuaTableValue):
            continue
        prefab = lua_to_python(entry.map.get("prefab"))
        if not isinstance(prefab, str):
            continue
        prefab = prefab.strip()
        if not prefab:
            continue
        cooker_val = entry.map.get("cooker_ingredient_value")
        if cooker_val is None:
            continue
        tags, tag_expr = _resolve_tags(cooker_val)
        if not tags and not tag_expr:
            continue

        ing_id = _clean_ingredient_id(f"{prefab}_inv")
        if not ing_id:
            continue

        row: Dict[str, Any] = {"id": ing_id}
        if tags:
            row["tags"] = tags
        if tag_expr:
            row["tags_expr"] = tag_expr
        if source:
            row["sources"] = [source]
        if len(row) > 1:
            out[ing_id] = row

    return out


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

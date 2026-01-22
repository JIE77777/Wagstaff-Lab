#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i18n index helpers (core).

Used by devtools to build data/index/wagstaff_i18n_v1.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, List, Tuple

from core.lua import find_matching, lua_to_python, parse_lua_table


_NAMES_PREFIX = "STRINGS.NAMES."
_CHAR_PREFIX = "STRINGS.CHARACTERS."
_DESC_MARK = ".DESCRIBE."
_QUOTES_MARK = ".QUOTES."
_ANNOUNCE_MARK = ".ANNOUNCE_"
_ID_RE = re.compile(r"^[a-z0-9_]+$")


def _po_unquote(s: str) -> str:
    """Unquote a PO string literal line segment."""

    s = (s or "").strip()
    if not (s.startswith('"') and s.endswith('"')):
        return ""
    inner = s[1:-1]
    out: List[str] = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == "\\" and i + 1 < len(inner):
            nxt = inner[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt == "r":
                out.append("\r")
            elif nxt == '"':
                out.append('"')
            elif nxt == "\\":
                out.append("\\")
            else:
                out.append(nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_po(text: str) -> Dict[str, str]:
    """Parse a PO file and return mapping: msgctxt -> msgstr.

    Notes
    - Only keep entries with non-empty msgctxt and msgstr.
    - For plural forms, take msgstr[0] only.
    """

    lines = (text or "").splitlines()
    cur: Dict[str, Any] = {}
    last_key: Optional[str] = None
    out: Dict[str, str] = {}

    def commit() -> None:
        nonlocal cur, last_key
        ctx = cur.get("msgctxt")
        msgstr = cur.get("msgstr")
        if isinstance(ctx, str) and ctx and isinstance(msgstr, str) and msgstr:
            out[ctx] = msgstr
        cur = {}
        last_key = None

    for raw in lines:
        line = raw.rstrip("\n")
        s = line.strip()
        if not s:
            commit()
            continue
        if s.startswith("#"):
            continue

        if s.startswith("msgctxt "):
            cur["msgctxt"] = _po_unquote(s[len("msgctxt ") :].strip())
            last_key = "msgctxt"
            continue

        if s.startswith("msgid "):
            cur["msgid"] = _po_unquote(s[len("msgid ") :].strip())
            last_key = "msgid"
            continue

        if s.startswith("msgid_plural "):
            cur["msgid_plural"] = _po_unquote(s[len("msgid_plural ") :].strip())
            last_key = "msgid_plural"
            continue

        if s.startswith("msgstr["):
            rb = s.find("]")
            idx_s = s[len("msgstr[") : rb].strip() if rb != -1 else ""
            try:
                idx = int(idx_s)
            except Exception:
                idx = -1
            if idx == 0:
                rest = s[rb + 1 :].strip() if rb != -1 else ""
                cur["msgstr"] = _po_unquote(rest)
                last_key = "msgstr"
            else:
                last_key = None
            continue

        if s.startswith("msgstr "):
            cur["msgstr"] = _po_unquote(s[len("msgstr ") :].strip())
            last_key = "msgstr"
            continue

        if s.startswith('"') and last_key:
            cur[last_key] = str(cur.get(last_key) or "") + _po_unquote(s)
            continue

    commit()
    return out


def _normalize_key(key: str) -> str:
    return str(key or "").strip().lower()


def _is_simple_id(s: str) -> bool:
    return bool(s) and bool(_ID_RE.match(s))


def build_item_map_from_raw(raw: Dict[str, str], *, item_ids: Optional[Iterable[str]] = None) -> Dict[str, str]:
    if not raw:
        return {}
    if item_ids is None:
        return dict(raw)
    out: Dict[str, str] = {}
    for iid in item_ids:
        if not iid:
            continue
        k1 = _normalize_key(iid)
        if not k1:
            continue
        k2 = k1.replace("_", "")
        v = raw.get(k1) or raw.get(k2)
        if v:
            out[str(iid)] = v
    return out


def extract_name_table(po_text: str) -> Dict[str, str]:
    """Return normalized key -> localized name."""

    ctx_map = parse_po(po_text or "")
    names: Dict[str, str] = {}
    for ctx, val in ctx_map.items():
        if not isinstance(ctx, str) or not ctx.startswith(_NAMES_PREFIX):
            continue
        key = _normalize_key(ctx[len(_NAMES_PREFIX) :])
        if not key:
            continue
        v = str(val or "").strip()
        if not v:
            continue
        names[key] = v
        if "_" in key:
            names.setdefault(key.replace("_", ""), v)
    return names


def extract_strings_names(lua_text: str) -> Dict[str, str]:
    inner = _extract_strings_subtable(lua_text, "NAMES")
    if not inner:
        return {}
    mp = _parse_lua_table_map(inner)
    out: Dict[str, str] = {}
    for k, v in mp.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        kid = _normalize_key(k)
        if not _is_simple_id(kid):
            continue
        out[kid] = v
    return out


def _char_preference_order(chars: Iterable[str]) -> List[str]:
    order = []
    for key in ("GENERIC", "WILSON"):
        if key in chars:
            order.append(key)
    for key in sorted(chars):
        if key not in order:
            order.append(key)
    return order


def _extract_char_map(po_text: str, marker: str) -> Dict[str, Dict[str, str]]:
    ctx_map = parse_po(po_text or "")
    char_map: Dict[str, Dict[str, str]] = {}
    for ctx, val in ctx_map.items():
        if not isinstance(ctx, str) or not ctx.startswith(_CHAR_PREFIX):
            continue
        rest = ctx[len(_CHAR_PREFIX) :]
        if marker not in rest:
            continue
        char, _, tail = rest.partition(marker)
        if not char or not tail:
            continue
        key = _normalize_key(tail)
        if not key:
            continue
        base = key.split(".", 1)[0]
        if not base:
            continue
        v = str(val or "").strip()
        if not v:
            continue
        char_map.setdefault(char, {})[base] = v
    return char_map


def _merge_char_maps(*maps: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for mp in maps:
        for char, entries in mp.items():
            if not isinstance(entries, dict):
                continue
            out.setdefault(char, {}).update(entries)
    return out


def _select_char_values(char_map: Dict[str, Dict[str, str]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    if not char_map:
        return {}, {}
    out: Dict[str, str] = {}
    meta: Dict[str, str] = {}
    order = _char_preference_order(char_map.keys())
    keys = set()
    for mp in char_map.values():
        keys.update(mp.keys())
    for key in keys:
        for char in order:
            val = char_map.get(char, {}).get(key)
            if val:
                out[key] = val
                meta[key] = _normalize_key(char)
                break
    return out, meta


def _extract_strings_subtable(lua_text: str, key: str) -> Optional[str]:
    src = lua_text or ""
    if not src:
        return None
    m = re.search(r"\bSTRINGS\s*=\s*\{", src)
    if not m:
        return None
    strings_open = src.find("{", m.end() - 1)
    if strings_open < 0:
        return None
    strings_close = find_matching(src, strings_open, "{", "}")
    if strings_close is None:
        return None
    block = src[strings_open : strings_close + 1]
    m2 = re.search(rf"(?<![A-Za-z0-9_]){re.escape(key)}\s*=\s*\{{", block)
    if not m2:
        return None
    inner_open = strings_open + m2.end() - 1
    inner_close = find_matching(src, inner_open, "{", "}")
    if inner_close is None:
        return None
    return src[inner_open + 1 : inner_close]


def _parse_lua_table_map(inner: str) -> Dict[str, Any]:
    try:
        tbl = parse_lua_table(inner)
    except Exception:
        return {}
    py = lua_to_python(tbl)
    return py if isinstance(py, dict) else {}


def _extract_strings_characters(lua_text: str) -> Dict[str, Dict[str, Any]]:
    inner = _extract_strings_subtable(lua_text, "CHARACTERS")
    if not inner:
        return {}
    mp = _parse_lua_table_map(inner)
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in mp.items():
        if not isinstance(k, str) or not isinstance(v, dict):
            continue
        out[k] = v
    return out


def _extract_strings_char_map(lua_text: str, key: str) -> Dict[str, Dict[str, str]]:
    chars = _extract_strings_characters(lua_text)
    out: Dict[str, Dict[str, str]] = {}
    for char, data in chars.items():
        sub = data.get(key)
        if not isinstance(sub, dict):
            continue
        for k, v in sub.items():
            if not isinstance(k, str) or not isinstance(v, str):
                continue
            kid = _normalize_key(k)
            if not _is_simple_id(kid):
                continue
            out.setdefault(char, {})[kid] = v
    return out


def _extract_strings_announce_map(lua_text: str) -> Dict[str, Dict[str, str]]:
    chars = _extract_strings_characters(lua_text)
    out: Dict[str, Dict[str, str]] = {}
    for char, data in chars.items():
        if not isinstance(data, dict):
            continue
        for k, v in data.items():
            if not isinstance(k, str) or not isinstance(v, str):
                continue
            if not k.startswith("ANNOUNCE_"):
                continue
            kid = _normalize_key(k[len("ANNOUNCE_") :])
            if not _is_simple_id(kid):
                continue
            out.setdefault(char, {})[kid] = v
    return out


def extract_desc_table(po_text: str) -> Dict[str, str]:
    """Return normalized key -> localized description (CHARACTER.DESCRIBE)."""

    char_map = _extract_char_map(po_text, _DESC_MARK)
    return _select_char_values(char_map)[0]


def extract_quote_table(po_text: str) -> Dict[str, str]:
    """Return normalized key -> localized quote (CHARACTER.QUOTES/ANNOUNCE_*)."""

    return extract_quote_table_with_meta(po_text)[0]


def extract_quote_table_with_meta(po_text: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    quotes_map = _extract_char_map(po_text, _QUOTES_MARK)
    announce_map = _extract_char_map(po_text, _ANNOUNCE_MARK)
    merged = _merge_char_maps(quotes_map, announce_map)
    return _select_char_values(merged)


def build_item_name_map(po_text: str, *, item_ids: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """Build item_id -> localized name mapping from PO content."""

    raw = extract_name_table(po_text or "")
    return build_item_map_from_raw(raw, item_ids=item_ids)


def build_item_desc_map(po_text: str, *, item_ids: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """Build item_id -> localized description mapping from PO content."""

    raw = extract_desc_table(po_text or "")
    return build_item_map_from_raw(raw, item_ids=item_ids)


def build_item_quote_map(po_text: str, *, item_ids: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """Build item_id -> localized quote mapping from PO content."""

    raw = extract_quote_table(po_text or "")
    return build_item_map_from_raw(raw, item_ids=item_ids)


def build_item_quote_map_with_meta(
    po_text: str, *, item_ids: Optional[Iterable[str]] = None
) -> Tuple[Dict[str, str], Dict[str, str]]:
    raw, meta = extract_quote_table_with_meta(po_text or "")
    if item_ids is None:
        return dict(raw), dict(meta)
    out = build_item_map_from_raw(raw, item_ids=item_ids)
    out_meta: Dict[str, str] = {}
    for iid in out.keys():
        key = _normalize_key(iid)
        alt = key.replace("_", "")
        out_meta[iid] = meta.get(key) or meta.get(alt) or ""
    return out, out_meta


def extract_strings_desc_table(lua_text: str) -> Dict[str, str]:
    char_map = _extract_strings_char_map(lua_text, "DESCRIBE")
    return _select_char_values(char_map)[0]


def extract_strings_quote_table_with_meta(lua_text: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    quotes_map = _extract_strings_char_map(lua_text, "QUOTES")
    announce_map = _extract_strings_announce_map(lua_text)
    merged = _merge_char_maps(quotes_map, announce_map)
    return _select_char_values(merged)


def build_item_quote_map_with_meta_from_lua(
    lua_text: str, *, item_ids: Optional[Iterable[str]] = None
) -> Tuple[Dict[str, str], Dict[str, str]]:
    raw, meta = extract_strings_quote_table_with_meta(lua_text or "")
    if item_ids is None:
        return dict(raw), dict(meta)
    out = build_item_map_from_raw(raw, item_ids=item_ids)
    out_meta: Dict[str, str] = {}
    for iid in out.keys():
        key = _normalize_key(iid)
        alt = key.replace("_", "")
        out_meta[iid] = meta.get(key) or meta.get(alt) or ""
    return out, out_meta


def load_ui_strings(path: Path) -> Dict[str, Dict[str, str]]:
    """Load UI strings JSON: {lang: {key: text}}."""

    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(doc, dict):
        return {}

    out: Dict[str, Dict[str, str]] = {}
    for lang, mp in doc.items():
        if not isinstance(mp, dict):
            continue
        l = _normalize_key(lang)
        if not l:
            continue
        out[l] = {str(k): str(v) for k, v in mp.items() if k and v}
    return out


def load_tag_strings(path: Path) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    """Load tag strings JSON: {lang: {tag: {text, source}}}."""

    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}, {}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}, {}
    if not isinstance(doc, dict):
        return {}, {}

    tags: Dict[str, Dict[str, str]] = {}
    meta: Dict[str, Dict[str, str]] = {}
    for lang, mp in doc.items():
        if not isinstance(mp, dict):
            continue
        l = _normalize_key(lang)
        if not l:
            continue
        tags.setdefault(l, {})
        meta.setdefault(l, {})
        for key, val in mp.items():
            k = _normalize_key(key)
            if not k:
                continue
            text = ""
            source = "manual"
            if isinstance(val, dict):
                text = str(val.get("text") or val.get("label") or "").strip()
                source = str(val.get("source") or val.get("src") or "manual").strip().lower() or "manual"
            else:
                text = str(val or "").strip()
            if not text:
                continue
            tags[l][k] = text
            meta[l][k] = source
    return tags, meta

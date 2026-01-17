#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i18n index helpers (core).

Used by devtools to build data/index/wagstaff_i18n_v1.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, List, Tuple


_NAMES_PREFIX = "STRINGS.NAMES."


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


def build_item_name_map(po_text: str, *, item_ids: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """Build item_id -> localized name mapping from PO content."""

    raw = extract_name_table(po_text or "")
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

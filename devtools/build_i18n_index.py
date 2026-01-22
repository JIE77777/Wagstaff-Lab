#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Wagstaff i18n index (names + UI strings)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.indexers.i18n_index import (  # noqa: E402
    build_item_desc_map,
    build_item_map_from_raw,
    build_item_name_map,
    build_item_quote_map_with_meta,
    extract_strings_names,
    load_tag_strings,
    load_ui_strings,
)
from core.lua import find_matching, lua_to_python, parse_lua_table  # noqa: E402
from core.schemas.meta import build_meta  # noqa: E402
from devtools.build_cache import file_sig, load_cache, save_cache  # noqa: E402

try:
    from core.config import wagstaff_config  # type: ignore
except Exception:
    wagstaff_config = None  # type: ignore


_PO_CANDIDATES = {
    "zh": [
        "scripts/languages/chinese_s.po",
        "languages/chinese_s.po",
    ]
}

_STRINGS_CANDIDATES = [
    "scripts/strings.lua",
    "strings.lua",
]


def _resolve_dst_root(arg: Optional[str]) -> Optional[str]:
    if arg:
        return str(arg)
    if wagstaff_config is None:
        return None
    try:
        return wagstaff_config.get("PATHS", "DST_ROOT")
    except Exception:
        return None


def _read_po_from_zip(zip_path: Path, candidates: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not zip_path.exists() or not zip_path.is_file():
        return (None, None, None)
    try:
        with zipfile.ZipFile(str(zip_path), "r") as z:
            for inner in candidates:
                try:
                    data = z.read(inner)
                except Exception:
                    continue
                try:
                    txt = data.decode("utf-8", errors="replace")
                except Exception:
                    txt = data.decode("utf-8", errors="replace")
                sig = _zip_sig(zip_path, inner)
                return (inner, txt, sig)
    except Exception:
        return (None, None, None)
    return (None, None, None)


def _read_text_from_zip(zip_path: Path, candidates: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not zip_path.exists() or not zip_path.is_file():
        return (None, None, None)
    try:
        with zipfile.ZipFile(str(zip_path), "r") as z:
            for inner in candidates:
                try:
                    data = z.read(inner)
                except Exception:
                    continue
                try:
                    txt = data.decode("utf-8", errors="replace")
                except Exception:
                    txt = data.decode("utf-8", errors="replace")
                sig = _zip_sig(zip_path, inner)
                return (inner, txt, sig)
    except Exception:
        return (None, None, None)
    return (None, None, None)


def _read_po_from_dir(dir_path: Path, candidates: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not dir_path.exists() or not dir_path.is_dir():
        return (None, None, None)
    for inner in candidates:
        rel = inner.replace("scripts/", "", 1) if inner.startswith("scripts/") else inner
        p = dir_path / rel
        if p.exists() and p.is_file():
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                txt = p.read_text(encoding="utf-8", errors="replace")
            sig = _file_sig(p)
            return (inner, txt, sig)
    return (None, None, None)


def _read_text_from_dir(dir_path: Path, candidates: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not dir_path.exists() or not dir_path.is_dir():
        return (None, None, None)
    for inner in candidates:
        rel = inner.replace("scripts/", "", 1) if inner.startswith("scripts/") else inner
        p = dir_path / rel
        if p.exists() and p.is_file():
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                txt = p.read_text(encoding="utf-8", errors="replace")
            sig = _file_sig(p)
            return (inner, txt, sig)
    return (None, None, None)


def _file_sig(path: Path) -> str:
    try:
        st = path.stat()
        return f"file:{path}:{float(st.st_mtime)}:{int(st.st_size)}"
    except Exception:
        return f"file:{path}"


def _zip_sig(zip_path: Path, inner: str) -> str:
    zip_mtime = 0.0
    zip_size = 0
    try:
        st = zip_path.stat()
        zip_mtime = float(st.st_mtime)
        zip_size = int(st.st_size)
    except Exception:
        pass

    crc = -1
    fsz = -1
    dt = None
    try:
        with zipfile.ZipFile(str(zip_path), "r") as z:
            info = z.getinfo(inner)
            crc = int(getattr(info, "CRC", -1))
            fsz = int(getattr(info, "file_size", -1))
            dt = getattr(info, "date_time", None)
    except Exception:
        pass

    return f"zip:{zip_path}:{zip_mtime}:{zip_size}:{inner}:{crc}:{fsz}:{dt}"


def _resolve_po(
    *,
    lang: str,
    po_path: Optional[str],
    scripts_zip: Optional[str],
    scripts_dir: Optional[str],
    dst_root: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Return (po_source, inner, text, sig)."""

    candidates = _PO_CANDIDATES.get(lang, [])
    if not candidates:
        return (None, None, None, None)

    if po_path:
        p = Path(po_path).expanduser()
        if p.exists() and p.is_file():
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                txt = p.read_text(encoding="utf-8", errors="replace")
            return (str(p), None, txt, _file_sig(p))

    if scripts_zip:
        zp = Path(scripts_zip).expanduser()
        inner, txt, sig = _read_po_from_zip(zp, candidates)
        if txt:
            return (str(zp), inner, txt, sig)

    if scripts_dir:
        dp = Path(scripts_dir).expanduser()
        inner, txt, sig = _read_po_from_dir(dp, candidates)
        if txt:
            return (str(dp), inner, txt, sig)

    if dst_root:
        root = Path(dst_root).expanduser()
        zp = root / "data" / "databundles" / "scripts.zip"
        inner, txt, sig = _read_po_from_zip(zp, candidates)
        if txt:
            return (str(zp), inner, txt, sig)
        dp = root / "data" / "scripts"
        inner, txt, sig = _read_po_from_dir(dp, candidates)
        if txt:
            return (str(dp), inner, txt, sig)

    return (None, None, None, None)


def _resolve_strings_lua(
    *,
    strings_path: Optional[str],
    scripts_zip: Optional[str],
    scripts_dir: Optional[str],
    dst_root: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Return (strings_source, inner, text, sig)."""

    candidates = list(_STRINGS_CANDIDATES)
    if strings_path:
        p = Path(strings_path).expanduser()
        if p.exists() and p.is_file():
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                txt = p.read_text(encoding="utf-8", errors="replace")
            return (str(p), None, txt, _file_sig(p))

    if scripts_zip:
        zp = Path(scripts_zip).expanduser()
        inner, txt, sig = _read_text_from_zip(zp, candidates)
        if txt:
            return (str(zp), inner, txt, sig)

    if scripts_dir:
        dp = Path(scripts_dir).expanduser()
        inner, txt, sig = _read_text_from_dir(dp, candidates)
        if txt:
            return (str(dp), inner, txt, sig)

    if dst_root:
        root = Path(dst_root).expanduser()
        zp = root / "data" / "databundles" / "scripts.zip"
        inner, txt, sig = _read_text_from_zip(zp, candidates)
        if txt:
            return (str(zp), inner, txt, sig)
        dp = root / "data" / "scripts"
        inner, txt, sig = _read_text_from_dir(dp, candidates)
        if txt:
            return (str(dp), inner, txt, sig)

    return (None, None, None, None)


def _load_script_text(
    *,
    script_path: str,
    scripts_zip: Optional[str],
    scripts_dir: Optional[str],
    dst_root: Optional[str],
) -> Optional[str]:
    candidates = [script_path]
    if script_path.startswith("scripts/"):
        candidates.append(script_path[len("scripts/") :])
    if scripts_zip:
        zp = Path(scripts_zip).expanduser()
        inner, txt, _ = _read_text_from_zip(zp, candidates)
        if txt:
            return txt
    if scripts_dir:
        dp = Path(scripts_dir).expanduser()
        inner, txt, _ = _read_text_from_dir(dp, candidates)
        if txt:
            return txt
    if dst_root:
        root = Path(dst_root).expanduser()
        zp = root / "data" / "databundles" / "scripts.zip"
        inner, txt, _ = _read_text_from_zip(zp, candidates)
        if txt:
            return txt
        dp = root / "data" / "scripts"
        inner, txt, _ = _read_text_from_dir(dp, candidates)
        if txt:
            return txt
    return None


def _select_char_values(char_map: Dict[str, Dict[str, str]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    if not char_map:
        return {}, {}
    order = []
    for key in ("GENERIC", "WILSON"):
        if key in char_map:
            order.append(key)
    for key in sorted(char_map.keys()):
        if key not in order:
            order.append(key)
    keys = set()
    for mp in char_map.values():
        keys.update(mp.keys())
    out: Dict[str, str] = {}
    meta: Dict[str, str] = {}
    for key in keys:
        for char in order:
            val = char_map.get(char, {}).get(key)
            if val:
                out[key] = val
                meta[key] = str(char).lower()
                break
    return out, meta


def _extract_character_requires(strings_text: str) -> Dict[str, str]:
    src = strings_text or ""
    m = re.search(r"STRINGS\.CHARACTERS\s*=\s*\{", src)
    if not m:
        return {}
    open_idx = src.find("{", m.end() - 1)
    if open_idx < 0:
        return {}
    close_idx = find_matching(src, open_idx, "{", "}")
    if close_idx is None:
        return {}
    block = src[open_idx + 1 : close_idx]
    out: Dict[str, str] = {}
    pat = re.compile(r"([A-Z0-9_]+)\s*=\s*require\s*\(?\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
    for m in pat.finditer(block):
        char = m.group(1)
        mod = m.group(2)
        if char and mod:
            out[char] = mod
    return out


def _parse_return_table(text: str) -> Dict[str, Any]:
    src = text or ""
    m = re.search(r"\breturn\s*\{", src)
    if not m:
        return {}
    open_idx = src.find("{", m.end() - 1)
    if open_idx < 0:
        return {}
    close_idx = find_matching(src, open_idx, "{", "}")
    if close_idx is None:
        return {}
    inner = src[open_idx + 1 : close_idx]
    try:
        tbl = parse_lua_table(inner)
    except Exception:
        return {}
    py = lua_to_python(tbl)
    return py if isinstance(py, dict) else {}


def _extract_speech_char_maps(
    *,
    strings_text: str,
    scripts_zip: Optional[str],
    scripts_dir: Optional[str],
    dst_root: Optional[str],
) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    def _pick_string(val: Any) -> Optional[str]:
        if isinstance(val, str):
            return val
        if isinstance(val, list):
            for item in val:
                s = _pick_string(item)
                if s:
                    return s
            return None
        if isinstance(val, dict):
            for key in ("GENERIC", "DEFAULT", "LEVEL1", "LEVEL2", "LEVEL3"):
                if key in val:
                    s = _pick_string(val.get(key))
                    if s:
                        return s
            arr = val.get("__array__") if isinstance(val.get("__array__"), list) else None
            if arr:
                for item in arr:
                    s = _pick_string(item)
                    if s:
                        return s
            for item in val.values():
                s = _pick_string(item)
                if s:
                    return s
        return None

    char_requires = _extract_character_requires(strings_text)
    desc_map: Dict[str, Dict[str, str]] = {}
    quote_map: Dict[str, Dict[str, str]] = {}
    for char, mod in char_requires.items():
        script_path = mod.replace(".", "/")
        if not script_path.endswith(".lua"):
            script_path = f"{script_path}.lua"
        if not script_path.startswith("scripts/"):
            script_path = f"scripts/{script_path}"
        txt = _load_script_text(
            script_path=script_path,
            scripts_zip=scripts_zip,
            scripts_dir=scripts_dir,
            dst_root=dst_root,
        )
        if not txt:
            continue
        data = _parse_return_table(txt)
        if not data:
            continue
        describe = data.get("DESCRIBE")
        if isinstance(describe, dict):
            for k, v in describe.items():
                if not isinstance(k, str):
                    continue
                sval = _pick_string(v)
                if not sval:
                    continue
                kid = str(k).strip().lower()
                if not kid or not re.match(r"^[a-z0-9_]+$", kid):
                    continue
                desc_map.setdefault(char, {})[kid] = sval
        quotes = data.get("QUOTES")
        if isinstance(quotes, dict):
            for k, v in quotes.items():
                if not isinstance(k, str):
                    continue
                sval = _pick_string(v)
                if not sval:
                    continue
                kid = str(k).strip().lower()
                if not kid or not re.match(r"^[a-z0-9_]+$", kid):
                    continue
                quote_map.setdefault(char, {})[kid] = sval
        for k, v in data.items():
            if not isinstance(k, str):
                continue
            if not k.startswith("ANNOUNCE_"):
                continue
            sval = _pick_string(v)
            if not sval:
                continue
            kid = str(k[len("ANNOUNCE_") :]).strip().lower()
            if not kid or not re.match(r"^[a-z0-9_]+$", kid):
                continue
            quote_map.setdefault(char, {})[kid] = sval
    return desc_map, quote_map


def _load_item_ids(
    catalog_path: Path,
    icon_index_path: Optional[Path],
    farming_defs_path: Optional[Path],
) -> List[str]:
    ids = set()
    if catalog_path.exists() and catalog_path.is_file():
        try:
            doc = json.loads(catalog_path.read_text(encoding="utf-8"))
        except Exception:
            doc = {}
        if isinstance(doc, dict):
            items = doc.get("items")
            if isinstance(items, dict):
                ids.update([str(k) for k in items.keys() if k])
            assets = doc.get("assets")
            if isinstance(assets, dict):
                ids.update([str(k) for k in assets.keys() if k])
    if icon_index_path and icon_index_path.exists() and icon_index_path.is_file():
        try:
            doc2 = json.loads(icon_index_path.read_text(encoding="utf-8"))
        except Exception:
            doc2 = {}
        if isinstance(doc2, dict):
            ids.update([str(k) for k in doc2.keys() if k])
    if farming_defs_path and farming_defs_path.exists() and farming_defs_path.is_file():
        try:
            doc3 = json.loads(farming_defs_path.read_text(encoding="utf-8"))
        except Exception:
            doc3 = {}
        if isinstance(doc3, dict):
            plants = doc3.get("plants")
            if isinstance(plants, dict):
                for row in plants.values():
                    if not isinstance(row, dict):
                        continue
                    seed = row.get("seed")
                    if isinstance(seed, str) and seed:
                        ids.add(seed)
            weeds = doc3.get("weeds")
            if isinstance(weeds, dict):
                for row in weeds.values():
                    if not isinstance(row, dict):
                        continue
                    seed = row.get("seed")
                    if isinstance(seed, str) and seed:
                        ids.add(seed)
    return sorted(ids)


def main() -> int:
    p = argparse.ArgumentParser(description="Build Wagstaff i18n index (names + UI strings).")
    p.add_argument("--out", default="data/index/wagstaff_i18n_v1.json", help="Output JSON path")
    p.add_argument("--catalog", default="data/index/wagstaff_catalog_v2.json", help="Catalog JSON path")
    p.add_argument("--icon-index", default="data/index/wagstaff_icon_index_v1.json", help="Icon index JSON path")
    p.add_argument("--farming-defs", default="data/index/wagstaff_farming_defs_v1.json", help="Farming defs JSON path")
    p.add_argument("--ui", default="conf/i18n_ui.json", help="UI strings JSON path")
    p.add_argument("--tags", default="conf/i18n_tags.json", help="Tag strings JSON path")
    p.add_argument("--lang", default="zh", help="Language code (default: zh)")
    p.add_argument("--po", default=None, help="Override PO file path")
    p.add_argument("--scripts-zip", default=None, help="Override scripts.zip path")
    p.add_argument("--scripts-dir", default=None, help="Override scripts folder path")
    p.add_argument("--dst-root", default=None, help="Override DST root (default from config)")
    p.add_argument("--strings-lua", default=None, help="Override strings.lua path")
    p.add_argument("--force", action="store_true", help="Force rebuild even if cache matches")

    args = p.parse_args()

    dst_root = _resolve_dst_root(args.dst_root)

    lang = str(args.lang or "").strip().lower()
    if not lang:
        raise SystemExit("--lang is required")

    catalog_path = (PROJECT_ROOT / args.catalog).resolve()
    icon_index_path = (PROJECT_ROOT / args.icon_index).resolve() if args.icon_index else None
    farming_defs_path = (PROJECT_ROOT / args.farming_defs).resolve() if args.farming_defs else None
    ui_path = (PROJECT_ROOT / args.ui).resolve()
    tags_path = (PROJECT_ROOT / args.tags).resolve() if args.tags else None
    out_path = (PROJECT_ROOT / args.out).resolve()

    po_src, po_inner, po_text, po_sig = _resolve_po(
        lang=lang,
        po_path=args.po,
        scripts_zip=args.scripts_zip,
        scripts_dir=args.scripts_dir,
        dst_root=dst_root,
    )

    if not po_text:
        raise SystemExit("PO file not found. Pass --po or --dst-root (or --scripts-zip/dir).")

    strings_src, strings_inner, strings_text, strings_sig = _resolve_strings_lua(
        strings_path=args.strings_lua,
        scripts_zip=args.scripts_zip,
        scripts_dir=args.scripts_dir,
        dst_root=dst_root,
    )

    inputs_sig = {
        "lang": lang,
        "dst_root": str(Path(dst_root).expanduser().resolve()) if dst_root else None,
        "catalog": file_sig(catalog_path),
        "icon_index": file_sig(icon_index_path) if icon_index_path else None,
        "farming_defs": file_sig(farming_defs_path) if farming_defs_path else None,
        "ui": file_sig(ui_path),
        "tags": file_sig(tags_path) if tags_path else None,
        "po": {
            "source": str(po_src) if po_src else None,
            "inner": po_inner,
            "sig": po_sig,
        },
        "strings": {
            "source": str(strings_src) if strings_src else None,
            "inner": strings_inner,
            "sig": strings_sig,
        },
        "out": str(out_path),
    }
    outputs_sig = {
        "out": file_sig(out_path),
    }
    cache = load_cache()
    cache_key = f"i18n_index:{lang}"
    if not args.force:
        entry = cache.get(cache_key) or {}
        if entry.get("signature") == inputs_sig and entry.get("outputs") == outputs_sig:
            print("✅ i18n index up-to-date; skip rebuild")
            return 0

    item_ids = _load_item_ids(catalog_path, icon_index_path, farming_defs_path)
    names = build_item_name_map(po_text, item_ids=item_ids)
    descriptions = build_item_desc_map(po_text, item_ids=item_ids)
    quotes, quotes_meta = build_item_quote_map_with_meta(po_text, item_ids=item_ids)

    en_names = {}
    en_descriptions = {}
    en_quotes = {}
    en_quotes_meta = {}
    if strings_text:
        raw_names = extract_strings_names(strings_text)
        en_names = build_item_map_from_raw(raw_names, item_ids=item_ids)
        desc_char_map, quote_char_map = _extract_speech_char_maps(
            strings_text=strings_text,
            scripts_zip=args.scripts_zip,
            scripts_dir=args.scripts_dir,
            dst_root=dst_root,
        )
        raw_desc, _ = _select_char_values(desc_char_map)
        raw_quotes, raw_quotes_meta = _select_char_values(quote_char_map)
        en_descriptions = build_item_map_from_raw(raw_desc, item_ids=item_ids)
        en_quotes = build_item_map_from_raw(raw_quotes, item_ids=item_ids)
        for iid in en_quotes.keys():
            key = str(iid).strip().lower()
            alt = key.replace("_", "")
            en_quotes_meta[iid] = raw_quotes_meta.get(key) or raw_quotes_meta.get(alt) or ""

    ui_strings = load_ui_strings(ui_path)

    tag_strings, tag_meta = load_tag_strings(tags_path) if tags_path else ({}, {})

    langs = set()
    langs.update([lang])
    langs.update(ui_strings.keys())
    langs.update(tag_strings.keys())
    if en_names or en_descriptions or en_quotes:
        langs.add("en")
    langs = sorted({str(x) for x in langs if x})

    meta = build_meta(
        schema=1,
        tool="build_i18n_index",
        sources={
            "po_source": str(po_src or ""),
            "po_inner": str(po_inner or ""),
            "po_sig": str(po_sig or ""),
            "strings_source": str(strings_src or ""),
            "strings_inner": str(strings_inner or ""),
            "strings_sig": str(strings_sig or ""),
            "catalog": str(catalog_path),
            "icon_index": str(icon_index_path) if icon_index_path else "",
            "farming_defs": str(farming_defs_path) if farming_defs_path else "",
            "ui_source": str(ui_path),
            "tags_source": str(tags_path) if tags_path else "",
        },
        extra={
            "lang": lang,
            "po_source": str(po_src or ""),
            "po_inner": str(po_inner or ""),
            "po_sig": str(po_sig or ""),
            "strings_source": str(strings_src or ""),
            "strings_inner": str(strings_inner or ""),
            "strings_sig": str(strings_sig or ""),
            "catalog": str(catalog_path),
            "icon_index": str(icon_index_path) if icon_index_path else "",
            "farming_defs": str(farming_defs_path) if farming_defs_path else "",
            "ui_source": str(ui_path),
            "tags_source": str(tags_path) if tags_path else "",
            "counts": {
                "names": {lang: len(names), "en": len(en_names)},
                "descriptions": {lang: len(descriptions), "en": len(en_descriptions)},
                "quotes": {lang: len(quotes), "en": len(en_quotes)},
                "ui": {k: len(v) for k, v in (ui_strings or {}).items()},
                "tags": {k: len(v) for k, v in (tag_strings or {}).items()},
            },
        },
    )

    doc = {
        "schema_version": 1,
        "meta": meta,
        "langs": langs,
        "names": {lang: names} if names else {},
        "descriptions": {lang: descriptions} if descriptions else {},
        "quotes": {lang: quotes} if quotes else {},
        "quotes_meta": {lang: quotes_meta} if quotes_meta else {},
        "ui": ui_strings or {},
        "tags": tag_strings or {},
        "tags_meta": tag_meta or {},
    }

    if en_names:
        doc.setdefault("names", {})["en"] = en_names
    if en_descriptions:
        doc.setdefault("descriptions", {})["en"] = en_descriptions
    if en_quotes:
        doc.setdefault("quotes", {})["en"] = en_quotes
    if en_quotes_meta:
        doc.setdefault("quotes_meta", {})["en"] = en_quotes_meta

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs_sig = {
        "out": file_sig(out_path),
    }
    cache[cache_key] = {"signature": inputs_sig, "outputs": outputs_sig}
    save_cache(cache)

    print(f"✅ i18n index written: {out_path}")
    print(
        f"   lang: {lang}, names: {len(names)}, desc: {len(descriptions)}, "
        f"quotes: {len(quotes)}, en_names: {len(en_names)}, en_desc: {len(en_descriptions)}, "
        f"en_quotes: {len(en_quotes)}, ui: {sum(len(v) for v in (ui_strings or {}).values())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Wagstaff i18n index (names + UI strings)."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.indexers.i18n_index import build_item_name_map, load_ui_strings, load_tag_strings  # noqa: E402
from core.schemas.meta import build_meta  # noqa: E402

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


def _load_item_ids(catalog_path: Path, icon_index_path: Optional[Path]) -> List[str]:
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
    return sorted(ids)


def main() -> int:
    p = argparse.ArgumentParser(description="Build Wagstaff i18n index (names + UI strings).")
    p.add_argument("--out", default="data/index/wagstaff_i18n_v1.json", help="Output JSON path")
    p.add_argument("--catalog", default="data/index/wagstaff_catalog_v2.json", help="Catalog JSON path")
    p.add_argument("--icon-index", default="data/index/wagstaff_icon_index_v1.json", help="Icon index JSON path")
    p.add_argument("--ui", default="conf/i18n_ui.json", help="UI strings JSON path")
    p.add_argument("--tags", default="conf/i18n_tags.json", help="Tag strings JSON path")
    p.add_argument("--lang", default="zh", help="Language code (default: zh)")
    p.add_argument("--po", default=None, help="Override PO file path")
    p.add_argument("--scripts-zip", default=None, help="Override scripts.zip path")
    p.add_argument("--scripts-dir", default=None, help="Override scripts folder path")
    p.add_argument("--dst-root", default=None, help="Override DST root (default from config)")

    args = p.parse_args()

    dst_root = _resolve_dst_root(args.dst_root)

    lang = str(args.lang or "").strip().lower()
    if not lang:
        raise SystemExit("--lang is required")

    catalog_path = (PROJECT_ROOT / args.catalog).resolve()
    icon_index_path = (PROJECT_ROOT / args.icon_index).resolve() if args.icon_index else None

    po_src, po_inner, po_text, po_sig = _resolve_po(
        lang=lang,
        po_path=args.po,
        scripts_zip=args.scripts_zip,
        scripts_dir=args.scripts_dir,
        dst_root=dst_root,
    )

    if not po_text:
        raise SystemExit("PO file not found. Pass --po or --dst-root (or --scripts-zip/dir).")

    item_ids = _load_item_ids(catalog_path, icon_index_path)
    names = build_item_name_map(po_text, item_ids=item_ids)

    ui_path = (PROJECT_ROOT / args.ui).resolve()
    ui_strings = load_ui_strings(ui_path)

    tags_path = (PROJECT_ROOT / args.tags).resolve() if args.tags else None
    tag_strings, tag_meta = load_tag_strings(tags_path) if tags_path else ({}, {})

    langs = sorted(set([lang] + list(ui_strings.keys()) + list(tag_strings.keys())))

    meta = build_meta(
        schema=1,
        tool="build_i18n_index",
        sources={
            "po_source": str(po_src or ""),
            "po_inner": str(po_inner or ""),
            "po_sig": str(po_sig or ""),
            "catalog": str(catalog_path),
            "icon_index": str(icon_index_path) if icon_index_path else "",
            "ui_source": str(ui_path),
            "tags_source": str(tags_path) if tags_path else "",
        },
        extra={
            "lang": lang,
            "po_source": str(po_src or ""),
            "po_inner": str(po_inner or ""),
            "po_sig": str(po_sig or ""),
            "catalog": str(catalog_path),
            "icon_index": str(icon_index_path) if icon_index_path else "",
            "ui_source": str(ui_path),
            "tags_source": str(tags_path) if tags_path else "",
            "counts": {
                "names": len(names),
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
        "ui": ui_strings or {},
        "tags": tag_strings or {},
        "tags_meta": tag_meta or {},
    }

    out_path = (PROJECT_ROOT / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ i18n index written: {out_path}")
    print(f"   lang: {lang}, names: {len(names)}, ui: {sum(len(v) for v in (ui_strings or {}).values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

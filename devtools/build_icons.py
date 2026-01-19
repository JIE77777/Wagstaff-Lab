#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_icons.py (v1.3) - reduce missing by supporting:
- multi-bundle zip search (databundles/*.zip)
- AND loose files under DST_ROOT/data (not in databundles)

This directly fixes the common case:
  images/inventoryimages.xml references "inventoryimages.tex"
but inventoryimages.tex exists as a loose file under data/tex/ (not inside images.zip).

Also removes dependency on klei_atlas_tex.extract_atlas_element for export.
We crop directly from atlas u/v coordinates -> PIL crop, ensuring export works reliably.

Usage (your environment):
  python3 devtools/build_icons.py --dst-root ~/dontstarvetogether_dedicated_server --all-elements --overwrite --verbose

Notes:
- Output PNGs to data/static/icons/<name>.png
- Index JSON to data/index/wagstaff_icon_index_v1.json

"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

import xml.etree.ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core.klei_atlas_tex import decode_ktex_to_image, fix_ktex_orientation  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "ERROR: cannot import core.klei_atlas_tex.decode_ktex_to_image. Ensure project root is on PYTHONPATH.\n"
        f"{e}"
    )
from devtools.build_cache import dir_sig, file_sig, load_cache, paths_sig, save_cache  # noqa: E402

# ---------------------------- utils ----------------------------

def _norm(p: str) -> str:
    return (p or "").replace("\\", "/").lstrip("/")


def _expand(p: Optional[str]) -> Optional[str]:
    if not p:
        return None
    return os.path.expanduser(p)


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _default_catalog_path() -> Path:
    return PROJECT_ROOT / "data" / "index" / "wagstaff_catalog_v2.json"


def _default_out_dir() -> Path:
    return PROJECT_ROOT / "data" / "static" / "icons"


def _default_index_path() -> Path:
    return PROJECT_ROOT / "data" / "index" / "wagstaff_icon_index_v1.json"


def _databundles_dir(dst_root: str) -> Path:
    return Path(dst_root) / "data" / "databundles"


def _data_dir(dst_root: str) -> Path:
    return Path(dst_root) / "data"


def _auto_bundles(dst_root: str) -> List[Path]:
    d = _databundles_dir(dst_root)
    if not d.is_dir():
        return []
    zips = sorted([p for p in d.glob("*.zip") if p.is_file() and p.name.lower() != "scripts.zip"])
    zips.sort(key=lambda p: (0 if p.name.lower() == "images.zip" else 1, p.name.lower()))
    return zips


def _read_ini_dst_root(ini_path: str) -> Optional[str]:
    try:
        import configparser
        cp = configparser.ConfigParser()
        cp.read(ini_path, encoding="utf-8")
        if cp.has_option("PATHS", "DST_ROOT"):
            return os.path.expanduser(cp.get("PATHS", "DST_ROOT"))
    except Exception:
        return None
    return None


def _strip_tex_suffix(name: str) -> str:
    return name[:-4] if (name or "").lower().endswith(".tex") else name


def _is_inventory_atlas(path: str, extra_globs: Sequence[str]) -> bool:
    p = _norm(path)
    bn = os.path.basename(p).lower()
    if bn.startswith("inventoryimages") and bn.endswith(".xml"):
        return True
    for g in extra_globs:
        if fnmatch(p, g):
            return True
    return False


def _is_images_xml(path: str) -> bool:
    p = _norm(path)
    return p.startswith("images/") and p.endswith(".xml")


def _to_pil(img_obj):
    """
    Convert decoder output to PIL.Image.Image.
    """
    if img_obj is None:
        raise ValueError("image is None")

    # PIL Image
    if hasattr(img_obj, "mode") and hasattr(img_obj, "size") and hasattr(img_obj, "crop"):
        return img_obj

    # numpy array
    try:
        import numpy as np  # type: ignore
        if isinstance(img_obj, np.ndarray):
            from PIL import Image  # type: ignore
            return Image.fromarray(img_obj)
    except Exception:
        pass

    raise TypeError(f"Unsupported decoded image type: {type(img_obj)}")


def _unpremultiply_rgba(pil_img):
    """
    Unpremultiply alpha using numpy (fast).
    """
    try:
        import numpy as np  # type: ignore
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")
        arr = np.asarray(pil_img).astype("float32")
        a = arr[..., 3:4] / 255.0
        # avoid division by zero
        mask = a > 0
        arr[..., :3] = np.where(mask, arr[..., :3] / a, arr[..., :3])
        arr[..., :3] = np.clip(arr[..., :3], 0, 255)
        out = arr.astype("uint8")
        from PIL import Image  # type: ignore
        return Image.fromarray(out, mode="RGBA")
    except Exception:
        # fallback: return original
        return pil_img

# ---------------------------- FS layer ----------------------------

@dataclass
class Bundle:
    path: Path
    zf: zipfile.ZipFile
    paths: Set[str]
    paths_lc: Dict[str, str]
    basename_map_lc: Dict[str, List[str]]


class BundleFS:
    def __init__(self, bundle_paths: Sequence[Path]):
        self.bundles: List[Bundle] = []
        self._path_owner_lc: Dict[str, Tuple[int, str]] = {}
        self._basename_owner_lc: Dict[str, List[Tuple[int, str]]] = defaultdict(list)

        for idx, p in enumerate(bundle_paths):
            zf = zipfile.ZipFile(p, "r")
            names = [n for n in zf.namelist() if not n.endswith("/")]
            paths = set(_norm(n) for n in names)
            paths_lc = {n.lower(): n for n in paths}
            bmap_lc: Dict[str, List[str]] = defaultdict(list)
            for n in paths:
                bn = os.path.basename(n)
                if bn:
                    bmap_lc[bn.lower()].append(n)

            self.bundles.append(Bundle(path=p, zf=zf, paths=paths, paths_lc=paths_lc, basename_map_lc=bmap_lc))

            for n_lc, real in paths_lc.items():
                if n_lc not in self._path_owner_lc:
                    self._path_owner_lc[n_lc] = (idx, real)

            for bn_lc, plist in bmap_lc.items():
                for full in plist:
                    self._basename_owner_lc[bn_lc].append((idx, full))

    def close(self) -> None:
        for b in self.bundles:
            try:
                b.zf.close()
            except Exception:
                pass

    def resolve(self, path: str, *, base_dir: Optional[str] = None) -> Optional[Tuple[int, str]]:
        raw = (path or "").strip()
        if not raw:
            return None
        raw = raw.replace("\\", "/")
        candidates: List[str] = []

        candidates.append(_norm(raw))
        if raw.startswith("./"):
            candidates.append(_norm(raw[2:]))

        if raw.startswith("images/"):
            candidates.append(_norm(raw))
            candidates.append(_norm(raw.replace("images/", "", 1)))
        else:
            candidates.append(_norm("images/" + raw))

        if base_dir:
            bd = _norm(base_dir).rstrip("/")
            candidates.append(_norm(f"{bd}/{raw}"))
            if raw.startswith("images/"):
                candidates.append(_norm(f"{bd}/{raw.replace('images/', '', 1)}"))

        for c in candidates:
            cl = c.lower()
            if cl in self._path_owner_lc:
                return self._path_owner_lc[cl]

        bn = os.path.basename(_norm(raw)).lower()
        if not bn:
            return None
        opts = self._basename_owner_lc.get(bn) or []
        if not opts:
            return None

        bd = _norm(base_dir or "").rstrip("/")
        def score(opt: Tuple[int, str]) -> Tuple[int, int, int]:
            idx, full = opt
            same_dir = 0
            if bd and full.startswith(bd + "/"):
                same_dir = -1
            return (same_dir, idx, len(full))

        best = sorted(opts, key=score)[0]
        return best

    def read(self, resolved: Tuple[int, str]) -> Optional[bytes]:
        idx, real = resolved
        try:
            return self.bundles[idx].zf.read(real)
        except Exception:
            return None

    def scan_paths(self) -> Iterable[str]:
        seen = set()
        for b in self.bundles:
            for p in b.paths:
                if p in seen:
                    continue
                seen.add(p)
                yield p


class LocalFS:
    """
    Read loose files under data_dir (DST_ROOT/data).
    We index basenames under:
      - data/images
      - data/tex
    because atlas xml often references textures by basename only (e.g. inventoryimages.tex).
    """
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._basename_index_lc: Dict[str, List[Path]] = defaultdict(list)
        self._build_index()

    def _build_index(self) -> None:
        for sub in ("images", "tex"):
            root = self.data_dir / sub
            if not root.is_dir():
                continue
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    self._basename_index_lc[fn.lower()].append(Path(dirpath) / fn)

    def resolve(self, path: str, *, base_dir: Optional[str] = None) -> Optional[Path]:
        raw = (path or "").strip()
        if not raw:
            return None
        raw = raw.replace("\\", "/")

        candidates: List[Path] = []

        # 1) treat as relative to data_dir
        candidates.append(self.data_dir / _norm(raw))

        # 2) relative to base_dir
        if base_dir:
            bd = _norm(base_dir).rstrip("/")
            candidates.append(self.data_dir / bd / raw)
            if raw.startswith("images/"):
                candidates.append(self.data_dir / bd / raw.replace("images/", "", 1))

        # 3) common: xml references "foo.tex" but file is under data/tex/foo.tex
        bn = os.path.basename(_norm(raw))
        if bn.lower().endswith(".tex"):
            candidates.append(self.data_dir / "tex" / bn)
            candidates.append(self.data_dir / "images" / bn)

        for c in candidates:
            if c.exists() and c.is_file():
                return c

        # basename index fallback (only within data/images and data/tex)
        if bn:
            opts = self._basename_index_lc.get(bn.lower()) or []
            if len(opts) == 1:
                return opts[0]
            elif len(opts) > 1:
                # prefer a file under /tex if texture
                if bn.lower().endswith(".tex"):
                    for p in opts:
                        if "/tex/" in str(p).replace("\\", "/"):
                            return p
                return opts[0]
        return None

    def read(self, resolved: Path) -> Optional[bytes]:
        try:
            return resolved.read_bytes()
        except Exception:
            return None

    def scan_inventory_atlas_xmls(self, extra_globs: Sequence[str], *, include_all_images: bool = False) -> List[str]:
        """
        Return paths relative to data_dir, like 'images/inventoryimages.xml'
        """
        out: List[str] = []
        img_dir = self.data_dir / "images"
        if not img_dir.is_dir():
            return out
        if include_all_images:
            files = img_dir.rglob("*.xml")
        else:
            files = img_dir.glob("inventoryimages*.xml")
        for p in files:
            rel = p.relative_to(self.data_dir).as_posix()
            if include_all_images or _is_inventory_atlas(rel, extra_globs):
                out.append(rel)
        out.sort()
        return out


class ResourceFS:
    """
    Combined resolver:
      zip bundles first, then local files (if provided).
    """
    def __init__(self, zip_fs: BundleFS, local_fs: Optional[LocalFS]):
        self.zip_fs = zip_fs
        self.local_fs = local_fs

    def resolve(self, path: str, *, base_dir: Optional[str] = None) -> Optional[Tuple[str, Union[Tuple[int, str], Path]]]:
        z = self.zip_fs.resolve(path, base_dir=base_dir)
        if z is not None:
            return ("zip", z)
        if self.local_fs is not None:
            f = self.local_fs.resolve(path, base_dir=base_dir)
            if f is not None:
                return ("file", f)
        return None

    def read(self, resolved: Tuple[str, Union[Tuple[int, str], Path]]) -> Optional[bytes]:
        kind, obj = resolved
        if kind == "zip":
            return self.zip_fs.read(obj)  # type: ignore[arg-type]
        else:
            if self.local_fs is None:
                return None
            return self.local_fs.read(obj)  # type: ignore[arg-type]


# ---------------------------- atlas parsing ----------------------------

def _parse_atlas_xml(xml_bytes: bytes) -> Tuple[Optional[str], Dict[str, Dict[str, float]]]:
    try:
        root = ET.fromstring(xml_bytes.decode("utf-8", errors="replace"))
    except Exception:
        return None, {}

    tex = None
    tex_node = root.find(".//Texture")
    if tex_node is not None:
        tex = tex_node.attrib.get("filename") or tex_node.attrib.get("name")

    elems: Dict[str, Dict[str, float]] = {}
    for el in root.findall(".//Element"):
        name = el.attrib.get("name")
        if not name:
            continue
        try:
            u1 = float(el.attrib.get("u1", "0"))
            u2 = float(el.attrib.get("u2", "0"))
            v1 = float(el.attrib.get("v1", "0"))
            v2 = float(el.attrib.get("v2", "0"))
        except Exception:
            continue
        elems[name] = {"u1": u1, "u2": u2, "v1": v1, "v2": v2}
    return tex, elems


def _crop_uv(tex_img_pil, uv: Dict[str, float], *, invert_v: bool = True):
    """
    Crop using atlas UVs.

    Some Klei atlases use bottom-origin v; others (incl. DST inventory) behave top-origin.
    We only invert v when explicitly requested.
    """
    W, H = tex_img_pil.size
    u1 = float(uv.get("u1", 0.0))
    u2 = float(uv.get("u2", 0.0))
    v1 = float(uv.get("v1", 0.0))
    v2 = float(uv.get("v2", 0.0))

    x1 = int(round(min(u1, u2) * W))
    x2 = int(round(max(u1, u2) * W))

    if invert_v:
        # bottom-origin -> top-origin
        y1 = int(round((1.0 - max(v1, v2)) * H))
        y2 = int(round((1.0 - min(v1, v2)) * H))
    else:
        y1 = int(round(min(v1, v2) * H))
        y2 = int(round(max(v1, v2) * H))

    # clamp
    x1 = max(0, min(W, x1))
    x2 = max(0, min(W, x2))
    y1 = max(0, min(H, y1))
    y2 = max(0, min(H, y2))

    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"invalid crop rect ({x1},{y1},{x2},{y2}) for size {W}x{H}")

    return tex_img_pil.crop((x1, y1, x2, y2))


# ---------------------------- wanted ids ----------------------------

def _collect_catalog_ids(catalog_path: Path) -> Set[str]:
    ids: Set[str] = set()
    try:
        doc = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception:
        return ids

    items = doc.get("items")
    if isinstance(items, dict) and items:
        for k, v in items.items():
            if isinstance(k, str):
                ids.add(k)
            if isinstance(v, dict):
                vid = v.get("id")
                if isinstance(vid, str):
                    ids.add(vid)
        assets = doc.get("assets") or {}
        if isinstance(assets, dict):
            for k in assets.keys():
                if isinstance(k, str):
                    ids.add(k)

        out = {x for x in ids if re.match(r"^[a-z0-9_]+$", x or "")}
        return out

    craft = (doc.get("craft") or {}).get("recipes") or {}
    for rname, r in craft.items():
        if isinstance(rname, str):
            ids.add(rname)
        prod = (r or {}).get("product")
        if isinstance(prod, str):
            ids.add(prod)
        for ing in (r or {}).get("ingredients") or []:
            it = (ing or {}).get("item")
            if isinstance(it, str):
                ids.add(it)

    cooking = doc.get("cooking") or {}
    for cname, c in cooking.items():
        if isinstance(cname, str):
            ids.add(cname)
        for row in (c or {}).get("card_ingredients") or []:
            if isinstance(row, list) and row and isinstance(row[0], str):
                ids.add(row[0])

    assets = doc.get("assets") or {}
    if isinstance(assets, dict):
        for k in assets.keys():
            if isinstance(k, str):
                ids.add(k)

    out = {x for x in ids if re.match(r"^[a-z0-9_]+$", x or "")}
    return out


# ---------------------------- main ----------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Export DST inventory atlas icons to PNG (zip + loose files).")
    ap.add_argument("--catalog", default=str(_default_catalog_path()))
    ap.add_argument("--out", default=str(_default_out_dir()))
    ap.add_argument("--index", default=str(_default_index_path()))

    ap.add_argument("--dst-root", default=None, help="Dedicated server root (contains data/ and data/databundles/).")
    ap.add_argument("--ini", default=None, help="INI path; reads [PATHS] DST_ROOT.")
    ap.add_argument("--bundles", default=None, help="Comma-separated zips to search (override auto).")
    ap.add_argument("--images-zip", default=None, help="Legacy: single bundle path (still supported).")

    ap.add_argument("--atlas-glob", action="append", default=[], help="Extra glob patterns to include atlas xmls.")
    ap.add_argument("--ids", default=None, help="Comma-separated ids to export (catalog-id mode override).")
    ap.add_argument("--all-elements", action="store_true", help="Export all elements from inventoryimages*.xml atlases.")
    ap.add_argument("--count-missing-tex", action="store_true", help="Strict: count elements whose texture cannot be resolved.")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--force", action="store_true", help="Force rebuild even if cache matches")
    ap.add_argument("--verbose", action="store_true")

    ap.add_argument("--unpremultiply", action="store_true", default=True, help="Unpremultiply alpha (default: true).")
    ap.add_argument("--no-unpremultiply", action="store_true", help="Disable unpremultiply alpha.")
    ap.add_argument("--invert-v", action="store_true", default=False, help="Invert v coords (default: false for DST inventory atlases).")
    ap.add_argument("--no-invert-v", action="store_true", help="Disable v inversion.")

    args = ap.parse_args()

    catalog_path = Path(_expand(args.catalog) or args.catalog)
    out_dir = Path(_expand(args.out) or args.out)
    index_path = Path(_expand(args.index) or args.index)
    _ensure_dir(out_dir)
    _ensure_dir(index_path.parent)

    dst_root = _expand(args.dst_root)
    if not dst_root and args.ini:
        dst_root = _read_ini_dst_root(_expand(args.ini) or args.ini)

    # bundles
    bundle_paths: List[Path] = []
    if args.bundles:
        for s in args.bundles.split(","):
            s = s.strip()
            if s:
                bundle_paths.append(Path(_expand(s) or s))
    elif args.images_zip:
        bundle_paths = [Path(_expand(args.images_zip) or args.images_zip)]
    elif dst_root:
        bundle_paths = _auto_bundles(dst_root)
    else:
        # infer from catalog.meta.scripts_zip sibling
        try:
            doc = json.loads(catalog_path.read_text(encoding="utf-8"))
            scripts_zip = (doc.get("meta") or {}).get("scripts_zip")
            if scripts_zip:
                cand = Path(str(scripts_zip)).resolve().parent / "images.zip"
                if cand.exists():
                    bundle_paths = [cand]
        except Exception:
            pass

    bundle_paths = [p for p in bundle_paths if p.exists()]
    if not bundle_paths:
        raise SystemExit("No bundles found. Use --dst-root or --bundles or --images-zip.")

    zip_fs = BundleFS(bundle_paths)

    # local FS (loose files)
    local_fs: Optional[LocalFS] = None
    data_dir = None
    if dst_root:
        data_dir = _data_dir(dst_root)
        if data_dir.is_dir():
            local_fs = LocalFS(data_dir)

    fs = ResourceFS(zip_fs, local_fs)

    export_all = bool(args.all_elements)
    scan_all_images = (not export_all) and (len(args.atlas_glob) == 0)

    inputs_sig = {
        "catalog": file_sig(catalog_path),
        "bundles": paths_sig(bundle_paths),
        "args": {
            "all_elements": export_all,
            "atlas_glob": sorted(args.atlas_glob or []),
            "ids": str(args.ids or ""),
            "invert_v": bool(args.invert_v) and not bool(args.no_invert_v),
            "unpremultiply": bool(args.unpremultiply) and not bool(args.no_unpremultiply),
            "overwrite": bool(args.overwrite),
            "scan_all_images": scan_all_images,
        },
    }
    if data_dir:
        inputs_sig["data_images_xml"] = dir_sig(Path(data_dir) / "images", suffixes=[".xml"], glob="**/*.xml", label="images_xml")
        inputs_sig["data_tex"] = dir_sig(Path(data_dir) / "tex", suffixes=[".tex"], glob="**/*.tex", label="tex")

    outputs_sig = {
        "index": file_sig(index_path),
        "out_dir": dir_sig(out_dir, suffixes=[".png"], glob="**/*.png", label="icons"),
    }
    cache = load_cache()
    cache_key = "icons"
    if not args.force:
        entry = cache.get(cache_key) or {}
        if entry.get("signature") == inputs_sig and entry.get("outputs") == outputs_sig:
            print("✅ build_icons up-to-date; skip rebuild")
            return

    # atlas xmls: from zip + (optional) local
    atlas_xmls: List[Tuple[str, str]] = []  # (source, rel_path) where rel_path uses "images/xxx.xml"
    seen: Set[str] = set()

    if local_fs is not None:
        for rel in local_fs.scan_inventory_atlas_xmls(args.atlas_glob, include_all_images=scan_all_images):
            if rel in seen:
                continue
            seen.add(rel)
            atlas_xmls.append(("file", rel))

    for p in zip_fs.scan_paths():
        if not p.lower().endswith(".xml"):
            continue
        if not _is_inventory_atlas(p, args.atlas_glob):
            if not (scan_all_images and _is_images_xml(p)):
                continue
        if p in seen:
            continue
        seen.add(p)
        atlas_xmls.append(("zip", p))

    atlas_xmls.sort(key=lambda x: (0 if x[0] == "file" else 1, len(x[1]), x[1]))

    if args.verbose:
        print(f"[i] bundles: {[p.name for p in bundle_paths]}")
        if data_dir:
            print(f"[i] data_dir: {data_dir}")
        print(f"[i] atlas xml count: {len(atlas_xmls)}")

    if args.ids:
        catalog_ids = {x.strip() for x in args.ids.split(",") if x.strip()}
    else:
        catalog_ids = _collect_catalog_ids(catalog_path)

    wanted_match: Set[str] = set()
    if not export_all:
        wanted_match = set(catalog_ids) | {f"{x}.tex" for x in catalog_ids}

    # flags
    unpremultiply = bool(args.unpremultiply) and not bool(args.no_unpremultiply)
    invert_v = bool(args.invert_v) and not bool(args.no_invert_v)

    # index + stats
    exported = 0
    skipped = 0
    desired_out_names: Set[str] = set()
    exported_out_names: Set[str] = set()
    unresolved_atlases: List[Dict[str, str]] = []

    missing_reason: Dict[str, str] = {}
    missing_by_atlas: Dict[str, int] = defaultdict(int)
    icon_index: Dict[str, Dict[str, str]] = {}

    tex_cache: Dict[str, object] = {}  # resolved key -> PIL image

    for src, xml_path in atlas_xmls:
        # read xml
        if src == "zip":
            xml_res = ("zip", zip_fs.resolve(xml_path, base_dir=None) or (0, xml_path))
            # zip_fs.resolve should succeed for xml itself; but be defensive:
            if isinstance(xml_res[1], tuple):
                xml_bytes = zip_fs.read(xml_res[1])  # type: ignore[arg-type]
            else:
                xml_bytes = None
        else:
            if local_fs is None:
                continue
            resolved = local_fs.resolve(xml_path)
            xml_bytes = local_fs.read(resolved) if resolved else None

        if not xml_bytes:
            continue

        tex_ref, elems_uv = _parse_atlas_xml(xml_bytes)
        if not tex_ref or not elems_uv:
            continue

        if not export_all and not any(el_name in wanted_match for el_name in elems_uv.keys()):
            continue

        xml_dir = os.path.dirname(_norm(xml_path))

        # resolve texture (zip then file)
        tex_res = fs.resolve(tex_ref, base_dir=xml_dir)
        if tex_res is None:
            unresolved_atlases.append({"atlas": xml_path, "texture": tex_ref})
            if args.verbose:
                print(f"[warn] missing texture for atlas {xml_path}: {tex_ref}")
            if args.count_missing_tex:
                for el_name in elems_uv.keys():
                    out_name = _strip_tex_suffix(el_name)
                    if export_all or el_name in wanted_match:
                        desired_out_names.add(out_name)
                        missing_reason.setdefault(out_name, "missing_tex")
                        missing_by_atlas[xml_path] += 1
            continue

        # decode texture to PIL
        kind, obj = tex_res
        tex_key = f"{kind}:{obj}"  # stable string key

        tex_img_pil = tex_cache.get(tex_key)
        if tex_img_pil is None:
            tex_bytes = fs.read(tex_res)
            if not tex_bytes:
                unresolved_atlases.append({"atlas": xml_path, "texture": str(obj), "reason": "missing_tex_bytes"})
                continue
            try:
                tex_img = decode_ktex_to_image(tex_bytes)
                tex_img_pil = _to_pil(tex_img)
                tex_cache[tex_key] = tex_img_pil
            except Exception as e:
                unresolved_atlases.append({"atlas": xml_path, "texture": str(obj), "reason": f"decode_fail:{type(e).__name__}"})
                continue

        # export
        for el_name, uv in elems_uv.items():
            if not export_all and el_name not in wanted_match:
                continue

            out_name = _strip_tex_suffix(el_name)
            desired_out_names.add(out_name)

            out_path = out_dir / f"{out_name}.png"
            if out_path.exists() and not args.overwrite:
                skipped += 1
                exported_out_names.add(out_name)
                icon_index.setdefault(out_name, {"png": str(out_path.relative_to(PROJECT_ROOT)).replace("\\", "/")})
                continue

            try:
                crop = _crop_uv(tex_img_pil, uv, invert_v=invert_v)
                crop = fix_ktex_orientation(crop)
                if unpremultiply:
                    crop = _unpremultiply_rgba(crop)
                crop.save(out_path, format="PNG")
            except Exception as e:
                missing_reason[out_name] = f"export_fail:{type(e).__name__}"
                missing_by_atlas[xml_path] += 1
                continue

            exported += 1
            exported_out_names.add(out_name)
            icon_index[out_name] = {"png": str(out_path.relative_to(PROJECT_ROOT)).replace("\\", "/")}

    # missing
    if export_all:
        missing = sorted([n for n in desired_out_names if not (out_dir / f"{n}.png").exists()])
    else:
        missing = sorted([n for n in catalog_ids if not (out_dir / f"{n}.png").exists()])

    # missing_by_reason counts
    reason_counts: Dict[str, int] = defaultdict(int)
    for n in missing:
        reason_counts[missing_reason.get(n, "not_exported")] += 1

    doc = {
        "schema_version": 1,
        "generated_from": {
            "catalog": str(catalog_path),
            "bundles": [str(p) for p in bundle_paths],
            "data_dir": str(data_dir) if data_dir else None,
            "mode": "all-elements" if export_all else "catalog-ids",
        },
        "counts": {
            "exported": int(exported),
            "skipped_existing": int(skipped),
            "desired": int(len(desired_out_names)) if export_all else int(len(catalog_ids)),
            "missing": int(len(missing)),
        },
        "unresolved_atlases": unresolved_atlases,
        "missing_by_reason": dict(sorted(reason_counts.items(), key=lambda x: (-x[1], x[0]))),
        "missing_by_atlas_top": sorted(
            [{"atlas": k, "missing": v} for k, v in missing_by_atlas.items()],
            key=lambda x: x["missing"],
            reverse=True
        )[:20],
        "icons": icon_index,
    }
    index_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    outputs_sig = {
        "index": file_sig(index_path),
        "out_dir": dir_sig(out_dir, suffixes=[".png"], glob="**/*.png", label="icons"),
    }
    cache[cache_key] = {"signature": inputs_sig, "outputs": outputs_sig}
    save_cache(cache)

    print("✅ build_icons finished")
    print(f"  catalog: {catalog_path}")
    print(f"  bundles: {', '.join([p.name for p in bundle_paths])}")
    if data_dir:
        print(f"  data_dir: {data_dir}")
    print(f"  out: {out_dir}")
    print(f"  index: {index_path}")
    print(f"  exported: {exported}, skipped(existing): {skipped}, missing: {len(missing)}")
    if unresolved_atlases:
        print(f"  unresolved_atlases: {len(unresolved_atlases)} (see index json)")
    if args.verbose and missing:
        print("[i] missing samples:", ", ".join(missing[:40]))


if __name__ == "__main__":
    main()

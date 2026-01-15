# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from klei_atlas_tex import (
    Atlas,
    decode_ktex_to_image,
    parse_atlas_xml,
    pick_first_existing,
    resolve_tex_path_from_atlas,
    extract_atlas_element,
)


_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")


@dataclass(frozen=True)
class IconConfig:
    """Runtime icon configuration.

    mode:
      - off      : UI shows no icons (always fallback to text)
      - static   : serve only prebuilt PNG icons from static_dir
      - dynamic  : generate icons from (atlas xml + tex) on demand (cached as png)
      - auto     : static first, if missing then dynamic

    static_dir:
      - directory that contains <id>.png files (served via /static/icons/...)

    game_data_dir:
      - directory root where atlas/xml/tex can be resolved, e.g. DST data folder that contains "images/..."
        Example: /path/to/Don't Starve Together/data

    unpremultiply:
      - whether to unpremultiply alpha for cropped icons (usually True for DST inventory icons)
    """

    mode: str = "auto"
    static_dir: Path = Path("data/static/icons")
    game_data_dir: Optional[Path] = None
    unpremultiply: bool = True

    def normalized_mode(self) -> str:
        m = (self.mode or "").strip().lower()
        if m in ("off", "0", "false", "none"):
            return "off"
        if m in ("static", "png"):
            return "static"
        if m in ("dynamic", "tex"):
            return "dynamic"
        return "auto"

    def to_public_dict(self) -> Dict[str, Any]:
        # URL bases are fixed by server routing.
        return {
            "mode": self.normalized_mode(),
            "static_base": "/static/icons",
            "api_base": "/api/v1/icon",
        }


class IconService:
    """Icon build/serve helper.

    The service is safe for concurrent requests.
    """

    def __init__(self, cfg: IconConfig):
        self.cfg = cfg
        self._lock = threading.RLock()
        self._atlas_cache: Dict[Path, Tuple[float, Atlas]] = {}
        self._tex_cache: Dict[Path, Tuple[float, Any]] = {}  # PIL.Image.Image, but keep Any to avoid import
        self._tex_cache_order: list[Path] = []
        self._tex_cache_max = 4

        # Ensure static directory exists (even in off mode).
        try:
            self.cfg.static_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    @staticmethod
    def is_safe_id(item_id: str) -> bool:
        return bool(item_id) and bool(_SAFE_ID_RE.match(item_id))

    def icon_path(self, item_id: str) -> Path:
        return self.cfg.static_dir / f"{item_id}.png"

    def resolve_existing(self, item_id: str) -> Optional[Path]:
        if not self.is_safe_id(item_id):
            return None
        p = self.icon_path(item_id)
        return p if p.exists() else None

    def ensure_icon(self, item_id: str, asset: Optional[Dict[str, Any]] = None) -> Optional[Path]:
        """Ensure icon PNG exists and return its path.

        Behavior depends on cfg.mode.
        """

        if not self.is_safe_id(item_id):
            return None

        mode = self.cfg.normalized_mode()
        if mode == "off":
            return None

        # 1) static
        p = self.icon_path(item_id)
        if p.exists():
            return p

        alias = self._resolve_existing_alias(item_id, asset=asset)
        if alias is not None:
            return alias

        if mode == "static":
            return None

        # 2) dynamic
        if mode in ("dynamic", "auto"):
            gd = self.cfg.game_data_dir
            if gd is None:
                return None
            if not asset:
                return None
            ok = self._build_from_asset(item_id, asset, out_path=p)
            return p if ok and p.exists() else None

        return None

    # ----------------- internals -----------------
    def _resolve_existing_alias(self, item_id: str, asset: Optional[Dict[str, Any]] = None) -> Optional[Path]:
        for cand in self._alias_candidates(item_id, asset=asset):
            if not self.is_safe_id(cand):
                continue
            p = self.icon_path(cand)
            if p.exists():
                return p
        return None

    def _alias_candidates(self, item_id: str, asset: Optional[Dict[str, Any]] = None) -> list[str]:
        if not item_id:
            return []

        out: list[str] = []

        def _push(v: Optional[str]) -> None:
            if not v:
                return
            if v == item_id:
                return
            if v not in out:
                out.append(v)

        # explicit known aliases
        explicit = {
            "waterpump": ["waterpump_item"],
            "hermit_bundle_shells": ["hermit_bundle"],
            "dragonboat_kit": ["dragonboat_pack"],
        }
        for v in explicit.get(item_id, []):
            _push(v)

        if item_id.startswith("wintercooking_"):
            _push(item_id[len("wintercooking_") :])

        if item_id.endswith("_builder"):
            base = item_id[: -len("_builder")]
            _push(f"{base}_sketch")
            _push(base)

        if item_id.endswith("_kit"):
            base = item_id[: -len("_kit")]
            _push(f"{base}_item")
            _push(f"{base}_pack")
            _push(base)

        if item_id.endswith("_item"):
            _push(item_id[: -len("_item")])

        if item_id.endswith("_blueprint"):
            _push(item_id[: -len("_blueprint")])

        if item_id.endswith("_recipe"):
            _push(item_id[: -len("_recipe")])

        if asset:
            image_rel = str(asset.get("image") or "").strip()
            if image_rel:
                base = Path(image_rel).name
                if base.lower().endswith(".tex"):
                    base = base[: -len(".tex")]
                _push(base)

        return out

    def _read_atlas(self, xml_path: Path) -> Optional[Atlas]:
        try:
            mtime = xml_path.stat().st_mtime
        except Exception:
            return None

        with self._lock:
            cached = self._atlas_cache.get(xml_path)
            if cached and cached[0] == mtime:
                return cached[1]

        try:
            xml_text = xml_path.read_text(encoding="utf-8", errors="ignore")
            atlas = parse_atlas_xml(xml_text)
        except Exception:
            return None

        with self._lock:
            self._atlas_cache[xml_path] = (mtime, atlas)
        return atlas

    def _read_tex_image(self, tex_path: Path):
        """Decode and cache tex image (mipmap0)."""
        try:
            mtime = tex_path.stat().st_mtime
        except Exception:
            return None

        with self._lock:
            cached = self._tex_cache.get(tex_path)
            if cached and cached[0] == mtime:
                return cached[1]

        try:
            tex_bytes = tex_path.read_bytes()
            img = decode_ktex_to_image(tex_bytes)
        except Exception:
            return None

        with self._lock:
            self._tex_cache[tex_path] = (mtime, img)
            # LRU bookkeeping
            if tex_path in self._tex_cache_order:
                self._tex_cache_order.remove(tex_path)
            self._tex_cache_order.append(tex_path)
            while len(self._tex_cache_order) > self._tex_cache_max:
                old = self._tex_cache_order.pop(0)
                self._tex_cache.pop(old, None)

        return img

    def _build_from_asset(self, item_id: str, asset: Dict[str, Any], *, out_path: Path) -> bool:
        """Build <item_id>.png from one catalog assets entry."""

        gd = self.cfg.game_data_dir
        if gd is None:
            return False

        atlas_rel = str(asset.get("atlas") or "").strip()
        if not atlas_rel:
            return False

        # normalize leading slashes
        while atlas_rel.startswith("/"):
            atlas_rel = atlas_rel[1:]

        xml_path = (gd / atlas_rel).resolve()
        if not xml_path.exists():
            return False

        atlas = self._read_atlas(xml_path)
        if not atlas:
            return False

        tex_path = resolve_tex_path_from_atlas(xml_path, atlas)
        if not tex_path or not tex_path.exists():
            # fallback: swap suffix
            alt = xml_path.with_suffix(".tex")
            if alt.exists():
                tex_path = alt
            else:
                return False

        tex_img = self._read_tex_image(tex_path)
        if tex_img is None:
            return False

        # Pick element name candidates
        image_rel = str(asset.get("image") or "").strip()
        candidates = []
        if image_rel:
            base = Path(image_rel).name
            if base and not base.lower().endswith(".tex"):
                base = base + ".tex"
            if base:
                candidates.append(base)
        candidates.append(f"{item_id}.tex")
        if "_" in item_id:
            candidates.append(f"{item_id.replace('_','')}.tex")

        element_name = pick_first_existing(candidates, atlas.elements)
        if not element_name:
            return False

        invert_v = self._invert_v_for_atlas(atlas_rel)
        cropped = extract_atlas_element(
            atlas,
            tex_img,
            element_name,
            unpremultiply=bool(self.cfg.unpremultiply),
            invert_v=invert_v,
        )
        if cropped is None:
            return False

        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            cropped.save(out_path, format="PNG")
            return True
        except Exception:
            return False

    @staticmethod
    def _invert_v_for_atlas(atlas_rel: str) -> bool:
        p = str(atlas_rel or "").lower()
        if "inventoryimages" in p:
            return False
        return True

# -*- coding: utf-8 -*-
"""klei_atlas_tex.py

A small, self-contained parser for:
- Klei atlas XML files (e.g. images/inventoryimages.xml)
- Klei TEX (KTEX) texture files (e.g. images/inventoryimages.tex)

Primary goal
- Extract a named atlas element (e.g. "armor_wood.tex") into a normal PNG.

Important correctness notes
- Klei atlas v coordinates count *up from the bottom* (v=0 is bottom).
  This is a common gotcha in DST modding discussions.
- TEX files are commonly stored with premultiplied alpha. For inventory/craft
  icons, unpremultiplying the cropped icon usually produces the expected
  appearance.

This module intentionally has no Wagstaff-specific imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import struct
import xml.etree.ElementTree as ET

from PIL import Image


# -----------------------------
# Atlas XML
# -----------------------------


@dataclass(frozen=True)
class AtlasElement:
    name: str
    u1: float
    u2: float
    v1: float
    v2: float


@dataclass(frozen=True)
class Atlas:
    """Parsed atlas XML."""

    texture_filename: str
    elements: Dict[str, AtlasElement]

    def get(self, name: str) -> Optional[AtlasElement]:
        if not name:
            return None
        return self.elements.get(name)


def _xml_find_first(root: ET.Element, tag_local_name: str) -> Optional[ET.Element]:
    # Namespace-tolerant lookup
    return root.find(f".//{{*}}{tag_local_name}")


def _xml_find_all(root: ET.Element, tag_local_name: str) -> List[ET.Element]:
    return list(root.findall(f".//{{*}}{tag_local_name}"))


def parse_atlas_xml(xml_text: str) -> Atlas:
    """Parse a Klei atlas XML into an Atlas object."""

    root = ET.fromstring(xml_text)

    tex_node = _xml_find_first(root, "Texture")
    tex_filename = (tex_node.get("filename") if tex_node is not None else None) or ""

    elements: Dict[str, AtlasElement] = {}
    for el in _xml_find_all(root, "Element"):
        name = (el.get("name") or "").strip()
        if not name:
            continue
        try:
            u1 = float(el.get("u1") or "0")
            u2 = float(el.get("u2") or "0")
            v1 = float(el.get("v1") or "0")
            v2 = float(el.get("v2") or "0")
        except Exception:
            continue

        elements[name] = AtlasElement(name=name, u1=u1, u2=u2, v1=v1, v2=v2)

    return Atlas(texture_filename=tex_filename, elements=elements)


def atlas_uv_to_box(
    elem: AtlasElement,
    tex_w: int,
    tex_h: int,
    *,
    invert_v: bool = True,
) -> Tuple[int, int, int, int]:
    """Convert atlas UVs into a PIL crop box (left, top, right, bottom).

    Atlas coordinates:
      - u: 0..1 left->right
      - v: 0..1 top->bottom (for DST inventory atlases); some atlases use bottom-origin.

    PIL image coordinates:
      - (0,0) is top-left
    """

    x1 = int(round(elem.u1 * tex_w))
    x2 = int(round(elem.u2 * tex_w))

    if invert_v:
        y1_from_bottom = int(round(elem.v1 * tex_h))
        y2_from_bottom = int(round(elem.v2 * tex_h))
        top = tex_h - y2_from_bottom
        bottom = tex_h - y1_from_bottom
    else:
        y1 = int(round(elem.v1 * tex_h))
        y2 = int(round(elem.v2 * tex_h))
        top = min(y1, y2)
        bottom = max(y1, y2)

    # Normalize / clamp
    left = max(0, min(tex_w, min(x1, x2)))
    right = max(0, min(tex_w, max(x1, x2)))
    top2 = max(0, min(tex_h, min(top, bottom)))
    bottom2 = max(0, min(tex_h, max(top, bottom)))

    return left, top2, right, bottom2


# -----------------------------
# KTEX (Klei TEX)
# -----------------------------


class KTexError(RuntimeError):
    pass


@dataclass(frozen=True)
class KTexMipmap:
    width: int
    height: int
    pitch: int
    data_size: int
    data_offset: int


def _parse_ktex_variant(data: bytes, *, variant: str) -> Optional[Tuple[List[KTexMipmap], int]]:
    """Try parsing KTEX mipmap table.

    Returns:
      (mipmaps, end_offset) or None
    """

    if len(data) < 8:
        return None

    if data[:4] != b"KTEX":
        return None

    specs = struct.unpack_from("<I", data, 4)[0]

    if variant == "pre":
        mipmap_count = (specs >> 9) & 0xF
    elif variant == "post":
        mipmap_count = (specs >> 13) & 0x1F
    else:
        raise ValueError(f"unknown variant: {variant}")

    if mipmap_count <= 0:
        return None

    off = 8
    mips_meta: List[Tuple[int, int, int, int]] = []
    for _ in range(mipmap_count):
        if off + 10 > len(data):
            return None
        w, h, pitch, size = struct.unpack_from("<HHHI", data, off)
        off += 10
        if w <= 0 or h <= 0 or size <= 0:
            return None
        mips_meta.append((int(w), int(h), int(pitch), int(size)))

    data_off = off
    mips: List[KTexMipmap] = []
    for (w, h, pitch, size) in mips_meta:
        if data_off + size > len(data):
            return None
        mips.append(KTexMipmap(width=w, height=h, pitch=pitch, data_size=size, data_offset=data_off))
        data_off += size

    return mips, data_off


def parse_ktex(data: bytes) -> List[KTexMipmap]:
    """Parse a KTEX file and return mipmap descriptors.

    The KTEX header has two known variants (pre-caves-update and post-caves-update)
    which differ only in how the bitfield encodes mipmap_count.

    We attempt both and pick the one that yields the most plausible layout.

    Source for header bitfield layouts:
      - Stexatlaser project README (KTEX format section)
    """

    if len(data) < 8 or data[:4] != b"KTEX":
        raise KTexError("Not a KTEX file")

    candidates: List[Tuple[int, str, List[KTexMipmap], int]] = []
    for variant in ("post", "pre"):
        res = _parse_ktex_variant(data, variant=variant)
        if not res:
            continue
        mips, end_off = res
        # score: prefer layouts that consume most bytes (small remainder)
        remainder = abs(len(data) - end_off)
        candidates.append((remainder, variant, mips, end_off))

    if not candidates:
        raise KTexError("Failed to parse KTEX mipmap table")

    candidates.sort(key=lambda x: (x[0], 0 if x[1] == "post" else 1))
    _, _, mips, _ = candidates[0]
    return mips


def _infer_tex_payload_format(width: int, height: int, data_size: int, pitch: int) -> str:
    """Infer payload format from (w,h,data_size,pitch).

    Returns one of: "RGBA", "RGB", "DXT1", "DXT5".

    Many DST textures are DXT5.
    """

    w = int(width)
    h = int(height)
    if w <= 0 or h <= 0 or data_size <= 0:
        return ""

    rgba_size = w * h * 4
    rgb_size = w * h * 3

    blocks_w = (w + 3) // 4
    blocks_h = (h + 3) // 4
    dxt1_size = blocks_w * blocks_h * 8
    dxt5_size = blocks_w * blocks_h * 16

    # Exact matches first
    if data_size == rgba_size:
        return "RGBA"
    if data_size == rgb_size:
        return "RGB"
    if data_size == dxt1_size:
        return "DXT1"
    if data_size == dxt5_size:
        return "DXT5"

    # Heuristic via pitch
    if pitch in (w * 4, (w * 4) + 2):
        return "RGBA"
    if pitch in (w * 3, (w * 3) + 2):
        return "RGB"
    if pitch == blocks_w * 8 and data_size <= dxt1_size:
        return "DXT1"
    if pitch == blocks_w * 16 and data_size <= dxt5_size:
        return "DXT5"

    return ""


def _rgb565_to_rgb888(c: int) -> Tuple[int, int, int]:
    r = ((c >> 11) & 0x1F) * 255 // 31
    g = ((c >> 5) & 0x3F) * 255 // 63
    b = (c & 0x1F) * 255 // 31
    return int(r), int(g), int(b)


def _decompress_dxt1(payload: bytes, width: int, height: int) -> bytes:
    """Decompress DXT1 blocks into RGBA8888 bytes."""

    w = int(width)
    h = int(height)
    blocks_w = (w + 3) // 4
    blocks_h = (h + 3) // 4

    out = bytearray(w * h * 4)
    off = 0

    for by in range(blocks_h):
        for bx in range(blocks_w):
            if off + 8 > len(payload):
                raise KTexError("DXT1 payload truncated")

            c0, c1 = struct.unpack_from("<HH", payload, off)
            bits = struct.unpack_from("<I", payload, off + 4)[0]
            off += 8

            r0, g0, b0 = _rgb565_to_rgb888(c0)
            r1, g1, b1 = _rgb565_to_rgb888(c1)

            colors = [
                (r0, g0, b0, 255),
                (r1, g1, b1, 255),
            ]

            if c0 > c1:
                colors.append(((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3, 255))
                colors.append(((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3, 255))
            else:
                colors.append(((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 255))
                colors.append((0, 0, 0, 0))

            # Indices: 2 bits each, little-endian, row-major
            idx_bits = bits
            for py in range(4):
                for px in range(4):
                    idx = idx_bits & 0x3
                    idx_bits >>= 2

                    x = bx * 4 + px
                    y = by * 4 + py
                    if x >= w or y >= h:
                        continue

                    o = (y * w + x) * 4
                    r, g, b, a = colors[idx]
                    out[o + 0] = r
                    out[o + 1] = g
                    out[o + 2] = b
                    out[o + 3] = a

    return bytes(out)


def _decompress_dxt5(payload: bytes, width: int, height: int) -> bytes:
    """Decompress DXT5 blocks into RGBA8888 bytes."""

    w = int(width)
    h = int(height)
    blocks_w = (w + 3) // 4
    blocks_h = (h + 3) // 4

    out = bytearray(w * h * 4)
    off = 0

    for by in range(blocks_h):
        for bx in range(blocks_w):
            if off + 16 > len(payload):
                raise KTexError("DXT5 payload truncated")

            a0 = payload[off]
            a1 = payload[off + 1]
            alpha_bits = int.from_bytes(payload[off + 2 : off + 8], "little")

            # Alpha palette
            alphas = [0] * 8
            alphas[0] = a0
            alphas[1] = a1
            if a0 > a1:
                # 6 interpolated values
                alphas[2] = (6 * a0 + 1 * a1) // 7
                alphas[3] = (5 * a0 + 2 * a1) // 7
                alphas[4] = (4 * a0 + 3 * a1) // 7
                alphas[5] = (3 * a0 + 4 * a1) // 7
                alphas[6] = (2 * a0 + 5 * a1) // 7
                alphas[7] = (1 * a0 + 6 * a1) // 7
            else:
                # 4 interpolated, then 0 and 255
                alphas[2] = (4 * a0 + 1 * a1) // 5
                alphas[3] = (3 * a0 + 2 * a1) // 5
                alphas[4] = (2 * a0 + 3 * a1) // 5
                alphas[5] = (1 * a0 + 4 * a1) // 5
                alphas[6] = 0
                alphas[7] = 255

            # Color block (DXT1-style)
            c0, c1 = struct.unpack_from("<HH", payload, off + 8)
            color_bits = struct.unpack_from("<I", payload, off + 12)[0]

            r0, g0, b0 = _rgb565_to_rgb888(c0)
            r1, g1, b1 = _rgb565_to_rgb888(c1)

            # In DXT5, colors are always 4-color interpolations (alpha is separate)
            colors = [
                (r0, g0, b0),
                (r1, g1, b1),
                ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
                ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3),
            ]

            off += 16

            a_bits = alpha_bits
            c_bits = color_bits
            for py in range(4):
                for px in range(4):
                    a_idx = a_bits & 0x7
                    a_bits >>= 3

                    c_idx = c_bits & 0x3
                    c_bits >>= 2

                    x = bx * 4 + px
                    y = by * 4 + py
                    if x >= w or y >= h:
                        continue

                    r, g, b = colors[c_idx]
                    a = alphas[a_idx]

                    o = (y * w + x) * 4
                    out[o + 0] = r
                    out[o + 1] = g
                    out[o + 2] = b
                    out[o + 3] = a

    return bytes(out)


def decode_ktex_to_image(tex_bytes: bytes) -> Image.Image:
    """Decode KTEX to a PIL RGBA image using mipmap level 0."""

    mips = parse_ktex(tex_bytes)
    mip0 = mips[0]

    payload = tex_bytes[mip0.data_offset : mip0.data_offset + mip0.data_size]
    fmt = _infer_tex_payload_format(mip0.width, mip0.height, mip0.data_size, mip0.pitch)
    if not fmt:
        raise KTexError(
            f"Unsupported/unknown TEX payload format (w={mip0.width}, h={mip0.height}, size={mip0.data_size}, pitch={mip0.pitch})"
        )

    if fmt == "RGBA":
        rgba = payload
        if len(rgba) < mip0.width * mip0.height * 4:
            raise KTexError("RGBA payload truncated")
        rgba = rgba[: mip0.width * mip0.height * 4]
    elif fmt == "RGB":
        if len(payload) < mip0.width * mip0.height * 3:
            raise KTexError("RGB payload truncated")
        rgb = payload[: mip0.width * mip0.height * 3]
        # expand to RGBA
        out = bytearray(mip0.width * mip0.height * 4)
        j = 0
        for i in range(0, len(rgb), 3):
            out[j + 0] = rgb[i + 0]
            out[j + 1] = rgb[i + 1]
            out[j + 2] = rgb[i + 2]
            out[j + 3] = 255
            j += 4
        rgba = bytes(out)
    elif fmt == "DXT1":
        rgba = _decompress_dxt1(payload, mip0.width, mip0.height)
    else:
        rgba = _decompress_dxt5(payload, mip0.width, mip0.height)

    return Image.frombytes("RGBA", (mip0.width, mip0.height), rgba)


# -----------------------------
# Extraction helpers
# -----------------------------


def unpremultiply_alpha_rgba(img: Image.Image) -> Image.Image:
    """Return a new image with straight (unpremultiplied) alpha.

    This is applied *after* cropping for performance (icons are small).
    """

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    raw = bytearray(img.tobytes())
    for i in range(0, len(raw), 4):
        a = raw[i + 3]
        if a == 0 or a == 255:
            continue
        # Avoid rounding to >255
        raw[i + 0] = min(255, (raw[i + 0] * 255) // a)
        raw[i + 1] = min(255, (raw[i + 1] * 255) // a)
        raw[i + 2] = min(255, (raw[i + 2] * 255) // a)

    return Image.frombytes("RGBA", img.size, bytes(raw))


def fix_ktex_orientation(img: Image.Image) -> Image.Image:
    """Fix KTEX orientation for UI output."""

    try:
        return img.transpose(Image.FLIP_TOP_BOTTOM)
    except Exception:
        return img


def extract_atlas_element(
    atlas: Atlas,
    tex_image: Image.Image,
    element_name: str,
    *,
    unpremultiply: bool = True,
    invert_v: bool = True,
) -> Optional[Image.Image]:
    """Crop a named element from an atlas texture image."""

    el = atlas.get(element_name)
    if not el:
        return None

    w, h = tex_image.size
    left, top, right, bottom = atlas_uv_to_box(el, w, h, invert_v=invert_v)
    if right <= left or bottom <= top:
        return None

    cropped = tex_image.crop((left, top, right, bottom))
    cropped = fix_ktex_orientation(cropped)
    if unpremultiply:
        try:
            cropped = unpremultiply_alpha_rgba(cropped)
        except Exception:
            # If anything goes wrong, still return the cropped image.
            pass
    return cropped


def resolve_tex_path_from_atlas(xml_path: Path, atlas: Atlas) -> Optional[Path]:
    """Resolve the atlas <Texture filename="..."> into a filesystem path."""

    fn = (atlas.texture_filename or "").strip()
    if not fn:
        # Common fallback: same basename as xml
        return xml_path.with_suffix(".tex")

    # If XML stores full-ish path, try as-is relative to xml parent.
    p = Path(fn)
    if p.is_absolute():
        return p

    return (xml_path.parent / p).resolve()


def write_element_png(
    *,
    atlas_xml_path: Path,
    tex_path: Path,
    element_name: str,
    out_png_path: Path,
    unpremultiply: bool = True,
    overwrite: bool = False,
) -> bool:
    """Extract one element and write a PNG.

    Returns True on success.
    """

    if out_png_path.exists() and not overwrite:
        return True

    xml_text = atlas_xml_path.read_text(encoding="utf-8", errors="ignore")
    atlas = parse_atlas_xml(xml_text)

    tex_bytes = tex_path.read_bytes()
    tex_image = decode_ktex_to_image(tex_bytes)

    cropped = extract_atlas_element(atlas, tex_image, element_name, unpremultiply=unpremultiply)
    if cropped is None:
        return False

    out_png_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(out_png_path, format="PNG")
    return True


def pick_first_existing(names: Iterable[str], available: Dict[str, AtlasElement]) -> Optional[str]:
    for n in names:
        if not n:
            continue
        if n in available:
            return n
    return None


# =========================================================
# PNG writer helper (added by hotfix)
# =========================================================

def write_png(img, out_path):
    '''Write a PIL Image to PNG, ensuring parent directories exist.

    This is intentionally tiny and dependency-light (relies on Pillow already
    used by the atlas/tex pipeline).
    '''
    from pathlib import Path

    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # Ensure RGBA to avoid mode issues on some Pillow builds
    try:
        img.save(str(p), format="PNG")
    except Exception:
        img.convert("RGBA").save(str(p), format="PNG")

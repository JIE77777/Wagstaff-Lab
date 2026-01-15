# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class WebCraftSettings:
    """Runtime settings for WebCraft server.

    Notes
    - catalog_path should point to data/index/wagstaff_catalog_v1.json
    - root_path is for reverse-proxy mount (e.g. '/webcraft')
    """

    catalog_path: Path
    root_path: str = ""
    cors_allow_origins: Optional[List[str]] = None
    gzip_minimum_size: int = 800

    @staticmethod
    def normalize_root_path(root_path: str) -> str:
        rp = (root_path or "").strip()
        if not rp:
            return ""
        if not rp.startswith("/"):
            rp = "/" + rp
        rp = rp.rstrip("/")
        return rp

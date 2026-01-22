# -*- coding: utf-8 -*-
"""WebCraft UI template renderer."""

from __future__ import annotations

from functools import lru_cache
from html import escape
from pathlib import Path


_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


@lru_cache(maxsize=None)
def _load_template(name: str) -> str:
    path = _TEMPLATE_DIR / name
    return path.read_text(encoding="utf-8")


def _render_template(name: str, app_root: str) -> str:
    root = str(app_root or "").rstrip("/")
    return _load_template(name).replace("__WAGSTAFF_APP_ROOT__", escape(root))


def render_catalog_html(app_root: str = "") -> str:
    """Render the Catalog UI page."""
    return _render_template("catalog.html", app_root)


def render_index_html(app_root: str = "") -> str:
    """Render the Craft UI page.

    app_root:
      - ""       normal direct serving
      - "/xxx"   reverse proxy mount path
    """
    return _render_template("index.html", app_root)


def render_cooking_html(app_root: str = "") -> str:
    """Render the Cooking UI page."""
    return _render_template("cooking.html", app_root)


def render_cooking_tools_html(app_root: str = "") -> str:
    """Render the Cooking tools UI page."""
    return _render_template("cooking_tools.html", app_root)


def render_farming_tools_html(app_root: str = "") -> str:
    """Render the Farming tools UI page."""
    return _render_template("farming_tools.html", app_root)

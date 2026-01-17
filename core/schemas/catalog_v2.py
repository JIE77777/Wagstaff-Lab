#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catalog v2 data model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class WagstaffCatalogV2:
    schema_version: int
    meta: Dict[str, Any]
    items: Dict[str, Any]
    assets: Dict[str, Any]
    craft: Dict[str, Any]
    cooking: Dict[str, Any]
    cooking_ingredients: Dict[str, Any]
    stats: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": int(self.schema_version),
            "meta": self.meta,
            "items": self.items,
            "assets": self.assets,
            "craft": self.craft,
            "cooking": self.cooking,
            "cooking_ingredients": self.cooking_ingredients,
            "stats": self.stats,
        }

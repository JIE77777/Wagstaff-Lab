# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .catalog_store import CraftRecipe


def normalize_inventory(inv: Dict[str, Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k, v in (inv or {}).items():
        key = str(k).strip()
        if not key:
            continue
        try:
            num = float(v)
        except Exception:
            continue
        if num <= 0:
            continue
        out[key] = num
    return out


def _recipe_requires_builder_tag(recipe: CraftRecipe) -> Optional[str]:
    # builder_tags preferred
    if recipe.builder_tags:
        # a recipe can accept multiple tags; treat as "any-of"
        return ",".join(recipe.builder_tags)
    return None


def is_builder_allowed(recipe: CraftRecipe, builder_tag: Optional[str], strict: bool = False) -> Tuple[bool, str]:
    """Check if builder can craft this recipe.

    strict:
      - if True: treat builder_skill as locked (unknown to us), require builder_tag for builder_tags
      - if False: only enforce builder_tags; ignore builder_skill
    """
    bt_required = recipe.builder_tags or []
    if bt_required:
        if not builder_tag:
            return False, "missing_builder_tag"
        if builder_tag not in bt_required:
            return False, "builder_tag_mismatch"

    if strict and recipe.builder_skill:
        # we don't model skill tree yet; mark as blocked
        return False, "builder_skill_locked"

    return True, ""


@dataclass
class MissingItem:
    item: str
    need: float
    have: float
    reason: str = ""


def missing_for(recipe: CraftRecipe, inventory: Dict[str, float]) -> List[MissingItem]:
    """Compute missing materials for a recipe based on numeric amounts.

    If amount_num is missing/unresolvable => treated as missing with reason 'unresolved_amount'.
    """
    inv = inventory or {}
    missing: List[MissingItem] = []

    # unresolved list from catalog (e.g. CHARACTER_INGREDIENT.HEALTH)
    for unresolved in (recipe.ingredients_unresolved or []):
        missing.append(MissingItem(item=str(unresolved), need=1.0, have=0.0, reason="unresolved_ingredient"))

    for ing in (recipe.ingredients or []):
        item = str(ing.get("item") or "").strip()
        if not item:
            continue
        amt_num = ing.get("amount_num", None)
        if amt_num is None:
            # fallback: try parse amount string
            try:
                amt_num = float(ing.get("amount"))
            except Exception:
                amt_num = None
        if amt_num is None:
            missing.append(MissingItem(item=item, need=1.0, have=float(inv.get(item, 0.0)), reason="unresolved_amount"))
            continue

        have = float(inv.get(item, 0.0))
        need = float(amt_num)
        if have + 1e-9 < need:
            missing.append(MissingItem(item=item, need=need, have=have, reason="insufficient"))

    return missing


def craftable_recipes(
    recipes: List[CraftRecipe],
    inventory: Dict[str, float],
    builder_tag: Optional[str] = None,
    strict: bool = False,
) -> Tuple[List[CraftRecipe], List[Dict[str, Any]]]:
    """Return craftable recipes + blocked details."""
    inv = inventory or {}
    ok: List[CraftRecipe] = []
    blocked: List[Dict[str, Any]] = []

    for r in recipes:
        allowed, reason = is_builder_allowed(r, builder_tag, strict=strict)
        if not allowed:
            blocked.append({"name": r.name, "reason": reason})
            continue

        miss = missing_for(r, inv)
        if miss:
            blocked.append({"name": r.name, "reason": "missing_material", "missing": [m.__dict__ for m in miss]})
            continue

        ok.append(r)

    return ok, blocked

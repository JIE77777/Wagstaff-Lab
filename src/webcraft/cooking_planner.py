# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .catalog_store import CookingRecipe


def normalize_counts(inv: Dict[str, Any]) -> Dict[str, float]:
    """Normalize item->count mapping.

    - Keys are stripped strings.
    - Values must be numeric and > 0.

    This helper is shared by:
      - cookable query (inventory)
      - simulator (cookpot slots)
    """

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


def _requirements_satisfied(req: List[Tuple[str, float]], available: Dict[str, float]) -> bool:
    """Check if `available` contains all `req` items with required counts."""
    for item, need in (req or []):
        if not item:
            continue
        have = float(available.get(item, 0.0))
        if have + 1e-9 < float(need):
            return False
    return True


def find_cookable(
    recipes: List[CookingRecipe],
    inventory: Dict[str, Any],
    *,
    limit: int = 200,
) -> List[CookingRecipe]:
    """Find cookable recipes based on catalog `card_ingredients`.

    Current limitation
    - Only recipes with `card_ingredients` can be evaluated.
    """

    inv = normalize_counts(inventory)
    limit = max(1, min(int(limit or 200), 2000))

    out: List[CookingRecipe] = []
    for r in recipes:
        if not r.card_ingredients:
            continue
        if _requirements_satisfied(r.card_ingredients, inv):
            out.append(r)

    # Stable order: higher priority first, then name.
    out.sort(key=lambda x: (-float(x.priority), x.name))
    return out[:limit]


@dataclass(frozen=True)
class SimCandidate:
    name: str
    priority: float
    weight: float


def simulate_cookpot(
    recipes: List[CookingRecipe],
    slots: Dict[str, Any],
    *,
    return_top: int = 25,
) -> Dict[str, Any]:
    """Simulate cookpot output using catalog `card_ingredients`.

    Input
    - slots: mapping of item -> count placed into the pot.

    Behavior
    - Requires total slot count == 4 (cookpot rule).
    - Only evaluates recipes that have `card_ingredients`.
    - If multiple match, choose the highest priority; tie-break by weight then name.
    - If none match, fall back to 'wetgoop' if present in recipe list.

    Returns a dict suitable for JSON response.
    """

    counts = normalize_counts(slots)
    total = sum(int(round(v)) for v in counts.values())
    if total != 4:
        return {
            "ok": False,
            "error": "cookpot_requires_4_items",
            "total": total,
            "slots": {k: int(round(v)) for k, v in counts.items()},
        }

    # int-normalize (cookpot is discrete)
    slots_i: Dict[str, int] = {}
    for k, v in counts.items():
        n = int(round(v))
        if n <= 0:
            continue
        slots_i[k] = slots_i.get(k, 0) + n

    candidates: List[CookingRecipe] = []
    for r in recipes:
        if not r.card_ingredients:
            continue
        if _requirements_satisfied(r.card_ingredients, {k: float(v) for k, v in slots_i.items()}):
            candidates.append(r)

    if candidates:
        candidates.sort(key=lambda x: (-float(x.priority), -float(x.weight), x.name))
        best = candidates[0]
        top = [SimCandidate(name=r.name, priority=float(r.priority), weight=float(r.weight)) for r in candidates[:return_top]]
        return {
            "ok": True,
            "result": best.name,
            "reason": "matched_card_ingredients",
            "candidates": [c.__dict__ for c in top],
            "slots": slots_i,
        }

    # fallback
    wet = next((r for r in recipes if r.name == "wetgoop"), None)
    if wet is not None:
        return {
            "ok": True,
            "result": "wetgoop",
            "reason": "fallback_wetgoop",
            "candidates": [],
            "slots": slots_i,
        }

    return {
        "ok": False,
        "error": "no_match_and_no_wetgoop",
        "candidates": [],
        "slots": slots_i,
    }

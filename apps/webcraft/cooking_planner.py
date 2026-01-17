# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .catalog_store import CookingRecipe, guess_cooking_tags, normalize_cooking_tags

TAG_PENALTY = 10.0
NAME_PENALTY = 50.0
MAX_AVAILABLE_COMBOS = 15000


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
        key = str(k).strip().lower()
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


def _normalize_slots(slots: Dict[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for k, v in normalize_counts(slots).items():
        n = int(round(v))
        if n <= 0:
            continue
        out[k] = out.get(k, 0) + n
    return out


def _normalize_available(items: Optional[Iterable[str]]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for item in items or []:
        iid = str(item or "").strip().lower()
        if not iid or iid in seen:
            continue
        seen.add(iid)
        out.append(iid)
    return out


def _combo_count(n: int, k: int) -> int:
    if k <= 0:
        return 1
    if n <= 0:
        return 0
    num = 1
    den = 1
    for i in range(1, k + 1):
        num *= n + i - 1
        den *= i
    return num // den


def _build_slot_combos(items: List[str], remaining: int, *, max_count: int) -> Optional[List[Dict[str, int]]]:
    if remaining <= 0:
        return [dict()]
    if not items:
        return []
    if _combo_count(len(items), remaining) > max_count:
        return None

    combos: List[Dict[str, int]] = []

    def _walk(start: int, rem: int, cur: Dict[str, int]) -> None:
        if rem <= 0:
            combos.append(dict(cur))
            return
        for idx in range(start, len(items)):
            iid = items[idx]
            cur[iid] = cur.get(iid, 0) + 1
            _walk(idx, rem - 1, cur)
            nxt = cur.get(iid, 0) - 1
            if nxt <= 0:
                cur.pop(iid, None)
            else:
                cur[iid] = nxt

    _walk(0, remaining, {})
    return combos


def _merge_slots(base: Dict[str, int], extra: Dict[str, int]) -> Dict[str, int]:
    if not extra:
        return dict(base)
    out = dict(base)
    for k, v in extra.items():
        out[k] = out.get(k, 0) + int(v)
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


def build_ingredient_index(
    ingredients: Dict[str, Any],
    *,
    extra_items: Optional[Iterable[str]] = None,
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
    tags_by_item: Dict[str, Dict[str, float]] = {}
    max_by_tag: Dict[str, float] = {}

    def _merge(iid: str, tags: Dict[str, float]) -> None:
        if not tags:
            return
        out = tags_by_item.get(iid, {})
        for k, v in tags.items():
            key = str(k).strip().lower()
            if not key:
                continue
            try:
                num = float(v)
            except Exception:
                continue
            out[key] = num
            if key not in max_by_tag or num > max_by_tag[key]:
                max_by_tag[key] = num
        if out:
            tags_by_item[iid] = out

    for item_id, raw in (ingredients or {}).items():
        if not item_id or not isinstance(raw, dict):
            continue
        iid = str(item_id).strip().lower()
        if not iid:
            continue
        tags = normalize_cooking_tags(raw.get("tags"))
        guess = guess_cooking_tags(iid)
        if guess:
            for k, v in guess.items():
                tags.setdefault(k, v)
        _merge(iid, tags)

    for item_id in (extra_items or []):
        iid = str(item_id).strip().lower()
        if not iid or iid in tags_by_item:
            continue
        _merge(iid, guess_cooking_tags(iid))

    return tags_by_item, max_by_tag


def _sum_tags(slots: Dict[str, int], tags_by_item: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    for item_id, count in (slots or {}).items():
        tags = tags_by_item.get(str(item_id).strip().lower()) or {}
        if not tags:
            continue
        for tag, val in tags.items():
            totals[tag] = totals.get(tag, 0.0) + float(val) * float(count)
    return totals


def _sum_names(slots: Dict[str, int]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for item_id, count in (slots or {}).items():
        iid = str(item_id).strip().lower()
        if not iid:
            continue
        out[iid] = out.get(iid, 0) + int(count)
    return out


def _compare(lhs: float, op: str, rhs: float) -> bool:
    if op == "==":
        return abs(lhs - rhs) <= 1e-9
    if op == "~=":
        return abs(lhs - rhs) > 1e-9
    if op == ">":
        return lhs > rhs + 1e-9
    if op == ">=":
        return lhs + 1e-9 >= rhs
    if op == "<":
        return lhs + 1e-9 < rhs
    if op == "<=":
        return lhs <= rhs + 1e-9
    return True


def _constraint_delta(lhs: float, op: str, rhs: float) -> Tuple[float, str]:
    if op in (">", ">="):
        delta = max(0.0, rhs - lhs)
        return delta, "under"
    if op in ("<", "<="):
        delta = max(0.0, lhs - rhs)
        return delta, "over"
    if op == "==":
        delta = abs(lhs - rhs)
        return delta, "mismatch"
    if op == "~=":
        delta = 0.0 if abs(lhs - rhs) > 1e-9 else 1.0
        return delta, "equal"
    return 0.0, "unknown"


def _coerce_constraint_value(v: Any) -> Optional[float]:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v))
    except Exception:
        return None


def _get_rule_constraints(recipe: CookingRecipe) -> Dict[str, List[Dict[str, Any]]]:
    rule = recipe.raw.get("rule") if isinstance(recipe.raw, dict) else None
    if not isinstance(rule, dict):
        return {}
    cons = rule.get("constraints")
    if not isinstance(cons, dict):
        return {}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for key in ("tags", "names", "unparsed"):
        rows = cons.get(key)
        if isinstance(rows, list):
            out[key] = [r for r in rows if isinstance(r, dict)]

    tags = out.get("tags") or []
    if tags:
        not_keys: Set[str] = set()
        for c in tags:
            text = str(c.get("text") or "").strip().lower()
            key = str(c.get("key") or "").strip().lower()
            if key and text.startswith("not "):
                not_keys.add(key)
        if not_keys:
            filtered: List[Dict[str, Any]] = []
            for c in tags:
                key = str(c.get("key") or "").strip().lower()
                text = str(c.get("text") or "").strip().lower()
                op = str(c.get("op") or "").strip()
                if key in not_keys and not text.startswith("not ") and op in (">", ">="):
                    continue
                filtered.append(c)
            out["tags"] = filtered
    return out


def _evaluate_constraints(
    constraints: Dict[str, List[Dict[str, Any]]],
    *,
    tags_total: Dict[str, float],
    names_total: Dict[str, int],
) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
    missing: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for c in constraints.get("tags") or []:
        key = str(c.get("key") or "").strip().lower()
        op = str(c.get("op") or "").strip()
        rhs = _coerce_constraint_value(c.get("value"))
        if not key or rhs is None:
            warnings.append(str(c.get("text") or "tag_constraint_unparsed"))
            continue
        lhs = float(tags_total.get(key, 0.0))
        ok = _compare(lhs, op, float(rhs))
        if not ok:
            delta, direction = _constraint_delta(lhs, op, float(rhs))
            missing.append(
                {
                    "type": "tag",
                    "key": key,
                    "op": op,
                    "required": float(rhs),
                    "actual": lhs,
                    "delta": delta,
                    "direction": direction,
                    "text": c.get("text") or "",
                }
            )

    for c in constraints.get("names") or []:
        key = str(c.get("key") or "").strip().lower()
        op = str(c.get("op") or "").strip()
        rhs = _coerce_constraint_value(c.get("value"))
        if not key or rhs is None:
            warnings.append(str(c.get("text") or "name_constraint_unparsed"))
            continue
        lhs = float(names_total.get(key, 0))
        ok = _compare(lhs, op, float(rhs))
        if not ok:
            delta, direction = _constraint_delta(lhs, op, float(rhs))
            missing.append(
                {
                    "type": "name",
                    "key": key,
                    "op": op,
                    "required": float(rhs),
                    "actual": lhs,
                    "delta": delta,
                    "direction": direction,
                    "text": c.get("text") or "",
                }
            )

    return len(missing) == 0, missing, warnings


def _score_recipe(priority: float, weight: float, missing: List[Dict[str, Any]]) -> Tuple[float, float]:
    penalty = 0.0
    for m in missing or []:
        delta = float(m.get("delta") or 0.0)
        if m.get("type") == "tag":
            penalty += delta * TAG_PENALTY
        elif m.get("type") == "name":
            penalty += delta * NAME_PENALTY
    score = float(priority) * 1000.0 + float(weight) * 100.0 - penalty
    return score, penalty


def _evaluate_recipe(
    recipe: CookingRecipe,
    *,
    slots: Dict[str, int],
    tags_by_item: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    constraints = _get_rule_constraints(recipe)
    if constraints:
        tags_total = _sum_tags(slots, tags_by_item)
        names_total = _sum_names(slots)
        ok, missing, warnings = _evaluate_constraints(
            constraints,
            tags_total=tags_total,
            names_total=names_total,
        )
        return {
            "ok": ok,
            "missing": missing,
            "warnings": warnings,
            "tags_total": tags_total,
            "names_total": names_total,
            "rule_mode": "rule",
        }

    if recipe.card_ingredients:
        ok = _requirements_satisfied(recipe.card_ingredients, {k: float(v) for k, v in slots.items()})
        missing = []
        if not ok:
            for item, need in recipe.card_ingredients:
                have = float(slots.get(item, 0))
                if have + 1e-9 < float(need):
                    missing.append(
                        {
                            "type": "name",
                            "key": str(item),
                            "op": ">=",
                            "required": float(need),
                            "actual": have,
                            "delta": float(need) - have,
                            "direction": "under",
                            "text": "",
                        }
                    )
        return {
            "ok": ok,
            "missing": missing,
            "warnings": [],
            "tags_total": {},
            "names_total": _sum_names(slots),
            "rule_mode": "card",
        }

    return {
        "ok": False,
        "missing": [],
        "warnings": ["no_rule_or_card_ingredients"],
        "tags_total": {},
        "names_total": _sum_names(slots),
        "rule_mode": "none",
    }


def _possible_with_remaining(
    constraints: Dict[str, List[Dict[str, Any]]],
    *,
    tags_total: Dict[str, float],
    names_total: Dict[str, int],
    remaining: int,
    max_by_tag: Dict[str, float],
    available_names: Optional[Set[str]] = None,
) -> bool:
    for c in constraints.get("tags") or []:
        key = str(c.get("key") or "").strip().lower()
        op = str(c.get("op") or "").strip()
        rhs = _coerce_constraint_value(c.get("value"))
        if not key or rhs is None:
            continue
        lhs = float(tags_total.get(key, 0.0))
        max_add = float(max_by_tag.get(key, 0.0)) * float(max(0, remaining))
        max_possible = lhs + max_add
        if op in (">", ">=") and max_possible + 1e-9 < float(rhs):
            return False
        if op in ("<", "<=") and lhs > float(rhs) + 1e-9:
            return False
        if op == "==" and (float(rhs) < lhs - 1e-9 or float(rhs) > max_possible + 1e-9):
            return False
        if op == "~=" and abs(lhs - float(rhs)) <= 1e-9 and max_add <= 1e-9:
            return False

    for c in constraints.get("names") or []:
        key = str(c.get("key") or "").strip().lower()
        op = str(c.get("op") or "").strip()
        rhs = _coerce_constraint_value(c.get("value"))
        if not key or rhs is None:
            continue
        if available_names is not None and op in (">", ">=", "==") and float(rhs) > 0:
            if key not in available_names:
                return False
        lhs = float(names_total.get(key, 0))
        max_possible = lhs + float(max(0, remaining))
        if op in (">", ">=") and max_possible + 1e-9 < float(rhs):
            return False
        if op in ("<", "<=") and lhs > float(rhs) + 1e-9:
            return False
        if op == "==" and (float(rhs) < lhs - 1e-9 or float(rhs) > max_possible + 1e-9):
            return False
        if op == "~=" and abs(lhs - float(rhs)) <= 1e-9 and remaining <= 0:
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
    ingredients: Optional[Dict[str, Any]] = None,
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

    slots_i = _normalize_slots(slots)
    total = sum(int(v) for v in slots_i.values())
    if total != 4:
        return {
            "ok": False,
            "error": "cookpot_requires_4_items",
            "total": total,
            "slots": slots_i,
        }

    tags_by_item, _ = build_ingredient_index(ingredients or {}, extra_items=slots_i.keys())

    candidates: List[CookingRecipe] = []
    candidate_rows: List[Dict[str, Any]] = []
    near_miss: List[Dict[str, Any]] = []
    for r in recipes:
        ev = _evaluate_recipe(r, slots=slots_i, tags_by_item=tags_by_item)
        score, penalty = _score_recipe(float(r.priority), float(r.weight), ev.get("missing") or [])
        row = {
            "name": r.name,
            "priority": float(r.priority),
            "weight": float(r.weight),
            "score": score,
            "penalty": penalty,
            "missing": ev.get("missing") or [],
            "rule_mode": ev.get("rule_mode"),
            "warnings": ev.get("warnings") or [],
        }
        if ev.get("ok"):
            candidates.append(r)
            row["ok"] = True
            candidate_rows.append(row)
        else:
            row["ok"] = False
            near_miss.append(row)

    if candidates:
        candidates.sort(key=lambda x: (-float(x.priority), -float(x.weight), x.name))
        best = candidates[0]
        top = [SimCandidate(name=r.name, priority=float(r.priority), weight=float(r.weight)) for r in candidates[:return_top]]
        return {
            "ok": True,
            "result": best.name,
            "reason": "matched_constraints",
            "candidates": [c.__dict__ for c in top],
            "cookable": sorted(candidate_rows, key=lambda x: (-x.get("score", 0.0), x.get("name", "")))[: return_top],
            "slots": slots_i,
            "near_miss": sorted(near_miss, key=lambda x: (-x.get("score", 0.0), x.get("name", "")))[: return_top],
            "formula": "score = priority*1000 + weight*100 - missing_penalty",
        }

    # fallback
    wet = next((r for r in recipes if r.name == "wetgoop"), None)
    if wet is not None:
        return {
            "ok": True,
            "result": "wetgoop",
            "reason": "fallback_wetgoop",
            "candidates": [],
            "cookable": [],
            "slots": slots_i,
            "near_miss": [],
            "formula": "score = priority*1000 + weight*100 - missing_penalty",
        }

    return {
        "ok": False,
        "error": "no_match_and_no_wetgoop",
        "candidates": [],
        "slots": slots_i,
    }


def explore_cookpot(
    recipes: List[CookingRecipe],
    slots: Dict[str, Any],
    *,
    ingredients: Dict[str, Any],
    limit: int = 200,
    available: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    slots_i = _normalize_slots(slots)
    total = sum(int(v) for v in slots_i.values())
    if total > 4:
        return {
            "ok": False,
            "error": "cookpot_requires_max_4_items",
            "total": total,
            "slots": slots_i,
        }

    remaining = 4 - total
    avail_list = _normalize_available(available)
    avail_set = set(avail_list)
    extra_items = list(slots_i.keys()) + avail_list
    tags_by_item, max_by_tag = build_ingredient_index(ingredients or {}, extra_items=extra_items)
    if avail_list:
        max_by_tag = {}
        for iid in avail_list:
            for tag, val in (tags_by_item.get(iid) or {}).items():
                if tag not in max_by_tag or val > max_by_tag[tag]:
                    max_by_tag[tag] = val

    if avail_list:
        combos = _build_slot_combos(avail_list, remaining, max_count=MAX_AVAILABLE_COMBOS)
        if combos is not None:
            cookable: List[Dict[str, Any]] = []
            near_miss: List[Dict[str, Any]] = []
            for r in recipes:
                best_ok: Optional[Dict[str, Any]] = None
                best_any: Optional[Dict[str, Any]] = None
                for combo in combos:
                    slots_full = _merge_slots(slots_i, combo)
                    ev = _evaluate_recipe(r, slots=slots_full, tags_by_item=tags_by_item)
                    score, penalty = _score_recipe(float(r.priority), float(r.weight), ev.get("missing") or [])
                    row = {
                        "name": r.name,
                        "priority": float(r.priority),
                        "weight": float(r.weight),
                        "score": score,
                        "penalty": penalty,
                        "missing": ev.get("missing") or [],
                        "rule_mode": ev.get("rule_mode"),
                        "warnings": ev.get("warnings") or [],
                    }
                    if best_any is None or score > float(best_any.get("score", 0.0)):
                        best_any = row
                    if ev.get("ok") and (best_ok is None or score > float(best_ok.get("score", 0.0))):
                        best_ok = row
                if best_ok is not None:
                    cookable.append(best_ok)
                elif best_any is not None:
                    near_miss.append(best_any)

            cookable.sort(key=lambda x: (-x.get("score", 0.0), x.get("name", "")))
            near_miss.sort(key=lambda x: (-x.get("score", 0.0), x.get("name", "")))
            return {
                "ok": True,
                "slots": slots_i,
                "total": total,
                "remaining": remaining,
                "available": avail_list,
                "cookable": cookable[:limit],
                "near_miss": near_miss[:limit],
                "formula": "score = priority*1000 + weight*100 - missing_penalty",
            }

    cookable: List[Dict[str, Any]] = []
    near_miss: List[Dict[str, Any]] = []
    for r in recipes:
        ev = _evaluate_recipe(r, slots=slots_i, tags_by_item=tags_by_item)
        score, penalty = _score_recipe(float(r.priority), float(r.weight), ev.get("missing") or [])
        row = {
            "name": r.name,
            "priority": float(r.priority),
            "weight": float(r.weight),
            "score": score,
            "penalty": penalty,
            "missing": ev.get("missing") or [],
            "rule_mode": ev.get("rule_mode"),
            "warnings": ev.get("warnings") or [],
        }
        if ev.get("rule_mode") == "rule":
            possible = _possible_with_remaining(
                _get_rule_constraints(r),
                tags_total=ev.get("tags_total") or {},
                names_total=ev.get("names_total") or {},
                remaining=remaining,
                max_by_tag=max_by_tag,
                available_names=avail_set if avail_set else None,
            )
            if possible:
                cookable.append(row)
            else:
                near_miss.append(row)
        elif ev.get("rule_mode") == "card" and total == 4:
            if ev.get("ok"):
                cookable.append(row)
            else:
                near_miss.append(row)
        else:
            near_miss.append(row)

    cookable.sort(key=lambda x: (-x.get("score", 0.0), x.get("name", "")))
    near_miss.sort(key=lambda x: (-x.get("score", 0.0), x.get("name", "")))

    return {
        "ok": True,
        "slots": slots_i,
        "total": total,
        "remaining": remaining,
        "cookable": cookable[:limit],
        "near_miss": near_miss[:limit],
        "formula": "score = priority*1000 + weight*100 - missing_penalty",
    }

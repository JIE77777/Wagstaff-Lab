#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tag inference and overrides for catalog v2."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set


KIND_ORDER = ["character", "creature", "structure", "plant", "item", "fx", "unknown"]

CREATURE_TAGS = {
    "monster",
    "animal",
    "smallcreature",
    "largecreature",
    "epic",
    "hostile",
    "bird",
    "animal",
    "scarytoprey",
}

PLANT_TAGS = {"plant", "tree", "crop", "flower", "berrybush", "mushroom"}

STRUCTURE_TAGS = {"structure", "wall", "house", "ruins"}

FX_TAGS = {"fx", "noclick", "notarget"}


COMP_BEHAVIORS = {
    "equippable": "equippable",
    "edible": "edible",
    "stackable": "stackable",
    "burnable": "burnable",
    "perishable": "perishable",
    "repairable": "repairable",
    "fuel": "fuel",
    "tradable": "tradable",
    "hauntable": "hauntable",
    "deployable": "deployable",
}

COMP_CATEGORIES = {
    "weapon": "weapon",
    "armor": "armor",
    "edible": "food",
    "container": "container",
    "inventory": "container",
    "light": "light",
    "fueled": "light",
    "deployable": "deployable",
    "trap": "trap",
    "boat": "boat",
    "farmplanttendable": "farm",
    "tool": "tool",
}

TAG_CATEGORIES = {
    "weapon": "weapon",
    "armor": "armor",
    "food": "food",
    "cookable": "food",
    "magic": "magic",
    "container": "container",
    "boat": "boat",
    "decor": "decor",
    "toy": "toy",
    "cattoy": "toy",
    "light": "light",
    "deploykititem": "deployable",
}


@dataclass
class TagProfile:
    kind: str = "unknown"
    categories: Set[str] = field(default_factory=set)
    behaviors: Set[str] = field(default_factory=set)
    sources: Set[str] = field(default_factory=set)
    slots: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "categories": sorted(self.categories),
            "behaviors": sorted(self.behaviors),
            "sources": sorted(self.sources),
            "slots": sorted(self.slots),
        }


def _pick_kind(kind: str, tags: Set[str], components: Set[str]) -> str:
    if "character" in tags:
        return "character"
    if tags & CREATURE_TAGS or {"brain", "health", "combat"} <= components:
        return "creature"
    if tags & STRUCTURE_TAGS:
        return "structure"
    if tags & PLANT_TAGS or "pickable" in components or "crop" in components:
        return "plant"
    if tags & FX_TAGS:
        return "fx"
    if "inventoryitem" in components:
        return "item"
    return kind or "unknown"


def infer_tags(
    *,
    components: Iterable[str],
    tags: Iterable[str],
    sources: Iterable[str],
    kind_hint: Optional[str] = None,
) -> TagProfile:
    comps = {str(c).lower() for c in components if c}
    tgs = {str(t).lower() for t in tags if t}
    srcs = {str(s).lower() for s in sources if s}

    profile = TagProfile(kind=kind_hint or "unknown")
    profile.kind = _pick_kind(profile.kind, tgs, comps)

    for c in comps:
        beh = COMP_BEHAVIORS.get(c)
        if beh:
            profile.behaviors.add(beh)
        cat = COMP_CATEGORIES.get(c)
        if cat:
            profile.categories.add(cat)

    for t in tgs:
        cat = TAG_CATEGORIES.get(t)
        if cat:
            profile.categories.add(cat)

    if profile.kind == "item" and "food" in profile.categories and "edible" not in profile.behaviors:
        profile.categories.add("resource")

    profile.sources.update(srcs)
    return profile


def load_tag_overrides(path: Optional[str]) -> List[Dict[str, Any]]:
    if not path:
        return []
    try:
        import json

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rules = data.get("rules") or []
        return [r for r in rules if isinstance(r, dict)]
    except Exception:
        return []


def _apply_field(
    profile: TagProfile,
    field: str,
    *,
    add: Optional[Iterable[str]] = None,
    remove: Optional[Iterable[str]] = None,
    set_to: Optional[Iterable[str]] = None,
) -> None:
    if field == "kind":
        if set_to:
            profile.kind = str(list(set_to)[0])
        return

    target: Set[str]
    if field == "categories":
        target = profile.categories
    elif field == "behaviors":
        target = profile.behaviors
    elif field == "sources":
        target = profile.sources
    elif field == "slots":
        target = profile.slots
    else:
        return

    if set_to is not None:
        target.clear()
        for x in set_to:
            if x:
                target.add(str(x))
    if add:
        for x in add:
            if x:
                target.add(str(x))
    if remove:
        for x in remove:
            if x:
                target.discard(str(x))


def apply_overrides(item_id: str, profile: TagProfile, rules: List[Dict[str, Any]]) -> TagProfile:
    if not rules:
        return profile

    iid = str(item_id or "").strip()
    if not iid:
        return profile

    for rule in rules:
        pat = str(rule.get("match") or "").strip()
        if not pat:
            continue
        if pat != iid and not fnmatchcase(iid, pat):
            continue

        add = rule.get("add") or {}
        remove = rule.get("remove") or {}
        set_to = rule.get("set") or {}

        for field in ("kind", "categories", "behaviors", "sources", "slots"):
            _apply_field(
                profile,
                field,
                add=add.get(field),
                remove=remove.get(field),
                set_to=set_to.get(field),
            )
        break

    return profile

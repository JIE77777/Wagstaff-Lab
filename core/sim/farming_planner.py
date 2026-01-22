# -*- coding: utf-8 -*-
"""Farming mix planner (lightweight, data-driven)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import gcd
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class PlantProfile:
    plant_id: str
    consume: Tuple[float, float, float]
    restore: Tuple[bool, bool, bool]
    drink_rate: Optional[float]
    good_seasons: Tuple[str, ...]
    family_min: int


@dataclass(frozen=True)
class Pit:
    x: float
    y: float
    tile_x: int
    tile_y: int
    index: int


TILE_SIZE = 4.0
DEFAULT_FAMILY_RADIUS = 4.0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float))


def _as_float(value: Any) -> Optional[float]:
    if _is_number(value):
        return float(value)
    return None


def _normalize_season(season: Optional[str]) -> str:
    return str(season or "").strip().lower()


def _plant_family_min(plant: Dict[str, Any], tuning: Dict[str, Any]) -> int:
    val = plant.get("family_min_count")
    if not _is_number(val):
        val = tuning.get("FARM_PLANT_SAME_FAMILY_MIN")
    return int(val) if _is_number(val) else 0


def _plant_profile(plant_id: str, plant: Dict[str, Any], tuning: Dict[str, Any]) -> PlantProfile:
    consume = plant.get("nutrient_consumption") or [0, 0, 0]
    if not isinstance(consume, list) or len(consume) != 3:
        consume = [0, 0, 0]
    consume_vec = tuple(float(x) if _is_number(x) else 0.0 for x in consume)

    restore = plant.get("nutrient_restoration") or []
    if not isinstance(restore, list) or len(restore) != 3:
        restore = [c == 0 for c in consume_vec]
    restore_vec = tuple(bool(x) for x in restore)

    moisture = plant.get("moisture") if isinstance(plant.get("moisture"), dict) else {}
    drink_rate = _as_float(moisture.get("drink_rate"))

    seasons = plant.get("good_seasons") if isinstance(plant.get("good_seasons"), dict) else {}
    good = tuple(sorted([k for k, v in seasons.items() if v]))

    return PlantProfile(
        plant_id=str(plant_id),
        consume=consume_vec,
        restore=restore_vec,
        drink_rate=drink_rate,
        good_seasons=good,
        family_min=_plant_family_min(plant, tuning),
    )


def build_plant_profiles(
    farming_defs: Dict[str, Any],
    *,
    season: Optional[str] = None,
    include_ids: Optional[Sequence[str]] = None,
    allow_randomseed: bool = False,
) -> Dict[str, PlantProfile]:
    plants = farming_defs.get("plants") if isinstance(farming_defs, dict) else None
    plants = plants if isinstance(plants, dict) else {}
    tuning = farming_defs.get("tuning") if isinstance(farming_defs.get("tuning"), dict) else {}

    season_key = _normalize_season(season)
    include = {str(x).strip().lower() for x in (include_ids or []) if x}

    profiles: Dict[str, PlantProfile] = {}
    for pid, row in plants.items():
        if not isinstance(row, dict):
            continue
        if not allow_randomseed and row.get("is_randomseed"):
            continue
        plant_id = str(pid).strip()
        if include and plant_id not in include:
            continue
        if season_key:
            good_seasons = row.get("good_seasons") if isinstance(row.get("good_seasons"), dict) else {}
            if not good_seasons.get(season_key):
                continue
        profiles[plant_id] = _plant_profile(plant_id, row, tuning)
    return profiles


def _pit_grid_positions(count: int) -> List[float]:
    if count <= 0:
        return []
    step = 1.0 / (count + 1)
    return [step * (i + 1) for i in range(count)]


def _pit_pattern(mode: str) -> List[Tuple[float, float]]:
    key = str(mode or "").strip()
    if key not in {"8", "9", "10"}:
        key = "9"

    if key in {"8", "9"}:
        coords: List[Tuple[float, float]] = []
        pts = _pit_grid_positions(3)
        for r, y in enumerate(pts):
            for c, x in enumerate(pts):
                if key == "8" and r == 1 and c == 1:
                    continue
                coords.append((x, y))
        return coords

    # 2-3-2-3 rows, evenly distributed (not locked to a 4x4 grid).
    row_lengths = [2, 3, 2, 3]
    ys = _pit_grid_positions(len(row_lengths))
    coords = []
    for row_len, y in zip(row_lengths, ys):
        xs = _pit_grid_positions(row_len)
        for x in xs:
            coords.append((x, y))
    return coords


def build_pits(tile_shape: Tuple[int, int], mode: str) -> List[Pit]:
    tw, th = tile_shape
    if tw <= 0 or th <= 0:
        return []
    local = _pit_pattern(mode)
    pits: List[Pit] = []
    idx = 0
    for ty in range(th):
        for tx in range(tw):
            for x, y in local:
                pits.append(Pit(x=x + tx, y=y + ty, tile_x=tx, tile_y=ty, index=idx))
                idx += 1
    return pits


def _family_radius_tiles(tuning: Dict[str, Any]) -> float:
    val = tuning.get("FARM_PLANT_SAME_FAMILY_RADIUS")
    radius = float(val) if _is_number(val) else DEFAULT_FAMILY_RADIUS
    return max(0.01, radius / TILE_SIZE)


def _build_pit_graph(pits: Sequence[Pit], radius: float) -> List[List[int]]:
    if not pits:
        return []
    radius2 = radius * radius
    graph: List[List[int]] = [[] for _ in pits]
    for i, pit in enumerate(pits):
        for j in range(i + 1, len(pits)):
            other = pits[j]
            dx = pit.x - other.x
            dy = pit.y - other.y
            if dx * dx + dy * dy <= radius2 + 1e-9:
                graph[i].append(j)
                graph[j].append(i)
    return graph


def _pit_grid_indices(pits: Sequence[Pit]) -> Tuple[Dict[int, Tuple[int, int]], int, int]:
    if not pits:
        return {}, 0, 0
    xs = sorted({round(p.x, 4) for p in pits})
    ys = sorted({round(p.y, 4) for p in pits})
    x_index = {x: i for i, x in enumerate(xs)}
    y_index = {y: i for i, y in enumerate(ys)}
    mapping: Dict[int, Tuple[int, int]] = {}
    for idx, pit in enumerate(pits):
        mapping[idx] = (y_index[round(pit.y, 4)], x_index[round(pit.x, 4)])
    return mapping, len(ys), len(xs)


def _layout_fixed_363(
    pits: Sequence[Pit],
    plant_ids: Sequence[str],
    counts: Sequence[int],
    tile_shape: Optional[Tuple[int, int]],
    pit_mode: Optional[str],
) -> Optional[List[str]]:
    if pit_mode != "9":
        return None
    if len(plant_ids) != 2 or len(counts) != 2:
        return None
    if sorted(counts) != [6, 12]:
        return None
    if tile_shape not in {(1, 2), (2, 1)}:
        return None

    mapping, rows, cols = _pit_grid_indices(pits)
    if rows == 6 and cols == 3:
        row_assign = [0, 0, 1, 1, 0, 0]
        major_idx = 0 if counts[0] >= counts[1] else 1
        minor_idx = 1 - major_idx
        pick = [major_idx if v == 0 else minor_idx for v in row_assign]
        layout = [""] * len(pits)
        for idx, (r, _) in mapping.items():
            layout[idx] = plant_ids[pick[r]]
        return layout
    if rows == 3 and cols == 6:
        col_assign = [0, 0, 1, 1, 0, 0]
        major_idx = 0 if counts[0] >= counts[1] else 1
        minor_idx = 1 - major_idx
        pick = [major_idx if v == 0 else minor_idx for v in col_assign]
        layout = [""] * len(pits)
        for idx, (_, c) in mapping.items():
            layout[idx] = plant_ids[pick[c]]
        return layout
    return None


def _layout_row_major(pits: Sequence[Pit], plant_ids: Sequence[str], counts: Sequence[int]) -> List[str]:
    order = sorted(range(len(pits)), key=lambda i: (pits[i].y, pits[i].x, pits[i].index))
    layout = [""] * len(pits)
    pairs = sorted(zip(plant_ids, counts), key=lambda x: (-x[1], x[0]))
    cursor = 0
    for pid, count in pairs:
        for _ in range(count):
            if cursor >= len(order):
                break
            layout[order[cursor]] = pid
            cursor += 1
    return layout


def _layout_col_major(pits: Sequence[Pit], plant_ids: Sequence[str], counts: Sequence[int]) -> List[str]:
    order = sorted(range(len(pits)), key=lambda i: (pits[i].x, pits[i].y, pits[i].index))
    layout = [""] * len(pits)
    pairs = sorted(zip(plant_ids, counts), key=lambda x: (-x[1], x[0]))
    cursor = 0
    for pid, count in pairs:
        for _ in range(count):
            if cursor >= len(order):
                break
            layout[order[cursor]] = pid
            cursor += 1
    return layout


def _layout_clustered(
    pits: Sequence[Pit],
    graph: Sequence[Sequence[int]],
    plant_ids: Sequence[str],
    counts: Sequence[int],
    family_min: Dict[str, int],
) -> List[str]:
    total = len(pits)
    layout = [""] * total
    remaining = {pid: int(cnt) for pid, cnt in zip(plant_ids, counts)}
    order = sorted(
        plant_ids,
        key=lambda pid: (-remaining.get(pid, 0), -family_min.get(pid, 0), pid),
    )

    def dist2(a: int, b: int) -> float:
        dx = pits[a].x - pits[b].x
        dy = pits[a].y - pits[b].y
        return dx * dx + dy * dy

    for pid in order:
        need = remaining.get(pid, 0)
        if need <= 0:
            continue
        unassigned = [i for i, val in enumerate(layout) if not val]
        if not unassigned:
            break
        seed = max(unassigned, key=lambda i: (sum(1 for j in graph[i] if not layout[j]), -i))
        layout[seed] = pid
        need -= 1
        queue = deque([seed])
        while queue and need > 0:
            cur = queue.popleft()
            neighbors = [j for j in graph[cur] if not layout[j]]
            neighbors.sort(key=lambda j: (dist2(seed, j), j))
            for j in neighbors:
                if need <= 0:
                    break
                layout[j] = pid
                need -= 1
                queue.append(j)
        if need > 0:
            leftovers = [i for i, val in enumerate(layout) if not val]
            leftovers.sort(key=lambda j: (dist2(seed, j), j))
            for j in leftovers[:need]:
                layout[j] = pid
            need = 0
        remaining[pid] = 0
    return layout


def _largest_cluster_graph(layout: Sequence[str], graph: Sequence[Sequence[int]]) -> Dict[str, int]:
    if not layout or not graph:
        return {}
    seen = [False] * len(layout)
    best: Dict[str, int] = {}
    for idx, pid in enumerate(layout):
        if seen[idx] or not pid:
            continue
        stack = [idx]
        seen[idx] = True
        size = 0
        while stack:
            cur = stack.pop()
            size += 1
            for nxt in graph[cur]:
                if not seen[nxt] and layout[nxt] == pid:
                    seen[nxt] = True
                    stack.append(nxt)
        best[pid] = max(best.get(pid, 0), size)
    return best


def _score_layout(clusters: Dict[str, int], required: Dict[str, int]) -> Tuple[int, float, int]:
    ok_count = 0
    min_ratio = None
    total = 0
    for pid, need in required.items():
        have = clusters.get(pid, 0)
        total += have
        if have >= need:
            ok_count += 1
        ratio = have / max(1, need)
        if min_ratio is None or ratio < min_ratio:
            min_ratio = ratio
    return ok_count, float(min_ratio or 0.0), total


def _choose_pit_layout(
    pits: Sequence[Pit],
    graph: Sequence[Sequence[int]],
    plant_ids: Sequence[str],
    counts: Sequence[int],
    family_min: Dict[str, int],
    net_map: Dict[str, Tuple[float, float, float]],
    tile_shape: Optional[Tuple[int, int]],
    pit_mode: Optional[str],
    prefer_fixed_layout: bool,
) -> Tuple[List[str], Dict[str, int]]:
    layouts: List[Tuple[str, List[str]]] = []
    fixed = _layout_fixed_363(pits, plant_ids, counts, tile_shape, pit_mode)
    if fixed:
        layouts.append(("fixed", fixed))
    layouts += [
        ("row", _layout_row_major(pits, plant_ids, counts)),
        ("col", _layout_col_major(pits, plant_ids, counts)),
        ("cluster", _layout_clustered(pits, graph, plant_ids, counts, family_min)),
    ]
    best_layout: List[str] = []
    best_clusters: Dict[str, int] = {}
    best_score: Optional[Tuple[int, float, float, int, int, float, int]] = None
    fixed_entry: Optional[Tuple[List[str], Dict[str, int], Tuple[int, float, float, int, int, float, int]]] = None
    best_deficit: Optional[Tuple[int, float, float, int]] = None
    for tag, layout in layouts:
        clusters = _largest_cluster_graph(layout, graph)
        family_score = _score_layout(clusters, family_min)
        tile_summary, _ = _tile_nutrient_summary(pits, layout, net_map, include_tiles=False)
        deficit = tile_summary.get("deficit", {})
        score = (
            int(deficit.get("count") or 0),
            float(deficit.get("total") or 0.0),
            float(deficit.get("max") or 0.0),
            1 if tile_summary.get("mid_stage_risk") else 0,
            -family_score[0],
            -family_score[1],
            -family_score[2],
        )
        deficit_key = score[:4]
        if best_deficit is None or deficit_key < best_deficit:
            best_deficit = deficit_key
        if tag == "fixed":
            fixed_entry = (layout, clusters, score)
        if best_score is None or score < best_score:
            best_layout = layout
            best_clusters = clusters
            best_score = score
    if prefer_fixed_layout and fixed_entry and best_deficit is not None:
        fixed_layout, fixed_clusters, fixed_score = fixed_entry
        if fixed_score[:4] == best_deficit:
            return fixed_layout, fixed_clusters
    return best_layout, best_clusters


def _ratio_label(counts: Sequence[int]) -> str:
    if not counts:
        return ""
    g = 0
    for c in counts:
        g = gcd(g, int(c))
    if g <= 1:
        return ":".join(str(int(c)) for c in counts)
    return ":".join(str(int(c // g)) for c in counts)


def _partitions(total: int, mins: Sequence[int], parts: int) -> Iterable[List[int]]:
    if parts <= 0:
        return
    if parts == 1:
        if total >= mins[0]:
            yield [total]
        return
    first_min = mins[0]
    rest_min_sum = sum(mins[1:])
    for first in range(first_min, total - rest_min_sum + 1):
        for tail in _partitions(total - first, mins[1:], parts - 1):
            yield [first] + tail


def _consume_total(counts: Sequence[int], profiles: Sequence[PlantProfile]) -> Tuple[float, float, float]:
    totals = [0.0, 0.0, 0.0]
    for count, prof in zip(counts, profiles):
        for i in range(3):
            totals[i] += count * prof.consume[i]
    return totals[0], totals[1], totals[2]


def _net_delta(counts: Sequence[int], profiles: Sequence[PlantProfile]) -> Tuple[float, float, float]:
    totals = [0.0, 0.0, 0.0]
    for count, prof in zip(counts, profiles):
        consume = prof.consume
        restore = prof.restore
        total_consume = sum(consume)
        restore_count = sum(1 for r in restore if r)
        restore_each = total_consume / restore_count if restore_count else 0.0
        for i in range(3):
            delta = (-consume[i]) + (restore_each if restore[i] else 0.0)
            totals[i] += count * delta
    return totals[0], totals[1], totals[2]


def _plant_net_delta(profile: PlantProfile) -> Tuple[float, float, float]:
    consume = profile.consume
    restore = profile.restore
    total_consume = sum(consume)
    restore_count = sum(1 for r in restore if r)
    restore_each = total_consume / restore_count if restore_count else 0.0
    return tuple((-consume[i]) + (restore_each if restore[i] else 0.0) for i in range(3))


def _deficit_summary(net: Sequence[float]) -> Dict[str, Any]:
    channels: List[int] = []
    deficit_total = 0.0
    deficit_max = 0.0
    for idx, val in enumerate(net, start=1):
        if val < -1e-9:
            channels.append(idx)
            deficit_total += abs(val)
            deficit_max = max(deficit_max, abs(val))
    return {"count": len(channels), "total": deficit_total, "max": deficit_max, "channels": channels}


def _tile_nutrient_summary(
    pits: Sequence[Pit],
    layout: Sequence[str],
    net_map: Dict[str, Tuple[float, float, float]],
    *,
    include_tiles: bool = False,
) -> Tuple[Dict[str, Any], Optional[List[Dict[str, Any]]]]:
    tile_net: Dict[Tuple[int, int], List[float]] = {}
    for pit, pid in zip(pits, layout):
        if not pid:
            continue
        delta = net_map.get(pid)
        if not delta:
            continue
        key = (pit.tile_x, pit.tile_y)
        bucket = tile_net.setdefault(key, [0.0, 0.0, 0.0])
        for i in range(3):
            bucket[i] += delta[i]

    tiles_out: List[Dict[str, Any]] = []
    worst: Optional[Dict[str, Any]] = None
    worst_score: Optional[Tuple[int, float, float]] = None
    any_risk = False

    for (tx, ty), net in sorted(tile_net.items()):
        net_round = [round(net[0], 3), round(net[1], 3), round(net[2], 3)]
        net_cycle = [round(n * 4, 3) for n in net_round]
        deficit = _deficit_summary(net_cycle)
        mid_risk = any(n < -100 for n in net_cycle)
        any_risk = any_risk or mid_risk
        if include_tiles:
            tiles_out.append(
                {
                    "tile_x": tx,
                    "tile_y": ty,
                    "net": net_round,
                    "net_cycle": net_cycle,
                    "deficit": deficit,
                    "mid_stage_risk": mid_risk,
                }
            )
        score = (deficit["count"], deficit["total"], deficit["max"])
        if worst_score is None or score > worst_score:
            worst_score = score
            worst = {
                "net": net_round,
                "net_cycle": net_cycle,
                "deficit": deficit,
                "mid_stage_risk": mid_risk,
            }

    if worst is None:
        worst = {
            "net": [0.0, 0.0, 0.0],
            "net_cycle": [0.0, 0.0, 0.0],
            "deficit": _deficit_summary([0.0, 0.0, 0.0]),
            "mid_stage_risk": False,
        }
    worst["mid_stage_risk"] = any_risk
    return worst, (tiles_out if include_tiles else None)


def _water_summary(counts: Sequence[int], profiles: Sequence[PlantProfile], tuning: Dict[str, Any]) -> Dict[str, Any]:
    total = 0.0
    known = True
    for count, prof in zip(counts, profiles):
        if prof.drink_rate is None:
            known = False
            continue
        total += count * abs(prof.drink_rate)
    avg = total / sum(counts) if counts and known else None
    label = None
    low = _as_float(tuning.get("FARM_PLANT_DRINK_LOW"))
    med = _as_float(tuning.get("FARM_PLANT_DRINK_MED"))
    high = _as_float(tuning.get("FARM_PLANT_DRINK_HIGH"))
    if avg is not None and low is not None and med is not None and high is not None:
        low = abs(low)
        med = abs(med)
        high = abs(high)
        if avg <= (low + med) / 2:
            label = "low"
        elif avg <= (med + high) / 2:
            label = "med"
        else:
            label = "high"
    return {"total": total if known else None, "avg": avg, "label": label}


def _build_layout(
    *,
    width: int,
    height: int,
    plant_ids: Sequence[str],
    counts: Sequence[int],
) -> List[List[str]]:
    total = width * height
    if sum(counts) != total:
        return []
    order = sorted(zip(plant_ids, counts), key=lambda x: -x[1])
    rows: List[List[str]] = []
    remaining = {pid: cnt for pid, cnt in order}

    # Allocate full rows first for maximal clustering.
    for pid, _ in order:
        full_rows = remaining[pid] // width
        for _ in range(full_rows):
            rows.append([pid] * width)
        remaining[pid] -= full_rows * width

    # Fill leftover rows with contiguous segments.
    while len(rows) < height:
        row: List[str] = []
        for pid, _ in order:
            cnt = remaining.get(pid, 0)
            if cnt <= 0:
                continue
            take = min(cnt, width - len(row))
            row += [pid] * take
            remaining[pid] -= take
            if len(row) >= width:
                break
        if len(row) < width:
            # Fallback: pad with the most common plant.
            for pid, _ in order:
                while len(row) < width and remaining.get(pid, 0) > 0:
                    row.append(pid)
                    remaining[pid] -= 1
                if len(row) >= width:
                    break
        if not row:
            row = [order[0][0]] * width
        rows.append(row)
    return rows[:height]


def _largest_cluster(layout: List[List[str]]) -> Dict[str, int]:
    if not layout:
        return {}
    h = len(layout)
    w = len(layout[0])
    seen = [[False] * w for _ in range(h)]
    best: Dict[str, int] = {}

    for y in range(h):
        for x in range(w):
            if seen[y][x]:
                continue
            pid = layout[y][x]
            if not pid:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            size = 0
            while stack:
                cx, cy = stack.pop()
                size += 1
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and layout[ny][nx] == pid:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            best[pid] = max(best.get(pid, 0), size)
    return best


def _overcrowding_ok(
    layout: List[List[str]],
    *,
    tile_group: Optional[Tuple[int, int]],
    max_per_tile: Optional[int],
) -> Optional[bool]:
    if not layout or not tile_group or not max_per_tile:
        return None
    h = len(layout)
    w = len(layout[0])
    gx, gy = tile_group
    for y0 in range(0, h, gy):
        for x0 in range(0, w, gx):
            count = 0
            for yy in range(y0, min(y0 + gy, h)):
                for xx in range(x0, min(x0 + gx, w)):
                    if layout[yy][xx]:
                        count += 1
            if count > max_per_tile:
                return False
    return True


def _overcrowding_ok_pits(pits: Sequence[Pit], max_per_tile: Optional[int]) -> Optional[bool]:
    if not pits or not max_per_tile:
        return None
    counts: Dict[Tuple[int, int], int] = {}
    for pit in pits:
        key = (pit.tile_x, pit.tile_y)
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > max_per_tile:
            return False
    return True


def _plan_deficit_key(plan: Dict[str, Any]) -> Tuple[int, float, float, int, float, float]:
    nutrients = plan.get("nutrients") if isinstance(plan.get("nutrients"), dict) else {}
    overall = nutrients.get("overall") if isinstance(nutrients.get("overall"), dict) else nutrients
    overall_def = overall.get("deficit") if isinstance(overall.get("deficit"), dict) else {}
    tile = nutrients.get("tile") if isinstance(nutrients.get("tile"), dict) else {}
    tile_def = tile.get("deficit") if isinstance(tile.get("deficit"), dict) else {}
    return (
        int(overall_def.get("count") or 0),
        float(overall_def.get("total") or 0.0),
        float(overall_def.get("max") or 0.0),
        int(tile_def.get("count") or 0),
        float(tile_def.get("total") or 0.0),
        float(tile_def.get("max") or 0.0),
    )


def suggest_plans(
    farming_defs: Dict[str, Any],
    *,
    slots: int,
    season: Optional[str] = None,
    include_ids: Optional[Sequence[str]] = None,
    allow_randomseed: bool = False,
    max_kinds: int = 3,
    grid: Optional[Tuple[int, int]] = None,
    tile_shape: Optional[Tuple[int, int]] = None,
    pit_mode: Optional[str] = None,
    pits: Optional[Sequence[Pit]] = None,
    tile_group: Optional[Tuple[int, int]] = None,
    top_n: int = 12,
    prefer_fixed_layout: bool = False,
) -> List[Dict[str, Any]]:
    if slots <= 0:
        return []
    profiles = build_plant_profiles(
        farming_defs,
        season=season,
        include_ids=include_ids,
        allow_randomseed=allow_randomseed,
    )
    tuning = farming_defs.get("tuning") if isinstance(farming_defs.get("tuning"), dict) else {}
    max_per_tile = tuning.get("FARM_PANT_OVERCROWDING_MAX_PLANTS")
    max_per_tile = int(max_per_tile) if _is_number(max_per_tile) else None
    pit_layout = list(pits) if pits else None
    pit_mode_key = str(pit_mode or "").strip() or None
    if not pit_layout and tile_shape and pit_mode_key:
        pit_layout = build_pits(tile_shape, pit_mode_key)
    if pit_layout:
        slots = len(pit_layout)
    pit_graph = _build_pit_graph(pit_layout, _family_radius_tiles(tuning)) if pit_layout else None
    pit_overcrowding = _overcrowding_ok_pits(pit_layout, max_per_tile) if pit_layout else None
    net_map = {pid: _plant_net_delta(profile) for pid, profile in profiles.items()} if pit_layout else {}

    plant_ids = sorted(profiles.keys())
    if not plant_ids:
        return []

    plans: List[Dict[str, Any]] = []
    for kinds in range(1, max_kinds + 1):
        if len(plant_ids) < kinds:
            break
        for combo in _combinations(plant_ids, kinds):
            combo_profiles = [profiles[pid] for pid in combo]
            mins = [p.family_min for p in combo_profiles]
            for counts in _partitions(slots, mins, kinds):
                consume_totals = _consume_total(counts, combo_profiles)
                net = _net_delta(counts, combo_profiles)
                net_cycle = tuple(round(n * 4, 3) for n in net)
                deficit = _deficit_summary(net_cycle)
                mid_stage_risk = any(n < -100 for n in net_cycle)
                water = _water_summary(counts, combo_profiles, tuning)

                overall = {
                    "consume": [round(consume_totals[0], 3), round(consume_totals[1], 3), round(consume_totals[2], 3)],
                    "net": [round(net[0], 3), round(net[1], 3), round(net[2], 3)],
                    "net_cycle": list(net_cycle),
                    "deficit": deficit,
                    "mid_stage_risk": mid_stage_risk,
                }
                nutrients = dict(overall)
                family_min = {pid: profiles[pid].family_min for pid in combo}
                clusters: Dict[str, int] = {}
                layout_ok = None
                overcrowding_ok = None

                if pit_layout:
                    layout, clusters = _choose_pit_layout(
                        pit_layout,
                        pit_graph or [],
                        combo,
                        counts,
                        family_min,
                        net_map,
                        tile_shape,
                        pit_mode_key,
                        prefer_fixed_layout,
                    )
                    layout_ok = all(clusters.get(pid, 0) >= profiles[pid].family_min for pid in combo)
                    tile_summary, _ = _tile_nutrient_summary(pit_layout, layout, net_map, include_tiles=False)
                    nutrients["overall"] = overall
                    nutrients["tile"] = tile_summary
                    overcrowding_ok = pit_overcrowding

                plans.append(
                    {
                        "plants": list(combo),
                        "counts": {pid: int(c) for pid, c in zip(combo, counts)},
                        "ratio": _ratio_label(counts),
                        "slots": int(slots),
                        "nutrients": nutrients,
                        "water": water,
                        "family": {
                            "min_required": family_min,
                            "counts_ok": all(c >= profiles[pid].family_min for pid, c in zip(combo, counts)),
                            "largest_cluster": clusters or None,
                            "layout_ok": layout_ok,
                        },
                        "overcrowding_ok": overcrowding_ok,
                        "layout": None,
                    }
                )

    plans.sort(key=_plan_deficit_key)
    if top_n and top_n > 0:
        plans = plans[:top_n]

    if pit_layout:
        tile_w = tile_shape[0] if tile_shape else max((p.tile_x for p in pit_layout), default=-1) + 1
        tile_h = tile_shape[1] if tile_shape else max((p.tile_y for p in pit_layout), default=-1) + 1
        holes_per_tile = None
        if tile_w > 0 and tile_h > 0:
            holes_per_tile = len(pit_layout) // (tile_w * tile_h)
        for plan in plans:
            combo = plan["plants"]
            counts = [plan["counts"].get(pid, 0) for pid in combo]
            family_min = {pid: profiles[pid].family_min for pid in combo}
            layout, clusters = _choose_pit_layout(
                pit_layout,
                pit_graph or [],
                combo,
                counts,
                family_min,
                net_map,
                tile_shape,
                pit_mode_key,
                prefer_fixed_layout,
            )
            layout_ok = all(clusters.get(pid, 0) >= profiles[pid].family_min for pid in combo)
            tile_summary, tiles = _tile_nutrient_summary(pit_layout, layout, net_map, include_tiles=True)
            plan["family"]["largest_cluster"] = clusters or None
            plan["family"]["layout_ok"] = layout_ok
            plan["overcrowding_ok"] = pit_overcrowding
            nutrients = plan.get("nutrients") if isinstance(plan.get("nutrients"), dict) else {}
            if isinstance(nutrients, dict):
                if "overall" not in nutrients:
                    nutrients["overall"] = {
                        "consume": nutrients.get("consume"),
                        "net": nutrients.get("net"),
                        "net_cycle": nutrients.get("net_cycle"),
                        "deficit": nutrients.get("deficit"),
                        "mid_stage_risk": nutrients.get("mid_stage_risk"),
                    }
                nutrients["tile"] = tile_summary
                if tiles is not None:
                    nutrients["tiles"] = tiles
            plan["layout"] = {
                "mode": "pits",
                "pattern": pit_mode_key,
                "holes_per_tile": holes_per_tile,
                "tile": {"width": tile_w, "height": tile_h},
                "unit": "tile",
                "pits": [
                    {
                        "x": round(pit.x, 3),
                        "y": round(pit.y, 3),
                        "tile_x": pit.tile_x,
                        "tile_y": pit.tile_y,
                        "plant": pid,
                    }
                    for pit, pid in zip(pit_layout, layout)
                ],
            }
    elif grid:
        for plan in plans:
            combo = plan["plants"]
            counts = [plan["counts"].get(pid, 0) for pid in combo]
            layout = _build_layout(width=grid[0], height=grid[1], plant_ids=combo, counts=counts)
            clusters = _largest_cluster(layout)
            layout_ok = all(clusters.get(pid, 0) >= profiles[pid].family_min for pid in combo)
            plan["family"]["largest_cluster"] = clusters or None
            plan["family"]["layout_ok"] = layout_ok
            plan["overcrowding_ok"] = _overcrowding_ok(layout, tile_group=tile_group, max_per_tile=max_per_tile)
            plan["layout"] = {
                "mode": "grid",
                "width": grid[0],
                "height": grid[1],
                "rows": layout,
            }

    return plans


def _combinations(items: Sequence[str], k: int) -> Iterable[Tuple[str, ...]]:
    if k == 0:
        yield ()
        return
    if k > len(items):
        return
    for i in range(len(items) - k + 1):
        head = items[i]
        for tail in _combinations(items[i + 1 :], k - 1):
            yield (head,) + tail

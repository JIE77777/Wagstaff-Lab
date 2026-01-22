# -*- coding: utf-8 -*-
"""Typed records for worldgen parsing."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class SettingsPresetRecord(TypedDict, total=False):
    type: str
    id: str
    name: str
    desc: str
    location: str
    version: int
    overrides: Dict[str, Any]
    playstyle: Optional[str]
    raw: Dict[str, Any]


class WorldgenPresetRecord(TypedDict, total=False):
    type: str
    id: str
    name: str
    desc: str
    location: str
    version: int
    task_set: Optional[str]
    start_location: Optional[str]
    required_setpieces: List[str]
    random_set_pieces: List[str]
    numrandom_set_pieces: Optional[int]
    overrides: Dict[str, Any]
    raw: Dict[str, Any]


class TaskSetRecord(TypedDict, total=False):
    type: str
    id: str
    name: str
    location: str
    tasks: List[str]
    optionaltasks: List[str]
    numoptionaltasks: Optional[int]
    valid_start_tasks: List[str]
    required_prefabs: List[str]
    set_pieces: Dict[str, Any]
    ocean_population: List[str]
    raw: Dict[str, Any]


class TaskRecord(TypedDict, total=False):
    type: str
    id: str
    locks: List[str]
    keys_given: List[str]
    room_choices: Dict[str, Any]
    room_bg: Optional[str]
    background_room: Optional[str]
    colour: Dict[str, Any]
    raw: Dict[str, Any]


class RoomRecord(TypedDict, total=False):
    type: str
    id: str
    value: Optional[str]
    tags: List[str]
    contents: Dict[str, Any]
    raw: Dict[str, Any]


class LayoutRecord(TypedDict, total=False):
    type: str
    id: str
    source: Optional[str]
    layout_type: Optional[str]
    defs: Dict[str, Any]
    layout: Dict[str, Any]
    count: Dict[str, Any]
    scale: Optional[float]
    add_topology: Dict[str, Any]
    areas: Dict[str, Any]
    raw: Dict[str, Any]


class StartLocationRecord(TypedDict, total=False):
    type: str
    id: str
    name: Optional[str]
    location: Optional[str]
    start_setpeice: Optional[str]
    start_node: Any
    raw: Dict[str, Any]


class TopologyGraph(TypedDict, total=False):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    meta: Dict[str, Any]

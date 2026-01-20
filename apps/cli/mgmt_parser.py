#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared parser helpers for management docs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Task:
    key: str
    desc: str


@dataclass
class Milestone:
    key: str
    title: str
    status: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def extract_section(text: str, heading_prefix: str) -> str:
    lines = text.splitlines()
    out: List[str] = []
    in_section = False
    for line in lines:
        if line.startswith(heading_prefix):
            if in_section:
                break
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            out.append(line)
    return "\n".join(out)


def normalize_status(raw: str) -> str:
    r = (raw or "").strip().lower()
    if not r:
        return "unknown"
    if any(x in r for x in ("完成", "done", "complete")):
        return "done"
    if any(x in r for x in ("进行中", "in progress", "ongoing")):
        return "in_progress"
    if any(x in r for x in ("规划中", "planned", "plan")):
        return "planned"
    return r


def parse_tasks(text: str) -> List[Task]:
    section = extract_section(text, "## 4.")
    tasks: List[Task] = []
    for line in section.splitlines():
        m = re.match(r"\s*-\s*\*\*(T-\d+)\*\*[：:]?\s*(.+)$", line.strip())
        if not m:
            continue
        key = m.group(1).strip()
        desc = m.group(2).strip()
        tasks.append(Task(key=key, desc=desc))
    return tasks


def parse_milestones(text: str) -> List[Milestone]:
    section = extract_section(text, "## 2.")
    out: List[Milestone] = []
    for line in section.splitlines():
        m = re.match(r"\s*-\s*\*\*(M[0-9.]+)\s+([^*]+)\*\*（?([^）)]*)", line.strip())
        if not m:
            continue
        key = m.group(1).strip()
        title = m.group(2).strip()
        status = normalize_status(m.group(3).strip())
        out.append(Milestone(key=key, title=title, status=status))
    return out

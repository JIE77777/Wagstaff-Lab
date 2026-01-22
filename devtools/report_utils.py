#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for report + portal hubs."""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def file_info(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"exists": False, "size": 0, "mtime": None}
    stat = path.stat()
    return {"exists": True, "size": int(stat.st_size), "mtime": stat.st_mtime}


def web_path(path: Path, base_dir: Path) -> Optional[str]:
    try:
        rel = path.resolve().relative_to(base_dir.resolve())
    except Exception:
        return None
    return str(rel).replace(os.sep, "/")


def summarize_quality_gate(path: Path) -> Dict[str, Any]:
    doc = load_json(path)
    issues = doc.get("issues") if isinstance(doc, dict) else None
    issues = issues if isinstance(issues, list) else []
    counts = {"fail": 0, "warn": 0}
    for row in issues:
        level = row.get("level") if isinstance(row, dict) else None
        if level in counts:
            counts[level] += 1
    summary = doc.get("summary") if isinstance(doc, dict) else {}
    return {
        "issues_total": len(issues),
        "issues_fail": counts["fail"],
        "issues_warn": counts["warn"],
        "catalog_items_total": (summary or {}).get("catalog_items_total"),
        "catalog_assets_total": (summary or {}).get("catalog_assets_total"),
        "mechanism_prefabs_total": (summary or {}).get("mechanism_prefabs_total"),
    }


def summarize_catalog_quality(path: Path) -> Dict[str, Any]:
    doc = load_json(path)
    counts = doc.get("counts") if isinstance(doc, dict) else {}
    items_total = int((counts or {}).get("items_total") or 0)
    items_with_stats = int((counts or {}).get("items_with_stats") or 0)
    ratio = (items_with_stats / items_total) if items_total else 0.0
    return {
        "items_total": items_total,
        "items_with_stats": items_with_stats,
        "stats_ratio": f"{ratio:.1%}",
    }


def summarize_static_mechanics(path: Path) -> Dict[str, Any]:
    doc = load_json(path)
    summary = doc.get("summary") if isinstance(doc, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    def _fmt(val: Any) -> Optional[str]:
        if isinstance(val, (int, float)):
            return f"{float(val):.1%}" if 0 <= val <= 1 else str(val)
        return None
    return {
        "components_total": summary.get("components_total"),
        "coverage_c0": _fmt(summary.get("coverage_c0")),
        "coverage_c1": _fmt(summary.get("coverage_c1")),
        "coverage_c2": _fmt(summary.get("coverage_c2")),
    }


def summarize_index_manifest(path: Path) -> Dict[str, Any]:
    doc = load_json(path)
    artifacts = doc.get("artifacts") if isinstance(doc, dict) else None
    artifacts = artifacts if isinstance(artifacts, list) else []
    missing = 0
    for row in artifacts:
        if not isinstance(row, dict):
            continue
        file_sig = row.get("file") if isinstance(row, dict) else None
        exists = file_sig.get("exists") if isinstance(file_sig, dict) else None
        if exists is False:
            missing += 1
    return {
        "artifacts_total": len(artifacts),
        "artifacts_missing": missing,
        "warnings": len(doc.get("warnings") or []),
    }


def render_markdown(md_text: str) -> str:
    lines = md_text.splitlines()
    out: List[str] = []
    in_code = False
    in_list = False
    para: List[str] = []

    def flush_para() -> None:
        if not para:
            return
        out.append(f"<p>{_render_inline(' '.join(para))}</p>")
        para.clear()

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_para()
            close_list()
            if not in_code:
                lang = stripped[3:].strip()
                class_attr = f' class="language-{_slug(lang)}"' if lang else ""
                out.append(f"<pre><code{class_attr}>")
                in_code = True
            else:
                out.append("</code></pre>")
                in_code = False
            i += 1
            continue

        if in_code:
            out.append(html.escape(line))
            i += 1
            continue

        table = _parse_table(lines, i)
        if table is not None:
            flush_para()
            close_list()
            i, headers, rows = table
            out.append("<table>")
            out.append("<thead><tr>" + "".join(f"<th>{_render_inline(h)}</th>" for h in headers) + "</tr></thead>")
            out.append("<tbody>")
            for row in rows:
                out.append("<tr>" + "".join(f"<td>{_render_inline(cell)}</td>" for cell in row) + "</tr>")
            out.append("</tbody></table>")
            continue

        if stripped.startswith("#"):
            flush_para()
            close_list()
            level = len(stripped) - len(stripped.lstrip("#"))
            level = max(1, min(level, 6))
            text = stripped[level:].strip()
            out.append(f"<h{level}>{_render_inline(text)}</h{level}>")
            i += 1
            continue

        list_match = re.match(r"^[-*]\s+(.*)$", stripped)
        if list_match:
            flush_para()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_render_inline(list_match.group(1))}</li>")
            i += 1
            continue

        if stripped == "":
            flush_para()
            close_list()
            i += 1
            continue

        para.append(stripped)
        i += 1

    flush_para()
    close_list()
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def _render_inline(text: str) -> str:
    escaped = html.escape(text)
    code_spans: List[Tuple[str, str]] = []

    def _code_repl(match: re.Match[str]) -> str:
        key = f"@@CODE{len(code_spans)}@@"
        code_spans.append((key, f"<code>{match.group(1)}</code>"))
        return key

    escaped = re.sub(r"`([^`]+)`", _code_repl, escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)

    for key, val in code_spans:
        escaped = escaped.replace(key, val)
    return escaped


def _split_table_row(line: str) -> List[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _is_table_sep(line: str) -> bool:
    if "|" not in line:
        return False
    tokens = _split_table_row(line)
    if not tokens:
        return False
    for tok in tokens:
        if not re.fullmatch(r":?-{3,}:?", tok):
            return False
    return True


def _parse_table(lines: List[str], start: int) -> Optional[Tuple[int, List[str], List[List[str]]]]:
    if start + 1 >= len(lines):
        return None
    header = lines[start]
    sep = lines[start + 1]
    if "|" not in header or not _is_table_sep(sep):
        return None
    headers = _split_table_row(header)
    rows: List[List[str]] = []
    idx = start + 2
    while idx < len(lines):
        row_line = lines[idx]
        if not row_line.strip() or "|" not in row_line:
            break
        rows.append(_split_table_row(row_line))
        idx += 1
    return idx, headers, rows


def _slug(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-z0-9_-]+", "-", text.strip().lower())

# -*- coding: utf-8 -*-
"""CLI i18n helpers (isolated from app/web layers)."""

from __future__ import annotations

import os
from typing import Dict, Optional


DEFAULT_LANG = "zh"
LANG_ALIASES = {
    "zh-cn": "zh",
    "zh_cn": "zh",
    "zh-hans": "zh",
    "en-us": "en",
    "en_us": "en",
}

TEXTS: Dict[str, Dict[str, str]] = {
    "en": {
        "mgmt.doc_label": "Management Doc",
        "mgmt.milestones_title": "Milestones",
        "mgmt.tasks_title": "Active Tasks",
        "mgmt.key": "Key",
        "mgmt.title": "Title",
        "mgmt.milestones_count": "milestones",
        "mgmt.tasks_count": "tasks",
        "mgmt.no_changes": "No changes.",
        "mgmt.pending_update": "Pending TASKS_TODO update (dry-run):",
        "mgmt.tasks_updated": "TASKS_TODO updated.",
        "mgmt.doc_missing": "Management doc not found: {path}",
        "mgmt.devguide_missing": "DEV_GUIDE missing: {path}",
        "mgmt.devguide_check": "DEV_GUIDE Check",
        "mgmt.check": "Check",
        "mgmt.status": "Status",
        "mgmt.details": "Details",
        "mgmt.devguide_meta": "DEV_GUIDE meta",
        "mgmt.devguide_age": "DEV_GUIDE age",
        "mgmt.readme_link": "README mentions DEV_GUIDE",
        "mgmt.mgmt_doc": "PROJECT_MANAGEMENT exists",
        "mgmt.devguide_meta_hint": "DEV_GUIDE_META block",
        "mgmt.devguide_age_hint": "mtime age {age}",
        "mgmt.readme_link_hint": "README mentions DEV_GUIDE",
        "mgmt.mgmt_doc_hint": "{path}",
        "status.done": "done",
        "status.in_progress": "in_progress",
        "status.planned": "planned",
        "status.unknown": "unknown",
        "status.ok": "OK",
        "status.warn": "WARN",
    },
    "zh": {
        "mgmt.doc_label": "管理文档",
        "mgmt.milestones_title": "里程碑",
        "mgmt.tasks_title": "当前任务",
        "mgmt.key": "编号",
        "mgmt.title": "标题",
        "mgmt.milestones_count": "里程碑",
        "mgmt.tasks_count": "任务",
        "mgmt.no_changes": "无变更。",
        "mgmt.pending_update": "待更新 TASKS_TODO（仅预览）：",
        "mgmt.tasks_updated": "TASKS_TODO 已更新。",
        "mgmt.doc_missing": "管理文档缺失：{path}",
        "mgmt.devguide_missing": "DEV_GUIDE 缺失：{path}",
        "mgmt.devguide_check": "DEV_GUIDE 检查",
        "mgmt.check": "检查项",
        "mgmt.status": "状态",
        "mgmt.details": "说明",
        "mgmt.devguide_meta": "DEV_GUIDE 元信息",
        "mgmt.devguide_age": "DEV_GUIDE 更新周期",
        "mgmt.readme_link": "README 引用 DEV_GUIDE",
        "mgmt.mgmt_doc": "PROJECT_MANAGEMENT 存在",
        "mgmt.devguide_meta_hint": "DEV_GUIDE_META 区块",
        "mgmt.devguide_age_hint": "更新时间 {age}",
        "mgmt.readme_link_hint": "README 是否引用 DEV_GUIDE",
        "mgmt.mgmt_doc_hint": "{path}",
        "status.done": "完成",
        "status.in_progress": "进行中",
        "status.planned": "规划中",
        "status.unknown": "未知",
        "status.ok": "正常",
        "status.warn": "注意",
    },
}


def resolve_lang(lang: Optional[str] = None) -> str:
    raw = (lang or os.environ.get("WAGSTAFF_LANG") or "").strip().lower().replace("_", "-")
    if raw in LANG_ALIASES:
        raw = LANG_ALIASES[raw]
    return raw if raw in TEXTS else DEFAULT_LANG


def t(key: str, lang: str, default: Optional[str] = None) -> str:
    if not lang:
        lang = DEFAULT_LANG
    return (
        TEXTS.get(lang, {}).get(key)
        or (default or TEXTS.get(DEFAULT_LANG, {}).get(key))
        or key
    )


def status_label(status: str, lang: str) -> str:
    return t(f"status.{status}", lang, status or "unknown")

# -*- coding: utf-8 -*-
"""Interactive server UI (menu-based)."""

from __future__ import annotations

import os
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from apps.server import manager
from apps.server.config import ServerConfig


LANG_DEFAULT = "zh"


def _supports_color() -> bool:
    if not sys.stdout.isatty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    term = os.environ.get("TERM", "")
    if term in ("", "dumb"):
        return False
    return True


class _Palette:
    def __init__(self, enabled: bool) -> None:
        if not enabled:
            self.reset = ""
            self.bold = ""
            self.dim = ""
            self.red = ""
            self.green = ""
            self.yellow = ""
            self.blue = ""
            self.cyan = ""
            self.white = ""
            self.black = ""
            self.bg_red = ""
            self.bg_green = ""
            self.bg_yellow = ""
            self.bg_blue = ""
            self.bg_cyan = ""
            return
        self.reset = "\033[0m"
        self.bold = "\033[1m"
        self.dim = "\033[2m"
        self.red = "\033[31m"
        self.green = "\033[32m"
        self.yellow = "\033[33m"
        self.blue = "\033[34m"
        self.cyan = "\033[36m"
        self.white = "\033[97m"
        self.black = "\033[30m"
        self.bg_red = "\033[41m"
        self.bg_green = "\033[42m"
        self.bg_yellow = "\033[43m"
        self.bg_blue = "\033[44m"
        self.bg_cyan = "\033[46m"


PALETTE = _Palette(_supports_color())


TEXT = {
    "title": {"zh": "Wagstaff-Lab 控制台", "en": "Wagstaff-Lab Control Center"},
    "box_status": {"zh": "状态监控", "en": "Status Monitor"},
    "box_paths": {"zh": "路径配置", "en": "Paths & Config"},
    "box_menu": {"zh": "功能菜单", "en": "Menu"},
    "status": {"zh": "状态", "en": "Status"},
    "master": {"zh": "地面", "en": "Master"},
    "caves": {"zh": "洞穴", "en": "Caves"},
    "running": {"zh": "运行中", "en": "RUNNING"},
    "stopped": {"zh": "未运行", "en": "STOPPED"},
    "unknown": {"zh": "未知", "en": "UNKNOWN"},
    "checks": {"zh": "检查", "en": "Checks"},
    "logs": {"zh": "日志", "en": "Logs"},
    "backups": {"zh": "备份", "en": "Backups"},
    "cluster_label": {"zh": "存档簇", "en": "Cluster"},
    "dst_label": {"zh": "DST目录", "en": "DST"},
    "klei_label": {"zh": "Klei目录", "en": "Klei"},
    "steam_label": {"zh": "Steam目录", "en": "Steam"},
    "backup_label": {"zh": "备份目录", "en": "Backup Dir"},
    "section_ops": {"zh": "运维管理", "en": "Server Ops"},
    "section_data": {"zh": "数据与工具", "en": "Data & Tools"},
    "menu_start": {"zh": "🚀 启动服务器", "en": "🚀 Start server"},
    "menu_stop": {"zh": "🛑 停止服务器", "en": "🛑 Stop server"},
    "menu_restart": {"zh": "🔄 重启服务器", "en": "🔄 Restart server"},
    "menu_update": {"zh": "⬇️ 更新版本", "en": "⬇️ Update game"},
    "menu_backup": {"zh": "💾 创建备份", "en": "💾 Backup"},
    "menu_restore": {"zh": "⏪ 恢复存档", "en": "⏪ Restore"},
    "menu_logs": {"zh": "📜 查看日志", "en": "📜 View logs"},
    "menu_console": {"zh": "🎮 控制台指令", "en": "🎮 Console shortcuts"},
    "menu_cmd": {"zh": "📡 发送指令", "en": "📡 Send command"},
    "menu_lang": {"zh": "🌐 切换语言", "en": "🌐 Language"},
    "menu_quit": {"zh": "🚪 退出", "en": "🚪 Quit"},
    "tip": {"zh": "回车刷新，或输入关键字/数字。", "en": "Press Enter to refresh; type keyword or number."},
    "prompt_select": {"zh": "选项", "en": "Select"},
    "prompt_shard": {"zh": "分片 (地面/洞穴)", "en": "Shard (master/caves)"},
    "prompt_timeout": {"zh": "超时时间 (秒)", "en": "Timeout (seconds)"},
    "prompt_force": {"zh": "超时后强制退出", "en": "Force kill if timeout"},
    "prompt_update_continue": {"zh": "服务器似乎在运行，继续更新？", "en": "Server appears running. Continue update"},
    "prompt_update_restart": {"zh": "重启前更新", "en": "Update before restart"},
    "prompt_start_caves": {"zh": "启动洞穴分片", "en": "Start caves shard"},
    "prompt_follow": {"zh": "持续跟随", "en": "Follow"},
    "prompt_lines": {"zh": "行数", "en": "Lines"},
    "prompt_backup_out": {"zh": "备份输出路径 (留空自动)", "en": "Backup output path (blank for auto)"},
    "prompt_restore_choose": {"zh": "选择备份序号/路径 (空取消, L=最新)", "en": "Choose backup index/path (blank to cancel, L=latest)"},
    "prompt_restore_start": {"zh": "恢复后启动服务器", "en": "Start server after restore"},
    "prompt_send_cmd": {"zh": "控制台指令", "en": "Console command"},
    "prompt_announce": {"zh": "公告内容", "en": "Announcement"},
    "prompt_regen_confirm": {"zh": "输入 YES 确认", "en": "Type YES to confirm"},
    "prompt_rollback_days": {"zh": "回滚天数", "en": "Rollback days"},
    "console_title": {"zh": "控制台指令中心", "en": "Console Command Center"},
    "console_save": {"zh": "💾 立即保存 (c_save)", "en": "💾 Save now (c_save)"},
    "console_rollback": {"zh": "⏪ 回滚 (c_rollback)", "en": "⏪ Rollback (c_rollback)"},
    "console_announce": {"zh": "📢 发送公告 (c_announce)", "en": "📢 Announce (c_announce)"},
    "console_regen": {"zh": "☠️  重置世界 (c_regenerateworld)", "en": "☠️  Regenerate world (c_regenerateworld)"},
    "console_players": {"zh": "👥 列出玩家 (c_listallplayers)", "en": "👥 List players (c_listallplayers)"},
    "console_back": {"zh": "🔙 返回", "en": "🔙 Back"},
    "msg_screen_missing": {"zh": "未找到 screen，请先安装。", "en": "screen not found. Install screen to manage DST sessions."},
    "msg_server_running": {"zh": "服务器已在运行。", "en": "Server already running."},
    "msg_server_not_running": {"zh": "服务器未运行。", "en": "Server not running."},
    "msg_steam_missing": {"zh": "未配置 SteamCMD (设置 STEAMCMD_DIR)。", "en": "SteamCMD not configured (set STEAMCMD_DIR)."},
    "msg_cluster_missing": {"zh": "存档目录不存在", "en": "Cluster dir missing"},
    "msg_backup_none": {"zh": "暂无备份。", "en": "No backups found."},
    "msg_backup_index_oob": {"zh": "备份序号超出范围。", "en": "Backup index out of range."},
    "msg_backup_not_found": {"zh": "备份不存在", "en": "Backup not found"},
    "msg_log_not_found": {"zh": "日志不存在", "en": "Log not found"},
    "msg_unknown": {"zh": "无效选项。", "en": "Unknown option."},
    "msg_enter_continue": {"zh": "按回车继续...", "en": "Press Enter to continue..."},
    "msg_enter_number": {"zh": "请输入数字。", "en": "Please enter a number."},
    "msg_enter_yn": {"zh": "请输入 y 或 n。", "en": "Please enter y or n."},
    "msg_restore_overwrite": {"zh": "恢复将覆盖以下目录：", "en": "Restore will overwrite:"},
    "msg_restore_confirm": {"zh": "输入 DELETE <path> 确认", "en": "Type DELETE <path> to confirm"},
    "backups_header": {"zh": "备份列表 (最新在前):", "en": "Backups (newest first):"},
    "backups_more": {"zh": "还有 {count} 个未显示", "en": "{count} more not shown"},
    "backup_latest": {"zh": "最新", "en": "latest"},
    "flag_ok": {"zh": "OK", "en": "OK"},
    "flag_missing": {"zh": "缺失", "en": "MISSING"},
    "flag_na": {"zh": "N/A", "en": "N/A"},
    "file_missing": {"zh": "缺失", "en": "missing"},
    "file_unknown": {"zh": "未知", "en": "unknown"},
    "result_ok": {"zh": "结果: 成功", "en": "Result: OK"},
    "result_exit": {"zh": "结果: exit={code}", "en": "Result: exit={code}"},
    "msg_interrupted": {"zh": "已中断。", "en": "Interrupted."},
}


def _t(key: str, lang: str) -> str:
    entry = TEXT.get(key) or {}
    if lang in entry:
        return entry[lang]
    if "en" in entry:
        return entry["en"]
    return key


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text or "")


def _display_width(text: str) -> int:
    width = 0
    for ch in _strip_ansi(text):
        if unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def _pad(text: str, width: int) -> str:
    padding = width - _display_width(text)
    if padding <= 0:
        return text
    return text + (" " * padding)


def _two_col(
    items: list[str],
    width: int,
    *,
    sep_text: str = "  │  ",
    min_col_width: int = 18,
) -> list[str]:
    sep = _paint(sep_text, PALETTE.dim)
    col_width = max(min_col_width, (width - _display_width(sep_text)) // 2)
    lines: list[str] = []
    for i in range(0, len(items), 2):
        left = items[i]
        right = items[i + 1] if i + 1 < len(items) else ""
        if right:
            line = _pad(left, col_width) + sep + right
        else:
            line = left
        lines.append(line.rstrip())
    return lines


def _lang_label(lang: str) -> str:
    return "中文" if lang == "zh" else "EN"


def _compose_title_line(width: int, lang: str, *, context: str = "") -> str:
    left = f"🦅 {_t('title', lang)}"
    ctx = str(context or "").strip()
    if ctx:
        left = f"{left} {_paint('·', PALETTE.dim)} {_paint(ctx, PALETTE.dim)}"
    right = f"🌐 {_lang_label(lang)}"
    gap = width - _display_width(left) - _display_width(right)
    if gap < 2:
        return left
    return left + (" " * gap) + right


def _kv_line(label: str, value: str, label_width: int) -> str:
    return f"{_pad(label, label_width)}: {value}"


def _truncate(text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if _display_width(text) <= max_width:
        return text
    if max_width == 1:
        return "…"

    limit = max_width - 1
    out: list[str] = []
    w = 0
    i = 0
    n = len(text)
    while i < n and w < limit:
        if text[i] == "\x1b" and i + 1 < n and text[i + 1] == "[":
            end = text.find("m", i)
            if end == -1:
                break
            out.append(text[i : end + 1])
            i = end + 1
            continue

        ch = text[i]
        i += 1
        if unicodedata.combining(ch):
            out.append(ch)
            continue
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if w + cw > limit:
            break
        out.append(ch)
        w += cw

    out.append("…")
    if PALETTE.reset:
        out.append(PALETTE.reset)
    return "".join(out)


def _divider_line(inner_width: int) -> str:
    return "─" * max(0, inner_width)


def _shorten_path(text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if _display_width(text) <= max_width:
        return text
    if max_width == 1:
        return "…"

    home = str(Path.home())
    if home and text.startswith(home):
        suffix = text[len(home) :]
        if not suffix or suffix.startswith(("/", "\\")):
            text = "~" + suffix

    sep = "/" if "/" in text else ("\\" if "\\" in text else os.sep)
    parts = [part for part in re.split(r"[\\/]+", text) if part]
    if not parts:
        return _truncate(text, max_width)

    has_tilde = text.startswith("~")
    tail = parts[-1]
    idx = len(parts) - 2
    while idx >= 0:
        candidate = parts[idx] + sep + tail
        if _display_width(f"…{sep}{candidate}") > max_width:
            break
        tail = candidate
        idx -= 1

    out = f"…{sep}{tail}"
    if has_tilde and not tail.startswith("~"):
        prefixed = f"~{sep}{out}"
        if _display_width(prefixed) <= max_width:
            out = prefixed
    if _display_width(out) > max_width:
        return _truncate(out, max_width)
    return out


def _fit_value(value: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    raw = str(value or "")
    if "/" in raw or "\\" in raw:
        return _shorten_path(raw, max_width)
    return _truncate(raw, max_width)


def _box_lines(title: str, lines: list[str], width: int, *, dim_body: bool = False) -> list[str]:
    width = max(40, width)
    inner = width - 2

    title_text = f" {title} "
    title_text = _truncate(title_text, inner)
    title_w = _display_width(title_text)
    top = "┌" + title_text + ("─" * max(0, inner - title_w)) + "┐"
    bottom = "└" + ("─" * inner) + "┘"

    border_style = (PALETTE.cyan + PALETTE.dim) if PALETTE.cyan else ""
    title_style = PALETTE.bold
    body_style = PALETTE.dim if dim_body else ""

    out: list[str] = []
    out.append(_paint(top, border_style, title_style))
    for raw in lines:
        line = _truncate(raw, inner)
        line = _pad(line, inner)
        if body_style:
            line = _paint(line, body_style)
        out.append(_paint("│", border_style) + line + _paint("│", border_style))
    out.append(_paint(bottom, border_style))
    return out


def _box(title: str, lines: list[str], width: int, *, dim_body: bool = False) -> None:
    for line in _box_lines(title, lines, width, dim_body=dim_body):
        print(line)


def _pill(text: str, *, fg: str, bg: str, fallback: str) -> str:
    if not PALETTE.reset:
        return fallback
    return _paint(f" {text} ", PALETTE.bold, fg, bg)


def _paint(text: str, *styles: str) -> str:
    if not any(styles):
        return text
    return "".join(styles) + text + PALETTE.reset


def _term_width(default: int = 80) -> int:
    try:
        width = shutil.get_terminal_size((default, 20)).columns
    except Exception:
        return default
    return max(60, min(120, width))


def _vstack(blocks: list[list[str]], *, gap: int = 1) -> list[str]:
    out: list[str] = []
    for idx, block in enumerate(blocks):
        if idx and gap:
            out.extend([""] * gap)
        out.extend(block)
    return out


def _hstack(
    left: list[str],
    right: list[str],
    *,
    left_width: int,
    right_width: int,
    gap: int = 2,
) -> list[str]:
    gap_text = " " * max(0, int(gap))
    blank_left = " " * max(0, left_width)
    blank_right = " " * max(0, right_width)
    height = max(len(left), len(right))
    out: list[str] = []
    for i in range(height):
        l = left[i] if i < len(left) else blank_left
        r = right[i] if i < len(right) else blank_right
        out.append(_pad(l, left_width) + gap_text + r)
    return out


def _sidebar_layout(width: int) -> Optional[tuple[int, int, int]]:
    gap = 2
    min_sidebar = 32
    max_sidebar = 48
    sidebar = min(max_sidebar, max(min_sidebar, width // 3))
    main_min = 58
    if width >= (main_min + gap + sidebar):
        return (width - gap - sidebar, sidebar, gap)
    return None


def _clear() -> None:
    if not sys.stdout.isatty():
        return
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass


def _prompt(text: str, *, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        raw = input(f"{text}{suffix}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("")
        return default or ""
    return raw if raw else (default or "")


def _prompt_bool(text: str, *, default: bool = False, lang: str = LANG_DEFAULT) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{text} [{hint}]: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print(_t("msg_enter_yn", lang))


def _prompt_int(text: str, *, default: int, lang: str = LANG_DEFAULT) -> int:
    while True:
        raw = _prompt(text, default=str(default))
        try:
            return int(raw)
        except ValueError:
            print(_t("msg_enter_number", lang))


def _prompt_float(text: str, *, default: float, lang: str = LANG_DEFAULT) -> float:
    while True:
        raw = _prompt(text, default=str(default))
        try:
            return float(raw)
        except ValueError:
            print(_t("msg_enter_number", lang))


def _prompt_path(text: str, *, default: Optional[str] = None) -> Optional[Path]:
    raw = _prompt(text, default=default)
    if not raw:
        return None
    return Path(raw).expanduser()


def _pause(lang: str = LANG_DEFAULT) -> None:
    try:
        input(f"\n{_t('msg_enter_continue', lang)}")
    except (KeyboardInterrupt, EOFError):
        print("")


def _format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(value)}{unit}"
            return f"{value:.1f}{unit}"
        value /= 1024.0
    return f"{value:.1f}PB"


def _format_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _path_exists(path: Optional[Path]) -> Optional[bool]:
    if path is None:
        return None
    try:
        return path.exists()
    except Exception:
        return None


def _flag(ok: Optional[bool], lang: str) -> str:
    if ok is True:
        return _paint(_t("flag_ok", lang), PALETTE.dim)
    if ok is False:
        return _paint(_t("flag_missing", lang), PALETTE.red)
    return _paint(_t("flag_na", lang), PALETTE.dim)


def _check_item(label: str, ok: Optional[bool], lang: str) -> str:
    return f"{_paint(label, PALETTE.dim)} {_flag(ok, lang)}"


def _file_brief(path: Path, lang: str) -> str:
    try:
        if not path.exists():
            return _paint(_t("file_missing", lang), PALETTE.red)
        stat = path.stat()
        return f"{_format_bytes(stat.st_size)} @ {_format_time(stat.st_mtime)}"
    except Exception:
        return _paint(_t("file_unknown", lang), PALETTE.dim)


def _backup_brief(cfg: ServerConfig, lang: str) -> str:
    backups = manager.list_backups(cfg)
    if not backups:
        return _t("msg_backup_none", lang)
    latest = backups[0]
    size = "-"
    stamp = "-"
    try:
        stat = latest.stat()
        size = _format_bytes(stat.st_size)
        stamp = _format_time(stat.st_mtime)
    except Exception:
        pass
    return f"{len(backups)} ({_t('backup_latest', lang)} {latest.name} {size} {stamp})"


def _ensure_screen(lang: str) -> bool:
    if shutil.which("screen"):
        return True
    print(_paint(_t("msg_screen_missing", lang), PALETTE.red))
    return False


def _run_action(label: str, fn: Callable[[], int], lang: str) -> None:
    print(f"\n[{label}]")
    try:
        code = fn()
    except KeyboardInterrupt:
        print(f"\n{_t('msg_interrupted', lang)}")
        return
    except SystemExit as exc:
        msg = str(exc)
        if msg:
            print(msg)
        return
    except Exception as exc:
        print(f"Error: {exc}")
        return
    if isinstance(code, int):
        if code == 0:
            print(_paint(_t("result_ok", lang), PALETTE.green))
        else:
            msg = _t("result_exit", lang).format(code=code)
            print(_paint(msg, PALETTE.yellow))


def _choose_shard(lang: str) -> str:
    default = "地面" if lang == "zh" else "master"
    raw = _prompt(_t("prompt_shard", lang), default=default).strip().lower()
    if raw in ("c", "cave", "caves", "洞", "洞穴"):
        return "caves"
    if raw in ("m", "master", "地面", "主"):
        return "master"
    return "caves" if raw.startswith("c") or "洞" in raw else "master"


def _get_status(cfg: ServerConfig) -> tuple[Optional[bool], Optional[bool], Optional[str]]:
    try:
        master, caves = manager.get_status(cfg)
        return master, caves, None
    except SystemExit as exc:
        msg = str(exc) or "screen not available"
        return None, None, msg
    except Exception as exc:
        return None, None, f"status error: {exc}"


def _status_label(running: Optional[bool], lang: str) -> str:
    if running is True:
        label = _t("running", lang)
        return _pill(label, fg=PALETTE.black, bg=PALETTE.bg_green, fallback=f"🟢 {label}")
    if running is False:
        label = _t("stopped", lang)
        return _pill(label, fg=PALETTE.white, bg=PALETTE.bg_red, fallback=f"🔴 {label}")
    label = _t("unknown", lang)
    return _pill(label, fg=PALETTE.black, bg=PALETTE.bg_yellow, fallback=f"🟡 {label}")


def _status_line(cfg: ServerConfig, lang: str) -> str:
    master, caves, err = _get_status(cfg)
    if err:
        return _paint(err, PALETTE.yellow)
    return (
        f"{_t('master', lang)}: {_status_label(master, lang)} | "
        f"{_t('caves', lang)}: {_status_label(caves, lang)}"
    )


def _is_running(cfg: ServerConfig) -> Optional[bool]:
    master, caves, err = _get_status(cfg)
    if err:
        return None
    return bool(master or caves)


def _build_status_box(cfg: ServerConfig, lang: str, width: int) -> list[str]:
    screen_ok = shutil.which("screen") is not None
    bin_ok = _path_exists(cfg.bin_dir / "dontstarve_dedicated_server_nullrenderer")
    cluster_ok = _path_exists(cfg.cluster_dir)
    steam_path = cfg.steamcmd_dir / "steamcmd.sh" if cfg.steamcmd_dir else None
    steam_ok = _path_exists(steam_path) if steam_path else None

    master, caves, err = _get_status(cfg)

    inner = max(40, width) - 2
    check_items = [
        _check_item("Screen", screen_ok, lang),
        _check_item("Binary", bin_ok, lang),
        _check_item("Cluster", cluster_ok, lang),
        _check_item("SteamCMD", steam_ok, lang),
    ]
    checks = _two_col(check_items, inner, sep_text="  ·  ", min_col_width=16)

    status_rows = [
        (_t("master", lang), _status_label(master, lang)),
        (_t("caves", lang), _status_label(caves, lang)),
        (f"📜 {_t('logs', lang)}", f"master={_file_brief(cfg.master_log, lang)} · caves={_file_brief(cfg.caves_log, lang)}"),
        (f"💾 {_t('backups', lang)}", _backup_brief(cfg, lang)),
    ]
    s_label_w = max(_display_width(label) for label, _ in status_rows)
    status_lines = [
        _kv_line(status_rows[0][0], status_rows[0][1], s_label_w),
        _kv_line(status_rows[1][0], status_rows[1][1], s_label_w),
        _paint(_divider_line(inner), PALETTE.dim),
        _paint(f"🔎 {_t('checks', lang)}", PALETTE.bold),
        *checks,
        _paint(_divider_line(inner), PALETTE.dim),
        _kv_line(status_rows[2][0], status_rows[2][1], s_label_w),
        _kv_line(status_rows[3][0], status_rows[3][1], s_label_w),
    ]
    if err:
        status_lines.append(_paint(f"! {err}", PALETTE.red))

    return _box_lines(f"📡 {_t('box_status', lang)}", status_lines, width)


def _build_paths_box(cfg: ServerConfig, lang: str, width: int) -> list[str]:
    path_rows = [
        (_t("cluster_label", lang), str(cfg.cluster_name)),
        (_t("dst_label", lang), str(cfg.dst_root)),
        (_t("klei_label", lang), str(cfg.klei_home)),
        (_t("steam_label", lang), str(cfg.steamcmd_dir or "(not set)")),
        (_t("backup_label", lang), str(cfg.backup_dir)),
    ]
    inner = max(40, width) - 2
    p_label_w = max(_display_width(label) for label, _ in path_rows)
    value_max = inner - p_label_w - 2
    path_lines = [
        _kv_line(label, _fit_value(value, value_max), p_label_w)
        for label, value in path_rows
    ]
    return _box_lines(f"🧭 {_t('box_paths', lang)}", path_lines, width, dim_body=True)


def _format_entry(key: str, label: str) -> str:
    k = str(key or "").strip()
    if not k:
        return str(label)
    if not k.startswith("["):
        k = f"[{k}]"
    return f"{k} {label}"


def _build_main_menu_box(lang: str, width: int) -> list[str]:
    inner = max(10, width - 2)
    ops = [
        _format_entry("1", _t("menu_start", lang)),
        _format_entry("2", _t("menu_stop", lang)),
        _format_entry("3", _t("menu_restart", lang)),
        _format_entry("4", _t("menu_update", lang)),
    ]
    data = [
        _format_entry("5", _t("menu_backup", lang)),
        _format_entry("6", _t("menu_restore", lang)),
        _format_entry("7", _t("menu_logs", lang)),
        _format_entry("8", _t("menu_console", lang)),
        _format_entry("9", _t("menu_cmd", lang)),
        _format_entry("L", _t("menu_lang", lang)),
        _format_entry("0", _t("menu_quit", lang)),
    ]

    lines: list[str] = []
    lines.append(_paint(_t("section_ops", lang), PALETTE.bold))
    lines.append(_paint(_divider_line(inner), PALETTE.dim))
    lines.extend(_two_col(ops, inner))
    lines.append("")
    lines.append(_paint(_t("section_data", lang), PALETTE.bold))
    lines.append(_paint(_divider_line(inner), PALETTE.dim))
    lines.extend(_two_col(data, inner))
    lines.append(_paint(_divider_line(inner), PALETTE.dim))
    lines.append(_paint(_t("tip", lang), PALETTE.dim))
    return _box_lines(f"🧰 {_t('box_menu', lang)}", lines, width)


def _render_main_screen(cfg: ServerConfig, lang: str) -> None:
    _clear()
    width = _term_width()
    print(_paint(_compose_title_line(width, lang), PALETTE.bold))
    print("")

    layout = _sidebar_layout(width)
    if layout:
        main_w, side_w, gap = layout
        status_box = _build_status_box(cfg, lang, main_w)
        menu_box = _build_main_menu_box(lang, main_w)
        paths_box = _build_paths_box(cfg, lang, side_w)
        left_col = _vstack([status_box, menu_box], gap=1)
        for line in _hstack(left_col, paths_box, left_width=main_w, right_width=side_w, gap=gap):
            print(line)
        return

    status_box = _build_status_box(cfg, lang, width)
    menu_box = _build_main_menu_box(lang, width)
    paths_box = _build_paths_box(cfg, lang, width)
    for line in _vstack([status_box, menu_box, paths_box], gap=1):
        print(line)


def _build_console_menu_box(lang: str, width: int) -> list[str]:
    inner = max(10, width - 2)
    options = [
        _format_entry("1", _t("console_save", lang)),
        _format_entry("2", _t("console_rollback", lang)),
        _format_entry("3", _t("console_announce", lang)),
        _format_entry("4", _t("console_regen", lang)),
        _format_entry("5", _t("console_players", lang)),
        _format_entry("L", _t("menu_lang", lang)),
        _format_entry("0", _t("console_back", lang)),
    ]
    lines: list[str] = []
    lines.extend(_two_col(options, inner))
    lines.append(_paint(_divider_line(inner), PALETTE.dim))
    lines.append(_paint(_t("tip", lang), PALETTE.dim))
    return _box_lines(f"🎮 {_t('console_title', lang)}", lines, width)


def _render_console_screen(cfg: ServerConfig, lang: str) -> None:
    _clear()
    width = _term_width()
    print(_paint(_compose_title_line(width, lang, context=_t("menu_console", lang)), PALETTE.bold))
    print("")

    layout = _sidebar_layout(width)
    if layout:
        main_w, side_w, gap = layout
        status_box = _build_status_box(cfg, lang, main_w)
        menu_box = _build_console_menu_box(lang, main_w)
        paths_box = _build_paths_box(cfg, lang, side_w)
        left_col = _vstack([status_box, menu_box], gap=1)
        for line in _hstack(left_col, paths_box, left_width=main_w, right_width=side_w, gap=gap):
            print(line)
        return

    status_box = _build_status_box(cfg, lang, width)
    menu_box = _build_console_menu_box(lang, width)
    paths_box = _build_paths_box(cfg, lang, width)
    for line in _vstack([status_box, menu_box, paths_box], gap=1):
        print(line)


def _console_menu(cfg: ServerConfig, lang: str) -> str:
    cur = lang
    while True:
        if not _ensure_screen(cur):
            _pause(cur)
            return cur
        _render_console_screen(cfg, cur)

        choice = _prompt(_t("prompt_select", cur), default="").strip().lower()
        if not choice:
            continue

        if choice in ("0", "back", "b", "返回"):
            return cur
        if choice in ("l", "lang", "language", "语言", "切换"):
            cur = "en" if cur == "zh" else "zh"
            continue

        if choice == "1":
            _run_action("Save", lambda: manager.send_cmd(cfg, shard="master", command="c_save()"), cur)
            _pause(cur)
            continue
        if choice == "2":
            days = _prompt_int(_t("prompt_rollback_days", cur), default=1, lang=cur)
            _run_action("Rollback", lambda: manager.send_cmd(cfg, shard="master", command=f"c_rollback({days})"), cur)
            _pause(cur)
            continue
        if choice == "3":
            msg = _prompt(_t("prompt_announce", cur), default="")
            if not msg:
                continue
            msg = msg.replace('"', '\\"')
            _run_action("Announce", lambda: manager.send_cmd(cfg, shard="master", command=f'c_announce("{msg}")'), cur)
            _pause(cur)
            continue
        if choice == "4":
            confirm = _prompt(_t("prompt_regen_confirm", cur), default="")
            if confirm != "YES":
                continue
            _run_action("Regenerate", lambda: manager.send_cmd(cfg, shard="master", command="c_regenerateworld()"), cur)
            _pause(cur)
            continue
        if choice == "5":
            _run_action("Players", lambda: manager.send_cmd(cfg, shard="master", command="c_listallplayers()"), cur)
            _pause(cur)
            continue

        print(_t("msg_unknown", cur))
        _pause(cur)


def _build_restore_box(backups: list[Path], lang: str, width: int, *, limit: int = 10) -> list[str]:
    inner = max(40, width) - 2
    lines: list[str] = []
    lines.append(_paint(_t("backups_header", lang), PALETTE.bold))
    lines.append(_paint(_divider_line(inner), PALETTE.dim))
    for idx, path in enumerate(backups[:limit]):
        size = "-"
        stamp = "-"
        try:
            stat = path.stat()
            size = _format_bytes(stat.st_size)
            stamp = _format_time(stat.st_mtime)
        except Exception:
            pass
        lines.append(f"[{idx}] {path.name}  {size}  {stamp}")
    if len(backups) > limit:
        msg = _t("backups_more", lang).format(count=len(backups) - limit)
        lines.append(_paint(f"... {msg}", PALETTE.dim))
    lines.append(_paint(_divider_line(inner), PALETTE.dim))
    lines.append(_paint(_t("prompt_restore_choose", lang), PALETTE.dim))
    return _box_lines(_t("menu_restore", lang), lines, width)


def _render_restore_screen(cfg: ServerConfig, lang: str, backups: list[Path]) -> None:
    _clear()
    width = _term_width()
    print(_paint(_compose_title_line(width, lang, context=_t("menu_restore", lang)), PALETTE.bold))
    print("")

    layout = _sidebar_layout(width)
    if layout:
        main_w, side_w, gap = layout
        main_box = _build_restore_box(backups, lang, main_w)
        side_col = _vstack([_build_status_box(cfg, lang, side_w), _build_paths_box(cfg, lang, side_w)], gap=1)
        for line in _hstack(main_box, side_col, left_width=main_w, right_width=side_w, gap=gap):
            print(line)
        return

    status_box = _build_status_box(cfg, lang, width)
    restore_box = _build_restore_box(backups, lang, width)
    paths_box = _build_paths_box(cfg, lang, width)
    for line in _vstack([status_box, restore_box, paths_box], gap=1):
        print(line)


def _confirm_restore_target(cfg: ServerConfig, lang: str, *, selected_backup: Optional[Path] = None) -> bool:
    try:
        target = cfg.cluster_dir.resolve()
    except Exception:
        target = cfg.cluster_dir

    lines: list[str] = []
    lines.append(_paint(_t("msg_restore_overwrite", lang), PALETTE.bold))
    lines.append(f"  {target}")
    if selected_backup is not None:
        lines.append("")
        lines.append(_paint(f"Backup: {selected_backup.name}", PALETTE.dim))
    lines.append("")
    lines.append(_paint(_t("msg_restore_confirm", lang), PALETTE.dim))

    _clear()
    width = _term_width()
    print(_paint(_compose_title_line(width, lang, context=_t("menu_restore", lang)), PALETTE.bold))
    print("")

    layout = _sidebar_layout(width)
    if layout:
        main_w, side_w, gap = layout
        confirm_box = _box_lines("⚠️ Confirm", lines, main_w)
        side_col = _vstack([_build_status_box(cfg, lang, side_w), _build_paths_box(cfg, lang, side_w)], gap=1)
        for line in _hstack(confirm_box, side_col, left_width=main_w, right_width=side_w, gap=gap):
            print(line)
    else:
        status_box = _build_status_box(cfg, lang, width)
        confirm_box = _box_lines("⚠️ Confirm", lines, width)
        paths_box = _build_paths_box(cfg, lang, width)
        for line in _vstack([status_box, confirm_box, paths_box], gap=1):
            print(line)

    confirm = _prompt(_t("msg_restore_confirm", lang), default="")
    return confirm == f"DELETE {target}"


def run_ui(cfg: ServerConfig) -> int:
    lang = LANG_DEFAULT
    while True:
        _render_main_screen(cfg, lang)
        choice = _prompt(_t("prompt_select", lang), default="").strip().lower()
        if not choice:
            continue

        if choice in ("r", "refresh", "刷新"):
            continue

        if choice in ("0", "q", "quit", "exit", "退出"):
            return 0

        if choice in ("l", "lang", "language", "语言", "切换"):
            lang = "en" if lang == "zh" else "zh"
            continue

        if choice in ("1", "start", "启动", "开服"):
            if not _ensure_screen(lang):
                _pause(lang)
                continue
            if _is_running(cfg) is True:
                print(_t("msg_server_running", lang))
                _pause(lang)
                continue
            start_caves = _prompt_bool(_t("prompt_start_caves", lang), default=True, lang=lang)
            _run_action("Start", lambda: manager.start(cfg, start_caves=start_caves), lang)
            _pause(lang)
            continue

        if choice in ("2", "stop", "停止", "停服"):
            if not _ensure_screen(lang):
                _pause(lang)
                continue
            if _is_running(cfg) is False:
                print(_t("msg_server_not_running", lang))
                _pause(lang)
                continue
            timeout = _prompt_float(_t("prompt_timeout", lang), default=40.0, lang=lang)
            force = _prompt_bool(_t("prompt_force", lang), default=True, lang=lang)
            _run_action("Stop", lambda: manager.stop(cfg, timeout=timeout, force=force), lang)
            _pause(lang)
            continue

        if choice in ("3", "restart", "重启"):
            if not _ensure_screen(lang):
                _pause(lang)
                continue
            update = _prompt_bool(_t("prompt_update_restart", lang), default=False, lang=lang)
            start_caves = _prompt_bool(_t("prompt_start_caves", lang), default=True, lang=lang)
            _run_action("Restart", lambda: manager.restart(cfg, start_caves=start_caves, update=update), lang)
            _pause(lang)
            continue

        if choice in ("4", "update", "更新"):
            steam_path = cfg.steamcmd_dir / "steamcmd.sh" if cfg.steamcmd_dir else None
            if steam_path is None or not steam_path.exists():
                print(_t("msg_steam_missing", lang))
                _pause(lang)
                continue
            running = _is_running(cfg)
            if running:
                proceed = _prompt_bool(_t("prompt_update_continue", lang), default=False, lang=lang)
                if not proceed:
                    continue
            _run_action("Update", lambda: manager.update_game(cfg), lang)
            _pause(lang)
            continue

        if choice in ("5", "backup", "备份"):
            if not cfg.cluster_dir.exists():
                print(f"{_t('msg_cluster_missing', lang)}: {cfg.cluster_dir}")
                _pause(lang)
                continue
            out_path = _prompt_path(_t("prompt_backup_out", lang), default="")
            _run_action("Backup", lambda: manager.backup(cfg, out_path=out_path), lang)
            _pause(lang)
            continue

        if choice in ("6", "restore", "恢复"):
            backups = manager.list_backups(cfg)
            if not backups:
                print(_t("msg_backup_none", lang))
                _pause(lang)
                continue
            _render_restore_screen(cfg, lang, backups)
            raw = _prompt(_t("prompt_restore_choose", lang), default="")
            if not raw:
                continue
            file_path = None
            index = None
            latest = False
            selected_backup = None
            raw_lower = raw.lower()
            if raw_lower in ("l", "latest", "最新"):
                latest = True
                selected_backup = backups[0]
            elif raw.isdigit():
                index = int(raw)
                if index < 0 or index >= len(backups):
                    print(_t("msg_backup_index_oob", lang))
                    _pause(lang)
                    continue
                selected_backup = backups[index]
            else:
                file_path = Path(raw).expanduser()
                if not file_path.exists():
                    print(f"{_t('msg_backup_not_found', lang)}: {file_path}")
                    _pause(lang)
                    continue
                selected_backup = file_path

            if not _confirm_restore_target(cfg, lang, selected_backup=selected_backup):
                continue
            start_after = _prompt_bool(_t("prompt_restore_start", lang), default=True, lang=lang)
            _run_action(
                "Restore",
                lambda: manager.restore(
                    cfg,
                    file_path=file_path,
                    index=index,
                    latest=latest,
                    yes=True,
                    start_after=start_after,
                ),
                lang,
            )
            _pause(lang)
            continue

        if choice in ("7", "logs", "日志"):
            shard = _choose_shard(lang)
            log_path = cfg.master_log if shard == "master" else cfg.caves_log
            if not log_path.exists():
                print(f"{_t('msg_log_not_found', lang)}: {log_path}")
                _pause(lang)
                continue
            lines = _prompt_int(_t("prompt_lines", lang), default=120, lang=lang)
            follow = _prompt_bool(_t("prompt_follow", lang), default=True, lang=lang)
            _run_action("Logs", lambda: manager.logs(cfg, shard=shard, follow=follow, lines=lines), lang)
            _pause(lang)
            continue

        if choice in ("8", "console", "控制台"):
            lang = _console_menu(cfg, lang)
            continue

        if choice in ("9", "cmd", "command", "指令"):
            if not _ensure_screen(lang):
                _pause(lang)
                continue
            shard = _choose_shard(lang)
            cmd = _prompt(_t("prompt_send_cmd", lang), default="")
            if not cmd:
                continue
            _run_action("Send command", lambda: manager.send_cmd(cfg, shard=shard, command=cmd), lang)
            _pause(lang)
            continue

        print(_t("msg_unknown", lang))
        _pause(lang)

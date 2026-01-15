#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snapshot_gui.py

A lightweight GUI configurator + launcher for snapshot.py, built with stdlib tkinter/ttk.

Core features
- Visual project tree (lazy-loaded) with multi-select.
- Set per-path Mode: Full / Interface / Head(N lines) / Skip.
- Visual feedback via colors + "Mode" column (and bold for explicit overrides).
- Generate snapshot.py-compatible conf/snapshot_templates.json (explicit paths / simple dir globs).
- Run snapshot.py via subprocess and show output location.

Usage
- Put this file next to devtools/snapshot.py (recommended), or anywhere under the project.
- Run: python3 devtools/snapshot_gui.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox
from tkinter import ttk
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------
# Project root discovery
# ---------------------------

def _find_project_root(start: Path) -> Path:
    """
    Best-effort project root discovery.

    Strategy:
    - Walk up a few levels looking for typical repo markers:
      - conf/ and core/
      - PROJECT_STATUS.json
      - .git/
    """
    p = start.resolve()
    if p.is_file():
        p = p.parent

    for _ in range(8):
        if (p / "conf").is_dir() and (p / "core").is_dir():
            return p
        if (p / "PROJECT_STATUS.json").exists():
            return p
        if (p / ".git").is_dir():
            return p
        parent = p.parent
        if parent == p:
            break
        p = parent

    # Fallback: current working directory
    return Path.cwd().resolve()


# ---------------------------
# snapshot.py discovery + defaults
# ---------------------------

def _guess_snapshot_py(project_root: Path) -> Optional[Path]:
    """
    Locate snapshot.py inside the project.
    """
    candidates = [
        project_root / "devtools" / "snapshot.py",
        project_root / "snapshot.py",
        project_root / "tools" / "snapshot.py",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None


def _load_snapshot_defaults(project_root: Path, snapshot_py: Optional[Path]) -> Tuple[set[str], set[str], List[str], Dict[str, Any]]:
    """
    Try to import snapshot.py to reuse DEFAULT_IGNORE_* and BUILTIN_TEMPLATES.
    Falls back to local conservative defaults if import fails.
    """
    # Local fallbacks (keep consistent with snapshot.py in this repo family)
    fallback_ignore_dirs = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        "logs",
        "env",
        "venv",
        ".idea",
        ".vscode",
        "node_modules",
        "dist",
        "build",
    }
    fallback_ignore_files = {
        "project_context.txt",
        ".DS_Store",
        "id_rsa",
        "id_ed25519",
        "known_hosts",
    }
    fallback_ignore_globs = [
        "data/snapshots/**",
        "**/*.swp",
        "**/*.swo",
        "**/*.tmp",
        "**/*.bak",
        "**/*.log",
        "**/*.zip",
        "**/*.tar",
        "**/*.tar.gz",
        "**/*.gz",
        "**/*.7z",
        "**/*.rar",
        "**/*.png",
        "**/*.jpg",
        "**/*.jpeg",
        "**/*.webp",
        "**/*.pdf",
        "**/*.mp4",
        "**/*.mov",
        "**/*.sqlite",
        "**/*.db",
        "**/.env",
        "**/.env.*",
        "**/*.pem",
        "**/*.key",
    ]
    fallback_builtin_templates: Dict[str, Any] = {}

    if snapshot_py is None:
        return fallback_ignore_dirs, fallback_ignore_files, fallback_ignore_globs, fallback_builtin_templates

    try:
        import importlib.util  # stdlib

        spec = importlib.util.spec_from_file_location("_snapshot_mod", str(snapshot_py))
        if spec is None or spec.loader is None:
            raise RuntimeError("spec_from_file_location failed")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[misc]

        ignore_dirs = set(getattr(mod, "DEFAULT_IGNORE_DIRS", fallback_ignore_dirs))
        ignore_files = set(getattr(mod, "DEFAULT_IGNORE_FILES", fallback_ignore_files))
        ignore_globs = list(getattr(mod, "DEFAULT_IGNORE_GLOBS", fallback_ignore_globs))
        builtin_templates = dict(getattr(mod, "BUILTIN_TEMPLATES", fallback_builtin_templates))

        return ignore_dirs, ignore_files, ignore_globs, builtin_templates
    except Exception:
        return fallback_ignore_dirs, fallback_ignore_files, fallback_ignore_globs, fallback_builtin_templates


# ---------------------------
# Mode model
# ---------------------------

MODE_FULL = "full"
MODE_INTERFACE = "interface"
MODE_HEAD = "head"
MODE_SKIP = "skip"

MODE_LABELS = {
    MODE_FULL: "Full",
    MODE_INTERFACE: "Interface",
    MODE_HEAD: "Head",
    MODE_SKIP: "Skip",
}

MODE_COLOR_TAG = {
    MODE_FULL: "mode_full",
    MODE_INTERFACE: "mode_interface",
    MODE_HEAD: "mode_head",
    MODE_SKIP: "mode_skip",
}


@dataclass(frozen=True)
class ModeSpec:
    mode: str
    head_lines: Optional[int] = None

    def to_rule(self) -> Dict[str, Any]:
        r: Dict[str, Any] = {"mode": self.mode}
        if self.mode == MODE_HEAD and self.head_lines is not None:
            r["head_lines"] = int(self.head_lines)
        return r


# ---------------------------
# Presets (LLM-oriented profiles)
# ---------------------------

PROFILE_MANUAL = "Manual"
PROFILE_LLM_BEST = "LLM Best (balanced)"
PROFILE_LLM_DEEP = "LLM Deep (more code)"
PROFILE_ARCHIVE = "Archive (full + zip)"
PROFILE_AUDIT = "Audit (inventory all)"

PROFILE_ORDER = [
    PROFILE_MANUAL,
    PROFILE_LLM_BEST,
    PROFILE_LLM_DEEP,
    PROFILE_ARCHIVE,
    PROFILE_AUDIT,
]

# Note: Preset paths are RELATIVE to PROJECT_ROOT and should use POSIX slashes.
# For directories, either:
# - set "is_dir": True, or
# - end the path with "/"
PRESETS: Dict[str, Dict[str, Any]] = {
    PROFILE_LLM_BEST: {
        "template_name": "llm_best",
        "desc": "LLM best (balanced): core code full + surrounding head/interface, low-noise inventory.",
        "output": "project_context.txt",
        "redact": True,
        "include_reports": True,
        "limits": {"max_file_bytes": 250000, "max_total_bytes": 3000000},
        "tree": {"max_depth": 10, "max_entries_per_dir": 400},
        "zip": {"enabled": False, "output": "data/snapshots/llm_best_{timestamp}.zip"},
        "hash": "embedded",
        "embed_order": "smart",
        "inventory": {"scope": "included", "limit": 700},
        "default": {"mode": "skip", "head_lines": 200},
        "pinned": [
            "README.md",
            "PROJECT_STATUS.json",
            "conf/settings.ini",
            "conf/snapshot_templates.json",
            "apps/cli/registry.py",
            "core/engine.py",
            "core/analyzer.py",
            "apps/cli/wiki.py",
            "apps/cli/explorer.py",
            "apps/webcraft/app.py",
            "apps/webcraft/api.py",
            "apps/webcraft/catalog_store.py",
            "apps/webcraft/planner.py",
        ],
        "overrides": [
            {"path": "README.md", "mode": "head", "head_lines": 260},
            {"path": "PROJECT_STATUS.json", "mode": "head", "head_lines": 260},
            {"path": ".gitignore", "mode": "head", "head_lines": 120},
            {"path": "conf/", "mode": "full"},
            {"path": "core/", "mode": "full"},
            {"path": "apps/", "mode": "full"},
            {"path": "devtools/", "mode": "interface"},
            {"path": "docs/", "mode": "head", "head_lines": 240},
            {"path": "tests/", "mode": "head", "head_lines": 220},
            {"path": "bin/", "mode": "head", "head_lines": 160},
            {"path": "data/index/", "mode": "head", "head_lines": 200},
            {"path": "data/reports/", "mode": "head", "head_lines": 220},
            {"path": "data/samples/", "mode": "head", "head_lines": 200},
            {"path": "data/static/", "mode": "skip"},
        ],
    },
    PROFILE_LLM_DEEP: {
        "template_name": "llm_deep",
        "desc": "LLM deep: more full content (devtools full), larger safety limits.",
        "output": "project_context.txt",
        "redact": True,
        "include_reports": True,
        "limits": {"max_file_bytes": 400000, "max_total_bytes": 8000000},
        "tree": {"max_depth": 14, "max_entries_per_dir": 600},
        "zip": {"enabled": False, "output": "data/snapshots/llm_deep_{timestamp}.zip"},
        "hash": "embedded",
        "embed_order": "smart",
        "inventory": {"scope": "included", "limit": 1200},
        "default": {"mode": "skip", "head_lines": 200},
        "pinned": [
            "README.md",
            "PROJECT_STATUS.json",
            "apps/cli/registry.py",
            "core/engine.py",
            "core/analyzer.py",
            "devtools/snapshot.py",
            "devtools/snapshot_gui.py",
        ],
        "overrides": [
            {"path": "README.md", "mode": "head", "head_lines": 320},
            {"path": "PROJECT_STATUS.json", "mode": "head", "head_lines": 320},
            {"path": "conf/", "mode": "full"},
            {"path": "core/", "mode": "full"},
            {"path": "apps/", "mode": "full"},
            {"path": "devtools/", "mode": "full"},
            {"path": "docs/", "mode": "head", "head_lines": 300},
            {"path": "tests/", "mode": "interface"},
            {"path": "bin/", "mode": "head", "head_lines": 200},
            {"path": "data/index/", "mode": "head", "head_lines": 300},
            {"path": "data/reports/", "mode": "head", "head_lines": 300},
            {"path": "data/samples/", "mode": "head", "head_lines": 240},
            {"path": "data/static/", "mode": "skip"},
        ],
    },
    PROFILE_ARCHIVE: {
        "template_name": "archive",
        "desc": "Archive: full snapshot as much as possible + zip bundle (binaries still ignored).",
        "output": "data/snapshots/archive_{timestamp}.md",
        "redact": True,
        "include_reports": True,
        "limits": {"max_file_bytes": 600000, "max_total_bytes": 20000000},
        "tree": {"max_depth": 30, "max_entries_per_dir": 1200},
        "zip": {"enabled": True, "output": "data/snapshots/archive_{timestamp}.zip"},
        "hash": "embedded",
        "embed_order": "path",
        "inventory": {"scope": "included", "limit": 2000},
        "default": {"mode": "full", "head_lines": 200},
        "pinned": [],
        "overrides": [
            {"path": "data/static/", "mode": "skip"},
        ],
    },
    PROFILE_AUDIT: {
        "template_name": "audit",
        "desc": "Audit: inventory all + interface-by-default (useful to check project API surface).",
        "output": "project_context.txt",
        "redact": True,
        "include_reports": True,
        "limits": {"max_file_bytes": 200000, "max_total_bytes": 6000000},
        "tree": {"max_depth": 12, "max_entries_per_dir": 800},
        "zip": {"enabled": False, "output": ""},
        "hash": "none",
        "embed_order": "mode",
        "inventory": {"scope": "all", "limit": 2000},
        "default": {"mode": "interface", "head_lines": 200},
        "pinned": [],
        "overrides": [
            {"path": "data/static/", "mode": "skip"},
            {"path": "data/snapshots/", "mode": "skip"},
        ],
    },
}


# ---------------------------
# Helpers
# ---------------------------

_WILDCARD_CHARS_RE = re.compile(r"[*?\[]")


def _is_glob_like(pat: str) -> bool:
    return bool(_WILDCARD_CHARS_RE.search(pat))


def _as_posix_rel(project_root: Path, abs_path: Path) -> str:
    return abs_path.relative_to(project_root).as_posix()


def _specificity_key(match_pat: str) -> Tuple[int, int, int]:
    """
    Sorting key for rules: more specific first.

    Returns a tuple where "smaller is earlier" if used directly, but we'll reverse accordingly.
    We'll use: (wildcards, -segments, -len)
    """
    wildcards = sum(1 for ch in match_pat if ch in "*?[")
    segments = match_pat.count("/") + 1 if match_pat else 0
    return (wildcards, -segments, -len(match_pat))


def _safe_int(s: str, default: int) -> int:
    try:
        v = int(str(s).strip())
        return v
    except Exception:
        return default


# ---------------------------
# GUI
# ---------------------------

class SnapshotGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Snapshot GUI (config generator + launcher)")
        self.geometry("1120x720")
        self.minsize(980, 620)

        self.project_root = _find_project_root(Path(__file__))
        self.snapshot_py = _guess_snapshot_py(self.project_root)

        (
            self.ignore_dirs,
            self.ignore_files,
            self.ignore_globs,
            self.builtin_templates,
        ) = _load_snapshot_defaults(self.project_root, self.snapshot_py)

        # GUI-only additions for noise suppression
        self.gui_hidden_dirs = set(self.ignore_dirs) | {".tox", ".mypy_cache", ".ruff_cache", ".cache"}

        # Config file path (fixed per requirement)
        self.config_path = self.project_root / "conf" / "snapshot_templates.json"

        # State: explicit overrides keyed by rel_posix (dir or file). Root uses "".
        self.explicit: Dict[str, ModeSpec] = {}

        # Global defaults (used when nothing set on a path/ancestors)
        self.default_mode_var = tk.StringVar(value=MODE_SKIP)
        self.default_head_lines_var = tk.StringVar(value="200")

        # Template controls
        self.template_name_var = tk.StringVar(value="gui")
        self.template_desc_var = tk.StringVar(value="GUI generated template")
        self.output_path_var = tk.StringVar(value="project_context.txt")
        self.redact_var = tk.BooleanVar(value=True)
        self.include_reports_var = tk.BooleanVar(value=True)
        self.max_file_bytes_var = tk.StringVar(value="200000")
        self.max_total_bytes_var = tk.StringVar(value="1200000")
        self.tree_max_depth_var = tk.StringVar(value="8")
        self.tree_max_entries_var = tk.StringVar(value="250")
        self.make_zip_var = tk.BooleanVar(value=False)
        self.zip_output_var = tk.StringVar(value="data/snapshots/gui_{timestamp}.zip")
        # LLM/export optimization knobs (snapshot.py v4.2+ supports these)
        self.hash_mode_var = tk.StringVar(value="embedded")     # embedded/all/none
        self.embed_order_var = tk.StringVar(value="smart")      # smart/mode/path
        self.inventory_scope_var = tk.StringVar(value="included")    # all/included
        self.inventory_limit_var = tk.StringVar(value="700")

        # Profiles / presets
        self.profile_var = tk.StringVar(value=PROFILE_LLM_BEST)
        self.set_custom_default_var = tk.BooleanVar(value=True)
        # Pinned paths (saved into template as a list; edited via a small dialog)
        self.pinned_paths: List[str] = []


        # Mode controls
        self.head_lines_var = tk.StringVar(value="200")
        self.show_ignored_var = tk.BooleanVar(value=False)

        # Tree bookkeeping
        self._item_to_abs: Dict[str, Path] = {}
        self._item_to_rel: Dict[str, str] = {}

        self._build_styles()
        self._build_ui()

        # Load previous GUI template (best-effort) if exists
        self._try_load_existing_gui_template()

        # Initial tree
        self._rebuild_tree()

    # -----------------------
    # UI construction
    # -----------------------

    def _build_styles(self) -> None:
        style = ttk.Style(self)

        # Pick a modern-ish theme (cross-platform)
        preferred = ["clam", "vista", "xpnative", "alt", "default"]
        available = set(style.theme_names())
        for t in preferred:
            if t in available:
                style.theme_use(t)
                break

        style.configure("Toolbar.TFrame", padding=(10, 8))
        style.configure("Panel.TLabelframe", padding=(10, 8))
        style.configure("TButton", padding=(10, 6))
        style.configure("Danger.TButton", padding=(10, 6))

        # Tree row height (slightly larger)
        try:
            style.configure("Treeview", rowheight=24)
        except Exception:
            pass

        # Treeview tag colors
        self._tag_colors = {
            "mode_full": "#2e7d32",       # green
            "mode_interface": "#1565c0",  # blue
            "mode_head": "#ef6c00",       # orange
            "mode_skip": "#616161",       # gray
        }

        # Bold font for explicit overrides
        try:
            import tkinter.font as tkfont  # stdlib

            base = tkfont.nametofont("TkDefaultFont")
            self._explicit_font = base.copy()
            self._explicit_font.configure(weight="bold")
        except Exception:
            self._explicit_font = None

    def _build_ui(self) -> None:
        # Toolbar (top)
        toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="Refresh Tree", command=self._rebuild_tree).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Preview JSON", command=self._preview_json).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(toolbar, text="Save Config", command=self._save_config).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Estimate", command=self._plan_snapshot).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="Run Snapshot", command=self._run_snapshot).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Label(toolbar, text="Profile").pack(side=tk.LEFT)
        ttk.Combobox(
            toolbar,
            textvariable=self.profile_var,
            values=PROFILE_ORDER,
            state="readonly",
            width=22,
        ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(toolbar, text="Apply", command=self._apply_profile_replace).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="Merge", command=self._apply_profile_merge).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(toolbar, text="Pinned…", command=self._open_pinned_editor).pack(side=tk.LEFT, padx=(10, 0))

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Label(toolbar, text="Show ignored").pack(side=tk.LEFT)
        ttk.Checkbutton(toolbar, variable=self.show_ignored_var, command=self._rebuild_tree).pack(side=tk.LEFT, padx=(6, 0))

        # Main split
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Left: Tree panel
        left = ttk.Labelframe(paned, text="Project Tree", style="Panel.TLabelframe")
        paned.add(left, weight=2)

        self.tree = ttk.Treeview(
            left,
            columns=("mode", "extra"),
            selectmode="extended",
        )
        self.tree.heading("#0", text="Path", anchor="w")
        self.tree.heading("mode", text="Mode", anchor="w")
        self.tree.heading("extra", text="Extra", anchor="w")

        self.tree.column("#0", width=540, anchor="w")
        self.tree.column("mode", width=110, anchor="w")
        self.tree.column("extra", width=120, anchor="w")

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(left, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        # Tree bindings
        self.tree.bind("<<TreeviewOpen>>", self._on_open_node)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Button-3>", self._on_right_click)  # Windows / X11; on macOS may be Button-2

        # Right: Control panel
        right = ttk.Labelframe(paned, text="Mode & Template Settings", style="Panel.TLabelframe")
        paned.add(right, weight=1)

        # Selection info
        self.sel_info_var = tk.StringVar(value="Selected: 0")
        ttk.Label(right, textvariable=self.sel_info_var).grid(row=0, column=0, columnspan=3, sticky="w")

        # Mode buttons
        ttk.Label(right, text="Set Mode for selection:").grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 4))

        ttk.Button(right, text="🟢 Full", command=lambda: self._apply_mode(MODE_FULL)).grid(row=2, column=0, sticky="ew")
        ttk.Button(right, text="🔵 Interface", command=lambda: self._apply_mode(MODE_INTERFACE)).grid(row=2, column=1, sticky="ew", padx=(8, 0))
        ttk.Button(right, text="⚪ Skip", command=lambda: self._apply_mode(MODE_SKIP)).grid(row=2, column=2, sticky="ew", padx=(8, 0))

        ttk.Button(right, text="🟡 Head", command=lambda: self._apply_mode(MODE_HEAD)).grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Entry(right, textvariable=self.head_lines_var, width=10).grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Label(right, text="lines").grid(row=3, column=2, sticky="w", padx=(8, 0), pady=(8, 0))

        ttk.Button(right, text="Clear Override", command=self._clear_override).grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        # Default mode
        ttk.Separator(right, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=3, sticky="ew", pady=12)

        ttk.Label(right, text="Default (fallback) mode:").grid(row=6, column=0, columnspan=3, sticky="w")
        default_row = ttk.Frame(right)
        default_row.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        ttk.Combobox(
            default_row,
            textvariable=self.default_mode_var,
            values=[MODE_SKIP, MODE_HEAD, MODE_INTERFACE, MODE_FULL],
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT)
        ttk.Label(default_row, text="Head lines").pack(side=tk.LEFT, padx=(10, 6))
        ttk.Entry(default_row, textvariable=self.default_head_lines_var, width=8).pack(side=tk.LEFT)

        # Template block
        ttk.Separator(right, orient=tk.HORIZONTAL).grid(row=8, column=0, columnspan=3, sticky="ew", pady=12)

        ttk.Label(right, text="Template name").grid(row=9, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.template_name_var).grid(row=9, column=1, columnspan=2, sticky="ew", padx=(8, 0))

        ttk.Label(right, text="Description").grid(row=10, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(right, textvariable=self.template_desc_var).grid(row=10, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(8, 0))

        ttk.Label(right, text="Output path").grid(row=11, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(right, textvariable=self.output_path_var).grid(row=11, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(8, 0))

        flags_row = ttk.Frame(right)
        flags_row.grid(row=12, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Checkbutton(flags_row, text="Redact secrets", variable=self.redact_var).pack(side=tk.LEFT)
        ttk.Checkbutton(flags_row, text="Include reports", variable=self.include_reports_var).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Checkbutton(flags_row, text="Set as custom default", variable=self.set_custom_default_var).pack(side=tk.LEFT, padx=(10, 0))

        limits = ttk.Frame(right)
        limits.grid(row=13, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Label(limits, text="max_file_bytes").grid(row=0, column=0, sticky="w")
        ttk.Entry(limits, textvariable=self.max_file_bytes_var, width=12).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Label(limits, text="max_total_bytes").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(limits, textvariable=self.max_total_bytes_var, width=12).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        tree_cfg = ttk.Frame(right)
        tree_cfg.grid(row=14, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Label(tree_cfg, text="tree max_depth").grid(row=0, column=0, sticky="w")
        ttk.Entry(tree_cfg, textvariable=self.tree_max_depth_var, width=8).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Label(tree_cfg, text="max_entries/dir").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(tree_cfg, textvariable=self.tree_max_entries_var, width=8).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        zip_row = ttk.Frame(right)
        zip_row.grid(row=15, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(zip_row, text="Make zip bundle", variable=self.make_zip_var).pack(side=tk.LEFT)
        ttk.Entry(zip_row, textvariable=self.zip_output_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        # Advanced export knobs (LLM-oriented)
        ttk.Separator(right, orient=tk.HORIZONTAL).grid(row=16, column=0, columnspan=3, sticky="ew", pady=12)

        adv = ttk.Frame(right)
        adv.grid(row=17, column=0, columnspan=3, sticky="ew")

        ttk.Label(adv, text="hash").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            adv,
            textvariable=self.hash_mode_var,
            values=["embedded", "all", "none"],
            state="readonly",
            width=10,
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))

        ttk.Label(adv, text="embed_order").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(
            adv,
            textvariable=self.embed_order_var,
            values=["smart", "mode", "path"],
            state="readonly",
            width=10,
        ).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        ttk.Label(adv, text="inventory").grid(row=2, column=0, sticky="w", pady=(6, 0))
        inv_row = ttk.Frame(adv)
        inv_row.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(6, 0))
        ttk.Combobox(
            inv_row,
            textvariable=self.inventory_scope_var,
            values=["all", "included"],
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT)
        ttk.Label(inv_row, text="limit").pack(side=tk.LEFT, padx=(10, 6))
        ttk.Entry(inv_row, textvariable=self.inventory_limit_var, width=8).pack(side=tk.LEFT)

        # Legend
        ttk.Separator(right, orient=tk.HORIZONTAL).grid(row=18, column=0, columnspan=3, sticky="ew", pady=12)
        legend = ttk.Frame(right)
        legend.grid(row=19, column=0, columnspan=3, sticky="ew")
        ttk.Label(legend, text="Legend:").pack(side=tk.LEFT)
        ttk.Label(legend, text=" Full", foreground=self._tag_colors["mode_full"]).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(legend, text=" Interface", foreground=self._tag_colors["mode_interface"]).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(legend, text=" Head", foreground=self._tag_colors["mode_head"]).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(legend, text=" Skip", foreground=self._tag_colors["mode_skip"]).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(legend, text="  (bold = explicit override)").pack(side=tk.LEFT, padx=(12, 0))

        right.columnconfigure(1, weight=1)
        right.columnconfigure(2, weight=1)

        # Status bar
        self.status_var = tk.StringVar(value=self._status_text())
        status = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(10, 6))
        status.pack(side=tk.BOTTOM, fill=tk.X)

        # Context menu
        self._ctx_menu = tk.Menu(self, tearoff=0)
        self._ctx_menu.add_command(label="🟢 Full", command=lambda: self._apply_mode(MODE_FULL))
        self._ctx_menu.add_command(label="🔵 Interface", command=lambda: self._apply_mode(MODE_INTERFACE))
        self._ctx_menu.add_command(label="🟡 Head", command=lambda: self._apply_mode(MODE_HEAD))
        self._ctx_menu.add_command(label="⚪ Skip", command=lambda: self._apply_mode(MODE_SKIP))
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="Clear Override", command=self._clear_override)

    def _status_text(self) -> str:
        snap = str(self.snapshot_py) if self.snapshot_py else "(not found)"
        return f"PROJECT_ROOT: {self.project_root}    CONFIG: {self.config_path}    SNAPSHOT: {snap}"

    # -----------------------
    # Tree loading
    # -----------------------

    def _rebuild_tree(self) -> None:
        # Clear existing
        for item in self.tree.get_children(""):
            self.tree.delete(item)
        self._item_to_abs.clear()
        self._item_to_rel.clear()

        root_id = self.tree.insert("", "end", text=self.project_root.name, open=True, values=("", ""))
        self._item_to_abs[root_id] = self.project_root
        self._item_to_rel[root_id] = ""  # root rel

        # dummy child for lazy load
        self.tree.insert(root_id, "end", text="…")
        self._update_item_display(root_id)

        self.status_var.set(self._status_text())

    def _on_open_node(self, event: tk.Event) -> None:
        item = self.tree.focus()
        if not item:
            return
        self._populate_children_if_needed(item)

    def _populate_children_if_needed(self, item: str) -> None:
        # If first child is dummy, populate
        children = self.tree.get_children(item)
        if len(children) == 1 and self.tree.item(children[0], "text") == "…":
            self.tree.delete(children[0])
            self._populate_children(item)

    def _populate_children(self, parent_item: str) -> None:
        parent_abs = self._item_to_abs.get(parent_item)
        parent_rel = self._item_to_rel.get(parent_item, "")
        if parent_abs is None:
            return

        try:
            entries = list(parent_abs.iterdir())
        except Exception:
            return

        def visible(p: Path) -> bool:
            name = p.name
            if not self.show_ignored_var.get():
                if p.is_dir() and name in self.gui_hidden_dirs:
                    return False
                if p.is_file() and name in self.ignore_files:
                    return False
                # Hide dot-directories by default except "."
                if p.is_dir() and name.startswith(".") and name not in {".", ".github"}:
                    # allow .github by default (often useful)
                    if name in self.gui_hidden_dirs:
                        return False
                    return False
            return True

        entries = [p for p in entries if visible(p)]
        entries.sort(key=lambda p: (0 if p.is_dir() else 1, p.name.lower()))

        for p in entries:
            rel = p.name if parent_rel == "" else f"{parent_rel}/{p.name}"

            node_id = self.tree.insert(parent_item, "end", text=p.name, values=("", ""))
            self._item_to_abs[node_id] = p
            self._item_to_rel[node_id] = rel

            if p.is_dir():
                # lazy child
                self.tree.insert(node_id, "end", text="…")

            self._update_item_display(node_id)

        # Update parent as well (might inherit / explicit)
        self._update_item_display(parent_item)

    # -----------------------
    # Mode computation + visual updates
    # -----------------------

    def _effective_spec(self, rel: str) -> ModeSpec:
        """
        Inheritance:
        - explicit override on this rel
        - nearest ancestor override
        - global default
        """
        if rel in self.explicit:
            return self.explicit[rel]

        # walk up
        cur = rel
        while cur:
            parent = cur.rsplit("/", 1)[0] if "/" in cur else ""
            if parent in self.explicit:
                return self.explicit[parent]
            cur = parent

        # root
        if "" in self.explicit:
            return self.explicit[""]

        # global default
        dm = self.default_mode_var.get().strip() or MODE_SKIP
        if dm == MODE_HEAD:
            hl = _safe_int(self.default_head_lines_var.get(), 200)
            return ModeSpec(mode=MODE_HEAD, head_lines=hl)
        return ModeSpec(mode=dm)

    def _update_item_display(self, item: str) -> None:
        rel = self._item_to_rel.get(item, "")
        abs_path = self._item_to_abs.get(item)

        spec = self._effective_spec(rel)
        explicit = rel in self.explicit

        mode_label = MODE_LABELS.get(spec.mode, spec.mode)
        extra = ""
        if spec.mode == MODE_HEAD:
            hl = spec.head_lines if spec.head_lines is not None else _safe_int(self.head_lines_var.get(), 200)
            extra = f"{hl} lines"

        # Update columns
        self.tree.set(item, "mode", mode_label)
        self.tree.set(item, "extra", extra)

        # Tags for color + explicit bold
        tags: List[str] = []
        tags.append(MODE_COLOR_TAG.get(spec.mode, "mode_skip"))
        if explicit:
            tags.append("explicit")

        self.tree.item(item, tags=tags)

        # Configure tags globally (idempotent)
        self.tree.tag_configure("mode_full", foreground=self._tag_colors["mode_full"])
        self.tree.tag_configure("mode_interface", foreground=self._tag_colors["mode_interface"])
        self.tree.tag_configure("mode_head", foreground=self._tag_colors["mode_head"])
        self.tree.tag_configure("mode_skip", foreground=self._tag_colors["mode_skip"])

        if self._explicit_font is not None:
            self.tree.tag_configure("explicit", font=self._explicit_font)

        # Minor hint: directories always show trailing slash in mode column? (skip; keep clean)

        # Keep root open
        if abs_path == self.project_root:
            self.tree.item(item, open=True)

    def _update_loaded_subtree(self, item: str) -> None:
        self._update_item_display(item)
        for child in self.tree.get_children(item):
            # Skip dummy placeholder
            if self.tree.item(child, "text") == "…":
                continue
            self._update_loaded_subtree(child)

    # -----------------------
    # Selection + commands
    # -----------------------

    def _on_select(self, event: tk.Event) -> None:
        sel = self.tree.selection()
        self.sel_info_var.set(f"Selected: {len(sel)}")
        # Keep status bar in sync (optional)
        self.status_var.set(self._status_text())

    def _selected_rels(self) -> List[str]:
        rels: List[str] = []
        for item in self.tree.selection():
            rels.append(self._item_to_rel.get(item, ""))
        return rels

    def _apply_mode(self, mode: str) -> None:
        items = list(self.tree.selection())
        if not items:
            return

        spec: ModeSpec
        if mode == MODE_HEAD:
            hl = _safe_int(self.head_lines_var.get(), 200)
            spec = ModeSpec(mode=MODE_HEAD, head_lines=hl)
        else:
            spec = ModeSpec(mode=mode)

        for item in items:
            rel = self._item_to_rel.get(item, "")
            self.explicit[rel] = spec

            # Update this node and any currently loaded descendants
            self._update_loaded_subtree(item)

        self.status_var.set(self._status_text())

    def _clear_override(self) -> None:
        items = list(self.tree.selection())
        if not items:
            return

        for item in items:
            rel = self._item_to_rel.get(item, "")
            if rel in self.explicit:
                del self.explicit[rel]
            self._update_loaded_subtree(item)

    def _on_right_click(self, event: tk.Event) -> None:
        row_id = self.tree.identify_row(event.y)
        if row_id:
            # If clicked item not in current selection, select it
            if row_id not in self.tree.selection():
                self.tree.selection_set(row_id)
            try:
                self._ctx_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self._ctx_menu.grab_release()


    # -----------------------
    # Profiles / presets
    # -----------------------

    def _apply_profile_replace(self) -> None:
        """Apply selected profile and REPLACE current overrides/settings."""
        self._apply_profile(merge=False)

    def _apply_profile_merge(self) -> None:
        """Apply selected profile and MERGE into current overrides/settings."""
        self._apply_profile(merge=True)

    def _apply_profile(self, *, merge: bool) -> None:
        profile = (self.profile_var.get() or "").strip()
        if not profile or profile == PROFILE_MANUAL:
            return
        preset = PRESETS.get(profile)
        if not isinstance(preset, dict):
            messagebox.showerror("Profile", f"Unknown profile: {profile}")
            return

        if not merge:
            self.explicit.clear()

        # Template fields
        try:
            self.template_name_var.set(str(preset.get("template_name") or self.template_name_var.get() or "gui"))
            self.template_desc_var.set(str(preset.get("desc") or self.template_desc_var.get() or "GUI generated template"))
            self.output_path_var.set(str(preset.get("output") or self.output_path_var.get() or "project_context.txt"))

            self.redact_var.set(bool(preset.get("redact", True)))
            self.include_reports_var.set(bool(preset.get("include_reports", True)))

            limits = preset.get("limits") or {}
            if isinstance(limits, dict):
                if "max_file_bytes" in limits:
                    self.max_file_bytes_var.set(str(int(limits.get("max_file_bytes") or 0)))
                if "max_total_bytes" in limits:
                    self.max_total_bytes_var.set(str(int(limits.get("max_total_bytes") or 0)))

            tree = preset.get("tree") or {}
            if isinstance(tree, dict):
                if "max_depth" in tree:
                    self.tree_max_depth_var.set(str(int(tree.get("max_depth") or 0)))
                if "max_entries_per_dir" in tree:
                    self.tree_max_entries_var.set(str(int(tree.get("max_entries_per_dir") or 0)))

            z = preset.get("zip") or {}
            if isinstance(z, dict):
                self.make_zip_var.set(bool(z.get("enabled", False)))
                if isinstance(z.get("output"), str):
                    self.zip_output_var.set(z.get("output") or "")

            if isinstance(preset.get("hash"), str):
                self.hash_mode_var.set(preset.get("hash") or "embedded")
            if isinstance(preset.get("embed_order"), str):
                self.embed_order_var.set(preset.get("embed_order") or "smart")

            inv = preset.get("inventory") or {}
            if isinstance(inv, dict):
                if isinstance(inv.get("scope"), str):
                    self.inventory_scope_var.set(inv.get("scope") or "included")
                if "limit" in inv:
                    self.inventory_limit_var.set(str(int(inv.get("limit") or 0)))

            default = preset.get("default") or {}
            if isinstance(default, dict):
                dm = str(default.get("mode") or MODE_SKIP).strip() or MODE_SKIP
                self.default_mode_var.set(dm)
                if dm == MODE_HEAD:
                    self.default_head_lines_var.set(str(int(default.get("head_lines") or 200)))
                elif "head_lines" in default:
                    # keep handy
                    self.default_head_lines_var.set(str(int(default.get("head_lines") or 200)))

        except Exception as e:
            messagebox.showerror("Profile", f"Failed to apply profile settings:\n{e}")
            return

        # Pinned
        pinned = preset.get("pinned") or []
        if isinstance(pinned, list):
            if merge and self.pinned_paths:
                merged = list(self.pinned_paths)
                seen = set(merged)
                for p in pinned:
                    s = str(p).strip()
                    if not s or s in seen:
                        continue
                    merged.append(s)
                    seen.add(s)
                self.pinned_paths = merged
            else:
                self.pinned_paths = [str(p).strip() for p in pinned if str(p).strip()]

        # Overrides
        overrides = preset.get("overrides") or []
        if isinstance(overrides, list):
            for o in overrides:
                if not isinstance(o, dict):
                    continue
                raw = str(o.get("path") or "").strip().replace("\\", "/")
                if not raw:
                    continue
                is_dir = bool(o.get("is_dir")) or raw.endswith("/")
                rel = raw[:-1] if raw.endswith("/") else raw
                rel = rel.lstrip("./").lstrip("/")
                mode = str(o.get("mode") or MODE_SKIP).strip() or MODE_SKIP
                if mode not in {MODE_FULL, MODE_INTERFACE, MODE_HEAD, MODE_SKIP}:
                    continue
                hl = o.get("head_lines")
                if mode == MODE_HEAD:
                    spec = ModeSpec(mode=MODE_HEAD, head_lines=int(hl) if isinstance(hl, int) else 200)
                else:
                    spec = ModeSpec(mode=mode)

                # We store dir/file the same key (rel); rule generation will detect actual dir.
                # If the path doesn't exist, still store as an override.
                self.explicit[rel] = spec

        # Refresh currently-loaded subtree for visual update
        root_items = self.tree.get_children("")
        if root_items:
            self._update_loaded_subtree(root_items[0])

    # -----------------------
    # Pinned editor (dialog)
    # -----------------------

    def _open_pinned_editor(self) -> None:
        """Edit pinned paths (one per line)."""
        win = tk.Toplevel(self)
        win.title("Pinned paths (embed_order=smart)")
        win.geometry("720x520")
        win.minsize(620, 420)

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        info = (
            "Pinned paths are listed first when embed_order=smart.\n"
            "One relative path per line, e.g.:\n"
            "  README.md\n"
            "  core/engine.py\n"
        )
        ttk.Label(frm, text=info, justify="left").grid(row=0, column=0, columnspan=3, sticky="w")

        txt = tk.Text(frm, wrap="none", height=18)
        vsb = ttk.Scrollbar(frm, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)

        txt.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        vsb.grid(row=1, column=1, sticky="ns", pady=(8, 0))

        # Fill
        txt.insert("1.0", "\n".join(self.pinned_paths).strip() + ("\n" if self.pinned_paths else ""))

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        def _normalize_lines(lines: List[str]) -> List[str]:
            out: List[str] = []
            seen: set[str] = set()
            for s in lines:
                s = (s or "").strip().replace("\\", "/")
                while s.startswith("./"):
                    s = s[2:]
                s = s.lstrip("/")
                if not s:
                    continue
                if s in seen:
                    continue
                seen.add(s)
                out.append(s)
            return out

        def on_add_selected() -> None:
            sel = self._selected_rels()
            if not sel:
                return
            cur = txt.get("1.0", "end").splitlines()
            merged = _normalize_lines(cur + sel)
            txt.delete("1.0", "end")
            txt.insert("1.0", "\n".join(merged) + ("\n" if merged else ""))

        def on_sort_unique() -> None:
            cur = _normalize_lines(txt.get("1.0", "end").splitlines())
            cur_sorted = sorted(cur)
            txt.delete("1.0", "end")
            txt.insert("1.0", "\n".join(cur_sorted) + ("\n" if cur_sorted else ""))

        def on_clear() -> None:
            txt.delete("1.0", "end")

        def on_save() -> None:
            cur = _normalize_lines(txt.get("1.0", "end").splitlines())
            self.pinned_paths = cur
            win.destroy()

        ttk.Button(btns, text="Add selected", command=on_add_selected).pack(side=tk.LEFT)
        ttk.Button(btns, text="Sort+Unique", command=on_sort_unique).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Clear", command=on_clear).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Save", command=on_save).pack(side=tk.RIGHT, padx=(0, 8))

        frm.rowconfigure(1, weight=1)
        frm.columnconfigure(0, weight=1)


    # -----------------------
    # Config generation
    # -----------------------

    def _build_template_dict(self) -> Dict[str, Any]:
        """
        Convert current GUI state into snapshot.py template dict.

        Strategy:
        - Use explicit paths for file rules.
        - Use <dir>/** for directory rules.
        - Add a fallback rule (**/*) using the global default mode (unless root already explicitly set).
        - include_globs derived from non-skip explicit overrides (and from default mode if non-skip).
        """
        name = (self.template_name_var.get() or "").strip()
        if not name:
            raise ValueError("Template name is empty.")

        desc = (self.template_desc_var.get() or "").strip() or "GUI generated template"
        output = (self.output_path_var.get() or "").strip() or "project_context.txt"

        redact = bool(self.redact_var.get())
        include_reports = bool(self.include_reports_var.get())

        max_file_bytes = _safe_int(self.max_file_bytes_var.get(), 200000)
        max_total_bytes = _safe_int(self.max_total_bytes_var.get(), 1200000)
        tree_max_depth = _safe_int(self.tree_max_depth_var.get(), 8)
        tree_max_entries = _safe_int(self.tree_max_entries_var.get(), 250)

        # Build include_globs
        include_set: set[str] = set()

        default_mode = (self.default_mode_var.get() or MODE_SKIP).strip()
        if default_mode and default_mode != MODE_SKIP:
            include_set.add("**/*")

        for rel, spec in self.explicit.items():
            if spec.mode == MODE_SKIP:
                continue
            if rel == "":
                include_set.add("**/*")
                continue
            abs_path = self.project_root / rel
            if abs_path.exists() and abs_path.is_dir():
                include_set.add(f"{rel}/**/*")
            else:
                include_set.add(rel)

        include_globs = ["**/*"] if "**/*" in include_set else sorted(include_set)

        # Build rules
        rules: List[Dict[str, Any]] = []

        for rel, spec in self.explicit.items():
            if rel == "":
                match = "**/*"
            else:
                abs_path = self.project_root / rel
                if abs_path.exists() and abs_path.is_dir():
                    match = f"{rel}/**"
                else:
                    match = rel

            r = {"match": match}
            r.update(spec.to_rule())
            rules.append(r)

        # Sort rules by specificity: more specific first
        rules.sort(key=lambda r: _specificity_key(str(r.get("match", ""))))

        # Add fallback default rule, unless an explicit root override already exists
        has_root_rule = any(str(r.get("match")) == "**/*" for r in rules)
        if not has_root_rule:
            dm = default_mode or MODE_SKIP
            default_rule: Dict[str, Any] = {"match": "**/*", "mode": dm}
            if dm == MODE_HEAD:
                default_rule["head_lines"] = _safe_int(self.default_head_lines_var.get(), 200)
            rules.append(default_rule)

        # Pinned paths (optional; used by snapshot.py when embed_order=smart)
        pinned_norm: List[str] = []
        if getattr(self, "pinned_paths", None):
            seen_pin: set[str] = set()
            for p in list(self.pinned_paths):
                if not isinstance(p, str):
                    continue
                pp = p.strip().replace("\\", "/")
                while pp.startswith("./"):
                    pp = pp[2:]
                pp = pp.lstrip("/")
                if not pp or pp in seen_pin:
                    continue
                seen_pin.add(pp)
                pinned_norm.append(pp)

        tpl: Dict[str, Any] = {
            "desc": desc,
            "output": output,
            "redact": redact,
            "include_reports": include_reports,
            "max_file_bytes": max_file_bytes,
            "max_total_bytes": max_total_bytes,
            "tree": {"max_depth": tree_max_depth, "max_entries_per_dir": tree_max_entries},
            "include_globs": include_globs,
            "ignore_files": sorted(self.ignore_files),
            "ignore_globs": list(self.ignore_globs),
            "hash": (self.hash_mode_var.get() or "embedded").strip() or "embedded",
            "embed_order": (self.embed_order_var.get() or "smart").strip() or "smart",
            "inventory": {
                "enabled": True,
                "scope": (self.inventory_scope_var.get() or "all").strip() or "all",
                "limit": _safe_int(self.inventory_limit_var.get(), 700),
            },
            "rules": rules,
        }

        if pinned_norm:
            tpl["pinned"] = pinned_norm

        if bool(self.make_zip_var.get()):
            tpl["make_zip"] = True
            zip_out = (self.zip_output_var.get() or "").strip()
            if zip_out:
                tpl["zip_output"] = zip_out

        return tpl

    def _load_config_doc(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _merge_and_write_config(self, tpl_name: str, tpl_dict: Dict[str, Any]) -> None:
        doc = self._load_config_doc()

        if not isinstance(doc, dict):
            doc = {}

        doc.setdefault("version", 1)
        doc.setdefault("templates", {})
        if not isinstance(doc["templates"], dict):
            doc["templates"] = {}

        # Optionally seed built-in templates if config is empty (nice UX)
        if not doc["templates"] and self.builtin_templates:
            for k, v in self.builtin_templates.items():
                doc["templates"][k] = v

        doc["templates"][tpl_name] = tpl_dict

        # Keep or set defaults (safe)
        defaults = doc.get("defaults")
        if not isinstance(defaults, dict):
            defaults = {}
            doc["defaults"] = defaults
        mode_to_tpl = defaults.get("mode_to_template")
        if not isinstance(mode_to_tpl, dict):
            mode_to_tpl = {}
            defaults["mode_to_template"] = mode_to_tpl

        # Make "custom" point to GUI template for convenience, without touching core/archive.
        mode_to_tpl.setdefault("core", "core")
        mode_to_tpl.setdefault("archive", "archive")
        if bool(self.set_custom_default_var.get()):
            mode_to_tpl["custom"] = tpl_name

        # Ensure parent dir
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self.config_path.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _save_config(self) -> None:
        try:
            tpl_name = (self.template_name_var.get() or "").strip()
            tpl_dict = self._build_template_dict()
            self._merge_and_write_config(tpl_name, tpl_dict)
        except Exception as e:
            messagebox.showerror("Save Config failed", str(e))
            return

        messagebox.showinfo("Config saved", f"Saved to:\n{self.config_path}")

    def _preview_json(self) -> None:
        try:
            tpl_name = (self.template_name_var.get() or "").strip()
            tpl_dict = self._build_template_dict()
            doc = {"version": 1, "templates": {tpl_name: tpl_dict}}
            text = json.dumps(doc, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Preview failed", str(e))
            return

        win = tk.Toplevel(self)
        win.title("Preview JSON (template only)")
        win.geometry("820x620")

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(frm, wrap="none")
        vsb = ttk.Scrollbar(frm, orient="vertical", command=txt.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        txt.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frm.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)

        txt.insert("1.0", text)
        txt.configure(state="disabled")

    # -----------------------
    # Run snapshot.py
    # -----------------------

    def _plan_snapshot(self) -> None:
        """Run snapshot.py in --plan mode and show a compact summary."""
        if self.snapshot_py is None or not self.snapshot_py.exists():
            messagebox.showerror(
                "snapshot.py not found",
                f"Could not locate snapshot.py under:\n{self.project_root}\n\n"
                f"Expected one of:\n"
                f"- {self.project_root / 'devtools' / 'snapshot.py'}\n"
                f"- {self.project_root / 'snapshot.py'}",
            )
            return

        # Save config first (ensures plan matches UI)
        try:
            tpl_name = (self.template_name_var.get() or "").strip()
            tpl_dict = self._build_template_dict()
            self._merge_and_write_config(tpl_name, tpl_dict)
        except Exception as e:
            messagebox.showerror("Estimate failed", f"Config generation failed:\n{e}")
            return

        cmd = [
            sys.executable,
            str(self.snapshot_py),
            "--mode",
            "custom",
            "--template",
            tpl_name,
            "--config",
            str(self.config_path),
            "--plan",
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
            )
        except Exception as e:
            messagebox.showerror("Estimate failed", str(e))
            return

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if proc.returncode != 0:
            msg = stdout or stderr or f"Exit code: {proc.returncode}"
            if "--plan" in msg and ("unrecognized" in msg or "unknown" in msg):
                msg = (
                    msg
                    + "\n\nThis snapshot.py does not support --plan.\n"
                    + "Tip: use the optimized snapshot.py (with --plan) or update snapshot.py."
                )
            messagebox.showerror("Estimate failed", msg)
            return

        try:
            plan = json.loads(stdout) if stdout else {}
        except Exception:
            messagebox.showinfo("Estimate", stdout or "(no output)")
            return

        by_mode = plan.get("by_mode", {})
        timing = plan.get("timing_ms", {})
        top_large = plan.get("top_largest_non_skip", [])

        # Upper-bound token estimate (very rough): bytes / 4
        total_non_skip_bytes = 0
        if isinstance(by_mode, dict):
            for mk, mv in by_mode.items():
                if mk == "skip":
                    continue
                if isinstance(mv, dict):
                    try:
                        total_non_skip_bytes += int(mv.get("size_bytes") or 0)
                    except Exception:
                        pass
        approx_tokens = int(total_non_skip_bytes / 4) if total_non_skip_bytes > 0 else None

        lines: List[str] = []
        lines.append("PLAN SUMMARY")
        lines.append(f"mode: {plan.get('mode')}    template: {plan.get('template')}")
        lines.append(f"total_candidates: {plan.get('total_candidates')}")
        lines.append(f"included_records: {plan.get('included_records')}")
        lines.append(f"hash_mode: {plan.get('hash_mode')}    embed_order: {plan.get('embed_order')}")

        if isinstance(timing, dict):
            lines.append(
                f"timing_ms: scan={timing.get('scan')}  records={timing.get('records')}  total={timing.get('total')}"
            )

        if approx_tokens is not None:
            lines.append(f"approx_tokens_upper_bound: ~{approx_tokens} (bytes/4; based on source sizes)")

        lines.append("")
        lines.append("by_mode:")
        if isinstance(by_mode, dict):
            for k in sorted(by_mode.keys()):
                v = by_mode.get(k) or {}
                if isinstance(v, dict):
                    lines.append(f"  - {k}: {v.get('count')} files, {v.get('size_bytes')} bytes")

        outp = plan.get("output")
        if outp:
            lines.append("")
            lines.append(f"output: {outp}")

        if isinstance(top_large, list) and top_large:
            lines.append("")
            lines.append("top_largest_non_skip:")
            for x in top_large[:12]:
                if not isinstance(x, dict):
                    continue
                lines.append(f"  - {x.get('size_bytes')} bytes  [{x.get('mode')}]  {x.get('path')}")

        lines.append("")
        lines.append("RAW PLAN JSON:")
        try:
            lines.append(json.dumps(plan, ensure_ascii=False, indent=2))
        except Exception:
            lines.append(str(plan))

        win = tk.Toplevel(self)
        win.title("Estimate / Plan")
        win.geometry("920x680")
        win.minsize(740, 520)

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(frm, wrap="none")
        vsb = ttk.Scrollbar(frm, orient="vertical", command=txt.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=txt.xview)
        txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        txt.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frm.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)

        txt.insert("1.0", "\n".join(lines).strip() + "\n")
        txt.configure(state="disabled")

    def _run_snapshot(self) -> None:
        if self.snapshot_py is None or not self.snapshot_py.exists():
            messagebox.showerror(
                "snapshot.py not found",
                f"Could not locate snapshot.py under:\n{self.project_root}\n\n"
                f"Expected one of:\n"
                f"- {self.project_root / 'devtools' / 'snapshot.py'}\n"
                f"- {self.project_root / 'snapshot.py'}",
            )
            return

        # Save config first (per requirement)
        try:
            tpl_name = (self.template_name_var.get() or "").strip()
            tpl_dict = self._build_template_dict()
            self._merge_and_write_config(tpl_name, tpl_dict)
        except Exception as e:
            messagebox.showerror("Run failed", f"Config generation failed:\n{e}")
            return

        cmd = [
            sys.executable,
            str(self.snapshot_py),
            "--mode",
            "custom",
            "--template",
            tpl_name,
            "--config",
            str(self.config_path),
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
            )
        except Exception as e:
            messagebox.showerror("Run failed", str(e))
            return

        out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        out = out.strip()

        if proc.returncode != 0:
            messagebox.showerror("Snapshot failed", out or f"Exit code: {proc.returncode}")
            return

        # Try to find the output path from stdout
        out_path = None
        for line in (proc.stdout or "").splitlines():
            m = re.search(r"Snapshot written:\s*(.+)$", line)
            if m:
                out_path = m.group(1).strip()
                break

        if out_path:
            messagebox.showinfo("Snapshot done", f"Output:\n{out_path}")
        else:
            messagebox.showinfo("Snapshot done", out or "Done.")

    # -----------------------
    # Load existing GUI template (optional convenience)
    # -----------------------

    def _try_load_existing_gui_template(self) -> None:
        """
        Best-effort load:
        - If conf/snapshot_templates.json exists and contains the current template name,
          parse rules that look like explicit paths and restore them into GUI state.
        Notes:
        - Patterns containing wildcards are ignored (kept as-is in file, but not represented in GUI).
        """
        if not self.config_path.exists():
            return

        try:
            doc = json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            return

        if not isinstance(doc, dict):
            return
        templates = doc.get("templates")
        if not isinstance(templates, dict):
            return

        tpl_name = (self.template_name_var.get() or "").strip()
        tpl = templates.get(tpl_name)
        if not isinstance(tpl, dict):
            return

        # Restore basic template fields (best-effort)
        try:
            if isinstance(tpl.get("desc"), str):
                self.template_desc_var.set(tpl.get("desc") or "")
            if isinstance(tpl.get("output"), str):
                self.output_path_var.set(tpl.get("output") or "project_context.txt")

            if "redact" in tpl:
                self.redact_var.set(bool(tpl.get("redact")))
            if "include_reports" in tpl:
                self.include_reports_var.set(bool(tpl.get("include_reports")))

            if isinstance(tpl.get("max_file_bytes"), int):
                self.max_file_bytes_var.set(str(int(tpl.get("max_file_bytes"))))
            if isinstance(tpl.get("max_total_bytes"), int):
                self.max_total_bytes_var.set(str(int(tpl.get("max_total_bytes"))))

            tree = tpl.get("tree")
            if isinstance(tree, dict):
                if isinstance(tree.get("max_depth"), int):
                    self.tree_max_depth_var.set(str(int(tree.get("max_depth"))))
                if isinstance(tree.get("max_entries_per_dir"), int):
                    self.tree_max_entries_var.set(str(int(tree.get("max_entries_per_dir"))))

            if "make_zip" in tpl:
                self.make_zip_var.set(bool(tpl.get("make_zip")))
            if isinstance(tpl.get("zip_output"), str):
                self.zip_output_var.set(tpl.get("zip_output") or "")

            if isinstance(tpl.get("hash"), str):
                self.hash_mode_var.set(tpl.get("hash") or "embedded")
            if isinstance(tpl.get("embed_order"), str):
                self.embed_order_var.set(tpl.get("embed_order") or "smart")

            inv = tpl.get("inventory")
            if isinstance(inv, dict):
                if isinstance(inv.get("scope"), str):
                    self.inventory_scope_var.set(inv.get("scope") or "included")
                if isinstance(inv.get("limit"), int):
                    self.inventory_limit_var.set(str(int(inv.get("limit"))))

            pinned = tpl.get("pinned")
            if isinstance(pinned, list):
                self.pinned_paths = [str(x) for x in pinned if str(x).strip()]
        except Exception:
            pass

        rules = tpl.get("rules")
        if not isinstance(rules, list):
            return

        restored: Dict[str, ModeSpec] = {}
        for r in rules:
            if not isinstance(r, dict):
                continue
            match = str(r.get("match") or "")
            mode = str(r.get("mode") or "").strip()
            if not match or not mode:
                continue

            # Only restore "explicit path" rules:
            # - exact file path without wildcards
            # - directory patterns like "dir/**"
            if _is_glob_like(match) and not match.endswith("/**") and match != "**/*":
                continue

            if match == "**/*":
                # treat as root override
                hl = r.get("head_lines")
                if mode == MODE_HEAD and isinstance(hl, int):
                    restored[""] = ModeSpec(mode=MODE_HEAD, head_lines=int(hl))
                else:
                    restored[""] = ModeSpec(mode=mode)
                continue

            if match.endswith("/**"):
                rel = match[:-3]
                if not rel:
                    continue
                hl = r.get("head_lines")
                if mode == MODE_HEAD and isinstance(hl, int):
                    restored[rel] = ModeSpec(mode=MODE_HEAD, head_lines=int(hl))
                else:
                    restored[rel] = ModeSpec(mode=mode)
                continue

            if _is_glob_like(match):
                continue

            # exact file path
            rel = match
            hl = r.get("head_lines")
            if mode == MODE_HEAD and isinstance(hl, int):
                restored[rel] = ModeSpec(mode=MODE_HEAD, head_lines=int(hl))
            else:
                restored[rel] = ModeSpec(mode=mode)

        if restored:
            self.explicit.update(restored)


def main() -> None:
    app = SnapshotGUI()
    app.mainloop()


if __name__ == "__main__":
    main()

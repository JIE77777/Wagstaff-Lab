#!/usr/bin/env python3
"""Wagstaff-Lab Snapshot (v4.4)

Goal:
- Provide LLM-friendly snapshots by default.
- Provide two primary modes:
  - llm: LLM-friendly snapshot (project overview + core/apps full + non-core interfaces/head)
  - archive: archival snapshot (full content as much as possible + optional zip bundle)
- Provide custom templates via JSON config (growth-friendly).

Default behavior:
- `wagstaff snap` => llm template (LLM-friendly) => writes project_context.txt
- Use --focus to narrow the snapshot scope (repeatable).
- Use section switches to reduce noise.

Template config:
- Default path: conf/snapshot_templates.json
- See the example template file for schema.
"""

from __future__ import annotations

import argparse
import ast
import copy
import fnmatch
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import textwrap
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "conf" / "snapshot_templates.json"

DEFAULT_IGNORE_DIRS = {
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

DEFAULT_IGNORE_FILES = {
    "project_context.txt",
    ".DS_Store",
    "id_rsa",
    "id_ed25519",
    "known_hosts",
}

# Conservative binary-ish extensions we almost never want in an LLM snapshot.
DEFAULT_IGNORE_GLOBS = [
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

# Snapshot section switches (can be overridden per template).
DEFAULT_SECTIONS = {
    "config": True,
    "env": True,
    "overview": True,
    "tree": True,
    "inventory": True,
    "contents": True,
    "stats": True,
}

# LLM-friendly defaults (less noise).
LLM_SECTIONS = {
    "config": False,
    "env": True,
    "overview": True,
    "tree": True,
    "inventory": True,
    "contents": True,
    "stats": True,
}

# Minimal built-in templates (used if conf/snapshot_templates.json is missing).
_LLM_TEMPLATE = {
    "desc": "Builtin LLM-friendly template",
    "output": "project_context.txt",
    "redact": True,
    "include_reports": True,
    "hash": "embedded",
    "embed_order": "smart",
    "sections": dict(LLM_SECTIONS),
    "inventory": {"enabled": True, "scope": "included", "limit": 700},
    "pinned": [
        "PROJECT_STATUS.json",
        "README.md",
        "conf/settings.ini",
        "docs/guides/DEV_GUIDE.md",
        "docs/management/ROADMAP.md",
        "apps/cli/main.py",
        "apps/cli/registry.py",
    ],
    "max_file_bytes": 200000,
    "max_total_bytes": 1200000,
    "tree": {"max_depth": 8, "max_entries_per_dir": 250},
    "include_globs": [
        "README.md",
        "PROJECT_STATUS.json",
        ".gitignore",
        "conf/**/*.ini",
        "core/**/*.py",
        "apps/**/*.py",
        "devtools/**/*.py",
        "docs/**/*.md",
        "tests/**/*.py",
        "data/reports/**/*.md",
        "data/samples/**/*",
    ],
    "ignore_files": sorted(DEFAULT_IGNORE_FILES),
    "ignore_globs": list(DEFAULT_IGNORE_GLOBS),
    "rules": [
        {"match": "core/**/*.py", "mode": "full"},
        {"match": "apps/**/*.py", "mode": "full"},
        {"match": "devtools/**/*.py", "mode": "interface"},
        {"match": "docs/**/*.md", "mode": "head", "head_lines": 240},
        {"match": "data/reports/**/*.md", "mode": "head", "head_lines": 260},
        {"match": "**/*", "mode": "skip"},
    ],
}

BUILTIN_TEMPLATES = {
    "llm": _LLM_TEMPLATE,
    "core": copy.deepcopy(_LLM_TEMPLATE),
    "archive": {
        "desc": "Builtin archive template",
        "output": "data/snapshots/archive_{timestamp}.md",
        "make_zip": True,
        "zip_output": "data/snapshots/archive_{timestamp}.zip",
        "redact": True,
        "include_reports": True,
        "hash": "all",
        "embed_order": "path",
        "sections": dict(DEFAULT_SECTIONS),
        "inventory": {"enabled": True, "scope": "all", "limit": 2000},
        "max_file_bytes": 500000,
        "max_total_bytes": 20000000,
        "tree": {"max_depth": 30, "max_entries_per_dir": 1000},
        "include_globs": ["**/*"],
        "ignore_files": sorted(DEFAULT_IGNORE_FILES),
        "ignore_globs": list(DEFAULT_IGNORE_GLOBS),
        "rules": [{"match": "**/*", "mode": "full"}],
    },
}



@dataclass
class FileRecord:
    rel_posix: str
    abs_path: Path
    size_bytes: int
    sha256_12: str
    mode: str

    # Rule-derived knobs (cached per file to avoid repeated rule scans)
    head_lines: int = 200
    per_file_max_bytes: int = 200000

    # Render-time metadata
    rendered_bytes: int = 0
    truncated: bool = False
    note: str = ""
    approx_tokens: int = 0


def _now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _run_cmd(cmd: str) -> str:
    try:
        return subprocess.check_output(
            cmd,
            shell=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "Unknown"


def get_system_fingerprint() -> str:
    info = []
    info.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    info.append(f"User: {os.getenv('USER', 'Unknown')}")
    info.append(f"Host: {platform.node()} ({platform.system()} {platform.release()})")
    info.append(f"Python: {platform.python_version()} ({sys.executable})")
    try:
        import rich  # type: ignore

        ver = getattr(rich, "__version__", "Installed (ver unknown)")
        info.append(f"Rich Ver: {ver}")
    except Exception:
        info.append("Rich Ver: Not Installed")
    return "\n".join(info)


def get_git_status() -> str:
    if not (PROJECT_ROOT / ".git").exists():
        return "Git: Not a repository"
    branch = _run_cmd("git rev-parse --abbrev-ref HEAD")
    commit = _run_cmd("git rev-parse --short HEAD")
    last_msg = _run_cmd("git log -1 --pretty=%B")
    is_dirty = _run_cmd("git status --porcelain") != ""
    dirty_mark = " [DIRTY]" if is_dirty else " [CLEAN]"
    return f"Branch: {branch}{dirty_mark}\nCommit: {commit}\nMessage: {last_msg}"


def _is_probably_binary(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(2048)
        if b"\x00" in chunk:
            return True
        # Heuristic: if too many non-text bytes, treat as binary.
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
        nontext = chunk.translate(None, text_chars)
        return len(nontext) / max(len(chunk), 1) > 0.30
    except Exception:
        return True


_SECRET_KV_RE = re.compile(
    r"(?i)\b(password|passphrase|token|secret|api[_-]?key|client[_-]?secret|access[_-]?key)\b\s*[:=]\s*([^\n\r]+)"
)


def _redact(text: str) -> str:
    # Block private keys
    text = re.sub(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        "-----BEGIN PRIVATE KEY-----\n<REDACTED>\n-----END PRIVATE KEY-----",
        text,
        flags=re.DOTALL,
    )

    def _kv_sub(m: re.Match) -> str:
        key = m.group(1)
        return f"{key}=<REDACTED>"

    text = _SECRET_KV_RE.sub(_kv_sub, text)
    return text


def _sha256_12(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 256), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

DEFAULT_SHA_CACHE_PATH = PROJECT_ROOT / "data" / "snapshots" / ".snapshot_sha_cache.json"


def _load_sha_cache(cache_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load SHA cache from disk (best-effort)."""
    try:
        if cache_path.exists():
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                # Ensure nested dicts
                out: Dict[str, Dict[str, Any]] = {}
                for k, v in data.items():
                    if isinstance(k, str) and isinstance(v, dict):
                        out[k] = v
                return out
    except Exception:
        pass
    return {}


def _save_sha_cache(cache_path: Path, cache: Dict[str, Dict[str, Any]]) -> None:
    """Persist SHA cache to disk (best-effort)."""
    try:
        _ensure_parent(cache_path)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        # Cache is purely an optimization; ignore failures
        return


def _sha256_12_cached(path: Path, rel_posix: str, cache: Dict[str, Dict[str, Any]]) -> str:
    """Compute sha256_12 with a simple stat-based cache."""
    try:
        st = path.stat()
        mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
        size = int(st.st_size)
    except Exception:
        return "Unknown"

    entry = cache.get(rel_posix)
    if isinstance(entry, dict):
        try:
            if int(entry.get("mtime_ns", -1)) == mtime_ns and int(entry.get("size", -2)) == size:
                val = entry.get("sha256_12")
                if isinstance(val, str) and len(val) == 12:
                    return val
        except Exception:
            pass

    try:
        sha = _sha256_12(path)
    except Exception:
        sha = "Unknown"

    cache[rel_posix] = {"mtime_ns": mtime_ns, "size": size, "sha256_12": sha}
    return sha


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (useful for context-window sizing).

    Heuristic:
    - ASCII chars ~ 1 token / 4 chars
    - Non-ASCII chars ~ 1 token / char (works better for CJK)
    """
    if not text:
        return 0
    n = len(text)
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    ascii_cnt = n - non_ascii
    # ceil-ish without math import
    return int(non_ascii + (ascii_cnt + 3) // 4)


def _posix_rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _match_glob(rel_posix: str, pattern: str) -> bool:
    """Glob matching with stable ** semantics.

    Semantics:
    - If pattern has no '/', treat it as a basename pattern.
    - '**' matches 0..N path segments (unlike pathlib.Path.match which may require >=1).
    - Other segments use fnmatch-style wildcards.
    """
    rel_posix = rel_posix.lstrip("/")
    pattern = str(pattern or "").lstrip("/")

    if not pattern:
        return False

    # Basename-only pattern: match only the filename.
    if "/" not in pattern:
        name = rel_posix.rsplit("/", 1)[-1]
        return fnmatch.fnmatchcase(name, pattern)

    path_parts = rel_posix.split("/") if rel_posix else []
    pat_parts = pattern.split("/") if pattern else []

    def rec(i: int, j: int) -> bool:
        if i == len(pat_parts):
            return j == len(path_parts)

        pat = pat_parts[i]

        if pat == "**":
            # Match zero segments
            if rec(i + 1, j):
                return True
            # Match one segment and keep '**' active
            return j < len(path_parts) and rec(i, j + 1)

        if j >= len(path_parts):
            return False

        if fnmatch.fnmatchcase(path_parts[j], pat):
            return rec(i + 1, j + 1)

        return False

    return rec(0, 0)

def _load_templates(config_path: Path) -> Dict[str, Any]:
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("templates"), dict):
                return data
        except Exception:
            pass
    # Fallback
    return {
        "version": 1,
        "defaults": {
            "mode_to_template": {
                "llm": "llm",
                "core": "llm",
                "archive": "archive",
                "custom": "llm",
            }
        },
        "templates": BUILTIN_TEMPLATES,
    }


def _resolve_template(templates_doc: Dict[str, Any], mode: str, template_name: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    templates = templates_doc.get("templates", {})
    if template_name:
        if template_name not in templates:
            raise SystemExit(f"Unknown template: {template_name}")
        return template_name, templates[template_name]

    defaults = templates_doc.get("defaults", {}).get("mode_to_template", {})
    picked = defaults.get(mode, mode)
    if picked in templates:
        return picked, templates[picked]

    if mode in templates:
        return mode, templates[mode]

    # Compatibility: allow llm/core aliasing when only one exists.
    if mode == "core" and "llm" in templates:
        return "llm", templates["llm"]
    if mode == "llm" and "core" in templates:
        return "core", templates["core"]

    # Fallback to core
    return "core", templates.get("core", BUILTIN_TEMPLATES["core"])


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _dedupe_list(items: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for item in items:
        s = str(item)
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _normalize_focus_globs(raw: Iterable[str]) -> List[str]:
    globs: List[str] = []
    for val in raw:
        s = str(val).strip()
        if not s:
            continue
        s = s.replace("\\", "/").lstrip("/")
        if re.search(r"[*?\[]", s):
            globs.append(s)
            continue
        p = (PROJECT_ROOT / s).resolve()
        try:
            rel = p.relative_to(PROJECT_ROOT).as_posix()
        except Exception:
            rel = s
        if p.exists():
            if p.is_dir():
                globs.append(rel.rstrip("/") + "/**")
            else:
                globs.append(rel)
        else:
            globs.append(s)
    return _dedupe_list(globs)


def _simplify_include_globs(include_globs: List[str]) -> List[str]:
    globs = [str(g).strip() for g in (include_globs or []) if str(g).strip()]
    out: List[str] = []
    seen: set[str] = set()
    for g in globs:
        if g in seen:
            continue
        seen.add(g)
        out.append(g)

    # Common redundancy: if include-all is present, additional include globs are unnecessary
    if any(g in {"**", "**/*"} for g in out):
        return ["**/*"]

    return out


def _derive_prunable_ignore_prefixes(ignore_globs: List[str]) -> List[str]:
    """Best-effort directory pruning from ignore globs.

    If an ignore glob is of the form 'path/to/dir/**' (no wildcard in the prefix),
    we can prune that subtree during os.walk for speed.
    """
    prefixes: List[str] = []
    wildcard_re = re.compile(r"[*?\[]")
    for pat in ignore_globs or []:
        pat = str(pat).strip().lstrip("/")
        if not pat:
            continue
        if not pat.endswith("/**") and not pat.endswith("/**/*"):
            continue
        prefix = pat[:-3] if pat.endswith("/**") else pat[:-5]
        if not prefix:
            continue
        if wildcard_re.search(prefix):
            continue
        prefixes.append(prefix)
    # Longer prefixes first to match more specifically
    prefixes.sort(key=len, reverse=True)
    return prefixes


def _iter_candidates(
    include_globs: List[str],
    *,
    ignore_dirs: set[str],
    ignore_files: set[str],
    ignore_globs: List[str],
) -> List[Path]:
    """Iterate candidate files with a single filesystem walk.

    This is substantially faster than multiple Path.glob() passes when include_globs grows.
    """
    include_globs = _simplify_include_globs(include_globs)
    if not include_globs:
        return []

    include_all = include_globs == ["**/*"]

    # Separate basename patterns (no '/') vs full path patterns
    basename_pats: List[str] = []
    path_pats: List[str] = []
    if not include_all:
        for pat in include_globs:
            if "/" in pat:
                path_pats.append(pat)
            else:
                basename_pats.append(pat)

    prunable_prefixes = _derive_prunable_ignore_prefixes(ignore_globs)

    files: List[Path] = []

    for root, dirs, filenames in os.walk(PROJECT_ROOT, topdown=True, followlinks=False):
        # Rel path for pruning (posix)
        try:
            rel_root = Path(root).relative_to(PROJECT_ROOT).as_posix()
        except Exception:
            rel_root = ""

        # Prune by ignore_dirs (name-based)
        if dirs:
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

        # Prune by ignore_globs-derived subtree prefixes
        if rel_root:
            for pref in prunable_prefixes:
                if rel_root == pref or rel_root.startswith(pref + "/"):
                    dirs[:] = []
                    filenames = []
                    break

        for name in filenames:
            if name in ignore_files:
                continue

            abs_path = Path(root) / name
            try:
                rel = abs_path.relative_to(PROJECT_ROOT).as_posix()
            except Exception:
                continue

            # Ignore globs (fast reject)
            ignored = False
            for pat in ignore_globs:
                if _match_glob(rel, pat):
                    ignored = True
                    break
            if ignored:
                continue

            # Include filter
            if include_all:
                files.append(abs_path)
                continue

            ok = False
            if basename_pats:
                for pat in basename_pats:
                    if fnmatch.fnmatchcase(name, pat):
                        ok = True
                        break
            if (not ok) and path_pats:
                for pat in path_pats:
                    if _match_glob(rel, pat):
                        ok = True
                        break
            if ok:
                files.append(abs_path)

    files.sort(key=lambda p: _posix_rel(p))
    return files


def _should_ignore(path: Path, ignore_files: set[str], ignore_globs: List[str], ignore_dirs: set[str]) -> bool:
    """Return True if a file path should be ignored."""
    try:
        rel = _posix_rel(path)
    except Exception:
        return True

    # Ignore by directory segment (relative path only)
    parts = rel.split("/")
    for seg in parts[:-1]:
        if seg in ignore_dirs:
            return True

    if path.name in ignore_files:
        return True

    for pat in ignore_globs:
        if _match_glob(rel, pat):
            return True

    return False


def _pick_rule(rel_posix: str, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    for r in rules:
        pat = r.get("match")
        if not pat:
            continue
        if _match_glob(rel_posix, pat):
            return r
    return {"mode": "skip"}


def _read_text_limited(path: Path, max_bytes: int) -> Tuple[str, bool]:
    # Returns (text, truncated)
    size = path.stat().st_size
    truncated = size > max_bytes
    with open(path, "rb") as f:
        data = f.read(max_bytes if truncated else size)
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception:
        text = data.decode(errors="replace")
    return text, truncated


def _read_head_lines(path: Path, head_lines: int) -> Tuple[str, bool]:
    lines: List[str] = []
    truncated = False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= head_lines:
                    truncated = True
                    break
                lines.append(line.rstrip("\n"))
    except Exception:
        # binary or unreadable
        return "[Unreadable]", True
    return "\n".join(lines), truncated


def _safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)  # type: ignore[attr-defined]
    except Exception:
        return "..."


def _format_args(args: ast.arguments) -> str:
    parts: List[str] = []

    def fmt_arg(a: ast.arg, default: Optional[ast.AST]) -> str:
        s = a.arg
        if a.annotation is not None:
            s += f": {_safe_unparse(a.annotation)}"
        if default is not None:
            d = _safe_unparse(default)
            if len(d) > 40:
                d = d[:37] + "..."
            s += f"={d}"
        return s

    # Positional-only
    posonly = getattr(args, "posonlyargs", [])
    if posonly:
        defaults_pad = [None] * (len(posonly) + len(args.args) - len(args.defaults)) + list(args.defaults)
        for a, d in zip(posonly, defaults_pad[: len(posonly)]):
            parts.append(fmt_arg(a, d))
        parts.append("/")

    # Positional or keyword
    all_pos = list(args.args)
    defaults_pad = [None] * (len(posonly) + len(all_pos) - len(args.defaults)) + list(args.defaults)
    # defaults for args start after posonly
    for idx, a in enumerate(all_pos):
        d = defaults_pad[len(posonly) + idx]
        parts.append(fmt_arg(a, d))

    # vararg
    if args.vararg is not None:
        va = "*" + args.vararg.arg
        if args.vararg.annotation is not None:
            va += f": {_safe_unparse(args.vararg.annotation)}"
        parts.append(va)
    elif args.kwonlyargs:
        parts.append("*")

    # kw-only
    for a, d in zip(args.kwonlyargs, args.kw_defaults):
        parts.append(fmt_arg(a, d))

    # kwarg
    if args.kwarg is not None:
        ka = "**" + args.kwarg.arg
        if args.kwarg.annotation is not None:
            ka += f": {_safe_unparse(args.kwarg.annotation)}"
        parts.append(ka)

    return ", ".join(parts)


def _first_doc_line(doc: Optional[str], max_len: int = 120) -> str:
    if not doc:
        return ""
    line = doc.strip().splitlines()[0].strip()
    if len(line) > max_len:
        line = line[: max_len - 3] + "..."
    return line


def _extract_python_interface(path: Path, max_chars: int = 40000) -> str:
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except Exception as e:
        head, _ = _read_head_lines(path, 200)
        return f"# [Interface Extraction Failed]\n# {e}\n\n" + head

    out: List[str] = []
    mod_doc = ast.get_docstring(tree)
    if mod_doc:
        out.append('"""' + _first_doc_line(mod_doc) + '"""')
        out.append("")

    # Constants (simple Assign to ALLCAPS)
    consts: List[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.isupper():
                    try:
                        v = _safe_unparse(node.value)
                        if len(v) > 80:
                            v = v[:77] + "..."
                        consts.append(f"{t.id} = {v}")
                    except Exception:
                        consts.append(f"{t.id} = ...")
    if consts:
        out.append("# Constants")
        out.extend(consts[:40])
        if len(consts) > 40:
            out.append(f"# ... {len(consts)-40} more")
        out.append("")

    # Functions / Classes
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            sig = _format_args(node.args)
            ret = f" -> {_safe_unparse(node.returns)}" if node.returns is not None else ""
            doc = _first_doc_line(ast.get_docstring(node))
            out.append(f"def {node.name}({sig}){ret}:")
            out.append(f"    \"\"\"{doc}\"\"\"" if doc else "    ...")
            out.append("")
        elif isinstance(node, ast.ClassDef):
            bases = [
                _safe_unparse(b)
                for b in node.bases
                if not (isinstance(b, ast.Name) and b.id == "object")
            ]
            base_s = f"({', '.join(bases)})" if bases else ""
            doc = _first_doc_line(ast.get_docstring(node))
            out.append(f"class {node.name}{base_s}:")
            out.append(f"    \"\"\"{doc}\"\"\"" if doc else "    ...")

            # Methods
            methods: List[str] = []
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef):
                    if sub.name.startswith("__") and sub.name.endswith("__"):
                        continue
                    msig = _format_args(sub.args)
                    mret = f" -> {_safe_unparse(sub.returns)}" if sub.returns is not None else ""
                    mdoc = _first_doc_line(ast.get_docstring(sub))
                    line = f"    def {sub.name}({msig}){mret}:"
                    if mdoc:
                        line += f"  # {mdoc}"
                    methods.append(line)
            if methods:
                out.extend(methods[:60])
                if len(methods) > 60:
                    out.append(f"    # ... {len(methods)-60} more")
            out.append("")

    text = "\n".join(out).strip() + "\n"
    if len(text) > max_chars:
        return text[: max_chars - 200] + "\n\n# [TRUNCATED: interface too large]\n"
    return text


def _render_tree(root: Path, prefix: str, depth: int, max_depth: int, max_entries: int,
                 ignore_dirs: set[str], ignore_files: set[str], ignore_globs: List[str]) -> str:
    if depth > max_depth:
        return f"{prefix}└── ... (max depth reached)\n"

    try:
        children = [p for p in sorted(root.iterdir(), key=lambda p: p.name.lower())]
    except PermissionError:
        return f"{prefix}└── [Permission Denied]\n"

    # Filter ignored
    filtered: List[Path] = []
    for p in children:
        if p.name in ignore_dirs and p.is_dir():
            continue
        if p.name in ignore_files and p.is_file():
            continue
        rel = _posix_rel(p) if p.exists() else p.name
        if any(_match_glob(rel, pat) for pat in ignore_globs):
            continue
        filtered.append(p)

    omitted = 0
    if len(filtered) > max_entries:
        omitted = len(filtered) - max_entries
        filtered = filtered[:max_entries]

    lines: List[str] = []
    for i, p in enumerate(filtered):
        pointer = "├── " if i < len(filtered) - 1 else "└── "
        lines.append(f"{prefix}{pointer}{p.name}")
        if p.is_dir():
            extension = "│   " if pointer == "├── " else "    "
            sub = _render_tree(
                p,
                prefix=prefix + extension,
                depth=depth + 1,
                max_depth=max_depth,
                max_entries=max_entries,
                ignore_dirs=ignore_dirs,
                ignore_files=ignore_files,
                ignore_globs=ignore_globs,
            )
            lines.append(sub.rstrip("\n"))

    if omitted:
        lines.append(f"{prefix}└── ... ({omitted} entries omitted)")

    return "\n".join(lines) + "\n"


def _extract_registry_tools() -> Optional[List[Dict[str, Any]]]:
    reg_path = PROJECT_ROOT / "apps" / "cli" / "registry.py"
    if not reg_path.exists():
        return None
    try:
        src = reg_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "TOOLS":
                        return ast.literal_eval(node.value)  # type: ignore[arg-type]
    except Exception:
        return None
    return None


def _render_tools_overview(tools: Optional[List[Dict[str, Any]]]) -> str:
    if not tools:
        return "(registry tools not available)"

    # Keep it simple to control size.
    headers = ["alias", "file", "type", "desc", "usage"]
    rows: List[List[str]] = []
    for t in tools:
        rows.append([
            str(t.get("alias") or ""),
            str(t.get("file") or ""),
            str(t.get("type") or ""),
            str(t.get("desc") or ""),
            str(t.get("usage") or ""),
        ])

    # Column widths
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = min(48, max(widths[i], len(cell)))

    def fmt_row(r: List[str]) -> str:
        out = []
        for i, cell in enumerate(r):
            s = cell.replace("\n", " ").strip()
            if len(s) > widths[i]:
                s = s[: widths[i] - 3] + "..."
            out.append(s.ljust(widths[i]))
        return " | ".join(out)

    lines = [fmt_row(headers), "-+-".join(["-" * w for w in widths])]
    lines.extend(fmt_row(r) for r in rows)
    return "\n".join(lines)


def _render_project_status() -> str:
    status_path = PROJECT_ROOT / "PROJECT_STATUS.json"
    if not status_path.exists():
        return "No project status file found."

    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        return "Error reading project status."

    lines: List[str] = []

    manifesto = data.get("DEV_MANIFESTO") or data.get("guidelines") or []
    if isinstance(manifesto, list) and manifesto:
        lines.append("DEV MANIFESTO:")
        for rule in manifesto:
            lines.append(f"* {rule}")
        lines.append("-" * 20)

    objective = data.get("OBJECTIVE") or data.get("objective")
    lines.append(f"OBJECTIVE: {objective}")

    tasks_todo = data.get("TASKS_TODO")
    tasks_done = data.get("TASKS_DONE")
    if isinstance(tasks_todo, list) or isinstance(tasks_done, list):
        todo_list = tasks_todo if isinstance(tasks_todo, list) else []
        done_list = tasks_done if isinstance(tasks_done, list) else []
        if todo_list:
            lines.append("\nTASKS TODO:")
            for t in todo_list:
                lines.append(f"- {t}")
        if done_list:
            lines.append("\nTASKS DONE:")
            for t in done_list:
                lines.append(f"- {t}")
    else:
        tasks = data.get("tasks", [])
        if isinstance(tasks, list) and tasks:
            lines.append("\nTASKS:")
            for i, t in enumerate(tasks):
                if isinstance(t, dict):
                    mark = "[x]" if t.get("status") == "done" else "[ ]"
                    desc = t.get("desc")
                    lines.append(f"{i}. {mark} {desc}")
                else:
                    lines.append(f"- {t}")

    logs = data.get("RECENT_LOGS") or data.get("logs") or []
    if isinstance(logs, list) and logs:
        lines.append("\nRECENT LOGS:")
        for l in logs[-5:]:
            lines.append(f"- {l}")

    return "\n".join(lines)


def _render_file_inventory(records: List[FileRecord], limit: int = 500) -> str:
    # Inventory is useful for LLM context even if contents are truncated.
    headers = ["mode", "bytes", "sha256_12", "path"]

    rows: List[List[str]] = []
    for r in records[:limit]:
        rows.append([
            r.mode + ("*" if r.truncated else ""),
            str(r.size_bytes),
            r.sha256_12,
            r.rel_posix,
        ])
    if len(records) > limit:
        rows.append(["...", "", "", f"({len(records)-limit} more omitted)"])

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = min(80, max(widths[i], len(cell)))

    def fmt_row(row: List[str]) -> str:
        cells: List[str] = []
        for i, cell in enumerate(row):
            s = cell
            if len(s) > widths[i]:
                s = s[: widths[i] - 3] + "..."
            cells.append(s.ljust(widths[i]))
        return " | ".join(cells)

    lines = [fmt_row(headers), "-+-".join(["-" * w for w in widths])]
    lines.extend(fmt_row(r) for r in rows)
    return "\n".join(lines)


def _write_zip(zip_path: Path, records: List[FileRecord]) -> None:
    _ensure_parent(zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Include a manifest
        manifest = {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "files": [
                {
                    "path": r.rel_posix,
                    "mode": r.mode,
                    "size_bytes": r.size_bytes,
                    "sha256_12": r.sha256_12,
                }
                for r in records
                if r.mode != "skip"
            ],
        }
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        # Add raw files
        for r in records:
            if r.mode == "skip":
                continue
            # Only archive repo files (text), skip binaries defensively.
            if _is_probably_binary(r.abs_path):
                continue
            z.write(r.abs_path, arcname=r.rel_posix)


def main() -> None:
    parser = argparse.ArgumentParser(description="Wagstaff-Lab snapshot generator (llm/archive/custom via templates).")
    parser.add_argument("--mode", choices=["llm", "core", "archive", "custom"], default="llm")
    parser.add_argument("--template", help="Template name from conf/snapshot_templates.json")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to snapshot template config JSON")
    parser.add_argument("--output", help="Override output path")
    parser.add_argument("--list-templates", action="store_true", help="List available templates and exit")
    parser.add_argument("--focus", action="append", help="Limit snapshot to specific paths/globs (repeatable)")
    parser.add_argument("--no-redact", action="store_true", help="Disable secret redaction")
    parser.add_argument("--zip", action="store_true", help="Force creating zip bundle when supported")
    parser.add_argument("--hash", choices=["all", "embedded", "none"], help="Override hashing mode (all/embedded/none)")
    parser.add_argument("--no-env", action="store_true", help="Disable environment diagnostics section")
    parser.add_argument("--no-overview", action="store_true", help="Disable project overview section")
    parser.add_argument("--no-tree", action="store_true", help="Disable project tree section")
    parser.add_argument("--no-inventory", action="store_true", help="Disable file inventory section")
    parser.add_argument("--no-contents", action="store_true", help="Disable file contents section")
    parser.add_argument("--no-stats", action="store_true", help="Disable snapshot stats section")
    parser.add_argument("--verbose", action="store_true", help="Include template config section")
    parser.add_argument("--plan", action="store_true", help="Print a JSON plan summary and exit (no snapshot written)")

    args = parser.parse_args()

    t0 = time.perf_counter()

    cfg_path = Path(args.config)
    templates_doc = _load_templates(cfg_path)

    if args.list_templates:
        tpls = templates_doc.get("templates", {})
        print("Available templates:")
        for name, t in sorted(tpls.items(), key=lambda x: x[0]):
            print(f"- {name}: {t.get('desc', '')}")
        return

    tpl_name, tpl = _resolve_template(templates_doc, args.mode, args.template)

    ts = _now_ts()

    out_str = args.output or str(tpl.get("output", "project_context.txt"))
    out_str = out_str.replace("{timestamp}", ts)
    output_path = PROJECT_ROOT / out_str

    make_zip = bool(tpl.get("make_zip", False)) or bool(args.zip)
    zip_output = tpl.get("zip_output")
    zip_path: Optional[Path] = None
    if make_zip:
        if isinstance(zip_output, str) and zip_output:
            zip_path = PROJECT_ROOT / zip_output.replace("{timestamp}", ts)
        else:
            zip_path = output_path.with_suffix(".zip")

    # Template controls
    focus_globs = _normalize_focus_globs(args.focus or [])
    include_globs = _simplify_include_globs(list(tpl.get("include_globs") or []))
    if focus_globs:
        include_globs = _simplify_include_globs(
            ["PROJECT_STATUS.json", "README.md", "conf/settings.ini"] + focus_globs
        )

    ignore_dirs = set(DEFAULT_IGNORE_DIRS) | set(tpl.get("ignore_dirs") or [])
    ignore_files = set(tpl.get("ignore_files") or list(DEFAULT_IGNORE_FILES))
    ignore_globs = list(tpl.get("ignore_globs") or list(DEFAULT_IGNORE_GLOBS))

    # Always ignore generated artifacts to avoid snapshot recursion
    ignore_files.add(output_path.name)
    if zip_path is not None:
        ignore_files.add(zip_path.name)
        try:
            ignore_globs.append(zip_path.relative_to(PROJECT_ROOT).as_posix())
        except Exception:
            pass

    # Optional reports toggle (hard exclude)
    if not bool(tpl.get("include_reports", True)):
        ignore_globs.append("data/reports/**")

    redact_enabled = bool(tpl.get("redact", True)) and (not args.no_redact)

    max_file_bytes = int(tpl.get("max_file_bytes", 200000))
    max_total_bytes = int(tpl.get("max_total_bytes", 1200000))

    tree_cfg = tpl.get("tree") or {}
    tree_max_depth = int(tree_cfg.get("max_depth", 8))
    tree_max_entries = int(tree_cfg.get("max_entries_per_dir", 250))

    rules = list(tpl.get("rules") or [])
    if focus_globs:
        focus_rules = [{"match": pat, "mode": "full"} for pat in focus_globs]
        rules = focus_rules + rules

    # Hashing / ordering / inventory knobs
    hash_mode = str(args.hash or tpl.get("hash") or tpl.get("hash_mode") or "all").strip().lower()
    if hash_mode not in {"all", "embedded", "none"}:
        hash_mode = "all"

    embed_order = str(tpl.get("embed_order", "path")).strip().lower()
    if embed_order not in {"path", "mode", "smart"}:
        embed_order = "path"

    pinned = list(tpl.get("pinned") or [])
    if focus_globs:
        pinned = _dedupe_list(focus_globs + pinned)

    tpl_sections = tpl.get("sections")
    if isinstance(tpl_sections, dict):
        sections = dict(DEFAULT_SECTIONS)
        for key, val in tpl_sections.items():
            if key in sections:
                sections[key] = bool(val)
    else:
        sections = dict(LLM_SECTIONS if args.mode in {"llm", "core"} else DEFAULT_SECTIONS)

    if args.verbose:
        sections["config"] = True
    if args.no_env:
        sections["env"] = False
    if args.no_overview:
        sections["overview"] = False
    if args.no_tree:
        sections["tree"] = False
    if args.no_inventory:
        sections["inventory"] = False
    if args.no_contents:
        sections["contents"] = False
    if args.no_stats:
        sections["stats"] = False

    inv_cfg = tpl.get("inventory") or {}
    inv_enabled = bool(inv_cfg.get("enabled", True)) and sections["inventory"]
    inv_scope = str(inv_cfg.get("scope", "all")).strip().lower()
    inv_limit = int(inv_cfg.get("limit", 700))

    sha_cache_path = DEFAULT_SHA_CACHE_PATH
    if isinstance(tpl.get("hash_cache"), str) and tpl.get("hash_cache"):
        sha_cache_path = PROJECT_ROOT / str(tpl.get("hash_cache"))

    sha_cache: Dict[str, Dict[str, Any]] = {}
    if hash_mode in {"all", "embedded"}:
        sha_cache = _load_sha_cache(sha_cache_path)

    if not args.plan:
        print(f"📸 Generating snapshot: mode={args.mode}, template={tpl_name}, output={output_path}")

    # 1) Collect candidates (single walk, already filtered by ignore_files/ignore_globs/ignore_dirs)
    t_scan0 = time.perf_counter()
    candidates = _iter_candidates(
        include_globs,
        ignore_dirs=ignore_dirs,
        ignore_files=ignore_files,
        ignore_globs=ignore_globs,
    )
    t_scan_ms = int((time.perf_counter() - t_scan0) * 1000)

    records: List[FileRecord] = []
    t_rec0 = time.perf_counter()
    for p in candidates:
        rel = _posix_rel(p)
        rule = _pick_rule(rel, rules)
        mode = str(rule.get("mode", "skip")).strip() or "skip"
        if mode not in {"full", "interface", "head", "skip"}:
            mode = "skip"

        try:
            size = p.stat().st_size
        except Exception:
            continue

        head_lines = int(rule.get("head_lines", 200))
        per_file = int(rule.get("max_file_bytes", max_file_bytes))

        sha = "-"
        if hash_mode == "all" and mode != "skip":
            sha = _sha256_12_cached(p, rel, sha_cache)

        records.append(
            FileRecord(
                rel_posix=rel,
                abs_path=p,
                size_bytes=size,
                sha256_12=sha,
                mode=mode,
                head_lines=head_lines,
                per_file_max_bytes=per_file,
            )
        )

    t_rec_ms = int((time.perf_counter() - t_rec0) * 1000)

    # Plan mode: emit JSON and exit (no file I/O except optional SHA cache)
    if args.plan:
        by_mode: Dict[str, Dict[str, int]] = {}
        for r in records:
            d = by_mode.setdefault(r.mode, {"count": 0, "size_bytes": 0})
            d["count"] += 1
            d["size_bytes"] += int(r.size_bytes)

        non_skip = [r for r in records if r.mode != "skip"]
        top_large = sorted(non_skip, key=lambda r: r.size_bytes, reverse=True)[:20]

        plan = {
            "mode": args.mode,
            "template": tpl_name,
            "config_file": str(cfg_path),
            "output": str(output_path.relative_to(PROJECT_ROOT)),
            "zip": {
                "enabled": bool(zip_path is not None),
                "output": str(zip_path.relative_to(PROJECT_ROOT)) if zip_path is not None else None,
            },
            "redact_enabled": redact_enabled,
            "hash_mode": hash_mode,
            "embed_order": embed_order,
            "sections": sections,
            "focus": focus_globs,
            "limits": {"max_file_bytes": max_file_bytes, "max_total_bytes": max_total_bytes},
            "tree": {"max_depth": tree_max_depth, "max_entries_per_dir": tree_max_entries},
            "include_globs": include_globs,
            "ignore_dirs": sorted(ignore_dirs),
            "ignore_files": sorted(ignore_files),
            "ignore_globs": ignore_globs,
            "rules_count": len(rules),
            "total_candidates": len(candidates),
            "included_records": len(records),
            "by_mode": by_mode,
            "timing_ms": {"scan": t_scan_ms, "records": t_rec_ms, "total": int((time.perf_counter() - t0) * 1000)},
            "top_largest_non_skip": [
                {"path": r.rel_posix, "mode": r.mode, "size_bytes": r.size_bytes} for r in top_large
            ],
        }

        if hash_mode == "all":
            _save_sha_cache(sha_cache_path, sha_cache)

        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    # 2) Build report
    report: List[str] = []
    report.append("# Wagstaff-Lab Project Snapshot")
    report.append("")
    report.append(f"- Generated: {datetime.now().isoformat(timespec='seconds')}")
    report.append(f"- Mode: {args.mode}")
    report.append(f"- Template: {tpl_name}")
    if focus_globs:
        report.append(f"- Focus: {', '.join(focus_globs)}")

    section_idx = 0

    def add_section(title: str) -> None:
        nonlocal section_idx
        section_idx += 1
        report.append(f"\n## {section_idx}. {title}")

    eff = {
        "mode": args.mode,
        "template": tpl_name,
        "config_file": str(cfg_path),
        "output": str(output_path.relative_to(PROJECT_ROOT)),
        "zip": {
            "enabled": bool(zip_path is not None),
            "output": str(zip_path.relative_to(PROJECT_ROOT)) if zip_path is not None else None,
        },
        "redact_enabled": redact_enabled,
        "hash_mode": hash_mode,
        "embed_order": embed_order,
        "limits": {"max_file_bytes": max_file_bytes, "max_total_bytes": max_total_bytes},
        "tree": {"max_depth": tree_max_depth, "max_entries_per_dir": tree_max_entries},
        "glob_semantics": {"**": "matches 0..N path segments"},
        "include_globs": include_globs,
        "ignore_dirs": sorted(ignore_dirs),
        "ignore_files": sorted(ignore_files),
        "ignore_globs": ignore_globs,
        "rules": rules,
        "sections": sections,
        "focus": focus_globs,
        "inventory": {"enabled": inv_enabled, "scope": inv_scope, "limit": inv_limit},
        "pinned": pinned,
    }

    if sections["config"]:
        add_section("Effective Template Config")
        report.append("```json")
        report.append(json.dumps(eff, ensure_ascii=False, indent=2))
        report.append("```")

    if sections["env"]:
        add_section("Environment Diagnostics")
        report.append("```yaml")
        report.append(get_system_fingerprint())
        report.append("-" * 20)
        report.append(get_git_status())
        report.append("```")

    if sections["overview"]:
        add_section("Project Overview")
        report.append("### Toolbox (apps/cli/registry.py)")
        report.append("```text")
        report.append(_render_tools_overview(_extract_registry_tools()))
        report.append("```")

        report.append("\n### Project Context (PROJECT_STATUS.json)")
        report.append("```text")
        report.append(_render_project_status())
        report.append("```")

    if sections["tree"]:
        add_section("Project Structure")
        report.append("```text")
        report.append(
            _render_tree(
                PROJECT_ROOT,
                prefix="",
                depth=0,
                max_depth=tree_max_depth,
                max_entries=tree_max_entries,
                ignore_dirs=ignore_dirs,
                ignore_files=ignore_files,
                ignore_globs=ignore_globs,
            ).rstrip("\n")
        )
        report.append("```")

    if inv_enabled:
        add_section("File Inventory")
        report.append("(mode: full/interface/head/skip; '*' means truncated when rendered)\n")
        report.append("```text")
        inv_records: List[FileRecord]
        if inv_scope in {"included", "non_skip", "nonskip"}:
            inv_records = [r for r in records if r.mode != "skip"]
        else:
            inv_records = records
        report.append(_render_file_inventory(inv_records, limit=inv_limit))
        report.append("```")

    t_render_ms = 0
    budget = max_total_bytes
    embedded_files = 0
    approx_total_tokens = 0

    if sections["contents"]:
        add_section("File Contents")

        # 3) Emit contents within budget
        t_render0 = time.perf_counter()

        embed_records = [r for r in records if r.mode != "skip"]

        def mode_prio(m: str) -> int:
            return {"full": 0, "interface": 1, "head": 2}.get(m, 9)

        if embed_order == "mode":
            embed_records.sort(key=lambda r: (mode_prio(r.mode), r.rel_posix))
        elif embed_order == "smart":
            def pin_rank(r: FileRecord) -> int:
                if not pinned:
                    return 10_000
                for i, pat in enumerate(pinned):
                    if pat and _match_glob(r.rel_posix, str(pat)):
                        return i
                return 10_000
            embed_records.sort(key=lambda r: (pin_rank(r), mode_prio(r.mode), r.rel_posix))
        # else: "path" keeps as-is (already sorted by path)

        for rec in embed_records:
            if _is_probably_binary(rec.abs_path):
                rec.note = "[skipped: binary]"
                continue

            mode = rec.mode
            content = ""
            truncated = False

            if mode == "head":
                content, truncated = _read_head_lines(rec.abs_path, head_lines=rec.head_lines)
            elif mode == "interface":
                if rec.abs_path.suffix.lower() == ".py":
                    content = _extract_python_interface(rec.abs_path)
                    truncated = False
                else:
                    content, truncated = _read_head_lines(rec.abs_path, head_lines=rec.head_lines)
            elif mode == "full":
                content, truncated = _read_text_limited(rec.abs_path, max_bytes=rec.per_file_max_bytes)
            else:
                continue

            if redact_enabled:
                content = _redact(content)

            # Optionally hash only embedded files
            if hash_mode == "embedded" and rec.sha256_12 == "-":
                rec.sha256_12 = _sha256_12_cached(rec.abs_path, rec.rel_posix, sha_cache)

            # Rough byte count for budget
            render_blob = content.encode("utf-8", errors="replace")
            needed = len(render_blob)

            # Keep a small overhead for section headers
            needed += 200

            if budget - needed < 0:
                rec.note = "[omitted: total budget exceeded]"
                continue

            budget -= needed
            rec.rendered_bytes = needed
            rec.truncated = truncated

            tok = _estimate_tokens(content)
            rec.approx_tokens = tok
            approx_total_tokens += tok

            embedded_files += 1

            report.append(f"\n### File: {rec.rel_posix}")
            report.append(f"- mode: {mode}")
            report.append(f"- size_bytes: {rec.size_bytes}")
            report.append(f"- sha256_12: {rec.sha256_12}")
            if truncated:
                report.append("- note: TRUNCATED")
            if rec.note and rec.note not in {"[skipped: binary]"}:
                report.append(f"- note: {rec.note}")
            report.append("")

            # code fence lang
            lang = rec.abs_path.suffix.lstrip(".")
            if lang == "ini":
                lang = "toml"
            if mode == "interface":
                lang = "py"

            report.append(f"```{lang}")
            report.append(content.rstrip("\n"))
            report.append("```")

        t_render_ms = int((time.perf_counter() - t_render0) * 1000)

    if sections["stats"]:
        add_section("Snapshot Stats")
        report.append("```yaml")
        report.append(f"total_candidates: {len(candidates)}")
        report.append(f"included_records: {len(records)}")
        report.append(f"embedded_files: {embedded_files}")
        report.append(f"hash_mode: {hash_mode}")
        report.append(f"embed_order: {embed_order}")
        report.append(f"timing_ms: {{scan: {t_scan_ms}, records: {t_rec_ms}, render: {t_render_ms}, total: {int((time.perf_counter() - t0) * 1000)}}}")
        report.append(f"approx_total_tokens: {approx_total_tokens}")
        report.append(f"max_total_bytes: {max_total_bytes}")
        report.append(f"bytes_remaining: {budget}")
        report.append("```")

    # 4) Write output
    _ensure_parent(output_path)
    output_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"✅ Snapshot written: {output_path}")

    # Persist SHA cache (optimization only)
    if hash_mode in {"all", "embedded"}:
        _save_sha_cache(sha_cache_path, sha_cache)

    # 5) Optional zip bundle
    if zip_path is not None:
        try:
            _write_zip(zip_path, records)
            print(f"✅ Zip bundle written: {zip_path}")
        except Exception as e:
            print(f"⚠️  Zip bundle failed: {e}")


if __name__ == "__main__":
    main()

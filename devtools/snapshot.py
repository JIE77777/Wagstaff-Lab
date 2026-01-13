#!/usr/bin/env python3
"""Wagstaff-Lab Snapshot (v4)

Goal:
- Provide two primary modes:
  - core: LLM-friendly snapshot (project overview + core code full + non-core interfaces/head)
  - archive: archival snapshot (full content as much as possible + optional zip bundle)
- Provide custom templates via JSON config (growth-friendly).

Default behavior:
- `wagstaff snap` => core template => writes project_context.txt

Template config:
- Default path: conf/snapshot_templates.json
- See the example template file for schema.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import textwrap
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
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

# Minimal built-in templates (used if conf/snapshot_templates.json is missing).
BUILTIN_TEMPLATES = {
    "core": {
        "desc": "Builtin core template",
        "output": "project_context.txt",
        "redact": True,
        "include_reports": True,
        "max_file_bytes": 200000,
        "max_total_bytes": 1200000,
        "tree": {"max_depth": 8, "max_entries_per_dir": 250},
        "include_globs": [
            "README.md",
            "PROJECT_STATUS.json",
            ".gitignore",
            "conf/**/*.ini",
            "src/**/*.py",
            "devtools/**/*.py",
            "tests/**/*.py",
            "bin/**",
            "data/reports/**/*.md",
            "data/samples/**/*",
        ],
        "ignore_files": sorted(DEFAULT_IGNORE_FILES),
        "ignore_globs": list(DEFAULT_IGNORE_GLOBS),
        "rules": [
            {"match": "src/**/*.py", "mode": "full"},
            {"match": "devtools/**/*.py", "mode": "interface"},
            {"match": "bin/**", "mode": "head", "head_lines": 160},
            {"match": "data/reports/**/*.md", "mode": "head", "head_lines": 260},
            {"match": "**/*", "mode": "skip"},
        ],
    },
    "archive": {
        "desc": "Builtin archive template",
        "output": "data/snapshots/archive_{timestamp}.md",
        "make_zip": True,
        "zip_output": "data/snapshots/archive_{timestamp}.zip",
        "redact": True,
        "include_reports": True,
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
    rendered_bytes: int = 0
    truncated: bool = False
    note: str = ""


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


def _posix_rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _match_glob(rel_posix: str, pattern: str) -> bool:
    # Prefer pathlib's match to get ** semantics.
    try:
        return PurePosixPath(rel_posix).match(pattern)
    except Exception:
        return fnmatch.fnmatch(rel_posix, pattern)


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
        "defaults": {"mode_to_template": {"core": "core", "archive": "archive", "custom": "core"}},
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

    # Fallback to core
    return "core", templates.get("core", BUILTIN_TEMPLATES["core"])


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _iter_candidates(include_globs: List[str]) -> List[Path]:
    files: List[Path] = []
    seen: set[str] = set()
    for pattern in include_globs:
        for p in PROJECT_ROOT.glob(pattern):
            if p.is_dir():
                continue
            try:
                rel = _posix_rel(p)
            except Exception:
                continue
            if rel in seen:
                continue
            seen.add(rel)
            files.append(p)
    files.sort(key=lambda x: _posix_rel(x))
    return files


def _should_ignore(path: Path, ignore_files: set[str], ignore_globs: List[str], ignore_dirs: set[str]) -> bool:
    # Fast dir ignore
    parts = set(path.parts)
    if parts & ignore_dirs:
        return True

    if path.name in ignore_files:
        return True

    rel = _posix_rel(path)
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
    reg_path = PROJECT_ROOT / "src" / "registry.py"
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
    if data.get("guidelines"):
        lines.append("DEV MANIFESTO:")
        for rule in data["guidelines"]:
            lines.append(f"* {rule}")
        lines.append("-" * 20)

    lines.append(f"OBJECTIVE: {data.get('objective')}")

    tasks = data.get("tasks", [])
    if tasks:
        lines.append("\nTASKS:")
        for i, t in enumerate(tasks):
            mark = "[x]" if t.get("status") == "done" else "[ ]"
            lines.append(f"{i}. {mark} {t.get('desc')}")

    logs = data.get("logs", [])
    if logs:
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
    parser = argparse.ArgumentParser(description="Wagstaff-Lab snapshot generator (core/archive/custom via templates).")
    parser.add_argument("--mode", choices=["core", "archive", "custom"], default="core")
    parser.add_argument("--template", help="Template name from conf/snapshot_templates.json")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to snapshot template config JSON")
    parser.add_argument("--output", help="Override output path")
    parser.add_argument("--list-templates", action="store_true", help="List available templates and exit")
    parser.add_argument("--no-redact", action="store_true", help="Disable secret redaction")
    parser.add_argument("--zip", action="store_true", help="Force creating zip bundle when supported")

    args = parser.parse_args()

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
    include_globs = list(tpl.get("include_globs") or [])
    ignore_files = set(tpl.get("ignore_files") or list(DEFAULT_IGNORE_FILES))
    ignore_globs = list(tpl.get("ignore_globs") or list(DEFAULT_IGNORE_GLOBS))

    # Optional reports toggle
    if not bool(tpl.get("include_reports", True)):
        ignore_globs.append("data/reports/**")

    redact_enabled = bool(tpl.get("redact", True)) and (not args.no_redact)

    max_file_bytes = int(tpl.get("max_file_bytes", 200000))
    max_total_bytes = int(tpl.get("max_total_bytes", 1200000))

    tree_cfg = tpl.get("tree") or {}
    tree_max_depth = int(tree_cfg.get("max_depth", 8))
    tree_max_entries = int(tree_cfg.get("max_entries_per_dir", 250))

    rules = list(tpl.get("rules") or [])

    print(f"📸 Generating snapshot: mode={args.mode}, template={tpl_name}, output={output_path}")

    # 1) Collect candidates
    candidates = _iter_candidates(include_globs)

    records: List[FileRecord] = []
    for p in candidates:
        if _should_ignore(p, ignore_files, ignore_globs, DEFAULT_IGNORE_DIRS):
            continue
        rel = _posix_rel(p)
        rule = _pick_rule(rel, rules)
        mode = str(rule.get("mode", "skip"))
        try:
            size = p.stat().st_size
        except Exception:
            continue
        sha = "-"
        try:
            # Hashing is useful, but avoid expensive work for skipped files.
            if mode != "skip":
                sha = _sha256_12(p)
        except Exception:
            sha = "Unknown"
        records.append(FileRecord(rel_posix=rel, abs_path=p, size_bytes=size, sha256_12=sha, mode=mode))

    # 2) Build report
    report: List[str] = []
    report.append("# Wagstaff-Lab Project Snapshot")
    report.append("")
    report.append(f"- Generated: {datetime.now().isoformat(timespec='seconds')}")
    report.append(f"- Mode: {args.mode}")
    report.append(f"- Template: {tpl_name}")

    report.append("\n## 1. Environment Diagnostics")
    report.append("```yaml")
    report.append(get_system_fingerprint())
    report.append("-" * 20)
    report.append(get_git_status())
    report.append("```")

    report.append("\n## 2. Project Overview")
    report.append("### 2.1 Toolbox (src/registry.py)")
    report.append("```text")
    report.append(_render_tools_overview(_extract_registry_tools()))
    report.append("```")

    report.append("\n### 2.2 Project Context (PROJECT_STATUS.json)")
    report.append("```text")
    report.append(_render_project_status())
    report.append("```")

    report.append("\n## 3. Project Structure")
    report.append("```text")
    report.append(
        _render_tree(
            PROJECT_ROOT,
            prefix="",
            depth=0,
            max_depth=tree_max_depth,
            max_entries=tree_max_entries,
            ignore_dirs=DEFAULT_IGNORE_DIRS,
            ignore_files=ignore_files,
            ignore_globs=ignore_globs,
        ).rstrip("\n")
    )
    report.append("```")

    report.append("\n## 4. File Inventory")
    report.append("(mode: full/interface/head/skip; '*' means truncated when rendered)\n")
    report.append("```text")
    report.append(_render_file_inventory(records, limit=700))
    report.append("```")

    report.append("\n## 5. File Contents")

    # 3) Emit contents within budget
    budget = max_total_bytes
    embedded_files = 0

    for rec in records:
        if rec.mode == "skip":
            continue

        if _is_probably_binary(rec.abs_path):
            rec.note = "[skipped: binary]"
            continue

        rule = _pick_rule(rec.rel_posix, rules)
        mode = rec.mode
        head_lines = int(rule.get("head_lines", 200))

        content = ""
        truncated = False

        if mode == "head":
            content, truncated = _read_head_lines(rec.abs_path, head_lines=head_lines)
        elif mode == "interface":
            if rec.abs_path.suffix.lower() == ".py":
                content = _extract_python_interface(rec.abs_path)
                truncated = False
            else:
                content, truncated = _read_head_lines(rec.abs_path, head_lines=head_lines)
        elif mode == "full":
            per_file = int(rule.get("max_file_bytes", max_file_bytes))
            content, truncated = _read_text_limited(rec.abs_path, max_bytes=per_file)
        else:
            continue

        if redact_enabled:
            content = _redact(content)

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
        embedded_files += 1

        report.append(f"\n### File: {rec.rel_posix}")
        report.append(f"- mode: {mode}")
        report.append(f"- size_bytes: {rec.size_bytes}")
        report.append(f"- sha256_12: {rec.sha256_12}")
        if truncated:
            report.append(f"- note: TRUNCATED")
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

    report.append("\n## 6. Snapshot Stats")
    report.append("```yaml")
    report.append(f"total_candidates: {len(candidates)}")
    report.append(f"included_records: {len(records)}")
    report.append(f"embedded_files: {embedded_files}")
    report.append(f"max_total_bytes: {max_total_bytes}")
    report.append(f"bytes_remaining: {budget}")
    report.append("```")

    # 4) Write output
    _ensure_parent(output_path)
    output_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"✅ Snapshot written: {output_path}")

    # 5) Optional zip bundle
    if zip_path is not None:
        try:
            _write_zip(zip_path, records)
            print(f"✅ Zip bundle written: {zip_path}")
        except Exception as e:
            print(f"⚠️  Zip bundle failed: {e}")


if __name__ == "__main__":
    main()

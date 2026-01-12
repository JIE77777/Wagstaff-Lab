#!/usr/bin/env python3
"""
Wagstaff-Lab Snapshot Generator (v3)

Key upgrades:
- Path-safe: works no matter where you run it from
- Recursive scan via include/ignore globs
- Skip binary & guard against huge files (head/tail truncation)
- Basic secret redaction (KEY=..., KEY: ...)
- Per-file metadata: size + sha256 prefix
- Output summary + robust PROJECT_STATUS.json loading
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Iterable, List, Optional, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "project_context.txt"


# What to include (relative to PROJECT_ROOT)
DEFAULT_INCLUDE_GLOBS: List[str] = [
    "README.md",
    "setup.sh",
    "PROJECT_STATUS.json",
    ".gitignore",
    "conf/**/*.ini",
    "src/**/*.py",
    "devtools/**/*.py",
    "tests/**/*.py",
    "bin/**/*.sh",
    # wrapper scripts (no ext)
    "bin/Wagstaff-Lab",
    "bin/wagstaff",
    "bin/pm",
    # auto-generated reports (useful; can be disabled via --no-reports)
    "data/reports/**/*.md",
    # root docs
    "*.md",
    "*.txt",
]

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "logs",
    "env",
    "venv",
    ".venv",
    ".idea",
    ".vscode",
    "dist",
    "build",
}

# Exact filenames to ignore
DEFAULT_IGNORE_FILES = {
    "project_context.txt",
    ".DS_Store",
    "id_rsa",
    "id_ed25519",
    "known_hosts",
}

# Glob patterns (relative to PROJECT_ROOT) to ignore
DEFAULT_IGNORE_GLOBS: List[str] = [
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

# Basic secret-like keys to redact if they appear as KEY=... or KEY: ...
REDACT_KEYS = (
    "PASSWORD",
    "PASSWD",
    "PWD",
    "SECRET",
    "TOKEN",
    "API_KEY",
    "ACCESS_KEY",
    "PRIVATE_KEY",
    "OPENAI_API_KEY",
)


@dataclass(frozen=True)
class ReadResult:
    text: str
    truncated: bool
    size_bytes: int
    sha256_12: str


def _run_cmd(args: Sequence[str]) -> str:
    try:
        return subprocess.check_output(
            list(args),
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "Unknown"


def _is_git_repo() -> bool:
    return (PROJECT_ROOT / ".git").exists()


def get_system_fingerprint() -> str:
    info: List[str] = []
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    info.append(f"Time: {now}")
    info.append(f"User: {os.getenv('USER') or os.getenv('USERNAME') or 'Unknown'}")
    info.append(f"Host: {platform.node()} ({platform.system()} {platform.release()})")
    info.append(f"Platform: {platform.platform()}")
    info.append(f"Python: {platform.python_version()} ({sys.executable})")
    info.append(f"Conda Env: {os.getenv('CONDA_DEFAULT_ENV', 'None')}")
    try:
        import rich  # type: ignore
        ver = getattr(rich, "__version__", "Installed (ver unknown)")
        info.append(f"Rich Ver: {ver}")
    except Exception:
        info.append("Rich Ver: Not Installed")
    return "\n".join(info)


def get_git_status() -> str:
    if not _is_git_repo():
        return "Git: Not a repository"

    branch = _run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    commit = _run_cmd(["git", "rev-parse", "--short", "HEAD"])
    last_msg = _run_cmd(["git", "log", "-1", "--pretty=%B"]).replace("\n", " ").strip()

    porcelain = _run_cmd(["git", "status", "--porcelain"])
    is_dirty = porcelain not in ("", "Unknown")
    dirty_mark = " [DIRTY]" if is_dirty else " [CLEAN]"

    modified = 0
    untracked = 0
    if porcelain not in ("", "Unknown"):
        for line in porcelain.splitlines():
            if line.startswith("??"):
                untracked += 1
            else:
                modified += 1

    out = [
        f"Branch: {branch}{dirty_mark}",
        f"Commit: {commit}",
        f"Message: {last_msg}",
        f"Changes: modified={modified}, untracked={untracked}",
    ]

    diff_stat = _run_cmd(["git", "diff", "--stat"])
    if diff_stat not in ("", "Unknown"):
        lines = diff_stat.splitlines()
        if len(lines) > 20:
            lines = lines[:20] + ["... (diff --stat truncated)"]
        out.append("---")
        out.extend(lines)

    return "\n".join(out)


def _to_rel_posix(p: Path) -> PurePosixPath:
    rel = p.relative_to(PROJECT_ROOT)
    return PurePosixPath(rel.as_posix())


def _match_any(rel_posix: PurePosixPath, patterns: Iterable[str]) -> bool:
    for pat in patterns:
        if rel_posix.match(pat):
            return True
    return False


def should_ignore(path: Path, ignore_files: set[str], ignore_globs: Sequence[str]) -> bool:
    try:
        rel = _to_rel_posix(path)
    except Exception:
        return True

    if any(part in IGNORE_DIRS for part in rel.parts):
        return True

    if path.name in ignore_files:
        return True

    if _match_any(rel, ignore_globs):
        return True

    return False


def collect_files(
    include_globs: Sequence[str],
    ignore_files: set[str],
    ignore_globs: Sequence[str],
    include_reports: bool,
    output_file: Path,
) -> List[Path]:
    files: set[Path] = set()

    for pat in include_globs:
        if (not include_reports) and pat.startswith("data/reports/"):
            continue
        for p in PROJECT_ROOT.glob(pat):
            if p.is_file():
                files.add(p)

    files.discard(output_file)

    out = [p for p in files if not should_ignore(p, ignore_files, ignore_globs)]
    out.sort(key=lambda x: _to_rel_posix(x).as_posix())
    return out


def _looks_binary(sample: bytes) -> bool:
    if b"\x00" in sample:
        return True
    if not sample:
        return False
    text_chars = b"\t\n\r\b" + bytes(range(32, 127))
    nontext = sum(1 for b in sample if b not in text_chars)
    return (nontext / max(1, len(sample))) > 0.30


def _sha256_12(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def _redact(text: str) -> str:
    out_lines: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        upper = stripped.upper()

        # KEY=... or KEY: ...
        replaced = False
        for k in REDACT_KEYS:
            if upper.startswith(k + "=") or upper.startswith(k + ":"):
                sep = "=" if "=" in stripped else ":"
                prefix = stripped.split(sep, 1)[0]
                out_lines.append(f"{prefix}{sep} ***REDACTED***")
                replaced = True
                break
        if replaced:
            continue

        # obvious key blocks
        if "BEGIN" in upper and "PRIVATE KEY" in upper:
            out_lines.append("***REDACTED PRIVATE KEY BLOCK***")
            continue

        out_lines.append(line)

    return "\n".join(out_lines)


def read_file_snippet(
    path: Path,
    max_file_bytes: int,
    redact: bool,
) -> Optional[ReadResult]:
    try:
        size = path.stat().st_size
    except Exception:
        return None

    # binary guard
    try:
        with path.open("rb") as f:
            head = f.read(min(4096, size))
            if _looks_binary(head):
                return None
    except Exception:
        return None

    # hash (helps diff between snapshots)
    try:
        sha12 = _sha256_12(path)
    except Exception:
        sha12 = "Unknown"

    truncated = False
    try:
        if size <= max_file_bytes:
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            truncated = True
            head_bytes = max_file_bytes
            tail_bytes = max_file_bytes

            with path.open("rb") as f:
                head_chunk = f.read(head_bytes)

                if size > tail_bytes:
                    f.seek(-tail_bytes, os.SEEK_END)
                tail_chunk = f.read(tail_bytes)

            text = (
                head_chunk.decode("utf-8", errors="replace")
                + "\n\n... [TRUNCATED: middle omitted] ...\n\n"
                + tail_chunk.decode("utf-8", errors="replace")
            )
    except Exception:
        return None

    if redact:
        text = _redact(text)

    return ReadResult(text=text, truncated=truncated, size_bytes=size, sha256_12=sha12)


def detect_lang(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".py":
        return "python"
    if ext == ".sh":
        return "bash"
    if ext in (".md", ".markdown"):
        return "markdown"
    if ext == ".ini":
        # your settings.ini is TOML-like; keep toml fence for readability
        return "toml"
    if ext == ".json":
        return "json"
    if ext in (".yml", ".yaml"):
        return "yaml"

    # no/unknown ext: try shebang
    try:
        first = path.open("r", encoding="utf-8", errors="replace").readline()
    except Exception:
        return ""
    if first.startswith("#!"):
        if "python" in first:
            return "python"
        if "bash" in first or "sh" in first:
            return "bash"
    return ""


def generate_tree(
    root: Path,
    ignore_files: set[str],
    ignore_globs: Sequence[str],
) -> str:
    lines: List[str] = []

    def walk(dir_path: Path, prefix: str = "") -> None:
        try:
            entries = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            lines.append(f"{prefix}└── [Permission Denied]")
            return

        filtered: List[Path] = []
        for p in entries:
            if p.name in IGNORE_DIRS:
                continue
            if should_ignore(p, ignore_files, ignore_globs):
                continue
            filtered.append(p)

        for i, p in enumerate(filtered):
            pointer = "└── " if i == len(filtered) - 1 else "├── "
            lines.append(f"{prefix}{pointer}{p.name}")
            if p.is_dir():
                extension = "    " if pointer == "└── " else "│   "
                walk(p, prefix + extension)

    walk(root, "")
    return "\n".join(lines)


def render_project_status(status_path: Path) -> str:
    if not status_path.exists():
        return "No project status file found."

    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        return "Error reading project status."

    out: List[str] = []

    guidelines = data.get("guidelines") or []
    if guidelines:
        out.append("DEV MANIFESTO:")
        for rule in guidelines:
            out.append(f"* {rule}")
        out.append("-" * 20)

    objective = data.get("objective")
    if objective is not None:
        out.append(f"OBJECTIVE: {objective}")

    tasks = data.get("tasks") or []
    if tasks:
        done = sum(1 for t in tasks if t.get("status") == "done")
        out.append(f"\nTASKS: ({done}/{len(tasks)} done)")
        for i, t in enumerate(tasks, start=1):
            status = t.get("status", "todo")
            mark = "[x]" if status == "done" else "[ ]"
            desc = t.get("desc", "")
            out.append(f"{i}. {mark} {desc}")

    return "\n".join(out).rstrip()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Wagstaff-Lab project snapshot.")
    parser.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output file path (absolute or relative to project root). Default: project_context.txt",
    )
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=200_000,
        help="Max bytes to include per file. Larger files are head/tail truncated.",
    )
    parser.add_argument(
        "--max-total-bytes",
        type=int,
        default=2_000_000,
        help="Soft cap for total embedded source bytes (prevents exploding snapshots).",
    )
    parser.add_argument(
        "--no-redact",
        action="store_true",
        help="Disable basic secret redaction (NOT recommended).",
    )
    parser.add_argument(
        "--no-reports",
        action="store_true",
        help="Exclude data/reports/**/* from snapshot.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    ignore_files = set(DEFAULT_IGNORE_FILES) | {output_path.name}
    ignore_globs = list(DEFAULT_IGNORE_GLOBS)
    include_globs = list(DEFAULT_INCLUDE_GLOBS)

    print("📸 Generating Wagstaff-Lab snapshot...")

    report: List[str] = []
    report.append("# Wagstaff-Lab Project Snapshot")

    report.append("\n## 1. Environment Diagnostics")
    report.append("```yaml")
    report.append(get_system_fingerprint())
    report.append("-" * 20)
    report.append(get_git_status())
    report.append("```")

    report.append("\n## 2. Project Structure")
    report.append("```text")
    report.append(generate_tree(PROJECT_ROOT, ignore_files=ignore_files, ignore_globs=ignore_globs))
    report.append("```")

    report.append("\n## 3. Source Code")
    files = collect_files(
        include_globs=include_globs,
        ignore_files=ignore_files,
        ignore_globs=ignore_globs,
        include_reports=not args.no_reports,
        output_file=output_path,
    )

    total_embedded = 0
    included = 0
    truncated = 0
    skipped = 0

    for p in files:
        rr = read_file_snippet(p, max_file_bytes=args.max_file_bytes, redact=not args.no_redact)
        if rr is None:
            skipped += 1
            continue

        payload_bytes = len(rr.text.encode("utf-8", errors="replace"))
        if total_embedded + payload_bytes > args.max_total_bytes:
            report.append("\n> [SNAPSHOT LIMIT] Reached --max-total-bytes; remaining files skipped.")
            break

        rel = p.relative_to(PROJECT_ROOT).as_posix()
        report.append(f"\n### File: {rel}")
        report.append(f"> size={rr.size_bytes}B, sha256={rr.sha256_12}" + (" (TRUNCATED)" if rr.truncated else ""))
        lang = detect_lang(p)
        report.append(f"```{lang}".rstrip())
        report.append(rr.text)
        report.append("```")

        included += 1
        if rr.truncated:
            truncated += 1
        total_embedded += payload_bytes

    report.append("\n## 4. Snapshot Summary")
    report.append("```text")
    report.append(f"Included files: {included}")
    report.append(f"Truncated files: {truncated}")
    report.append(f"Skipped (binary/unreadable): {skipped}")
    report.append(f"Embedded text bytes: {total_embedded}")
    report.append("```")

    report.append("\n## 5. Project Context (Auto-Generated)")
    report.append("```text")
    report.append(render_project_status(PROJECT_ROOT / "PROJECT_STATUS.json"))
    report.append("```")

    output_path.write_text("\n".join(report), encoding="utf-8")
    print(f"✅ Snapshot written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
